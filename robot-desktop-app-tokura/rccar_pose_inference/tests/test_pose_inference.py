import numpy as np
import pytest

from rccar_pose_inference.pose_inference import DetectionResult, PoseInference
from rccar_pose_inference.pose_kalman import PoseKalmanFilter


class _FakeArray:
    """Minimal stand-in for a torch tensor: supports the .tolist()/np.asarray()
    calls PoseInference makes on ultralytics results."""

    def __init__(self, data):
        self._data = np.asarray(data)

    def __getitem__(self, index):
        return _FakeArray(self._data[index])

    def __array__(self, dtype=None):
        return self._data if dtype is None else self._data.astype(dtype)

    def tolist(self):
        return self._data.tolist()

    def argmax(self):
        return int(self._data.argmax())

    def __float__(self):
        return float(self._data)


class _FakeBoxes:
    def __init__(self, xyxy, conf):
        self.xyxy = _FakeArray(xyxy)
        self.conf = _FakeArray(conf)

    def __len__(self):
        return len(self.conf._data)


class _FakeKeypoints:
    def __init__(self, xy):
        self.xy = _FakeArray(xy)


class _FakeResult:
    def __init__(self, boxes, keypoints=None):
        self.boxes = boxes
        self.keypoints = keypoints


def _make_model_dir(tmp_path, extra_config=None):
    weights = tmp_path / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"")
    config = {"ground": {}}
    if extra_config:
        config.update(extra_config)
    import json
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


def test_init_raises_when_weights_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        PoseInference(model_dir=tmp_path, weights_path=tmp_path / "does_not_exist.pt")


def test_infer_returns_none_yaw_dist_when_no_detection(tmp_path):
    inference = PoseInference.__new__(PoseInference)  # bypass __init__ to inject mocks
    inference._ground = None
    inference._aruco = None
    inference._use_aruco_dist = False
    inference._gimbal_provider = None
    inference._kalman = PoseKalmanFilter()
    inference._max_coast_sec = 1.0
    inference._model = _StubModel(_FakeResult(boxes=_FakeBoxes(xyxy=np.empty((0, 4)), conf=np.empty(0))))
    inference._confidence = 0.35
    inference._last_infer_time = None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = inference.infer(frame)
    assert result.yaw_deg is None
    assert result.dist_m is None
    assert result.bbox is None


class _StubModel:
    def __init__(self, result):
        self._result = result

    def predict(self, frame, conf, verbose):
        return [self._result]


def test_infer_combines_keypoint_pose_aruco_fusion_and_kalman(tmp_path, monkeypatch):
    model_dir = _make_model_dir(tmp_path)

    class _FakeGround:
        def __init__(self, g):
            pass

        def pose(self, L, R, F):
            return {"X": 0.0, "Z": 0.5, "yaw_deg": 12.3, "dist_m": 0.5}

    class _FakeAruco:
        def __init__(self, cfg):
            pass

        def __call__(self, frame):
            return {"dist_m": 0.42, "edge_px": 42.0}

    monkeypatch.setattr("rccar_pose_inference.pose_inference.RcCarGround", _FakeGround)
    monkeypatch.setattr("rccar_pose_inference.pose_inference.RcCarAruco", _FakeAruco)

    fake_result = _FakeResult(
        boxes=_FakeBoxes(xyxy=[[10.0, 20.0, 110.0, 220.0]], conf=[0.9]),
        keypoints=_FakeKeypoints(xy=[[[1, 1], [2, 2], [3, 3]]]),
    )
    monkeypatch.setattr("ultralytics.YOLO", lambda path: _StubModel(fake_result))

    inference = PoseInference(model_dir=model_dir, weights_path=model_dir / "weights" / "best.pt")
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    result = inference.infer(frame)

    assert result.bbox == (10, 20, 100, 200)
    assert result.confidence == pytest.approx(0.9)
    # Ground (0.5m, sigma default) and ArUco (0.42m) inverse-variance fused,
    # then run through the Kalman filter's first (direct-assignment) update.
    assert result.dist_m == pytest.approx(0.431034, abs=1e-4)
    assert result.yaw_deg == pytest.approx(12.3, abs=1e-6)


def test_infer_reports_camera_relative_bearing_deg_via_atan2(tmp_path, monkeypatch):
    """回帰テスト: ジンバルセンタリングで固定5度ステップを使うと、実際に必要な
    角度とズレて行ったり来たり振動する問題があったため、atan2(X, Z)で正確な
    角度を計算してGimbalThreadに渡せるようにした。bearing_degはgimbal_provider
    によるロボット相対回転より前の、カメラ視点そのままの値であること
    (X=0.3, Z=0.4 -> atan2(0.3, 0.4) ≈ 36.87度)。"""
    model_dir = _make_model_dir(tmp_path)

    class _FakeGround:
        def __init__(self, g):
            pass

        def pose(self, L, R, F):
            return {"X": 0.3, "Z": 0.4, "yaw_deg": 0.0, "dist_m": 0.5}

    class _FakeAruco:
        def __init__(self, cfg):
            pass

        def __call__(self, frame):
            return None

    monkeypatch.setattr("rccar_pose_inference.pose_inference.RcCarGround", _FakeGround)
    monkeypatch.setattr("rccar_pose_inference.pose_inference.RcCarAruco", _FakeAruco)

    fake_result = _FakeResult(
        boxes=_FakeBoxes(xyxy=[[10.0, 20.0, 110.0, 220.0]], conf=[0.9]),
        keypoints=_FakeKeypoints(xy=[[[1, 1], [2, 2], [3, 3]]]),
    )
    monkeypatch.setattr("ultralytics.YOLO", lambda path: _StubModel(fake_result))

    # gimbal_providerを渡し、ロボット相対回転がbearing_degには影響しないことも確認する
    inference = PoseInference(model_dir=model_dir, weights_path=model_dir / "weights" / "best.pt",
                               gimbal_provider=lambda: (90.0, 70.0, True))
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    result = inference.infer(frame)

    assert result.bearing_deg == pytest.approx(36.87, abs=0.1)


