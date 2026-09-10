# 追従モード実装計画

## 概要

ESP32-CAMの映像からYOLOで前の車を検出し、Stanley制御で後ろの車を自動追従するシステム。

## 関連ドキュメント

- [PID制御実装ガイド](FOLLOW_MODE_PID_IMPLEMENTATION.md) - PID制御の詳細な実装手順
- [ハイブリッド制御方式の利点](FOLLOW_MODE_HYBRID_CONTROL.md) - Stanley+PIDハイブリッド制御の説明

## 使用シナリオ

**この追従モードは、前の車がこちらに向いている場合（3時〜9時方向）に使用します。**

```
        12時（正面向き）
            ↑
    9時 ←  車A  → 3時
            ↓
        6時（後ろ向き）
```

- **3時〜9時方向**: 前の車がカメラに向いてくるシナリオ
- **使用不可**: 12時方向（正面向き）や6時方向（後ろ向き）の追従には対応していません
- **前提条件**: 前の車にArUcoマーカーが設置されており、YOLOv8-Poseで検出可能であること

## 技術構成

| 技術 | 用途 |
|------|------|
| YOLOv8-Pose | 車の検出・キーポイント検出 |
| Stanley制御 | 追従アルゴリズム |
| WebSocket | ESP32との通信 |
| PyQt6 | GUI |
| Python | 全体実装 |

## ファイル構成

```
app2/
├── detectors.py          # 変更: Detectionにyaw_deg, dist_m追加
├── follow_controller.py  # 新規: Stanley制御ロジック
├── app.py                # 変更: Follow Mode UI追加
```

## 実装手順

### Step 1: Detectionクラスの拡張

`detectors.py`の`Detection`クラスにフィールドを追加:

```python
@dataclass(frozen=True)
class Detection:
    boxes: list[tuple[int, int, int, int]]
    labels: list[str]
    scores: list[float]
    poses: list[MarkerPose | None] = field(default_factory=list)
    yaw_deg: float | None = None
    dist_m: float | None = None
```

`RcCarPoseDetector.detect()`の返り値に`yaw_deg`, `dist_m`を格納。

### Step 2: Stanley制御の実装

`follow_controller.py`を新規作成:

```python
import math
from enum import Enum

class FollowState(Enum):
    FOLLOWING = "following"
    TURNING = "turning"
    WAITING = "waiting"
    SEARCHING = "searching"

class StanleyController:
    def __init__(self, k=0.5, max_steer=30.0):
        self.k = k
        self.max_steer = max_steer

    def control(self, yaw_deg, dist_m, speed):
        psi = math.radians(yaw_deg)
        e = dist_m * math.sin(psi)
        if speed > 0.1:
            delta = psi + math.atan2(self.k * e, speed)
        else:
            delta = psi
        delta_deg = max(-self.max_steer, min(self.max_steer, math.degrees(delta)))
        
        if abs(delta_deg) < 10 and dist_m > 0.5:
            throttle = min(1.0, dist_m / 2.0)
        elif dist_m < 0.3:
            throttle = 0.0
        else:
            throttle = 0.3
        return delta_deg, throttle

class FollowController:
    THRESHOLDS = {
        "turn_start_dist": 1.0,
        "stop_dist": 0.3,
        "turn_complete_yaw": 30,
        "follow_max_yaw": 60,
    }
    
    def __init__(self, rover_ws, esp32_api):
        self.ws = rover_ws
        self.esp32 = esp32_api
        self.stanley = StanleyController()
        self.state = FollowState.SEARCHING
        self.target_speed = 100
    
    def update(self, yaw_deg, dist_m):
        self._check_transitions(yaw_deg, dist_m)
        if self.state == FollowState.FOLLOWING:
            self._control_following(yaw_deg, dist_m)
        elif self.state == FollowState.TURNING:
            self._control_turning(yaw_deg)
        elif self.state == FollowState.WAITING:
            self._control_waiting()
        elif self.state == FollowState.SEARCHING:
            self._control_searching()
    
    def _check_transitions(self, yaw_deg, dist_m):
        if self.state == FollowState.FOLLOWING:
            if abs(yaw_deg) > 90 and dist_m > self.THRESHOLDS["turn_start_dist"]:
                self.state = FollowState.TURNING
            elif abs(yaw_deg) > 90:
                self.state = FollowState.WAITING
        elif self.state == FollowState.TURNING:
            if abs(yaw_deg) < self.THRESHOLDS["turn_complete_yaw"]:
                self.state = FollowState.FOLLOWING
            elif dist_m < self.THRESHOLDS["stop_dist"]:
                self.state = FollowState.WAITING
        elif self.state == FollowState.WAITING:
            if abs(yaw_deg) < self.THRESHOLDS["turn_complete_yaw"]:
                self.state = FollowState.FOLLOWING
        elif self.state == FollowState.SEARCHING:
            if abs(yaw_deg) < self.THRESHOLDS["follow_max_yaw"]:
                self.state = FollowState.FOLLOWING
            elif yaw_deg != 0:
                self.state = FollowState.TURNING
    
    def _control_following(self, yaw_deg, dist_m):
        steering, throttle = self.stanley.control(yaw_deg, dist_m, self.target_speed / 100.0)
        if abs(steering) < 5:
            self.ws.send("forward")
        elif steering > 0:
            self.ws.send("right")
        else:
            self.ws.send("left")
        self.ws.send(f"speed:{int(throttle * self.target_speed)}")
    
    def _control_turning(self, yaw_deg):
        direction = "right" if yaw_deg > 0 else "left"
        self.ws.send(direction)
        self.ws.send("speed:80")
    
    def _control_waiting(self):
        self.ws.send("stop")
    
    def _control_searching(self):
        self.ws.send("forward")
        self.ws.send("speed:50")
    
    def stop(self):
        self.ws.send("stop")
        self.state = FollowState.SEARCHING
```

