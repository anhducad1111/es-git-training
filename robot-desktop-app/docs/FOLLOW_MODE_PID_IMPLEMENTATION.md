# PID制御実装ガイド

## 概要

Follow Mode の制御をバンBang制御からPID制御に変更するためのガイド。
現在はログ出力のみ（DRY RUN）で動作確認中。

## ハイブリッド制御方式

**重要**: Follow Mode では方向に応じて2つの制御方式を切り替える。

```
        12時（正面向き）
            ↑
    9時 ←  車A  → 3時
            ↓
        6時（後ろ向き）
```

| 方向 | 制御方式 | 理由 |
|------|----------|------|
| **3時〜9時** | Stanley制御 | 前の車がこちらに向いている |
| **9時〜3時** | PID制御 | 前の車がこちらから離れている |

### なぜハイブリッドが良いのか

**3時〜9時方向（Stanley制御）**:
- 横方向の誤差を考慮した安定した追従
- 速度に応じたステアリング調整
- 正面からの接近に最適化

**9時〜3時方向（PID制御）**:
- 距離に応じた速度制御が可能
- 積分制御で定常偏差を修正
- 滑らかな速度変化

詳細は [ハイブリッド制御方式の利点](FOLLOW_MODE_HYBRID_CONTROL.md) を参照

## 現在の制御方式 vs PID制御

### 現在: バンBang制御（ON/OFF）

```
yaw角が5°以上 → right (100%)
yaw角が-5°以下 → left (100%)
yaw角が-5°~+5° → forward (100%)
```

**問題点**: yaw角が6°でも44°でも同じ速度で旋回する

### 変更後: PID制御

```
error = yaw角（目標との誤差）
output = Kp × error + Ki × ∫error dt + Kd × d(error)/dt

outputに応じて速度を変化させる
```

**利点**: yaw角に応じた滑らかな速度制御が可能

## PID制御の仕組み

### 基本式

```
output(t) = Kp × e(t) + Ki × ∫e(τ)dτ + Kd × de(t)/dt
```

| 項 | 名前 | 役割 |
|---|------|------|
| Kp × e(t) | 比例項 | 誤差に比例した出力 |
| Ki × ∫e(τ)dτ | 積分項 | 累積誤差の補正 |
| Kd × de(t)/dt | 微分項 | 誤差の変化率の抑制 |

### ゲインの役割

```
Kp（比例ゲイン）: 大きい → 反応速い、振動しやすい
Ki（積分ゲイン）: 大きい → 積分飽和、オーバーシュートしやすい
Kd（微分ゲイン）: 大きい → 過減衰、遅れやすい
```

## 実装手順

### Step 1: PIDControllerクラスの修正

`follow_controller.py` の `PIDController` クラスを修正:

```python
class PIDController:
    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.1) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._prev_error = 0.0
        self._integral = 0.0
        self._integral_limit = 100.0  # 積分項のリミット

    def compute(self, error: float, dt: float = 0.1) -> float:
        # 積分項（ワインドアップ防止）
        self._integral += error * dt
        self._integral = max(-self._integral_limit, 
                           min(self._integral_limit, self._integral))
        
        # 微分項
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error
        
        # PID出力
        return self.kp * error + self.ki * self._integral + self.kd * derivative

    def reset(self) -> None:
        self._prev_error = 0.0
        self._integral = 0.0
```

### Step 2: FollowConfigにPIDゲイン追加

```python
@dataclass
class FollowConfig:
    # ... 既存の設定 ...
    
    # PID制御用ゲイン
    kp: float = 2.0      # 比例ゲイン（yaw制御用）
    ki: float = 0.1      # 積分ゲイン
    kd: float = 0.5      # 微分ゲイン
    
    # 距離制御用PID
    dist_kp: float = 1.0
    dist_ki: float = 0.0
    dist_kd: float = 0.1
```

### Step 3: FollowControllerにyaw用PID追加

