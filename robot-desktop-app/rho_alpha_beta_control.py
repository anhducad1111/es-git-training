"""
ρ-α-β 制御則: 先行車の真後ろに正しい向きで停車する制御モジュール

Aicardi et al. の極座標フィードバック制御則を参考に実装。
自車を原点、自車ヘディングをy軸正方向とする自車座標系で計算を行う。

入力:
  rho  : 自車〜先行車の距離 [m]
  alpha: 自車正面(y軸)を0とした先行車の方位角 [deg]
         正=左, 負=右
  theta: 先行車自体の向きのズレ（自車ヘ딩に対する相対ヨー角）[deg]
         正=左向き, 負=右向き

制御出力:
  v    : 目標速度 [m/s] (正=前進, 負=後退)
  omega: 目標角速度 [rad/s] (正=左旋回, 負=右旋回)
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RhoAlphaBetaConfig:
    """ρ-α-β制御のパラメータ."""

    # --- フォロー距離 ---
    follow_distance: float = 0.5

    # --- 制御ゲイン ---
    # 安定条件 (Aicardi et al.):
    #   k_rho > 0
    #   k_beta < 0
    #   k_alpha - k_rho > 0  (すなわち k_alpha > k_rho)
    #
    # デフォルト値の根拠:
    #   k_rho  = 1.5  : アプローチ速度 (距離に比例)
    #   k_alpha = 2.0 : 方位誤差に対する応答性 (k_alpha > k_rho を満たす)
    #   k_beta = -1.0 : 姿勢誤差の減衰 (k_beta < 0 を満たす)
    k_rho: float = 1.5
    k_alpha: float = 2.0
    k_beta: float = -1.0

    # --- 安全制限 ---
    max_speed: float = 1.5
    min_speed: float = 0.1
    max_omega: float = 1.5
    stop_dist: float = 0.3

    # --- 入力フィルタ (EMA) ---
    filter_alpha: bool = True
    filter_theta: bool = True
    filter_rho: bool = True
    ema_alpha: float = 0.3

    # --- 大角度警告しきい値 [deg] ---
    large_angle_threshold: float = 90.0


def wrap_angle(deg: float) -> float:
    """角度を [-180, 180) に正規化."""
    return (deg + 180.0) % 360.0 - 180.0


def compute_target_position(
    rho: float, alpha_deg: float, theta_deg: float, follow_distance: float
) -> tuple[float, float]:
    """先行車の位置から、真後ろのゴール位置を計算する.

    座標系:
      - 自車座標系: 自車を原点、自車ヘディング(y軸正)を前方とする
      - alpha_deg: 先行車が見える方位角 [deg] (自車前方=0, 左=正)
      - theta_deg: 先行車の相対ヨー角 [deg] (先行車の向きのズレ)

    ゴール位置:
      先行車位置から、先行車の向き(theta)の逆方向にfollow_distanceだけオフセット

    Returns:
      (x_goal, y_goal): 自車座標系でのゴール位置
    """
    alpha = math.radians(alpha_deg)
    theta = math.radians(theta_deg)

    # 先行車の自車座標系での位置
    x_lead = rho * math.sin(alpha)
    y_lead = rho * math.cos(alpha)

    # ゴール位置: 先行車の後方 follow_distance に配置
    # 先行車の向き(theta)の逆方向 = theta + π
    x_goal = x_lead - follow_distance * math.sin(theta)
    y_goal = y_lead - follow_distance * math.cos(theta)

    return x_goal, y_goal


def compute_rho_alpha_beta(
    x_goal: float, y_goal: float, theta_deg: float
) -> tuple[float, float, float]:
    """自車からゴールまでの ρ, α, β を計算する.

    ρ_goal: 自車〜ゴール距離 [m]
    α_goal: 自車ヘディングとゴールへの視線のなす角 [deg] (正=左)
    β_goal: ゴールへの視線とゴール姿勢のなす角 [deg]

    Returns:
      (rho_goal, alpha_goal_deg, beta_goal_deg)
    """
    # ゴール距離
    rho_goal = math.hypot(x_goal, y_goal)

    if rho_goal < 1e-6:
        return 0.0, 0.0, 0.0

    # α_goal: 自車前方(y軸正)からゴールへの視線角度
    alpha_goal = math.degrees(math.atan2(x_goal, y_goal))

    # β_goal: ゴール視線方向とゴール姿勢の差
    # ゴール姿勢は先行車と同じ向き = theta_deg
    beta_goal = wrap_angle(theta_deg - alpha_goal)

    return rho_goal, alpha_goal, beta_goal


class EMAFilter:
    """指数移動平均フィルタ."""

    def __init__(self, alpha: float = 0.3):
        self._alpha = alpha
        self._value: Optional[float] = None

    def update(self, new_value: float) -> float:
        if self._value is None:
            self._value = new_value
        else:
            self._value = self._alpha * new_value + (1.0 - self._alpha) * self._value
        return self._value

    def reset(self):
        self._value = None

    @property
    def value(self) -> Optional[float]:
        return self._value


class RhoAlphaBetaController:
    """ρ-α-β制御則による先行車追従コントローラ.

    使い方:
        ctrl = RhoAlphaBetaController()
        v, omega, log = ctrl.compute(rho=1.5, alpha_deg=10.0, theta_deg=-5.0)
        # v: 速度 [m/s] (正=前進)
        # omega: 角速度 [rad/s] (正=左旋回)
    """

    def __init__(self, config: RhoAlphaBetaConfig = None):
        self.config = config or RhoAlphaBetaConfig()
        self._filter_rho = EMAFilter(self.config.ema_alpha)
        self._filter_alpha = EMAFilter(self.config.ema_alpha)
        self._filter_theta = EMAFilter(self.config.ema_alpha)
        self._lost_count = 0

    def reset(self):
        self._filter_rho.reset()
        self._filter_alpha.reset()
        self._filter_theta.reset()
        self._lost_count = 0

    def compute(
        self,
        rho: float,
        alpha_deg: float,
        theta_deg: float,
        detected: bool = True,
    ) -> tuple[float, float, dict]:
        """制御出力を計算する.

        Args:
            rho: 自車〜先行車距離 [m]
            alpha_deg: 先行車の方位角 [deg] (自車前方=0, 左=正)
            theta_deg: 先行車の相対ヨー角 [deg]
            detected: 先行車が検出されているか

        Returns:
            (v, omega, info_dict)
            v: 速度 [m/s] (正=前進, 負=後退)
            omega: 角速度 [rad/s] (正=左旋回)
            info_dict: デバッグ情報
        """
        info: dict = {
            "rho_raw": rho,
            "alpha_raw": alpha_deg,
            "theta_raw": theta_deg,
            "detected": detected,
        }

        # --- フェイルセーフ: 検出なし ---
        if not detected:
            self._lost_count += 1
            if self._lost_count > 30:
                info["warning"] = "lost_timeout"
                info["action"] = "stop"
                return 0.0, 0.0, info
            info["warning"] = f"lost_{self._lost_count}"
            info["action"] = "hold"
            return 0.0, 0.0, info
        else:
            self._lost_count = 0

        # --- 入力フィルタ ---
        if self.config.filter_rho:
            rho = self._filter_rho.update(rho)
        if self.config.filter_alpha:
            alpha_deg = self._filter_alpha.update(alpha_deg)
        if self.config.filter_theta:
            theta_deg = self._filter_theta.update(theta_deg)

        info["rho_filtered"] = rho
        info["alpha_filtered"] = alpha_deg
        info["theta_filtered"] = theta_deg

        # --- 安全制限: 近すぎる場合 ---
        if rho < self.config.stop_dist:
            info["warning"] = "too_close"
            info["action"] = "stop"
            return 0.0, 0.0, info

        # --- 大角度警告 ---
        if abs(alpha_deg) > self.config.large_angle_threshold:
            info["warning"] = f"large_alpha={alpha_deg:.1f}deg"
        if abs(theta_deg) > self.config.large_angle_threshold:
            info["warning"] = f"large_theta={theta_deg:.1f}deg"

        # --- 座標変換: ゴール位置を計算 ---
        x_goal, y_goal = compute_target_position(
            rho, alpha_deg, theta_deg, self.config.follow_distance
        )
        info["x_goal"] = x_goal
        info["y_goal"] = y_goal

        # --- ρ-α-β 誤差を計算 ---
        rho_goal, alpha_goal, beta_goal = compute_rho_alpha_beta(
            x_goal, y_goal, theta_deg
        )
        info["rho_goal"] = rho_goal
        info["alpha_goal"] = alpha_goal
        info["beta_goal"] = beta_goal

        # --- 制御則 ---
        # v = k_rho * rho_goal
        # omega = k_alpha * alpha_goal + k_beta * beta_goal
        #
        # 単位変換:
        #   alpha_goal, beta_goal は [deg] → [rad] に変換してから omega を計算
        alpha_rad = math.radians(alpha_goal)
        beta_rad = math.radians(beta_goal)

        v = self.config.k_rho * rho_goal
        omega = self.config.k_alpha * alpha_rad + self.config.k_beta * beta_rad

        # --- 出力クランプ ---
        v = max(-self.config.max_speed, min(self.config.max_speed, v))
        omega = max(-self.config.max_omega, min(self.config.max_omega, omega))

        # --- 減速ゾーン: 目標距離の2倍以内で比例減速 ---
        decel_zone = self.config.follow_distance * 2.0
        if rho < decel_zone and v > 0:
            ratio = max(0.0, (rho - self.config.follow_distance) / (decel_zone - self.config.follow_distance))
            v = v * ratio

        # --- オーバーシュート防止: 目標距離を過ぎたら停止 ---
        if rho < self.config.follow_distance and v > 0:
            v = 0.0

        info["v_raw"] = v
        info["omega_raw"] = omega
        info["action"] = "control"

        return v, omega, info

    def compute_command(
        self,
        rho: float,
        alpha_deg: float,
        theta_deg: float,
        detected: bool = True,
    ) -> dict:
        """コマンド辞書を返す (FollowController統合用).

        Returns:
            dict with keys: command, speed, log, chassis_enabled
        """
        v, omega, info = self.compute(rho, alpha_deg, theta_deg, detected)

        if info.get("action") == "stop":
            return {
                "command": "stop",
                "speed": 0,
                "v": 0.0,
                "omega": 0.0,
                "log": f"停止:{info.get('warning', '')}",
            }

        # v と omega → command + speed に変換
        # omega優先だが、vも显著な場合は交互にforwardを送る
        has_turn = abs(omega) > 0.1
        has_forward = v > 0.05
        has_backward = v < -0.05

        if has_turn and has_forward:
            # 交互に turn / forward を送信
            self._turn_toggle = not getattr(self, '_turn_toggle', False)
            if self._turn_toggle:
                command = "left" if omega > 0 else "right"
                speed = int(min(255, max(150, abs(omega) * 200)))
            else:
                command = "forward"
                speed = int(min(255, max(150, v * 150)))
        elif has_turn:
            command = "left" if omega > 0 else "right"
            speed = int(min(255, max(150, abs(omega) * 200)))
        elif has_forward:
            command = "forward"
            speed = int(min(255, max(150, v * 150)))
        elif has_backward:
            command = "backward"
            speed = int(min(255, max(150, abs(v) * 150)))
        else:
            command = "stop"
            speed = 0

        return {
            "command": command,
            "speed": speed,
            "v": round(v, 3),
            "omega": round(omega, 3),
            "log": f"v={v:+.2f} ω={omega:+.2f} ρg={info.get('rho_goal', 0):.2f} αg={info.get('alpha_goal', 0):+.1f}° βg={info.get('beta_goal', 0):+.1f}°",
        }
