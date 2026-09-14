"""Camera-relative <-> robot-chassis-relative floor-plane coordinate
conversion, and a tilt-based trust gate for the Ground floor-plane model.

See docs/superpowers/specs/2026-09-11-gimbal-pose-compensation-design.md.

IMPORTANT (sign convention): camera_left_rotation_deg's sign has NOT been
verified against physical hardware. See that spec's "符号規約の注意" section
and docs/superpowers/plans/2026-09-11-gimbal-pose-compensation.md Task 6
Step 4 for the required on-robot verification procedure before relying on
this for closed-loop control.
"""
from __future__ import annotations

import math


def rotate_pose_to_robot_frame(X: float, Z: float, yaw_deg: float, camera_left_rotation_deg: float) -> dict:
    """Rotates a camera-relative floor-plane (X, Z, yaw) into robot-chassis-
    relative coordinates, given how far the camera has rotated to ITS OWN
    left of chassis-forward (camera_left_rotation_deg; 0 = camera facing
    straight ahead of the chassis). Returns {'X': float, 'Z': float,
    'yaw_deg': float}."""
    theta = math.radians(camera_left_rotation_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    robot_x = X * cos_t - Z * sin_t
    robot_z = X * sin_t + Z * cos_t
    robot_yaw = (yaw_deg - camera_left_rotation_deg + 180.0) % 360.0 - 180.0
    return {"X": robot_x, "Z": robot_z, "yaw_deg": robot_yaw}


def is_tilt_within_calibration_range(current_tilt_deg: float, calibration_tilt_deg: float, max_deviation_deg: float) -> bool:
    """Whether the current tilt is close enough to the angle Ground's floor-
    plane projection constants were calibrated at (A, v0, fx, cu) for its
    distance/position estimate to be trusted at all."""
    return abs(current_tilt_deg - calibration_tilt_deg) <= max_deviation_deg
