import pytest
import time
from queue import Queue
from follow_controller import (
    FollowConfig, FollowState, GimbalThread, ControlThread,
    resolve_follow_state, wrap_angle, StateHysteresis, compute_goal_pose,
)


# =============================================================================
# Gimbal Plan Tests
# =============================================================================

def _make_gimbal_thread(**overrides):
    config_defaults = dict(
        calibration_tilt=70.0,
        tilt_deadband=0.15,
        tilt_return_gain=0.05,
        tilt_return_max_step=1.0,
    )
    config_defaults.update(overrides)
    thread = GimbalThread(set_gimbal=lambda pan, tilt: None)
    thread._calibration_tilt = config_defaults["calibration_tilt"]
    thread._tilt_deadband = config_defaults["tilt_deadband"]
    thread._tilt_return_gain = config_defaults["tilt_return_gain"]
    thread._tilt_return_max_step = config_defaults["tilt_return_max_step"]
    return thread


def test_tilt_returns_toward_calibration_when_centered():
    thread = _make_gimbal_thread()
    thread._current_tilt = 80.0
    step = thread._compute_tilt_step(error_y=0.0)
    assert step < 0
    assert abs(step) <= thread._tilt_return_max_step


def test_tilt_does_not_move_when_already_at_calibration_and_centered():
    thread = _make_gimbal_thread()
    thread._current_tilt = 70.0
    step = thread._compute_tilt_step(error_y=0.0)
    assert step == 0.0


def test_tilt_tracks_target_when_error_exceeds_deadband():
    thread = _make_gimbal_thread()
    thread._current_tilt = 70.0
    step = thread._compute_tilt_step(error_y=0.5)
    assert step != 0.0


def test_track_target_centers_bbox_vertically_not_head_hip():
    thread = _make_gimbal_thread()
    thread._current_pan = 90.0
    thread._current_tilt = 70.0

    frame_w, frame_h = 640, 480
    bbox = (450, 300, 40, 100)
    thread._track_target(bbox, frame_w, frame_h)

    assert thread._last_seen_side == "right"
    assert thread._search_state == "tracking"


def test_combined_error_x_blends_pixel_and_yaw():
    thread = _make_gimbal_thread()
    thread._pan_pixel_weight = 0.7
    thread._yaw_max = 45.0
    combined = thread._compute_combined_error_x(pixel_error_x=0.4, yaw_deg=18.0)
    assert combined == pytest.approx(0.4, abs=1e-6)


def test_combined_error_x_falls_back_to_pixel_when_yaw_missing():
    thread = _make_gimbal_thread()
    combined = thread._compute_combined_error_x(pixel_error_x=0.3, yaw_deg=None)
    assert combined == pytest.approx(0.3, abs=1e-6)


def test_combined_error_x_differs_when_yaw_disagrees_with_pixel():
    thread = _make_gimbal_thread()
    thread._pan_pixel_weight = 0.7
    thread._yaw_max = 45.0
    combined = thread._compute_combined_error_x(pixel_error_x=0.2, yaw_deg=45.0)
    assert combined == pytest.approx(0.44, abs=1e-6)


def test_update_detection_stores_yaw_deg():
    thread = _make_gimbal_thread()
    thread.update_detection(bbox=(0, 0, 10, 10), frame_w=640, frame_h=480, yaw_deg=12.5)
    assert thread._last_yaw_deg == 12.5


def test_update_detection_yaw_deg_defaults_to_none():
    thread = _make_gimbal_thread()
    thread.update_detection(bbox=(0, 0, 10, 10), frame_w=640, frame_h=480)
    assert thread._last_yaw_deg is None


# =============================================================================
# Distance Band Plan Tests
# =============================================================================

def test_follow_config_defaults_for_distance_band():
    config = FollowConfig()
    assert config.follow_distance == 0.5
    assert config.distance_band == 0.15
    assert config.min_pwm == 150
    assert config.blind_approach_pwm == 150
    assert config.head_on_threshold == 20.0
    assert config.state_hysteresis_frames == 3
    assert config.lost_timeout_sec == 5.0


def test_follow_state_has_new_members():
    assert FollowState.HEAD_ON_HOLD.value == "head_on_hold"
    assert FollowState.HOLDING.value == "holding"
    assert FollowState.APPROACHING_BLIND.value == "approaching_blind"
    assert FollowState.LOST_TIMEOUT.value == "lost_timeout"


def test_wrap_angle_normalizes_to_range():
    assert wrap_angle(180.0) == pytest.approx(-180.0)
    assert wrap_angle(190.0) == pytest.approx(-170.0)
    assert wrap_angle(-190.0) == pytest.approx(170.0)
    assert wrap_angle(10.0) == pytest.approx(10.0)


