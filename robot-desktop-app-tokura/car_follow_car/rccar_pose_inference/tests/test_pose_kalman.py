import math

import pytest

from rccar_pose_inference.pose_kalman import PoseKalmanFilter


def test_filter_not_initialized_before_first_update():
    kf = PoseKalmanFilter()
    assert kf.is_initialized() is False


def test_first_update_initializes_state_directly():
    kf = PoseKalmanFilter()
    kf.update(x=0.1, z=0.5, yaw_deg=10.0)
    assert kf.is_initialized() is True
    state = kf.state
    assert state["X"] == pytest.approx(0.1, abs=1e-6)
    assert state["Z"] == pytest.approx(0.5, abs=1e-6)
    assert state["yaw_deg"] == pytest.approx(10.0, abs=1e-6)
    assert state["dist_m"] == pytest.approx(math.hypot(0.1, 0.5), abs=1e-6)


def test_predict_moves_state_using_constant_velocity_after_two_updates():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    kf.predict(dt=0.1)
    kf.update(x=0.0, z=0.9, yaw_deg=0.0)  # approaching at ~1 m/s
    kf.predict(dt=0.1)
    state = kf.state
    assert state["Z"] < 0.9


def test_update_pulls_prediction_toward_new_measurement():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    kf.predict(dt=0.1)
    kf.update(x=0.0, z=0.5, yaw_deg=0.0)  # large jump in observation
    state = kf.state
    assert 0.4 < state["Z"] < 0.9


def test_coast_seconds_accumulates_across_predicts_without_update():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    kf.predict(dt=0.3)
    kf.predict(dt=0.3)
    assert kf.coast_seconds() == pytest.approx(0.6, abs=1e-6)


def test_coast_seconds_resets_on_update():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    kf.predict(dt=0.5)
    kf.update(x=0.0, z=0.9, yaw_deg=0.0)
    assert kf.coast_seconds() == pytest.approx(0.0, abs=1e-6)


def test_is_stale_reflects_max_coast_threshold():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    kf.predict(dt=0.5)
    assert kf.is_stale(max_coast_sec=1.0) is False
    kf.predict(dt=0.6)
    assert kf.is_stale(max_coast_sec=1.0) is True


def test_yaw_wraps_correctly_across_180_boundary():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=179.0)
    kf.predict(dt=0.1)
    kf.update(x=0.0, z=1.0, yaw_deg=-179.0)  # 2 deg turn across the wrap
    state = kf.state
    assert state["yaw_deg"] > 170.0 or state["yaw_deg"] < -170.0


def test_update_snaps_immediately_on_large_yaw_jump_like_a_reversal():
    """A car reversing direction flips the L->R axle-perpendicular yaw by
    ~180 degrees in a single frame; the constant-velocity model must not
    smooth that away like noise -- it should be reflected in the very same
    update() call."""
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    for _ in range(5):  # let the filter converge (small P) like a steady track
        kf.predict(dt=0.1)
        kf.update(x=0.0, z=1.0, yaw_deg=0.0)

    kf.predict(dt=0.1)
    kf.update(x=0.0, z=1.0, yaw_deg=178.0)

    assert kf.state["yaw_deg"] == pytest.approx(178.0, abs=1e-6)


def test_update_still_smooths_ordinary_yaw_changes_below_snap_threshold():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    kf.predict(dt=0.1)
    kf.update(x=0.0, z=1.0, yaw_deg=40.0)  # below the default 90 deg snap threshold

    assert 0.0 < kf.state["yaw_deg"] < 40.0  # blended toward it, not snapped


def test_low_position_confidence_barely_moves_state_toward_new_measurement():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    for _ in range(5):  # let the filter converge (small P) like a steady track
        kf.predict(dt=0.1)
        kf.update(x=0.0, z=1.0, yaw_deg=0.0)

    kf.predict(dt=0.1)
    kf.update(x=0.0, z=0.5, yaw_deg=0.0, position_confidence=0.01)  # large jump, low trust

    # A converged filter would otherwise respond noticeably to a 1.0->0.5
    # jump (see test below); low confidence should barely move it.
    assert kf.state["Z"] > 0.9


def test_default_position_confidence_matches_full_trust_behavior():
    kf = PoseKalmanFilter()
    kf.update(x=0.0, z=1.0, yaw_deg=0.0)
    for _ in range(5):
        kf.predict(dt=0.1)
        kf.update(x=0.0, z=1.0, yaw_deg=0.0)

    kf.predict(dt=0.1)
    kf.update(x=0.0, z=0.5, yaw_deg=0.0)  # position_confidence omitted -> full trust

    assert kf.state["Z"] < 0.9
