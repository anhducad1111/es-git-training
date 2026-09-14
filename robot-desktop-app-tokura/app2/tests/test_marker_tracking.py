import cv2
import numpy as np

from esp32_mjpeg_detector.detectors import Detection
from esp32_mjpeg_detector.marker_tracking import MarkerPose, MarkerTracker, marker_pose_from_corners, yaw_deg_from_rvec


def test_marker_pose_returns_distance_in_marker_length_units():
    camera = np.array([[500.0, 0.0, 320.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]])
    corners_3d = np.array([[-0.05, 0.05, 0], [0.05, 0.05, 0], [0.05, -0.05, 0], [-0.05, -0.05, 0]], dtype=np.float32)
    projected, _ = cv2.projectPoints(corners_3d, np.zeros(3), np.array([0.0, 0.0, 1.0]), camera, np.zeros(5))

    pose = marker_pose_from_corners(projected.reshape(4, 2), marker_size=0.1, camera_matrix=camera, distortion=np.zeros(5))

    assert pose is not None
    assert abs(pose.distance_m - 1.0) < 0.03
    assert abs(pose.x_m) < 0.03


def test_marker_pose_rejects_incomplete_corners():
    assert marker_pose_from_corners(np.zeros((3, 2)), 0.1, np.eye(3), np.zeros(5)) is None


def test_marker_pose_includes_yaw_degrees():
    camera = np.array([[500.0, 0.0, 320.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]])
    corners_3d = np.array([[-0.05, 0.05, 0], [0.05, 0.05, 0], [0.05, -0.05, 0], [-0.05, -0.05, 0]], dtype=np.float32)
    projected, _ = cv2.projectPoints(corners_3d, np.zeros(3), np.array([0.0, 0.0, 1.0]), camera, np.zeros(5))

    pose = marker_pose_from_corners(projected.reshape(4, 2), marker_size=0.1, camera_matrix=camera, distortion=np.zeros(5))

    assert pose is not None
    assert abs(pose.yaw_deg) < 3.0  # marker faces the camera head-on -> ~0 deg


def test_yaw_deg_from_rvec_matches_known_y_axis_rotation():
    rvec = np.array([0.0, np.deg2rad(30.0), 0.0])

    assert abs(yaw_deg_from_rvec(rvec) - 30.0) < 1e-6


def _pose(distance: float = 0.4) -> MarkerPose:
    return MarkerPose(x_m=0.1, y_m=0.2, z_m=distance, distance_m=distance, yaw_deg=5.0, rvec=None, tvec=None)


def test_marker_tracker_reports_none_when_nothing_ever_seen():
    tracker = MarkerTracker(hold_seconds=0.3)

    result = tracker.update(Detection([], [], []), now=0.0)

    assert result.status == "none"


def test_marker_tracker_reports_single_marker_immediately():
    tracker = MarkerTracker(hold_seconds=0.3)
    detection = Detection([(0, 0, 1, 1)], ["marker 0"], [1.0], [_pose()])

    result = tracker.update(detection, now=0.0)

    assert result.status == "single"
    assert result.label == "marker 0"
    assert result.pose.distance_m == 0.4
    assert result.stale is False


def test_marker_tracker_holds_last_pose_within_hold_window_after_a_miss():
    tracker = MarkerTracker(hold_seconds=0.3)
    detection = Detection([(0, 0, 1, 1)], ["marker 0"], [1.0], [_pose()])
    tracker.update(detection, now=0.0)

    result = tracker.update(Detection([], [], []), now=0.2)

    assert result.status == "single"
    assert result.stale is True
    assert result.pose.distance_m == 0.4


def test_marker_tracker_reports_none_after_hold_window_expires():
    tracker = MarkerTracker(hold_seconds=0.3)
    detection = Detection([(0, 0, 1, 1)], ["marker 0"], [1.0], [_pose()])
    tracker.update(detection, now=0.0)

    result = tracker.update(Detection([], [], []), now=0.31)

    assert result.status == "none"


def test_marker_tracker_reports_multiple_and_drops_held_state():
    tracker = MarkerTracker(hold_seconds=0.3)
    single = Detection([(0, 0, 1, 1)], ["marker 0"], [1.0], [_pose()])
    tracker.update(single, now=0.0)
    multi = Detection(
        [(0, 0, 1, 1), (0, 0, 1, 1)], ["marker 0", "marker 1"], [1.0, 1.0], [_pose(), _pose()]
    )

    result = tracker.update(multi, now=0.1)
    assert result.status == "multiple"
    assert result.count == 2

    after = tracker.update(Detection([], [], []), now=0.15)
    assert after.status == "none"


def test_marker_tracker_reports_uncalibrated_when_pose_missing():
    tracker = MarkerTracker(hold_seconds=0.3)
    detection = Detection([(0, 0, 1, 1)], ["marker 0"], [1.0], [None])

    result = tracker.update(detection, now=0.0)

    assert result.status == "uncalibrated"
