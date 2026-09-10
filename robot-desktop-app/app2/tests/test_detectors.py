import json

import cv2
import numpy as np
import pytest

from esp32_mjpeg_detector.calibration import CalibrationData
from esp32_mjpeg_detector.detectors import ArucoDetector, RcCarPoseDetector


def _frame_with_marker(marker_id: int = 0, size: int = 200, margin: int = 200) -> np.ndarray:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, size, borderBits=1)
    frame = np.full((size + 2 * margin, size + 2 * margin), 255, dtype=np.uint8)
    frame[margin : margin + size, margin : margin + size] = marker
    return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)


def test_aruco_detector_populates_pose_when_calibration_available():
    frame = _frame_with_marker()
    height, width = frame.shape[:2]
    camera_matrix = np.array([[width, 0, width / 2], [0, width, height / 2], [0, 0, 1]], dtype=np.float64)
    calibration = CalibrationData(camera_matrix, np.zeros(5), (width, height), 0.5)
    detector = ArucoDetector(marker_size_m=0.05, calibration=calibration)

    detection = detector.detect(frame)

    assert len(detection.boxes) == 1
    assert len(detection.poses) == 1
    assert detection.poses[0] is not None
    assert detection.poses[0].distance_m > 0


def test_aruco_detector_pose_is_none_without_calibration():
    frame = _frame_with_marker()
    detector = ArucoDetector(marker_size_m=0.05, calibration=None)

    detection = detector.detect(frame)

    assert detection.poses == [None]


class _FakeArray:
    """Minimal stand-in for a torch tensor: supports the .cpu().numpy() /
    .tolist() calls RcCarPoseDetector makes on ultralytics results."""

    def __init__(self, data):
        self._data = np.asarray(data)

    def __getitem__(self, index):
        return _FakeArray(self._data[index])

    def cpu(self):
        return self

    def numpy(self):
        return self._data

    def tolist(self):
        return self._data.tolist()

    def argmax(self):
        return int(self._data.argmax())

    def __float__(self):
        return float(self._data)


class _FakeKeypoints:
    def __init__(self, xy):
        self.xy = _FakeArray(xy)


class _FakeBoxes:
    def __init__(self, xyxy, conf):
        self.xyxy = _FakeArray(xyxy)
        self.conf = _FakeArray(conf)

    def __len__(self):
        return len(self.conf._data)


class _FakeResult:
    def __init__(self, boxes, keypoints=None):
        self.boxes = boxes
        self.keypoints = keypoints


def _make_model_dir(tmp_path, use_aruco_dist=True, with_ground=True):
    """Sets up a fake bundled rccar_pose_model directory: a placeholder
    weights file and config.json. Ground/Aruco geometry itself is monkeypatched
    per-test rather than exercised here (it's a plain, directly importable
    module, unlike the old sys.path-injected infer.py)."""
    weights = tmp_path / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"")
    config = {"use_aruco_dist": use_aruco_dist}
    if with_ground:
        config["ground"] = {}
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


def test_rccar_pose_detector_raises_when_weights_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        RcCarPoseDetector(model_dir=tmp_path)


def test_rccar_pose_detector_combines_keypoint_pose_and_aruco_distance(tmp_path, monkeypatch):
    model_dir = _make_model_dir(tmp_path)

    class _FakeGround:
        def __init__(self, g):
            pass

        def pose(self, L, R, F):
            return {"yaw_deg": 12.3, "dist_m": 0.5}

    class _FakeAruco:
        def __init__(self, cfg):
            pass

        def __call__(self, frame):
            return {"dist_m": 0.42}

    monkeypatch.setattr("esp32_mjpeg_detector.detectors.RcCarGround", _FakeGround)
    monkeypatch.setattr("esp32_mjpeg_detector.detectors.RcCarAruco", _FakeAruco)

    fake_result = _FakeResult(
        boxes=_FakeBoxes(xyxy=[[10.0, 20.0, 110.0, 220.0]], conf=[0.9]),
        keypoints=_FakeKeypoints(xy=[[[1, 1], [2, 2], [3, 3]]]),
    )

    class _FakeModel:
        def predict(self, frame, conf, verbose):
            return [fake_result]

    monkeypatch.setattr("ultralytics.YOLO", lambda path: _FakeModel())

    detector = RcCarPoseDetector(model_dir=model_dir)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    detection = detector.detect(frame)

    assert detection.boxes == [(10, 20, 100, 200)]
    assert detection.scores == pytest.approx([0.9])
    # ArUco distance (0.42) overrides the keypoint-derived one (0.5) when available.
    assert detection.labels == ["car yaw+12 d0.42m"]


def test_rccar_pose_detector_returns_empty_detection_when_nothing_detected(tmp_path, monkeypatch):
    model_dir = _make_model_dir(tmp_path, with_ground=False)

    fake_result = _FakeResult(boxes=_FakeBoxes(xyxy=np.empty((0, 4)), conf=np.empty(0)))

    class _FakeModel:
        def predict(self, frame, conf, verbose):
            return [fake_result]

    monkeypatch.setattr("ultralytics.YOLO", lambda path: _FakeModel())

    detector = RcCarPoseDetector(model_dir=model_dir)
    detection = detector.detect(np.zeros((240, 320, 3), dtype=np.uint8))

    assert detection.boxes == []
    assert detection.labels == []
    assert detection.scores == []
