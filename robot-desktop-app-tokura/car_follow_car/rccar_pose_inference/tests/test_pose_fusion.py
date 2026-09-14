import pytest

from rccar_pose_inference.pose_fusion import fuse_distance


def test_fuse_returns_ground_only_when_aruco_missing():
    assert fuse_distance(dist_ground=0.5, dist_aruco=None, sigma_ground=0.05, sigma_aruco=0.02) == 0.5


def test_fuse_returns_aruco_only_when_ground_missing():
    assert fuse_distance(dist_ground=None, dist_aruco=0.45, sigma_ground=0.05, sigma_aruco=0.02) == 0.45


def test_fuse_returns_none_when_both_missing():
    assert fuse_distance(dist_ground=None, dist_aruco=None, sigma_ground=0.05, sigma_aruco=0.02) is None


def test_fuse_weights_more_accurate_sensor_higher():
    # sigma_aruco is smaller (more accurate) -> fused value should sit closer to aruco
    fused = fuse_distance(dist_ground=0.60, dist_aruco=0.40, sigma_ground=0.10, sigma_aruco=0.02)
    assert fused < 0.50  # closer to aruco's 0.40 than the midpoint 0.50
    assert fused > 0.40
