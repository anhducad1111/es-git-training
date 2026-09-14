import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from follow_controller import GimbalThread


def test_is_settled_true_before_any_tracking():
    gimbal = GimbalThread(set_gimbal=lambda pan, tilt: None)
    assert gimbal.is_settled() is True


def test_is_settled_false_immediately_after_a_large_tracking_step():
    gimbal = GimbalThread(set_gimbal=lambda pan, tilt: None)
    gimbal._smooth_pan_step = 5.0
    assert gimbal.is_settled() is False


def test_is_settled_true_when_track_target_does_not_move_gimbal():
    gimbal = GimbalThread(set_gimbal=lambda pan, tilt: None)
    gimbal._track_target(bbox=(300, 200, 20, 20), frame_w=640, frame_h=480)
    assert gimbal.is_settled() is True


def test_get_pan_tilt_state_returns_current_command_values():
    gimbal = GimbalThread(set_gimbal=lambda pan, tilt: None)
    gimbal._current_pan = 75.0
    gimbal._current_tilt = 65.0
    pan, tilt, settled = gimbal.get_pan_tilt_state()
    assert pan == 75.0
    assert tilt == 65.0
    assert settled is True
