"""Self-contained RC-car pose inference module for follow-mode control.

Import PoseInference (and DetectionResult, the value it returns) directly
from this package: `from rccar_pose_inference import PoseInference, DetectionResult`.
See README.md in this directory for the integration contract and what's left
to wire up in the main app.
"""
from .pose_inference import DetectionResult, PoseInference
from .pose_kalman import PoseKalmanFilter
from .pose_fusion import fuse_distance
from .gimbal_transform import is_tilt_within_calibration_range, rotate_pose_to_robot_frame

__all__ = [
    "PoseInference",
    "DetectionResult",
    "PoseKalmanFilter",
    "fuse_distance",
    "is_tilt_within_calibration_range",
    "rotate_pose_to_robot_frame",
]
