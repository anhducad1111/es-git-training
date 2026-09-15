"""Camera-relative <-> robot-chassis-relative floor-plane coordinate
conversion, and tilt-dependent Ground floor-plane parameters/trust gating.

See docs/superpowers/specs/2026-09-11-gimbal-pose-compensation-design.md and
captures/rccar_pose/チルト較正手順.md (how tilt_curve is built and stored in
config.json).

IMPORTANT (sign convention): camera_left_rotation_deg's sign has NOT been
verified against physical hardware. See that spec's "符号規約の注意" section
and docs/superpowers/plans/2026-09-11-gimbal-pose-compensation.md Task 6
Step 4 for the required on-robot verification procedure before relying on
this for closed-loop control.
"""
from __future__ import annotations

import math

import numpy as np


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
    distance/position estimate to be trusted at all.

    Only used as a fallback when config.json has no `tilt_curve` (single-
    angle calibration). When `tilt_curve` is present, ground_params_for_tilt
    below replaces this coarse gate with a continuous per-tilt correction."""
    return abs(current_tilt_deg - calibration_tilt_deg) <= max_deviation_deg


def ground_params_for_tilt(tilt_curve: dict, current_tilt_deg: float, extrapolation_margin_deg: float) -> dict | None:
    """Evaluates the tilt_curve (built by captures/rccar_pose/tools/calib_tilt.py,
    see チルト較正手順.md) at current_tilt_deg to get the floor-plane
    projection constants (A, v0, fx) valid at that tilt.

    Returns None when current_tilt_deg is more than extrapolation_margin_deg
    outside the calibrated tilt_deg_range -- beyond that, the polynomial fit
    is extrapolating too far to be trusted, and the caller should fall back
    to not trusting Ground's distance/position estimate this frame at all
    (same as being outside is_tilt_within_calibration_range's range)."""
    range_min, range_max = tilt_curve["tilt_deg_range"]
    if current_tilt_deg < range_min - extrapolation_margin_deg or current_tilt_deg > range_max + extrapolation_margin_deg:
        return None
    A = float(np.polyval(tilt_curve["A_coeffs"], current_tilt_deg))
    v0 = float(np.polyval(tilt_curve["v0_coeffs"], current_tilt_deg))
    fx = float(tilt_curve["fx"])
    return {"A": A, "v0": v0, "fx": fx}
