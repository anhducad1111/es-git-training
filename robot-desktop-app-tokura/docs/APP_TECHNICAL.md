# robot-desktop-app 技術ドキュメント

## 1. アプリケーション概要

### 1.1 ファイル構成

```
robot-desktop-app/
├── app.py                    # メインアプリケーション
├── config.py                 # 設定管理
├── styles.py                 # スタイル定義
├── connection_manager.py     # WebSocket/接続管理
├── video_manager.py          # 映像管理
├── detection_manager.py      # 検出管理
├── follow_detector.py        # 追従検出（YOLOv8-pose）
├── follow_controller.py      # 追従制御（PID）
├── input_handler.py          # 入力処理
├── cloud_manager.py          # クラウド管理
├── remote_control_server.py  # リモート制御
├── esp32_api.py              # ESP32 REST API
├── rover_ws.py               # WebSocket通信
├── hog_detector.py           # HOG検出器
├── yolo_detector.py          # YOLO検出器
├── image_processor.py        # 画像処理
└── views/                    # UIビュー
    ├── header.py
    ├── main_view.py
    ├── diagnostics_view.py
    ├── snapshots_view.py
    ├── sidebar.py
    ├── bottom_controls.py
    └── log_panel.py
```

### 1.2 クラス構成

```
RoverTeleopApp (app.py)
├── ConnectionManager         # WebSocket/HTTP接続
├── VideoManager              # 映像録画/スナップショット
├── DetectionManager          # 検出処理管理
│   ├── HOGDetector           # 人物検出
│   ├── YOLODetector          # オブジェクト検出
│   ├── FollowDetector        # 車検出（YOLOv8-pose）
│   └── FollowController      # 追従制御
├── InputHandler              # キーボード/マウス入力
├── CloudManager              # クラウドAPI
└── RemoteControlServer       # WebSocketサーバー
```

---

## 2. 接続管理（ConnectionManager）

### 2.1 WebSocket接続

```python
# rover_ws.py
class RoverWebSocket(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def send(self, command: str):
        # コマンドをキューに追加
        self._send_queue.put_nowait((time.time(), command))
```

### 2.2 コマンド送信

```python
# app.py
def _send_command(self, command: str):
    self._add_log("CMD", command)
    self._conn_mgr.send_command(command)
```

### 2.3 対応コマンド

| コマンド | 説明 |
|---------|------|
| `forward` | 前進 |
| `backward` | 後退 |
| `left` | 左旋回 |
| `right` | 右旋回 |
| `stop` | 停止 |
| `speed:N` | 速度設定（80-255） |
| `drive:v,w` | 直接速度制御 |
| `servo:pan,tilt` | ジンバル角度 |

---

## 3. 検出管理（DetectionManager）

### 3.1 検出モード

```python
class DetectionManager(QObject):
    def toggle_detection(self):
        """HOG/YOLO検出の切替"""
        if self._detection_method == "HOG":
            # HOG検出器の初期化/停止
        elif self._detection_method == "YOLO":
            # YOLO検出器の初期化/停止
    
    def toggle_follow_mode(self):
        """追従モードの切替"""
        if self._follow_mode_active:
            # 追従モード停止
        else:
            # 追従モード開始
            self._follow_detector = FollowDetector(confidence=0.35)
            self._follow_controller = FollowController(dry_run=True)
```

### 3.2 FollowDetector（follow_detector.py）

```python
class FollowDetector(QThread):
    """YOLOv8-poseによる車検出"""
    
    detected = pyqtSignal(dict)  # {yaw_deg, dist_m, confidence, bbox}
    
    def run(self):
        while self._running:
            if self._frame is not None:
                result = self._detector.detect(self._frame)
                if result.boxes:
                    # yaw, distanceをラベルから抽出
                    yaw_deg = self._extract_yaw(label)
                    dist_m = self._extract_distance(label)
                    self.detected.emit({...})
```

### 3.3 FollowController（follow_controller.py）

```python
class FollowController:
    """PIDベースの追従制御"""
    
    def update(self, detection: dict):
        """検出結果からコマンドを生成"""
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        command = self._compute_command(yaw_deg, dist_m)
        self._send_command(command)
    
    def _compute_command(self, yaw_deg, dist_m):
        if abs(yaw_deg) < self.config.yaw_deadband:
            return "forward"
        elif yaw_deg > 0:
            return "right"
        else:
            return "left"
```

---

## 4. 映像管理（VideoManager）

### 4.1 フレーム処理

```python
# app.py
def _update_video_frame(self):
    frame = self._conn_mgr.take_frame()
    if frame:
        if self._video_mgr.is_recording:
            self._video_mgr.save_frame(frame)
        if isinstance(frame, QImage):
            self._video_canvas.update_frame_jpeg(frame)
        elif isinstance(frame, bytes):
            self._video_worker.push_frame(frame)

def _on_video_frame_ready(self, pixmap, bgr):
    self._video_canvas.update_frame_jpeg(pixmap)
    if bgr is not None:
        self._detection_mgr.set_frame(bgr)
```

### 4.2 フレームフロー

```
ESP32-CAM (MJPEG)
  → ConnectionManager.take_frame()
  → VideoWorker (JPEGデコード)
  → VideoCanvas (表示)
  → DetectionManager.set_frame()
  → FollowDetector.detect()
```

