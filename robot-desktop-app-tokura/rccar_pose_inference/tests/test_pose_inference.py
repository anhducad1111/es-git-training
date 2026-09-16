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
    inference._prediction_time_sec = 0.5
    inference._tilt_curve = None
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


class _FakeGroundReacquire:
    """First pose() call is near; every call after that is far -- simulates
    the car being close, then (after occlusion) reappearing much farther
    away, which looks like an implausible speed jump against the Kalman
    filter's now-stale (coasted) internal state."""

    def __init__(self):
        self.calls = 0

    def pose(self, L, R, F):
        self.calls += 1
        if self.calls == 1:
            return {"X": 0.0, "Z": 1.0, "yaw_deg": 0.0, "dist_m": 1.0}
        return {"X": 0.0, "Z": 3.0, "yaw_deg": 45.0, "dist_m": 3.0}


class _StubModelToggle:
    """Returns a detection or an empty result per a fixed True/False sequence,
    to simulate the car being occluded for a few frames then reappearing."""

    def __init__(self, detected_sequence):
        self._sequence = list(detected_sequence)
        self._index = 0

    def predict(self, frame, conf, verbose):
        detected = self._sequence[self._index]
        self._index += 1
        if not detected:
            return [_FakeResult(boxes=_FakeBoxes(xyxy=np.empty((0, 4)), conf=np.empty(0)))]
        boxes = _FakeBoxes(xyxy=[[10.0, 10.0, 50.0, 50.0]], conf=[0.9])
        keypoints = _FakeKeypoints(xy=[[[1, 1], [2, 2], [3, 3]]])
        return [_FakeResult(boxes=boxes, keypoints=keypoints)]


class _RecordingGroundForTiltCurve:
    """Records the A/v0/fx applied via apply_floor_params() just before each
    pose() call, so tests can assert the tilt curve was actually evaluated
    and fed into Ground for that frame's tilt angle."""

    def __init__(self):
        self.A = self.v0 = self.fx = None
        self.applied_calls = []

    def apply_floor_params(self, A, v0, fx):
        self.A, self.v0, self.fx = A, v0, fx
        self.applied_calls.append((A, v0, fx))

    def pose(self, L, R, F):
        return {"X": 0.0, "Z": 1.0, "yaw_deg": 0.0, "dist_m": 1.0}


_TILT_CURVE = {
    "fx": 556.06,
    "v0_coeffs": [-9.085, 777.575],  # v0(tilt) = -9.085*tilt + 777.575
    "A_coeffs": [-0.236536, 107.31828],
    "tilt_deg_range": [65.0, 80.0],
}


def _make_tilt_curve_inference(tilt_curve=_TILT_CURVE):
    inference = _make_gimbal_test_inference()
    inference._ground = _RecordingGroundForTiltCurve()
    inference._tilt_curve = tilt_curve
    return inference


def test_infer_applies_tilt_curve_params_to_ground_before_pose():
    inference = _make_tilt_curve_inference()
    inference._gimbal_provider = lambda: (90.0, 70.0, True)

    inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))

    expected_v0 = -9.085 * 70.0 + 777.575
    expected_A = -0.236536 * 70.0 + 107.31828
    assert inference._ground.applied_calls == [(pytest.approx(expected_A), pytest.approx(expected_v0), 556.06)]


def test_infer_uses_different_ground_params_at_different_tilt_angles():
    inference = _make_tilt_curve_inference()

    inference._gimbal_provider = lambda: (90.0, 65.0, True)
    inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))
    v0_at_65 = inference._ground.v0

    inference._gimbal_provider = lambda: (90.0, 80.0, True)
    inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))
    v0_at_80 = inference._ground.v0

    assert v0_at_65 != pytest.approx(v0_at_80)


def test_infer_trusts_tilt_curve_extrapolation_within_margin():
    inference = _make_tilt_curve_inference()
    # 5 degrees past the calibrated range (65-80), within the 10-degree margin.
    inference._gimbal_provider = lambda: (90.0, 85.0, True)

    result = inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))

    assert result.dist_m is not None
    assert inference._ground.applied_calls  # curve was still evaluated (clamped)


def test_infer_gates_out_pose_when_tilt_outside_tilt_curve_extrapolation_margin():
    inference = _make_tilt_curve_inference()
    # 15 degrees past the calibrated range (65-80), beyond the 10-degree margin.
    inference._gimbal_provider = lambda: (90.0, 95.0, True)

    result = inference.infer(np.zeros((480, 640, 3), dtype=np.uint8))

    assert result.yaw_deg is None
    assert result.dist_m is None