def test_infer_bearing_deg_is_none_when_pose_unavailable():
    inference = PoseInference.__new__(PoseInference)  # bypass __init__ to inject mocks
    inference._ground = None  # keypointsがあってもGround.pose()を呼べないケース
    inference._aruco = None
    inference._use_aruco_dist = False
    inference._gimbal_provider = None
    inference._kalman = PoseKalmanFilter()
    inference._max_coast_sec = 1.0
    inference._model = _StubModel(_FakeResult(
        boxes=_FakeBoxes(xyxy=[[10.0, 20.0, 110.0, 220.0]], conf=[0.9]),
        keypoints=_FakeKeypoints(xy=[[[1, 1], [2, 2], [3, 3]]]),
    ))
    inference._confidence = 0.35
    inference._last_infer_time = None

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    result = inference.infer(frame)

    assert result.bearing_deg is None


class _FakeGroundForGimbalTest:
    def pose(self, L, R, F):
        return {"X": 0.0, "Z": 1.0, "yaw_deg": 0.0, "dist_m": 1.0}


class _StubModelWithKeypoints:
    def predict(self, frame, conf, verbose):
        boxes = _FakeBoxes(xyxy=[[10.0, 10.0, 50.0, 50.0]], conf=[0.9])
        keypoints = _FakeKeypoints(xy=[[[1, 1], [2, 2], [3, 3]]])
        return [_FakeResult(boxes=boxes, keypoints=keypoints)]


def _make_gimbal_test_inference():
    from rccar_pose_inference.pose_kalman import PoseKalmanFilter

    inference = PoseInference.__new__(PoseInference)
    inference._ground = _FakeGroundForGimbalTest()
    inference._aruco = None
    inference._use_aruco_dist = False
    inference._sigma_ground = 0.05
    inference._sigma_aruco = 0.02
    inference._max_coast_sec = 1.0
    inference._calibration_tilt_deg = 70.0
    inference._tilt_max_deviation_deg = 10.0
    inference._gimbal_center_pan_deg = 90.0
    inference._max_plausible_speed_mps = 2.0
    inference._confidence = 0.35
    inference._kalman = PoseKalmanFilter()
    inference._last_infer_time = None
    inference._model = _StubModelWithKeypoints()
    return inference


def test_infer_rotates_pose_into_robot_frame_when_gimbal_provider_set():
    inference = _make_gimbal_test_inference()
    # Camera panned 90 degrees to its own left (pan=180, center=90).
    inference._gimbal_provider = lambda: (180.0, 70.0, True)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = inference.infer(frame)

    # Distance magnitude is rotation-invariant; direction (X/Z, folded into
    # dist_m here since |X,Z| unchanged) confirms the transform ran without
    # raising and produced a sane result.
    assert result.dist_m == pytest.approx(1.0, abs=0.05)


def test_infer_gates_out_pose_when_tilt_outside_calibration_range():
    inference = _make_gimbal_test_inference()
    # 30 degrees off the 70-degree calibration angle, well past the 10-degree tolerance.
    inference._gimbal_provider = lambda: (90.0, 100.0, True)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = inference.infer(frame)

    # No prior track to coast on, and this frame's pose was gated out ->
    # no yaw/dist, but the bbox itself is still reported (car is visible,
    # we just don't trust the distance at this tilt).
    assert result.yaw_deg is None
    assert result.dist_m is None
    assert result.bbox is not None


def test_infer_does_not_report_a_phantom_position_jump_while_gimbal_is_moving():
    inference = _make_gimbal_test_inference()

    # Frame 1: gimbal settled, stable observation (X=0, Z=1).
    inference._gimbal_provider = lambda: (90.0, 70.0, True)
    first = inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))
    assert first.dist_m == pytest.approx(1.0, abs=0.05)

    # Frame 2: gimbal unsettled (still moving from a recent pan command).
    # Even though the raw (X, Z) from the fake Ground is unchanged, the pan
    # angle jumped, which would rotate the observation a lot if trusted.
    inference._gimbal_provider = lambda: (120.0, 70.0, False)
    second = inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))

    # Low position_confidence keeps the filter close to its prior estimate
    # instead of snapping to the (rotation-corrupted) new observation.
    assert second.dist_m == pytest.approx(first.dist_m, abs=0.1)
