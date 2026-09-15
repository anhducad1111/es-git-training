import pytest

from rccar_pose_inference.rccar_pose_model.geometry import Ground


def test_apply_floor_params_overrides_a_v0_fx():
    ground = Ground({"A": 90.0, "v0": 196.0, "fx": 554.0, "cu": 320.0})

    ground.apply_floor_params(A=100.0, v0=200.0, fx=560.0)

    assert ground.A == pytest.approx(100.0)
    assert ground.v0 == pytest.approx(200.0)
    assert ground.fx == pytest.approx(560.0)


def test_apply_floor_params_rescales_a_front_by_calibration_time_ratio():
    # A_front/A ratio at calibration time is 60/90 = 2/3.
    ground = Ground({"A": 90.0, "v0": 196.0, "fx": 554.0, "cu": 320.0, "A_front": 60.0})

    ground.apply_floor_params(A=99.0, v0=200.0, fx=560.0)

    assert ground.A_front == pytest.approx(66.0)  # 99 * 2/3
