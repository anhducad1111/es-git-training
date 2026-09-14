"""ρ-α-β制御則の単体テスト."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rho_alpha_beta_control import (
    RhoAlphaBetaController,
    RhoAlphaBetaConfig,
    compute_target_position,
    compute_rho_alpha_beta,
    EMAFilter,
)


# --- 座標変換テスト ---

def test_target_position_straight_ahead():
    """rho=1.5, alpha=0, theta=0 → ゴールは自車前方0.5m."""
    x, y = compute_target_position(1.5, 0.0, 0.0, 1.0)
    assert abs(x) < 1e-6
    assert abs(y - 0.5) < 1e-6


def test_target_position_60deg_left():
    """alpha=60°, theta=60° → 先行車は左60°に見え、向いている."""
    x, y = compute_target_position(1.5, 60.0, 60.0, 1.0)
    # 先行車位置: (1.5*sin60, 1.5*cos60) = (1.299, 0.75)
    # ゴール: theta=60°の逆方向に1m → (-sin60, -cos60) = (-0.866, -0.5)
    # 合計: (1.299-0.866, 0.75-0.5) = (0.433, 0.25)
    assert abs(x - 0.433) < 0.01
    assert abs(y - 0.25) < 0.01


def test_rho_alpha_beta_already_at_goal():
    """既にゴール位置にいる場合、ρ, α, β がほぼゼロ."""
    rho, alpha, beta = compute_rho_alpha_beta(0.0, 0.0, 0.0)
    assert rho < 1e-6
    assert abs(alpha) < 1e-6
    assert abs(beta) < 1e-6


def test_rho_alpha_beta_alpha_positive():
    """ゴールが自車の左にある場合、α_goal > 0."""
    rho, alpha, beta = compute_rho_alpha_beta(1.0, 2.0, 0.0)
    assert rho > 0
    assert alpha > 0


def test_rho_alpha_beta_theta_offset():
    """theta ≠ 0 の場合、β_goal に反映される."""
    rho, alpha, beta = compute_rho_alpha_beta(0.0, 1.0, 30.0)
    # x=0, y=1 → alpha_goal=0, beta=wrap(30-0)=30
    assert abs(alpha) < 1e-6
    assert abs(beta - 30.0) < 1e-6


# --- コントローラーテスト ---

def test_controller_output_zero_when_at_goal():
    """既にゴール位置・姿勢にいる場合、出力がほぼゼロ."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    # alpha=0, theta=0, rho=follow_distance → ゴール位置=(0,0)
    v, omega, info = ctrl.compute(
        rho=0.5, alpha_deg=0.0, theta_deg=0.0
    )
    assert abs(v) < 0.1
    assert abs(omega) < 0.1


def test_controller_turns_left_for_left_target():
    """先行車が左にいる場合、左旋回 (omega > 0)."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    v, omega, info = ctrl.compute(
        rho=2.0, alpha_deg=30.0, theta_deg=0.0
    )
    assert omega > 0


def test_controller_turns_right_for_right_target():
    """先行車が右にいる場合、右旋回 (omega < 0)."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    v, omega, info = ctrl.compute(
        rho=2.0, alpha_deg=-30.0, theta_deg=0.0
    )
    assert omega < 0


def test_controller_theta60_turns_right():
    """theta=60°（先行車が左を向いている）、ゴールは右後方なので右旋回."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    v, omega, info = ctrl.compute(
        rho=2.0, alpha_deg=0.0, theta_deg=60.0
    )
    assert omega < 0


def test_controller_too_close_stops():
    """rho < stop_dist の場合、停止."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    v, omega, info = ctrl.compute(
        rho=0.2, alpha_deg=0.0, theta_deg=0.0
    )
    assert v == 0.0
    assert omega == 0.0
    assert info["action"] == "stop"


def test_controller_lost_detection():
    """検出なしの場合、一定時間後に停止."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    for _ in range(35):
        v, omega, info = ctrl.compute(
            rho=1.0, alpha_deg=0.0, theta_deg=0.0, detected=False
        )
    assert v == 0.0
    assert info["action"] == "stop"


def test_ema_filter():
    """EMAフィルタの動作確認."""
    f = EMAFilter(alpha=0.5)
    v1 = f.update(10.0)
    assert v1 == 10.0
    v2 = f.update(0.0)
    assert abs(v2 - 5.0) < 1e-6


def test_controller_compute_command():
    """compute_command の出力形式確認."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    cmd = ctrl.compute_command(rho=2.0, alpha_deg=0.0, theta_deg=0.0)
    assert "command" in cmd
    assert "speed" in cmd
    assert "v" in cmd
    assert "omega" in cmd
    assert "log" in cmd


def test_controller_large_alpha_warning():
    """大きなalphaに対して警告が出ること."""
    ctrl = RhoAlphaBetaController(RhoAlphaBetaConfig(
        filter_alpha=False, filter_theta=False, filter_rho=False
    ))
    v, omega, info = ctrl.compute(
        rho=2.0, alpha_deg=95.0, theta_deg=0.0
    )
    assert "warning" in info


def test_gain_stability_conditions():
    """ゲインが安定条件を満たしていること."""
    cfg = RhoAlphaBetaConfig()
    assert cfg.k_rho > 0
    assert cfg.k_beta < 0
    assert cfg.k_alpha > cfg.k_rho
