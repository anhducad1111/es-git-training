import pytest

from rccar_pose_inference.gimbal_transform import (
    is_tilt_within_calibration_range,
    rotate_pose_to_robot_frame,
)


def test_zero_rotation_is_identity():
    result = rotate_pose_to_robot_frame(X=0.2, Z=1.0, yaw_deg=10.0, camera_left_rotation_deg=0.0)
    assert result["X"] == pytest.approx(0.2, abs=1e-6)
    assert result["Z"] == pytest.approx(1.0, abs=1e-6)
    assert result["yaw_deg"] == pytest.approx(10.0, abs=1e-6)


def test_camera_turned_left_90_maps_camera_forward_to_robot_left():
    # If the camera is turned 90 degrees to its own left of chassis-forward,
    # what the camera sees as "straight ahead" (X=0, Z=1) is, from the
    # robot's own frame, straight to its left (X=-1, Z=0).
    result = rotate_pose_to_robot_frame(X=0.0, Z=1.0, yaw_deg=0.0, camera_left_rotation_deg=90.0)
    assert result["X"] == pytest.approx(-1.0, abs=1e-6)
    assert result["Z"] == pytest.approx(0.0, abs=1e-6)


def test_camera_turned_left_90_maps_camera_right_to_robot_forward():
    # What the camera sees as its own right (X=1, Z=0), with the camera
    # turned 90 degrees left, is the robot's straight-ahead (X=0, Z=1).
    result = rotate_pose_to_robot_frame(X=1.0, Z=0.0, yaw_deg=0.0, camera_left_rotation_deg=90.0)
    assert result["X"] == pytest.approx(0.0, abs=1e-6)
    assert result["Z"] == pytest.approx(1.0, abs=1e-6)


def test_yaw_shifts_opposite_the_camera_rotation():
    # A camera-frame yaw is measured from the camera's own forward axis; if
    # the camera itself has turned left by theta, the same real-world
    # heading now reads theta *less* in camera-relative terms, so it must be
    # corrected by subtracting theta to land back in the robot frame.
    result = rotate_pose_to_robot_frame(X=0.0, Z=1.0, yaw_deg=170.0, camera_left_rotation_deg=30.0)
    assert result["yaw_deg"] == pytest.approx(140.0, abs=1e-6)  # 170 - 30


def test_yaw_wraps_across_the_180_boundary():
    # camera turned 30 degrees right (negative left-rotation) -> 170-(-30)=200, wraps to -160.
    result = rotate_pose_to_robot_frame(X=0.0, Z=1.0, yaw_deg=170.0, camera_left_rotation_deg=-30.0)
    assert result["yaw_deg"] == pytest.approx(-160.0, abs=1e-6)


def test_is_tilt_within_calibration_range():
    assert is_tilt_within_calibration_range(current_tilt_deg=70.0, calibration_tilt_deg=70.0, max_deviation_deg=10.0) is True
    assert is_tilt_within_calibration_range(current_tilt_deg=79.0, calibration_tilt_deg=70.0, max_deviation_deg=10.0) is True
    assert is_tilt_within_calibration_range(current_tilt_deg=81.0, calibration_tilt_deg=70.0, max_deviation_deg=10.0) is False
    assert is_tilt_within_calibration_range(current_tilt_deg=59.0, calibration_tilt_deg=70.0, max_deviation_deg=10.0) is False
