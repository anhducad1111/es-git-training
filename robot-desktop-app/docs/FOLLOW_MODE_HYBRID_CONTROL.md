# ハイブリッド制御方式の利点

## 概要

Follow Mode では、車の向きに応じて2つの制御方式を切り替えるハイブリッド制御を採用する。

## 方向による制御方式の切り替え

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

## なぜハイブリッドが良いのか

### 3時〜9時方向（Stanley制御が適している）

**シナリオ**: 前の車がこちらに向いて过来る

```
     自分の車
         ↓
     ←←← 車A（3時〜9時方向）
```

**Stanley制御の利点**:
- 横方向の誤差を考慮した安定した追従
- 速度に応じたステアリング調整
- 正面からの接近に最適化

**具体的な動作**:
```python
# Stanley制御の計算式
psi = math.radians(yaw_deg)  # 車の向き
e = dist_m * math.sin(psi)   # 横方向の誤差
delta = psi + math.atan2(k * e, speed)  # ステアリング角
```

### 9時〜3時方向（PID制御が適している）

**シナリオ**: 前の車がこちらから離れていく

```
     自分の車
         ↑
     →→→ 車A（9時〜3時方向）
```

**PID制御の利点**:
- 距離に応じた速度制御が可能
- 積分制御で定常偏差を修正
- 滑らかな速度変化

**具体的な動作**:
```python
# PID制御の計算式
error = dist_m - target_distance  # 距離誤差
output = Kp * error + Ki * ∫error dt + Kd * d(error)/dt
throttle = max(0.0, min(1.0, output))
```

## ハイブリッド制御のメリット

### 1. 最適な制御方式の選択

| 状況 | Stanley | PID | 選択 |
|------|---------|-----|------|
| 正面からの接近 | ○ | △ | Stanley |
| 背面への離脱 | △ | ○ | PID |
| 横方向の追従 | ○ | × | Stanley |
| 距離維持 | × | ○ | PID |

### 2. 安定性の向上

```
Stanley制御:
- 横方向の誤差補正に優れる
- 速度変化への追従が良い

PID制御:
- 距離制御が安定
- 積分制御で定常偏差を修正
```

### 3. 状態遷移の平滑化

```
SEARCHING → FOLLOWING (Stanley)
    ↓
TURNING (Stanley)
    ↓
FOLLOWING (PID)
    ↓
WAITING
```

## 実装例

### 状態遷移ロジック

```python
def _check_transitions(self, yaw_deg: float, dist_m: float) -> None:
    old_state = self.state
    
    if self.state == FollowState.FOLLOWING:
        # 3時〜9時方向: Stanley制御を維持
        if abs(yaw_deg) > 90 and dist_m > self.config.turn_start_dist:
            self.state = FollowState.TURNING
        # 9時〜3時方向: PID制御に切り替え
        elif abs(yaw_deg) > 90:
            self.state = FollowState.WAITING
    
    # ... 他の状態遷移 ...
```

### 制御方式の切り替え

```python
def _control_following(self, yaw_deg: float, dist_m: float) -> None:
    # 3時〜9時方向: Stanley制御
    if abs(yaw_deg) <= 90:
        steering = self.stanley.control(yaw_deg, dist_m, self.config.base_speed / 100.0)
        self._log(f"[Stanley] ステアリング: {steering:+.1f}°")
    
    # 9時〜3時方向: PID制御
    else:
        dist_error = dist_m - self.target_distance
        throttle = self.pid_distance.compute(dist_error)
        self._log(f"[PID] 速度: {throttle:.2f}")
```

## ログ出力例

```
[FOLLOW] DRY RUN: [Stanley] ステアリング: +12.3° | yaw=+12.3° dist=1.00m
[FOLLOW] DRY RUN: [Stanley] ステアリング: -5.1° | yaw=-5.1° dist=0.85m
[FOLLOW] DRY RUN: [PID] 速度: 0.75 | yaw=+100.0° dist=1.50m
[FOLLOW] DRY RUN: [状態遷移] FOLLOWING → TURNING | yaw=+95.0° dist=1.20m
```

## パラメータ調整

### Stanley制御パラメータ

| パラメータ | 値 | 調整指針 |
|-----------|-----|---------|
| k | 0.5 | 横方向の補正ゲイン |
| max_steer | 30° | 最大旋回角 |

### PID制御パラメータ

| パラメータ | 値 | 調整指針 |
|-----------|-----|---------|
| dist_kp | 1.0 | 距離誤差の比例ゲイン |
| dist_ki | 0.0 | 積分ゲイン |
| dist_kd | 0.1 | 微分ゲイン |

## まとめ

ハイブリッド制御により：
1. **3時〜9時方向**: Stanley制御で安定した追従
2. **9時〜3時方向**: PID制御で滑らかな速度制御
3. **全体**: 最適な制御方式を状況に応じて自動選択