def test_infer_trusts_reacquired_detection_after_occlusion_despite_apparent_speed_jump(monkeypatch):
    """Regression test for a bug found by comparing against
    esp32_mjpeg_detector (which has no implausible-speed check and correctly
    snaps back to the true pose on reacquisition): the plausible-speed veto
    was comparing a fresh detection against the Kalman filter's own coasted
    (predict()-only) internal state, so a real detection reappearing after
    occlusion was itself flagged as "impossibly fast" and given almost no
    trust -- leaving yaw/dist stuck near the stale pre-occlusion value
    instead of correcting. The fix: only apply the veto when the filter's
    state came from an update() on the immediately preceding frame
    (coast_seconds() == 0), not from several frames of pure prediction."""
    import rccar_pose_inference.pose_inference as pi_module

    clock = {"t": 0.0}
    monkeypatch.setattr(pi_module.time, "time", lambda: clock["t"])

    inference = PoseInference.__new__(PoseInference)
    inference._ground = _FakeGroundReacquire()
    inference._aruco = None
    inference._use_aruco_dist = False
    inference._sigma_ground = 0.05
    inference._sigma_aruco = 0.02
    inference._max_coast_sec = 5.0  # keep the track alive across the occlusion below
    inference._calibration_tilt_deg = 70.0
    inference._tilt_max_deviation_deg = 10.0
    inference._gimbal_center_pan_deg = 90.0
    inference._max_plausible_speed_mps = 2.0
    inference._prediction_time_sec = 0.5
    inference._confidence = 0.35
    inference._kalman = PoseKalmanFilter()
    inference._last_infer_time = None
    inference._gimbal_provider = None
    inference._model = _StubModelToggle([True, False, False, False, True])

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    first = inference.infer(frame)
    assert first.dist_m == pytest.approx(1.0, abs=0.05)

    # 3 frames of occlusion (no detection): the filter only predicts, drifting
    # its internal state without correction.
    for _ in range(3):
        clock["t"] += 0.1
        inference.infer(frame)

    # Reacquired: a legitimate, correct detection 2m farther away. Against
    # the drifted internal state this looks like a large implied speed, but
    # it must still be trusted since it follows an occlusion, not a single
    # bad frame mid-track.
    clock["t"] += 0.1
    result = inference.infer(frame)

    # dist_m is the clearest signal here: R for X/Z is tight (measurement_noise
    # = 0.05), so a trusted (position_confidence=1.0) observation converges
    # almost fully in one update, while a distrusted one (position_confidence
    # capped at 0.05, R scaled up 20x) would barely move off the stale 1.0m
    # estimate -- which is exactly the bug this fix addresses.
    assert result.dist_m == pytest.approx(3.0, abs=0.3)
    # yaw's own measurement noise (R[2,2]=25) makes it converge slowly by
    # design regardless of position_confidence (that's what
    # yaw_snap_threshold_deg is for on a genuine reversal) - just confirm it
    # moved toward the true 45 deg instead of staying pinned at the stale 0.
    assert result.yaw_deg > 1.0


def test_predict_yaw_deg_projects_using_yaw_rate():
    inference = PoseInference.__new__(PoseInference)
    inference._prediction_time_sec = 0.5

    state = {"X": 0.0, "Z": 1.0, "yaw_deg": 10.0, "dist_m": 1.0,
              "vx_mps": 0.0, "vz_mps": 0.0, "yaw_rate_deg_s": 20.0}

    # future_yaw = 10 + 20 * 0.5 = 20
    assert inference._predict_yaw_deg(state) == pytest.approx(20.0, abs=1e-6)


def test_predict_yaw_deg_wraps_across_180_boundary():
    inference = PoseInference.__new__(PoseInference)
    inference._prediction_time_sec = 1.0

    state = {"X": 0.0, "Z": 1.0, "yaw_deg": 170.0, "dist_m": 1.0,
              "vx_mps": 0.0, "vz_mps": 0.0, "yaw_rate_deg_s": 20.0}

    # future_yaw = 170 + 20 = 190 -> wraps to -170
    assert inference._predict_yaw_deg(state) == pytest.approx(-170.0, abs=1e-6)


def test_infer_reports_yaw_deg_predicted_once_kalman_initialized():
    inference = _make_gimbal_test_inference()
    inference._gimbal_provider = None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = inference.infer(frame)

    assert result.yaw_deg_predicted is not None


def test_infer_reports_none_yaw_deg_predicted_when_no_detection(tmp_path):
    inference = PoseInference.__new__(PoseInference)
    inference._ground = None
    inference._aruco = None
    inference._use_aruco_dist = False
    inference._gimbal_provider = None
    inference._kalman = PoseKalmanFilter()
    inference._max_coast_sec = 1.0
    inference._prediction_time_sec = 0.5
    inference._model = _StubModel(_FakeResult(boxes=_FakeBoxes(xyxy=np.empty((0, 4)), conf=np.empty(0))))
    inference._confidence = 0.35
    inference._last_infer_time = None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = inference.infer(frame)
    assert result.yaw_deg_predicted is None
