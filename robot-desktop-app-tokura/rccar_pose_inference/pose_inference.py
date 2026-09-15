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

from .gimbal_transform import ground_params_for_tilt, is_tilt_within_calibration_range, rotate_pose_to_robot_frame
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
    # dist_m_predictedと対の、prediction_time_sec先のヨー角の等角速度予測
    # (yaw_future = yaw_deg + yaw_rate_deg_s * prediction_time_sec)。
    # 条件はdist_m_predictedと同じ(速度/回転速度が未確定のうちはNone)。
    yaw_deg_predicted: float | None = None
    # True if ArUco marker was detected in this frame
    aruco_detected: bool = False


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
        # チルト較正カーブ(captures/rccar_pose/チルト較正手順.md参照)。あれば
        # 毎フレーム現在のチルト角からGroundのA/v0/fxを補正する。無ければ
        # 従来通り単一角度較正値のまま(calibration_tilt_degとの差でゲートのみ)。
        self._tilt_curve = config.get("tilt_curve")

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

        # gimbal_providerは1フレームにつき1回だけ呼ぶ(pan/tilt/is_settledを
        # ここで確定させ、Ground.pose()の前後両方でこの値を使い回す)。
        pan_deg = tilt_deg = None
        is_settled = True
        tilt_trusted = True
        if self._gimbal_provider is not None:
            pan_deg, tilt_deg, is_settled = self._gimbal_provider()
            tilt_trusted = self._update_ground_for_tilt(tilt_deg)

        pose = None
        if keypoints is not None and self._ground is not None:
            pose = self._ground.pose(keypoints[0], keypoints[1], keypoints[2])

        # ジンバルのロボット相対回転をかける前の、カメラ視点そのままのbearing。
        # これがそのままカメラを何度振れば正面に来るかの答えになる(三平方の定理/
        # atan2(X, Z))。_apply_gimbal_compensationはposeのX/Zをロボット相対に
        # 回転してしまうので、その前に控えておく。
        bearing_deg = math.degrees(math.atan2(pose["X"], pose["Z"])) if pose is not None else None

        pose, position_confidence = self._apply_gimbal_compensation(pose, pan_deg, is_settled, tilt_trusted)

        dist_aruco = None
        aruco_detected = False
        if self._use_aruco_dist:
            marker = self._aruco(frame)
            if marker is not None:
                dist_aruco = marker["dist_m"]
                aruco_detected = True

        if pose is not None:
            dist_fused = fuse_distance(pose["dist_m"], dist_aruco, self._sigma_ground, self._sigma_aruco)
            if dist_fused is not None:
                # 起動直後の1フレームだけ極端な外れ値(距離が物理的にありえない
                # 速さで変化)が来るとカルマンがそれを速度として学習し、以後の
                # coastで誤った値を出し続けることが実機で確認された。直前距離との
                # implied速度が実速度を超えたら、この観測をほぼ信用しない
                # (position_confidenceを下げる)。
                #
                # coast中(predict()のみ)はstateがドリフトし続けるため、遮蔽から
                # 再検出した直後は「正しい新観測」とこのチェックが衝突し、ヨーが
                # 戻らないバグが確認された。coast_seconds()>0(直近がcoast)の
                # ときはこのチェックを適用しない。
                if (self._kalman.is_initialized() and dt > 1e-6
                        and self._kalman.coast_seconds() < 1e-6):
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
                    yaw_deg_predicted=self._predict_yaw_deg(state),
                    aruco_detected=aruco_detected,
                )

        return self._coast_or_empty(dt, w, h, now, bbox=bbox, score=score)

    def _predict_dist_m(self, state: dict) -> float:
        """Constant-velocity projection of dist_m `self._prediction_time_sec`
        seconds ahead, per docs/APP_TECHNICAL.md Phase 6 (future position
        prediction): future_position = current_position + velocity * t."""
        pred_x = state["X"] + state["vx_mps"] * self._prediction_time_sec
        pred_z = state["Z"] + state["vz_mps"] * self._prediction_time_sec
        return math.hypot(pred_x, pred_z)

    def _predict_yaw_deg(self, state: dict) -> float:
        """Constant-turn-rate projection of yaw_deg `self._prediction_time_sec`
        seconds ahead, mirroring _predict_dist_m()'s constant-velocity distance
        projection: future_yaw = current_yaw + yaw_rate * t."""
        predicted = state["yaw_deg"] + state["yaw_rate_deg_s"] * self._prediction_time_sec
        return (predicted + 180.0) % 360.0 - 180.0

    def _update_ground_for_tilt(self, tilt_deg: float) -> bool:
        """Corrects self._ground's floor-plane constants (A, v0, fx) for the
        current gimbal tilt angle, if a tilt_curve calibration is available.

        Returns whether this frame's tilt is trustworthy at all: with a
        tilt_curve, False only when tilt_deg is too far outside the
        calibrated tilt_deg_range to extrapolate (config.json's
        tilt_max_deviation_deg doubles as the extrapolation margin here).
        Without a tilt_curve, falls back to the old single-angle gate
        (is_tilt_within_calibration_range against calibration_tilt_deg)."""
        if self._ground is None:
            return True
        if self._tilt_curve is not None:
            params = ground_params_for_tilt(self._tilt_curve, tilt_deg, self._tilt_max_deviation_deg)
            if params is None:
                return False
            self._ground.apply_floor_params(**params)
            return True
        return is_tilt_within_calibration_range(tilt_deg, self._calibration_tilt_deg, self._tilt_max_deviation_deg)

    def _apply_gimbal_compensation(self, pose: dict | None, pan_deg: float | None, is_settled: bool,
                                    tilt_trusted: bool) -> tuple[dict | None, float]:
        """Returns (pose_in_robot_frame_or_None, position_confidence).

        pose_in_robot_frame_or_None is None when tilt_trusted is False (the
        current tilt is too far from calibration to trust Ground's
        floor-plane projection at all this frame -- falls through to
        coasting on the Kalman filter's prediction, same as a missed
        detection).

        position_confidence is 1.0 normally, or a small value while the
        gimbal hasn't settled after a pan/tilt move -- see
        PoseKalmanFilter.update()'s position_confidence parameter.
        """
        if pose is None or self._gimbal_provider is None:
            return pose, 1.0
        if not tilt_trusted:
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
                    yaw_deg_predicted=self._predict_yaw_deg(state),
                )
        return DetectionResult(
            yaw_deg=None, dist_m=None, confidence=score, bbox=bbox, frame_w=w, frame_h=h, timestamp=now,
        )
