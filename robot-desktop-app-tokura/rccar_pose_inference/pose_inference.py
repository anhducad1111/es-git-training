"""Standalone pose inference module: wraps YOLOv8-pose keypoint detection ->
Ground floor-plane projection -> yaw/distance, refined with confidence-
weighted ArUco distance fusion, Kalman-filter temporal smoothing, and (when a
gimbal_provider is supplied) camera-to-robot-frame rotation + tilt/motion
trust gating. Runs in-process; no separate service/API by design.

See:
- docs/superpowers/specs/2026-09-11-pose-inference-service-handoff.md
- docs/superpowers/plans/2026-09-11-pose-inference-module.md
- docs/superpowers/specs/2026-09-11-gimbal-pose-compensation-design.md
- docs/superpowers/plans/2026-09-11-gimbal-pose-compensation.md
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .gimbal_transform import is_tilt_within_calibration_range, rotate_pose_to_robot_frame
from .pose_fusion import fuse_distance
from .pose_kalman import PoseKalmanFilter
from .rccar_pose_model.geometry import Aruco as RcCarAruco
from .rccar_pose_model.geometry import Ground as RcCarGround

# (pan_deg, tilt_deg, is_settled) using the gimbal's own commanded angles --
# not real servo feedback (none is available). See GimbalThread.get_pan_tilt_state
# in the main app's follow_controller.py.
GimbalProvider = Callable[[], tuple[float, float, bool]]


@dataclass(frozen=True)
class DetectionResult:
    yaw_deg: float | None
    dist_m: float | None
    confidence: float
    bbox: tuple[int, int, int, int] | None  # (x, y, w, h)
    frame_w: int
    frame_h: int
    timestamp: float  # time.time()
    # atan2(X, Z) of the CAMERA-relative floor-plane pose (computed before any
    # gimbal_provider robot-frame rotation) -- how many degrees the camera's
    # current boresight is off from the target, positive = target to the
    # right. For aiming the gimbal itself, not the robot-frame yaw_deg above.
    # None whenever Ground.pose() didn't succeed this frame (e.g. far range,
    # missing keypoints) -- callers should fall back to a pixel-based
    # estimate in that case.
    bearing_deg: float | None = None
    # Kalman-filter velocity estimate (robot-frame X=right, Z=forward), m/s.
    # None until the filter has been updated at least once.
    vx_mps: float | None = None
    vz_mps: float | None = None
    # dist_m projected `prediction_time_sec` into the future using vx_mps/
    # vz_mps (constant-velocity extrapolation), so callers can react to a
    # closing/opening lead car before the raw distance measurement catches
    # up. None whenever velocity isn't available yet (same conditions as
    # vx_mps/vz_mps above).
    dist_m_predicted: float | None = None


class PoseInference:
    def __init__(self, model_dir: Path, weights_path: Path, confidence: float = 0.35,
                 max_coast_sec: float = 1.0, gimbal_provider: GimbalProvider | None = None) -> None:
        model_dir = Path(model_dir)
        weights_path = Path(weights_path)
        if not weights_path.is_file():
            raise FileNotFoundError(f"trained rccar_pose model not found: {weights_path}")

        config_path = model_dir / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}

        self._ground = RcCarGround(config["ground"]) if "ground" in config else None
        self._aruco = RcCarAruco(config)
        self._use_aruco_dist = bool(config.get("use_aruco_dist", True))
        self._sigma_ground = float(config.get("sigma_ground_m", 0.05))
        self._sigma_aruco = float(config.get("sigma_aruco_m", 0.02))
        self._max_coast_sec = float(config.get("max_coast_sec", max_coast_sec))
        yaw_snap_threshold_deg = float(config.get("yaw_snap_threshold_deg", 90.0))
        # この速さ(m/s)を超える距離変化はセンサー/推論の外れ値とみなし、
        # ほぼ無視する(position_confidenceを下げる)。この小さいRCカーの
        # 実速度に対して十分余裕を持たせた初期値であり、実車で調整してよい
        self._max_plausible_speed_mps = float(config.get("max_plausible_speed_mps", 2.0))
        # Phase 6 (future position prediction): how far ahead to project the
        # target's position using the Kalman filter's velocity estimate.
        # Configurable per docs/APP_TECHNICAL.md; set to 0.0 to disable
        # (dist_m_predicted will then equal the current dist_m).
        self._prediction_time_sec = float(config.get("prediction_time_sec", 0.5))

        # Gimbal compensation (docs/superpowers/specs/2026-09-11-gimbal-pose-compensation-design.md).
        # gimbal_provider=None (default) disables all of this -- fixed-camera
        # callers behave exactly as before.
        self._calibration_tilt_deg = float(config.get("calibration_tilt_deg", 70.0))
        self._tilt_max_deviation_deg = float(config.get("tilt_max_deviation_deg", 10.0))
        self._gimbal_center_pan_deg = float(config.get("gimbal_center_pan_deg", 90.0))
        self._gimbal_provider = gimbal_provider

        from ultralytics import YOLO

        self._model = YOLO(str(weights_path))
        self._confidence = confidence
        self._kalman = PoseKalmanFilter(yaw_snap_threshold_deg=yaw_snap_threshold_deg)
        self._last_infer_time: float | None = None

    def infer(self, frame: np.ndarray) -> DetectionResult:
        now = time.time()
        dt = (now - self._last_infer_time) if self._last_infer_time is not None else 0.1
        self._last_infer_time = now
        h, w = frame.shape[:2]

        result = self._model.predict(frame, conf=self._confidence, verbose=False)[0]
        if not len(result.boxes):
            return self._coast_or_empty(dt, w, h, now)

        best = int(result.boxes.conf.argmax())
        x1, y1, x2, y2 = result.boxes.xyxy[best].tolist()
        score = float(result.boxes.conf[best])
        bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))

        keypoints = None
        if result.keypoints is not None:
            candidate = np.asarray(result.keypoints.xy[best])
            if candidate.shape[0] >= 3 and candidate[:, 0].max() > 0:
                keypoints = candidate[:3]

        pose = None
        if keypoints is not None and self._ground is not None:
            pose = self._ground.pose(keypoints[0], keypoints[1], keypoints[2])

        # ジンバルのロボット相対回転をかける前の、カメラ視点そのままのbearing。
        # これがそのままカメラを何度振れば正面に来るかの答えになる(三平方の定理/
        # atan2(X, Z))。_apply_gimbal_compensationはposeのX/Zをロボット相対に
        # 回転してしまうので、その前に控えておく。
        bearing_deg = math.degrees(math.atan2(pose["X"], pose["Z"])) if pose is not None else None

        pose, position_confidence = self._apply_gimbal_compensation(pose)

        dist_aruco = None
        if self._use_aruco_dist:
            marker = self._aruco(frame)
            if marker is not None:
                dist_aruco = marker["dist_m"]

        if pose is not None:
            dist_fused = fuse_distance(pose["dist_m"], dist_aruco, self._sigma_ground, self._sigma_aruco)
            if dist_fused is not None:
                # 起動直後などカメラ・推論が安定する前の1フレームだけ極端に
                # おかしい観測(距離が物理的にありえない速さで変化)が来ると、
                # カルマンフィルタがそれを本当の速度として学習してしまい、
                # その後のcoast(predict)で「急接近しているかのような」誤った
                # 値を出し続けることが実機で確認された(yaw_snap_threshold_degは
                # 向きの反転を許容するためのものでこの種の外れ値は防げない)。
                # 直前の推定距離との差分から implied速度を求め、明らかに
                # 車体の実速度を超える場合はこの観測をほぼ信用しない
                # (position_confidenceを下げる、ジンバル未安定時と同じ仕組み)。
                if self._kalman.is_initialized() and dt > 1e-6:
                    implied_speed_mps = abs(dist_fused - self._kalman.state["dist_m"]) / dt
                    if implied_speed_mps > self._max_plausible_speed_mps:
                        position_confidence = min(position_confidence, 0.05)
                # Rescale the floor-plane (X, Z) to the fused distance while
                # keeping the direction (and hence yaw) from Ground.pose()
                # (already rotated into robot frame by _apply_gimbal_compensation).
                scale = dist_fused / pose["dist_m"] if pose["dist_m"] > 1e-9 else 1.0
                if self._kalman.is_initialized():
                    self._kalman.predict(dt)
                self._kalman.update(x=pose["X"] * scale, z=pose["Z"] * scale, yaw_deg=pose["yaw_deg"],
                                     position_confidence=position_confidence)
                state = self._kalman.state
                return DetectionResult(
                    yaw_deg=state["yaw_deg"], dist_m=state["dist_m"], confidence=score,
                    bbox=bbox, frame_w=w, frame_h=h, timestamp=now, bearing_deg=bearing_deg,
                    vx_mps=state["vx_mps"], vz_mps=state["vz_mps"],
                    dist_m_predicted=self._predict_dist_m(state),
                )

        return self._coast_or_empty(dt, w, h, now, bbox=bbox, score=score)

    def _predict_dist_m(self, state: dict) -> float:
        """Constant-velocity projection of dist_m `self._prediction_time_sec`
        seconds ahead, per docs/APP_TECHNICAL.md Phase 6 (future position
        prediction): future_position = current_position + velocity * t."""
        pred_x = state["X"] + state["vx_mps"] * self._prediction_time_sec
        pred_z = state["Z"] + state["vz_mps"] * self._prediction_time_sec
        return math.hypot(pred_x, pred_z)

    def _apply_gimbal_compensation(self, pose: dict | None) -> tuple[dict | None, float]:
        """Returns (pose_in_robot_frame_or_None, position_confidence).

        pose_in_robot_frame_or_None is None when the current tilt is too far
        from the calibration angle to trust Ground's floor-plane projection
        at all this frame (falls through to coasting on the Kalman filter's
        prediction, same as a missed detection).

        position_confidence is 1.0 normally, or a small value while the
        gimbal hasn't settled after a pan/tilt move -- see
        PoseKalmanFilter.update()'s position_confidence parameter.
        """
        if pose is None or self._gimbal_provider is None:
            return pose, 1.0
        pan_deg, tilt_deg, is_settled = self._gimbal_provider()
        if not is_tilt_within_calibration_range(tilt_deg, self._calibration_tilt_deg, self._tilt_max_deviation_deg):
            return None, 1.0
        camera_left_rotation_deg = pan_deg - self._gimbal_center_pan_deg
        rotated = rotate_pose_to_robot_frame(pose["X"], pose["Z"], pose["yaw_deg"], camera_left_rotation_deg)
        rotated["dist_m"] = pose["dist_m"]  # distance magnitude is rotation-invariant
        return rotated, (1.0 if is_settled else 0.05)

    def _coast_or_empty(self, dt: float, w: int, h: int, now: float,
                         bbox: tuple | None = None, score: float = 0.0) -> DetectionResult:
        if self._kalman.is_initialized():
            self._kalman.predict(dt)
            if not self._kalman.is_stale(self._max_coast_sec):
                state = self._kalman.state
                coast_ratio = self._kalman.coast_seconds() / self._max_coast_sec
                decayed_confidence = max(0.0, score if score else (1.0 - coast_ratio))
                return DetectionResult(
                    yaw_deg=state["yaw_deg"], dist_m=state["dist_m"], confidence=decayed_confidence,
                    bbox=bbox, frame_w=w, frame_h=h, timestamp=now,
                    vx_mps=state["vx_mps"], vz_mps=state["vz_mps"],
                    dist_m_predicted=self._predict_dist_m(state),
                )
        return DetectionResult(
            yaw_deg=None, dist_m=None, confidence=score, bbox=bbox, frame_w=w, frame_h=h, timestamp=now,
        )
