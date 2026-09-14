from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from .detectors import Detection


@dataclass(frozen=True)
class MarkerPose:
    x_m: float
    y_m: float
    z_m: float
    distance_m: float
    yaw_deg: float
    rvec: np.ndarray
    tvec: np.ndarray


def yaw_deg_from_rvec(rvec: np.ndarray) -> float:
    """Marker rotation about the vertical (camera-Y) axis, in degrees: how far
    the marker/vehicle is turned left/right relative to facing the camera."""
    rotation_matrix, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64))
    angles, *_ = cv2.RQDecomp3x3(rotation_matrix)
    return float(angles[1])


def marker_pose_from_corners(
    corners: np.ndarray,
    marker_size: float,
    camera_matrix: np.ndarray,
    distortion: np.ndarray,
) -> MarkerPose | None:
    points = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
    if points.shape != (4, 2) or marker_size <= 0:
        return None
    half = marker_size / 2.0
    object_points = np.array(
        [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
        dtype=np.float32,
    )
    ok, rvec, tvec = cv2.solvePnP(
        object_points, points, np.asarray(camera_matrix), np.asarray(distortion), flags=cv2.SOLVEPNP_IPPE_SQUARE
    )
    if not ok:
        return None
    xyz = tvec.reshape(3).astype(float)
    return MarkerPose(
        float(xyz[0]), float(xyz[1]), float(xyz[2]), float(np.linalg.norm(xyz)), yaw_deg_from_rvec(rvec), rvec, tvec
    )


@dataclass(frozen=True)
class MarkerTrackResult:
    status: str  # "single" | "none" | "multiple" | "uncalibrated"
    label: str | None = None
    pose: MarkerPose | None = None
    stale: bool = False
    count: int = 0


class MarkerTracker:
    """Bridges brief single-marker detection gaps (motion blur, a dropped
    frame) by holding the last known pose for a short window instead of
    reporting "lost" on every missed frame. Also the seam a future
    detect-and-follow control loop would read a smoothed pose from."""

    def __init__(self, hold_seconds: float = 0.3) -> None:
        self.hold_seconds = hold_seconds
        self._last: tuple[str, MarkerPose, float] | None = None

    def update(self, detection: "Detection | None", now: float) -> MarkerTrackResult:
        if detection is not None and detection.boxes:
            labeled_poses = [
                (label, pose) for label, pose in zip(detection.labels, detection.poses) if pose is not None
            ]
            if len(labeled_poses) > 1:
                self._last = None
                return MarkerTrackResult(status="multiple", count=len(labeled_poses))
            if len(labeled_poses) == 1:
                label, pose = labeled_poses[0]
                self._last = (label, pose, now)
                return MarkerTrackResult(status="single", label=label, pose=pose, stale=False)
            return MarkerTrackResult(status="uncalibrated")
        return self._held_or_none(now)

    def _held_or_none(self, now: float) -> MarkerTrackResult:
        if self._last is not None:
            label, pose, seen_at = self._last
            if now - seen_at <= self.hold_seconds:
                return MarkerTrackResult(status="single", label=label, pose=pose, stale=True)
            self._last = None
        return MarkerTrackResult(status="none")


def draw_pose(frame: np.ndarray, corners: np.ndarray, pose: MarkerPose, camera_matrix: np.ndarray, distortion: np.ndarray) -> None:
    points = np.asarray(corners, dtype=np.float32).reshape(1, 4, 2)
    cv2.polylines(frame, [points.astype(np.int32)], True, (0, 220, 80), 2)
    cv2.drawFrameAxes(frame, camera_matrix, distortion, pose.rvec, pose.tvec, 0.04, 2)