### Step 3: UI統合

`app.py`に追加:

```python
# _build_ui()内で検出グループに追加
self.follow_check = QCheckBox("Follow Mode")
self.follow_check.setToolTip("Stanley制御で前の車を自動追従")
detection_layout.addWidget(self.follow_check)

# MainWindow.__init__に追加
self.follow_controller = None

# start_workers()で初期化
if self.follow_check.isChecked():
    self.follow_controller = FollowController(self._rover_ws, self.esp32_api)

# _display_latest()内で追加
if self.follow_check.isChecked() and packet.detection and packet.detection.yaw_deg is not None:
    self.follow_controller.update(packet.detection.yaw_deg, packet.detection.dist_m)
```

### Step 4: 安全機能

```python
# FollowController.update()に追加
def update(self, yaw_deg, dist_m, obstacle_dist=None):
    if obstacle_dist and obstacle_dist < 0.3:
        self.ws.send("stop")
        return
    if dist_m < 0.2:
        self.ws.send("stop")
        return
    # ... 通常の制御ロジック
```

## データフロー

```
ESP32-CAM (MJPEG)
  → CaptureWorker (JPEGデコード)
  → InferenceWorker (RcCarPoseDetector)
  → Detection(yaw_deg, dist_m)
  → FollowController (Stanley制御)
  → rover_ws.send("left"/"right"/"forward")
  → rover_ws.send("speed:N")
  → ESP32 → モーター
```

## 状態遷移図

```
┌─────────────────────────────────────────────────────┐
│                    FOLLOWING                        │
│  (通常のStanley追従 - 車が前方にいる)                 │
└──────────┬──────────────────────┬───────────────────┘
           │ yaw > 90°           │ yaw < 30°
           │ && dist > 1.0m      │ (旋回完了)
           ▼                     │
┌──────────────────────┐         │
│      TURNING         │─────────┘
│  (低速で旋回中)       │
└──────┬───────────────┘
       │ yaw > 90°
       │ && dist <= 1.0m
       ▼
┌──────────────────────┐
│      WAITING         │
│  (停止して車を待つ)    │
└──────────┬───────────┘
           │ yaw < 30°
           ▼
       FOLLOWING
```

## 状態遷移テーブル

| 現在の状態 | 条件 | 次の状態 |
|-----------|------|---------|
| FOLLOWING | `abs(yaw) > 90° && dist > 1.0m` | TURNING |
| FOLLOWING | `abs(yaw) > 90° && dist <= 1.0m` | WAITING |
| FOLLOWING | 検出なし | SEARCHING |
| TURNING | `abs(yaw) < 30°` | FOLLOWING |
| TURNING | タイムアウト（5秒） | WAITING |
| TURNING | `dist < 0.3m` | WAITING（緊急停止） |
| WAITING | `abs(yaw) < 30°` | FOLLOWING |
| WAITING | タイムアウト（10秒） | SEARCHING |
| SEARCHING | 検出成功 && `abs(yaw) < 60°` | FOLLOWING |
| SEARCHING | 検出成功 && `abs(yaw) >= 60°` | TURNING |

## パラメータチューニング

| パラメータ | 初期値 | 調整指針 |
|-----------|--------|---------|
| k (Stanleyゲイン) | 0.5 | 大きいほど横方向の補正が強くなる |
| max_steer | 30度 | 最大旋回角 |
| target_speed | 100 | 基準速度 |
| turn_start_dist | 1.0m | 旋回開始距離 |
| stop_dist | 0.3m | 停止距離 |
| turn_complete_yaw | 30度 | 旋回完了角度 |

## テスト計画

1. **単体テスト**: Stanley制御の計算が正しいか
2. **統合テスト**: WebSocket経由でESP32にコマンドが送信されるか
3. **実機テスト**: 実際の車で追従動作を確認

## 既存コードとの連携

- `RcCarPoseDetector`: 既存のYOLOv8-Pose検出器を使用
- `rover_ws.py`: 既存のWebSocket通信を使用
- `esp32_api.py`: 既存のESP32 APIを使用