```python
class FollowController:
    def __init__(self, config: FollowConfig = None, dry_run: bool = False):
        self.config = config or FollowConfig()
        # ... 既存の初期化 ...
        
        # yaw制御用PID
        self.pid_yaw = PIDController(
            kp=self.config.kp,
            ki=self.config.ki,
            kd=self.config.kd
        )
        
        # 距離制御用PID
        self.pid_distance = PIDController(
            kp=self.config.dist_kp,
            ki=self.config.dist_ki,
            kd=self.config.dist_kd
        )
```

### Step 4: _control_following()をPID対応に変更

```python
def _control_following(self, yaw_deg: float, dist_m: float) -> None:
    # yaw制御（Stanley → PIDに変更）
    yaw_output = self.pid_yaw.compute(yaw_deg)
    
    # 出力の正規化 (-1.0 ~ 1.0)
    normalized_output = max(-1.0, min(1.0, yaw_output / self.config.yaw_max))
    
    # 距離制御
    dist_error = dist_m - self.target_distance
    dist_output = self.pid_distance.compute(dist_error)
    throttle = max(0.0, min(1.0, dist_output))
    
    # コマンド生成
    if abs(normalized_output) < 0.1:  # deadband
        command = "forward"
        direction = "正面"
    elif normalized_output > 0:
        command = "right"
        direction = "右"
    else:
        command = "left"
        direction = "左"
    
    # 速度計算
    speed = int(throttle * self.config.base_speed)
    
    # ログ出力
    self._log(
        f"[PID] yaw出力: {yaw_output:+.1f} (正規化: {normalized_output:+.2f}) | "
        f"速度: {speed} | "
        f"状態: {command} | yaw={yaw_deg:+.1f}° dist={dist_m:.2f}m"
    )
```

### Step 5: DRY RUN時のログ出力

```python
def _log(self, message: str) -> None:
    if self._log_callback:
        self._log_callback("FOLLOW", message)
    if self._dry_run:
        print(f"[FOLLOW] DRY RUN: {message}")
    elif self._send_command:
        self._send_command(message)
```

## パラメータチューニング

### 初期値

| パラメータ | 値 | 調整指針 |
|-----------|-----|---------|
| kp | 2.0 | 大きい → 反応速い、振動 |
| ki | 0.1 | 大きい → 積分飽和 |
| kd | 0.5 | 大きい → 過減衰 |
| yaw_max | 45° | 最大旋回角 |
| yaw_deadband | 5° | 旋回しない範囲 |

### チューニング手順

1. **Ki=0, Kd=0** にしてKpだけを調整
2. 振動するまでKpを大きくする
3. 振動し始めたらKpを半分にする
4. Kdを増やして振動を抑制
5. 積分偏差がある場合はKiを少し増やす

### テストシナリオ

```
1. 正面に車がある (yaw=0°, dist=1.0m)
   → forward, 速度180

2. 右に車がある (yaw=+30°, dist=1.0m)
   → right, 速度120

3. 左に車がある (yaw=-30°, dist=1.0m)
   → left, 速度120

4. 近づきすぎ (yaw=0°, dist=0.2m)
   → stop

5. 遠ざかりすぎ (yaw=0°, dist=2.5m)
   → stop
```

## ログ出力例

```
[FOLLOW] DRY RUN: [PID] yaw出力: +12.3 (正規化: +0.27) | 速度: 180 | 状態: right | yaw=+12.3° dist=1.00m
[FOLLOW] DRY RUN: [PID] yaw出力: -5.1 (正規化: -0.11) | 速度: 150 | 状態: left | yaw=-5.1° dist=0.85m
[FOLLOW] DRY RUN: [PID] yaw出力: +2.1 (正規化: +0.05) | 速度: 180 | 状態: forward | yaw=+2.1° dist=0.90m
```

## 注意事項

1. **積分ワインドアップ**: 積分項にリミットを設ける
2. **微分詰まり**: 微分項にはフィルタをかけること
3. **サンプルタイム**: dtは一定に保つ（制御ループに依存）
4. **リセット**: 状態遷移時にPIDの積分項をリセット

## 次のステップ

1. [ ] ログ出力でPIDの動作を確認
2. [ ] パラメータを調整
3. [ ] dry_runをFalseに変更
4. [ ] 実機テスト
5. [ ] ハイブリッド制御の切り替えロジックを実装