def test_resolve_state_head_on_takes_priority():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=175.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.HEAD_ON_HOLD


def test_resolve_state_no_bbox_is_searching():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=None, dist_m=None, bbox=None, config=config)
    assert state == FollowState.SEARCHING


def test_resolve_state_bbox_without_yaw_or_dist_is_approaching_blind():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=None, dist_m=1.5, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.APPROACHING_BLIND
    state = resolve_follow_state(yaw_deg=30.0, dist_m=None, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.APPROACHING_BLIND


def test_resolve_state_in_band_is_holding():
    config = FollowConfig()
    # target_distance=0.5, band=0.1 -> 0.4-0.6m
    state = resolve_follow_state(yaw_deg=10.0, dist_m=0.50, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.HOLDING


def test_resolve_state_out_of_band_is_following():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=10.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.FOLLOWING


def test_hysteresis_holds_previous_state_until_threshold_met():
    config = FollowConfig(state_hysteresis_frames=3)
    hysteresis = StateHysteresis(config, initial_state=FollowState.SEARCHING)

    assert hysteresis.update(FollowState.FOLLOWING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.FOLLOWING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.FOLLOWING) == FollowState.FOLLOWING


def test_hysteresis_resets_count_on_candidate_change():
    config = FollowConfig(state_hysteresis_frames=3)
    hysteresis = StateHysteresis(config, initial_state=FollowState.SEARCHING)

    hysteresis.update(FollowState.FOLLOWING)
    hysteresis.update(FollowState.FOLLOWING)
    assert hysteresis.update(FollowState.HOLDING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.HOLDING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.HOLDING) == FollowState.HOLDING


def test_hysteresis_head_on_hold_is_immediate_no_delay():
    config = FollowConfig(state_hysteresis_frames=3)
    hysteresis = StateHysteresis(config, initial_state=FollowState.FOLLOWING)
    assert hysteresis.update(FollowState.HEAD_ON_HOLD) == FollowState.HEAD_ON_HOLD


def _make_control_thread(**config_overrides):
    config_overrides.setdefault("state_hysteresis_frames", 1)
    config = FollowConfig(**config_overrides)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0
    return thread


def test_head_on_detection_stops_immediately():
    thread = _make_control_thread()
    detection = {"yaw_deg": 175.0, "dist_m": 1.0, "confidence": 0.9, "bbox": (0, 0, 10, 10),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert result["command"] == "stop"
    assert result["speed"] == 0
    assert thread.state == FollowState.HEAD_ON_HOLD


def test_approaching_blind_uses_fixed_pwm_and_pan_steering():
    thread = _make_control_thread()
    detection = {"yaw_deg": None, "dist_m": 1.2, "confidence": 0.9, "bbox": (400, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.APPROACHING_BLIND
    assert result["command"] == "stop"
    assert result["speed"] == 0


def test_holding_in_band_stops():
    thread = _make_control_thread()
    detection = {"yaw_deg": 5.0, "dist_m": 0.50, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.HOLDING
    assert result["command"] == "stop"
    assert result["speed"] == 0


def test_no_bbox_enters_searching_and_stops_chassis():
    thread = _make_control_thread()
    detection = {"yaw_deg": None, "dist_m": None, "confidence": 0.0, "bbox": None,
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.SEARCHING
    assert result["command"] == "stop"


def test_following_forward_command_is_clamped_to_min_pwm():
    thread = _make_control_thread()
    detection = {"yaw_deg": 5.0, "dist_m": 2.0, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.FOLLOWING
    assert result["command"] == "forward"
    assert result["speed"] == 150


def test_searching_transitions_to_lost_timeout_after_configured_seconds():
    config = FollowConfig(lost_timeout_sec=0.2, state_hysteresis_frames=1)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0
    detection = {"yaw_deg": None, "dist_m": None, "confidence": 0.0, "bbox": None,
                 "frame_w": 640, "frame_h": 480}

    result = thread._compute_command(detection)
    assert thread.state == FollowState.SEARCHING

    time.sleep(0.25)
    thread._last_cmd_t = 0.0
    result = thread._compute_command(detection)
    assert thread.state == FollowState.LOST_TIMEOUT
    assert result["command"] == "stop"


def test_scenario_far_then_lost_then_recovered():
    config = FollowConfig(state_hysteresis_frames=1)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0

    r1 = thread._compute_command({"yaw_deg": None, "dist_m": 1.8, "confidence": 0.4,
                                    "bbox": (300, 200, 15, 15), "frame_w": 640, "frame_h": 480})
    assert thread.state == FollowState.APPROACHING_BLIND
    assert r1["command"] == "stop"
    assert r1["speed"] == 0
    thread._last_cmd_t = 0.0

    r2 = thread._compute_command({"yaw_deg": None, "dist_m": None, "confidence": 0.0,
                                   "bbox": None, "frame_w": 640, "frame_h": 480})
    assert thread.state == FollowState.SEARCHING
    assert r2["command"] == "stop"
    thread._last_cmd_t = 0.0

    r3 = thread._compute_command({"yaw_deg": 8.0, "dist_m": 1.2, "confidence": 0.9,
                                   "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480})
    assert thread.state == FollowState.FOLLOWING


# =============================================================================
# Repositioning Plan Tests
# =============================================================================

def test_follow_state_has_repositioning_member():
    assert FollowState.REPOSITIONING.value == "repositioning"


def test_follow_config_defaults_for_repositioning():
    config = FollowConfig()
    assert config.reposition_yaw_threshold == 45.0
    assert config.k_rho == pytest.approx(0.6)
    assert config.k_alpha == pytest.approx(1.5)
    assert config.k_beta == pytest.approx(-0.6)


def test_resolve_state_head_on_still_takes_priority_over_repositioning():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=175.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config, bearing_deg=5.0)
    assert state == FollowState.HEAD_ON_HOLD


def test_resolve_state_repositioning_when_yaw_exceeds_threshold():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=60.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config, bearing_deg=10.0)
    assert state == FollowState.REPOSITIONING


def test_resolve_state_following_when_yaw_within_threshold():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=15.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config, bearing_deg=5.0)
    assert state == FollowState.FOLLOWING


def test_resolve_state_repositioning_requires_bearing_deg():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=60.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config, bearing_deg=None)
    assert state == FollowState.FOLLOWING


def test_resolve_state_repositioning_disabled():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=60.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config, bearing_deg=10.0, repositioning_enabled=False)
    assert state == FollowState.FOLLOWING


def test_compute_goal_pose_zero_when_already_at_goal():
    rho, alpha, beta = compute_goal_pose(bearing_deg=0.0, dist_m=0.375, yaw_deg=0.0, follow_distance=0.375)
    assert rho == pytest.approx(0.0, abs=1e-3)


def test_compute_goal_pose_nonzero_rho_when_offset():
    rho, alpha, beta = compute_goal_pose(bearing_deg=0.0, dist_m=1.0, yaw_deg=60.0, follow_distance=0.375)
    assert rho > 0.5


def test_handle_repositioning_turns_when_alpha_dominant():
    config = FollowConfig()
    thread = ControlThread(Queue(), Queue(), config)
    result = thread._handle_repositioning(bearing_deg=40.0, dist_m=1.0, yaw_deg=60.0)
    assert result["command"] in ("left", "right")
    assert result["speed"] >= config.min_pwm


def test_handle_repositioning_moves_forward_when_roughly_aligned():
    config = FollowConfig()
    thread = ControlThread(Queue(), Queue(), config)
    result = thread._handle_repositioning(bearing_deg=0.0, dist_m=1.5, yaw_deg=5.0)
    assert result["command"] == "forward"


def test_compute_command_dispatches_to_repositioning():
    config = FollowConfig(state_hysteresis_frames=1)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0
    thread.repositioning_enabled = True
    detection = {"yaw_deg": 60.0, "dist_m": 1.0, "confidence": 0.9,
                 "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480,
                 "bearing_deg": 10.0}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.REPOSITIONING


def test_scenario_following_to_repositioning_and_back():
    config = FollowConfig(state_hysteresis_frames=1)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0
    thread.repositioning_enabled = True

    r1 = thread._compute_command({"yaw_deg": 10.0, "dist_m": 1.0, "confidence": 0.9,
                                   "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480,
                                   "bearing_deg": 5.0})
    assert thread.state == FollowState.FOLLOWING
    thread._last_cmd_t = 0.0

    r2 = thread._compute_command({"yaw_deg": 60.0, "dist_m": 1.0, "confidence": 0.9,
                                   "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480,
                                   "bearing_deg": 15.0})
    assert thread.state == FollowState.REPOSITIONING
    thread._last_cmd_t = 0.0

    r3 = thread._compute_command({"yaw_deg": 20.0, "dist_m": 1.0, "confidence": 0.9,
                                   "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480,
                                   "bearing_deg": 3.0})
    assert thread.state == FollowState.FOLLOWING