---

## 5. 入力管理（InputHandler）

### 5.1 キーボード入力

```python
class InputHandler:
    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_W:
            self._send_command("forward")
        elif event.key() == Qt.Key.Key_S:
            self._send_command("backward")
        elif event.key() == Qt.Key.Key_A:
            self._send_command("left")
        elif event.key() == Qt.Key.Key_D:
            self._send_command("right")
        elif event.key() == Qt.Key.Key_Space:
            self._send_command("stop")
```

### 5.2 速度制御

```python
class InputHandler:
    def _tick_speed(self):
        """速度の漸増/漸減"""
        if self._shift_pressed:
            self._current_speed = min(255, self._current_speed + 1)
            self._send_command(f"speed:{self._current_speed}")
        elif self._ctrl_pressed:
            self._current_speed = max(80, self._current_speed - 1)
            self._send_command(f"speed:{self._current_speed}")
```

---

## 6. ESP32 API（esp32_api.py）

### 6.1 REST API

```python
class ESP32API:
    def set_speed(self, speed: int) -> bool:
        """GET /speed?val={80-255}"""
        
    def set_brake(self, enabled: bool) -> bool:
        """GET /api/distance?brake={0|1}"""
        
    def get_distance(self) -> dict:
        """GET /api/distance"""
        
    def set_servo(self, pan: int, tilt: int) -> bool:
        """GET /servo/angle?pan={0-180}&tilt={0-180}"""
        
    def get_pid(self) -> dict:
        """GET /api/pid"""
        
    def set_pid(self, kp=None, ki=None, kd=None, enabled=None, bias=None):
        """GET /api/pid?kp=&ki=&kd=&enabled=&bias="""
```

---

## 7. リモート制御（RemoteControlServer）

### 7.1 WebSocketサーバー

```python
class RemoteControlServer(QThread):
    command_received = pyqtSignal(str)
    
    def __init__(self, host, port):
        # WebSocketサーバーの初期化
    
    def run(self):
        # クライアント接続待機
        # コマンド受信 → command_received.emit()
```

### 7.2 リレーコマンド

```python
# app.py
def _relay_command(self, command):
    self._add_log("REMOTE", f"Relay: {command}")
    self._conn_mgr.send_command(command)
```

---

## 8. データフロー

### 8.1 全体フロー

```
1. 接続
   ESP32-CAM ←→ ConnectionManager ←→ RoverWebSocket

2. 映像
   ESP32-CAM → MJPEG → ConnectionManager → VideoWorker → VideoCanvas

3. 検出
   VideoCanvas → DetectionManager → FollowDetector → FollowController

4. 制御
   FollowController → _send_command() → RoverWebSocket → ESP32

5. 入力
   キーボード → InputHandler → _send_command() → RoverWebSocket → ESP32
```

### 8.2 シグナルフロー

```
FollowDetector.detected
  ↓
DetectionManager._on_follow_detected
  ↓
FollowController.update
  ↓
_send_command()
  ↓
ConnectionManager.send_command
  ↓
RoverWebSocket.send
```

---

## 9. 既存の追従モード実装

### 9.1 FollowControllerの仕様

| パラメータ | 初期値 | 説明 |
|-----------|--------|------|
| yaw_deadband | 5.0度 | この範囲内なら前進 |
| yaw_max | 45.0度 | 最大旋回角 |
| min_distance | 0.3m | 最小距離（停止） |
| max_distance | 2.0m | 最大距離（停止） |
| follow_distance | 0.8m | 目標追従距離 |
| base_speed | 180 | 基準速度 |
| turn_speed | 150 | 旋回時速度 |
| control_rate_hz | 10.0 | 制御ループ頻度 |

### 9.2 制御ロジック

```python
def _compute_command(self, yaw_deg, dist_m):
    # 距離チェック
    if dist_m > self.config.max_distance:
        return "stop"
    if dist_m < self.config.min_distance:
        return "stop"
    
    # 角度チェック
    if abs(yaw_deg) < self.config.yaw_deadband:
        return "forward"
    elif yaw_deg > 0:
        return "right"
    else:
        return "left"
```

---

## 10. app2との違い

| 項目 | robot-desktop-app | app2 |
|------|-------------------|------|
| 検出器 | FollowDetector (YOLOv8-pose) | RcCarPoseDetector |
| 制御 | FollowController (PID) | FollowController (Stanley) |
| 通信 | RoverWebSocket | print（仮実装） |
| 状態遷移 | なし | あり（4状態） |
| 後ろ向き対応 | なし | あり |

---

## 11. 統合時の注意点

### 11.1 追加が必要なもの

1. **Stanley制御の統合**: `follow_controller.py`にStanley制御を追加
2. **状態マシンの追加**: 後ろ向き対応の状態遷移ロジック
3. **安全機能**: 障害物検出、壁衝突回避

### 11.2 既存コードの活用

- `FollowDetector`: そのまま使用可能
- `RoverWebSocket`: そのまま使用可能
- `ESP32API`: PID制御に使用可能

### 11.3 推奨統合手順

1. `follow_controller.py`にStanley制御クラスを追加
2. `FollowController`をStanley制御ベースに書き換え
3. 状態遷移ロジックを追加
4. 安全機能を統合
