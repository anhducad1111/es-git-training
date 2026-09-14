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


def _compute_bearing_deg(X: float, Z: float) -> float:
    """LOS angle from ego to target in degrees. 0 = straight ahead, + = right."""
    return math.degrees(math.atan2(X, Z))


@dataclass(frozen=True)
class DetectionResult:
    yaw_deg: float | None
    dist_m: float | None
    bearing_deg: float | None  # LOS angle from ego to target (degrees). Distinct from yaw_deg (target heading).
    confidence: float
    bbox: tuple[int, int, int, int] | None  # (x, y, w, h)
    frame_w: int
    frame_h: int
    timestamp: float  # time.time()


class PoseInference:
    def __init__(self, model_dir: Path, weights_path: Path, confidence: float = 0.35,
                 max_coast_sec: float = 1.0, gimbal_provider: GimbalProvider | None = None,
                 log_callback=None) -> None:
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
            else:
                print(f"[POSE] keypoints invalid: shape={candidate.shape} max_x={candidate[:, 0].max()}")
        else:
            print(f"[POSE] no keypoints in result (boxes={len(result.boxes)})")

        pose = None
        if keypoints is not None and self._ground is not None:
            pose = self._ground.pose(keypoints[0], keypoints[1], keypoints[2])
            if pose is None:
                print(f"[POSE] Ground.pose() returned None for kps={keypoints.tolist()}")
        elif keypoints is None:
            print(f"[POSE] skipped Ground.pose: keypoints=None ground={'ok' if self._ground else 'None'}")

        pose, position_confidence = self._apply_gimbal_compensation(pose)

        dist_aruco = None
        if self._use_aruco_dist:
            marker = self._aruco(frame)
            if marker is not None:
                dist_aruco = marker["dist_m"]

        if pose is not None:
            dist_fused = fuse_distance(pose["dist_m"], dist_aruco, self._sigma_ground, self._sigma_aruco)
            if dist_fused is not None:
                # Rescale the floor-plane (X, Z) to the fused distance while
                # keeping the direction (and hence yaw) from Ground.pose()
                # (already rotated into robot frame by _apply_gimbal_compensation).
                scale = dist_fused / pose["dist_m"] if pose["dist_m"] > 1e-9 else 1.0
                if self._kalman.is_initialized():
                    self._kalman.predict(dt)
                self._kalman.update(x=pose["X"] * scale, z=pose["Z"] * scale, yaw_deg=pose["yaw_deg"],
                                     position_confidence=position_confidence)
                state = self._kalman.state
                bearing_deg = _compute_bearing_deg(state["X"], state["Z"])
                return DetectionResult(
                    yaw_deg=state["yaw_deg"], dist_m=state["dist_m"], bearing_deg=bearing_deg,
                    confidence=score, bbox=bbox, frame_w=w, frame_h=h, timestamp=now,
                )

        return self._coast_or_empty(dt, w, h, now, bbox=bbox, score=score)

    def _apply_gimbal_compensation(self, pose: dict | None) -> tuple[dict | None, float]:
        """Returns (pose_in_robot_frame_or_None, position_confidence).

        When the gimbal_provider is set:
        - If tilt is within calibration range: rotate pose into robot frame, full confidence when settled
        - If tilt is outside calibration range but gimbal is settled: return unrotated pose with low confidence
        - If tilt is outside calibration range and gimbal is moving: return None (reject observation)
        """
        if pose is None or self._gimbal_provider is None:
            return pose, 1.0
        pan_deg, tilt_deg, is_settled = self._gimbal_provider()
        if is_tilt_within_calibration_range(tilt_deg, self._calibration_tilt_deg, self._tilt_max_deviation_deg):
            camera_left_rotation_deg = pan_deg - self._gimbal_center_pan_deg
            rotated = rotate_pose_to_robot_frame(pose["X"], pose["Z"], pose["yaw_deg"], camera_left_rotation_deg)
            rotated["dist_m"] = pose["dist_m"]
            return rotated, (1.0 if is_settled else 0.05)
        if is_settled:
            return pose, 0.3
        return None, 1.0

    def _coast_or_empty(self, dt: float, w: int, h: int, now: float,
                         bbox: tuple | None = None, score: float = 0.0) -> DetectionResult:
        if self._kalman.is_initialized():
            self._kalman.predict(dt)
            if not self._kalman.is_stale(self._max_coast_sec):
                state = self._kalman.state
                coast_ratio = self._kalman.coast_seconds() / self._max_coast_sec
                decayed_confidence = max(0.0, score if score else (1.0 - coast_ratio))
                bearing_deg = _compute_bearing_deg(state["X"], state["Z"])
                return DetectionResult(
                    yaw_deg=state["yaw_deg"], dist_m=state["dist_m"], bearing_deg=bearing_deg,
                    confidence=decayed_confidence, bbox=bbox, frame_w=w, frame_h=h, timestamp=now,
                )
        return DetectionResult(
            yaw_deg=None, dist_m=None, bearing_deg=None, confidence=score,
            bbox=bbox, frame_w=w, frame_h=h, timestamp=now,
        )
