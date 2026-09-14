"""
ρ-α-β制御則 簡易シミュレーション

2Dキネマティクスモデル（自転車モデル）で制御則を動作させ、
軌跡をmatplotlibでプロットする。

使い方:
    python sim_rho_alpha_beta.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rho_alpha_beta_control import RhoAlphaBetaController, RhoAlphaBetaConfig


def simulate(
    lead_x0: float = 0.0,
    lead_y0: float = 5.0,
    lead_heading0: float = 0.0,
    ego_x0: float = 0.0,
    ego_y0: float = 0.0,
    ego_heading0: float = 0.0,
    dt: float = 0.1,
    max_steps: int = 500,
    lead_v: float = 0.0,
    config: RhoAlphaBetaConfig = None,
) -> dict:
    """シミュレーションを実行し、軌跡を返す.

    Args:
        lead_x0, lead_y0: 先行車の初期位置
        lead_heading0: 先行車の初期ヘディング [deg]
        ego_x0, ego_y0: 自車の初期位置
        ego_heading0: 自車の初期ヘディング [deg]
        dt: 時間刻み [s]
        max_steps: 最大ステップ数
        lead_v: 先行車の速度 [m/s]
        config: 制御パラメータ

    Returns:
        dict with keys: ego_traj, lead_traj, steps
    """
    ctrl = RhoAlphaBetaController(config)

    # 状態変数
    ego_x, ego_y, ego_h = ego_x0, ego_y0, math.radians(ego_heading0)
    lead_x, lead_y, lead_h = lead_x0, lead_y0, math.radians(lead_heading0)

    ego_traj = [(ego_x, ego_y)]
    lead_traj = [(lead_x, lead_y)]
    v_log = []
    omega_log = []

    for step in range(max_steps):
        # 先行車を前進させる
        lead_x += lead_v * dt * math.sin(lead_h)
        lead_y += lead_v * dt * math.cos(lead_h)

        # 自車から先行車への相対位置
        dx = lead_x - ego_x
        dy = lead_y - ego_y
        rho = math.hypot(dx, dy)

        # alpha: 自車ヘディングから見た先行車の方位角
        # 自車座標系: y=前方, x=左
        # dx, dy を自車座標系に変換
        dx_ego = dx * math.cos(ego_h) + dy * math.sin(ego_h)
        dy_ego = -dx * math.sin(ego_h) + dy * math.cos(ego_h)
        alpha_deg = math.degrees(math.atan2(dx_ego, dy_ego))

        # theta: 先行車の相対ヨー角
        theta_deg = math.degrees(lead_h - ego_h)

        # 制御出力
        v, omega, info = ctrl.compute(rho, alpha_deg, theta_deg, detected=True)

        # ゴール到達判定 (rho_goal < stop_dist)
        rho_goal = rho - ctrl.config.follow_distance
        if rho_goal < ctrl.config.stop_dist:
            break

        # 自車のキネマティクス更新
        ego_x += v * dt * math.sin(ego_h)
        ego_y += v * dt * math.cos(ego_h)
        ego_h += omega * dt

        ego_traj.append((ego_x, ego_y))
        lead_traj.append((lead_x, lead_y))
        v_log.append(v)
        omega_log.append(omega)

    return {
        "ego_traj": ego_traj,
        "lead_traj": lead_traj,
        "steps": len(ego_traj),
        "v_log": v_log,
        "omega_log": omega_log,
    }


def plot_results(result: dict, title: str = "ρ-α-β制御 シミュレーション"):
    """結果をプロット."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlibがインストールされていません。")
        return

    ego = result["ego_traj"]
    lead = result["lead_traj"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 軌跡プロット
    ax1 = axes[0]
    ex, ey = zip(*ego)
    lx, ly = zip(*lead)
    ax1.plot(ex, ey, "b-", linewidth=2, label="自車")
    ax1.plot(lx, ly, "r--", linewidth=2, label="先行車")
    ax1.plot(ex[0], ey[0], "bo", markersize=8, label="自車開始")
    ax1.plot(lx[0], ly[0], "ro", markersize=8, label="先行車開始")
    ax1.plot(ex[-1], ey[-1], "bs", markersize=10, label="自車停止")
    ax1.plot(lx[-1], ly[-1], "r^", markersize=10, label="先行車停止")
    ax1.set_xlabel("x [m]")
    ax1.set_ylabel("y [m]")
    ax1.set_title("軌跡")
    ax1.legend()
    ax1.grid(True)
    ax1.set_aspect("equal")

    # 制御入力プロット
    ax2 = axes[1]
    if result["v_log"]:
        ax2.plot(result["v_log"], "b-", label="v [m/s]")
        ax2.plot(result["omega_log"], "r-", label="ω [rad/s]")
        ax2.set_xlabel("Step")
        ax2.set_ylabel("制御入力")
        ax2.set_title("制御入力")
        ax2.legend()
        ax2.grid(True)

    plt.suptitle(title)
    plt.tight_layout()
    plt.savefig("sim_rho_alpha_beta_result.png", dpi=100)
    print(f"Plot saved to sim_rho_alpha_beta_result.png")


def main():
    """デフォルトシナリオでシミュレーション."""
    print("=" * 60)
    print("ρ-α-β制御則 シミュレーション")
    print("=" * 60)

    config = RhoAlphaBetaConfig(
        follow_distance=0.5,
        k_rho=1.5,
        k_alpha=2.0,
        k_beta=-1.0,
        max_speed=1.5,
        max_omega=1.5,
        stop_dist=1.2,
    )

    # シナリオ1: 真後ろに既にいる
    print("\n--- Scenario 1: Directly behind ---")
    r1 = simulate(
        lead_x0=0.0, lead_y0=2.0, lead_heading0=0.0,
        ego_x0=0.0, ego_y0=0.0, ego_heading0=0.0,
        config=config,
    )
    print(f"  Steps: {r1['steps']}")

    # シナリオ2: 少し横にずれている
    print("\n--- Scenario 2: Slightly offset ---")
    r2 = simulate(
        lead_x0=0.5, lead_y0=2.0, lead_heading0=0.0,
        ego_x0=0.0, ego_y0=0.0, ego_heading0=0.0,
        config=config,
    )
    print(f"  Steps: {r2['steps']}")

    # シナリオ3: theta=20°
    print("\n--- Scenario 3: theta=20 deg ---")
    r3 = simulate(
        lead_x0=0.0, lead_y0=2.0, lead_heading0=20.0,
        ego_x0=0.0, ego_y0=0.0, ego_heading0=0.0,
        config=config,
    )
    print(f"  Steps: {r3['steps']}")

    # シナリオ4: 横から接近 (alpha=15deg)
    print("\n--- Scenario 4: Approach from side ---")
    r4 = simulate(
        lead_x0=0.5, lead_y0=2.0, lead_heading0=0.0,
        ego_x0=0.0, ego_y0=0.0, ego_heading0=10.0,
        config=config,
    )
    print(f"  Steps: {r4['steps']}")

    try:
        plot_results(r3, "rho-alpha-beta: theta=20 scenario")
    except Exception as e:
        print(f"Plot error: {e}")


if __name__ == "__main__":
    main()
