# robot-desktop-app-tokura 技術ドキュメント

## 1. アプリケーション概要

### 1.1 ファイル構成

```
robot-desktop-app-tokura/
├── app.py                    # メインアプリケーション
├── config.py                 # 設定管理
├── styles.py                 # スタイル定義
├── connection_manager.py     # WebSocket/接続管理
├── video_manager.py          # 映像管理
├── stream_quality.py         # 映像ストリーム品質の適応制御
├── super_resolution.py       # スナップショットの4倍超解像（HF API + bicubicフォールバック）
├── detection_manager.py      # 検出管理
├── follow_detector.py        # 追従検出（YOLOv8-pose）
├── follow_controller.py      # 追従制御（連続速度制御drive:v,w + 8状態ステートマシン + ジンバル連携）
├── input_handler.py          # 入力処理
├── cloud_manager.py          # クラウド管理
├── cloud_worker.py           # 非同期HTTPリクエスト（PIDパラメータの400msデバウンス送信等）
├── telemetry_poller.py       # /api/telemetry の定期ポーリング
├── remote_control_server.py  # リモート制御
├── esp32_api.py              # ESP32 REST API
├── rover_ws.py               # WebSocket通信
├── hog_detector.py           # HOG検出器
├── yolo_detector.py          # YOLO検出器
├── image_processor.py        # 画像処理
├── rccar_pose_inference/     # 車姿勢推定パッケージ（Kalman, ArUco融合, ジンバル補正）
├── car_follow_car/           # 車追従車の作業中ワークスペース（rccar_pose_inferenceを複製）
├── follow-mode/              # 追従モデルの学習パイプライン
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
├── CloudManager               # クラウドAPI
├── CloudWorker (QThread)      # 非同期HTTPリクエスト（PIDデバウンス送信等）
├── TelemetryPoller (QThread)  # /api/telemetry 定期ポーリング
├── SuperResolutionWorker (QThread)  # スナップショット超解像
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

`FollowController` は単純な離散判定ではなく、`GimbalThread` / `DetectionThread` / `ControlThread` / `CommandThread` の4スレッド構成で動作する。`ControlThread._compute_command()` が本体のロジックで、`FollowState`（8状態、§12.1参照）に応じて距離PID＋ヘディング項のブレンドから連続的な `drive:v,w` コマンドを生成する。

```python
# ControlThread._compute_command() の概略（follow_controller.py:688-824）
def _compute_command(self, detection: dict):
    yaw_deg, dist_m = detection.get("yaw_deg"), detection.get("dist_m")
    bbox, confidence = detection.get("bbox"), detection.get("confidence", 0.0)

    # ステート解決（distance-band + hysteresis）
    self.state = self._hysteresis.update(
        resolve_follow_state(yaw_deg, dist_m, bbox, self.config)
    )
    if self.state in (FollowState.SEARCHING, FollowState.LOST_TIMEOUT,
                      FollowState.HOLDING) or confidence < self.config.min_confidence:
        return self._stop_command(...)  # 離散stopは特定状態のみ

    # 距離PID（Kp=70, Ki=0.4, Kd=10）
    err_lin = dist_m - self.target_distance
    lin_v = self._kp_lin * err_lin + self._ki_lin * self._err_lin_i + self._kd_lin * d_err_lin

    # ヘディング項（画像上のyaw誤差 + ジンバルpanのズレをブレンド）
    combined_heading_error = 0.15 * error_x + 0.85 * pan_error
    w = -combined_heading_error * self.config.max_steering_w

    if abs(combined_heading_error) > TURN_ONLY_HEADING_ERROR:
        command = self._pulsed_spin_command(spin_w)       # その場パルス旋回
    elif abs(err_lin) > self.config.distance_band:
        command = f"drive:{v},{w}"                        # 連続速度+ステアリング
    else:
        command = self._pulsed_spin_command(spin_w)        # 距離帯内・向き微調整

    return {"type": "control", "command": command, ...}
```

離散コマンド（`stop`）は SEARCHING / LOST_TIMEOUT / HOLDING / 低信頼度の場合にのみ使われ、通常の追従中は一貫して `drive:v,w` による連続制御が使われる。

> **既知の技術的負債**: `follow_controller.py`のコメントには過去「既存のStanley/PIDハイブリッド距離制御」とあったが、実際にはStanleyの数式（前輪操舵角の幾何モデル）は使われておらず、距離PID＋ヘディング項の線形ブレンドのみである（コメントは修正済み）。真のStanleyコントローラは `app2/follow_controller.py` にのみ存在する（§13参照）。
>
> **[修正済み]** かつて `detection_manager.py` はUIスライダーから `config.k` / `config.kp` / `config.ki` / `config.kd` / `config.dist_kp` を設定していたが、`FollowConfig` にこれらのフィールドが存在せず、実際のPIDゲイン（`ControlThread.__init__` にハードコード）に反映されないバグがあった。現在は `FollowConfig.kp_lin` / `ki_lin` / `kd_lin`（既定値 70.0 / 0.4 / 10.0）を正式なフィールドとして追加し、`ControlThread._compute_command()` が実行の都度 `self.config` から読むよう修正済み（follow mode実行中のスライダー操作もリアルタイムに反映される）。UIの「k」（Stanleyゲイン、本体では未使用）と「dist」（旧設計の重複した距離Kp）のスライダーは、現在の制御に対応する仕組みがないため削除した。

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

## 8. クラウド連携とPIDデバウンス（CloudWorker / CloudManager）

### 8.1 CloudWorker（cloud_worker.py）

```python
class CloudWorker(QThread):
    """任意のHTTPリクエストをバックグラウンドスレッドで実行する汎用ワーカー"""

    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, method, url, payload=None, timeout=10):
        ...

    def run(self):
        # GET/POST/DELETEを実行し、result/errorシグナルで結果を通知
```

GUIスレッドをブロックしない汎用の非同期HTTPワーカー。クラウドAPIへのテレメトリ送信だけでなく、ESP32へのPIDパラメータ送信にも使われる。

### 8.2 PIDパラメータの400msデバウンス

```python
# app.py
self._pid_apply_timer = QTimer()
self._pid_apply_timer.setSingleShot(True)
self._pid_apply_timer.timeout.connect(self._apply_pid_params)

def _schedule_pid_apply(self):
    """スライダー操作中は何度も呼ばれるが、操作が止まってから
    400ms後の1回だけESP32へ送信する"""
    self._pid_apply_timer.start(400)

def _apply_pid_params(self):
    params = {"kp": ..., "ki": ..., "kd": ..., "enabled": ..., "bias": ...}
    url = f"http://{self._config['car_ip']}/api/pid?{query}"
    worker = CloudWorker("GET", url)
    worker.result.connect(lambda data: self._add_log("PID", ...))
```

スライダーのドラッグ中に同期HTTPリクエストを都度発行していた旧実装ではGUIスレッドがブロックされていた。`QTimer`によるデバウンス＋`CloudWorker`による非同期送信の組み合わせでこれを解消している。

---

## 9. テレメトリポーリング（TelemetryPoller）

```python
# telemetry_poller.py
class TelemetryPoller(QThread):
    data_received = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        while self._running:
            if self._driving:
                self.msleep(100)
                continue
            resp = requests.get(f"http://{self.car_ip}/api/telemetry", timeout=5)
            ...
            self.msleep(self.interval_ms)
```

WebSocketによるプッシュ型テレメトリとは別に、`/api/telemetry`をREST経由で定期ポーリングする。`set_driving(True)`中はポーリングを一時停止し、走行操作中の通信負荷を抑える。

---

## 10. スナップショット超解像（SuperResolutionWorker）

```python
# super_resolution.py
class SuperResolutionWorker(QThread):
    def run(self):
        if not self._use_hf or not self._hf_token:
            self._fallback_bicubic()
            return
        try:
            self._try_hf_api()   # Hugging Face Gradio Space (hichi2-reals) で4倍超解像
        except Exception:
            self._fallback_bicubic()  # 失敗時はPIL bicubic + UnsharpMaskにフォールバック
```

`config.json`の`hf_token`が設定されていれば外部Hugging Face APIで4倍アップスケールを試み、未設定または失敗時はローカルのbicubic補間＋アンシャープマスクにフォールバックする。

---

## 11. データフロー

### 11.1 全体フロー

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

### 11.2 シグナルフロー

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

## 12. 既存の追従モード実装

### 12.1 FollowControllerの仕様

`FollowConfig`（follow_controller.py:22-81）の主要パラメータ（実装の現在値）:

| パラメータ | 現在値 | 説明 |
|-----------|--------|------|
| yaw_deadband | 5.0度 | この範囲内なら向き補正なし |
| yaw_max | 45.0度 | ヘディング誤差正規化の基準角 |
| min_distance | 0.3m | 最小距離（安全停止） |
| max_distance | 2.0m | 最大距離（安全停止） |
| follow_distance | 0.4m | 目標追従距離（32-48cm帯の中心） |
| distance_band | ±0.08m | 目標距離帯の幅（この範囲内では前後進せず向きのみ補正） |
| base_speed | 180 | 基準速度 |
| turn_speed | 190 | 旋回時速度（実機で150はパワー不足と確認） |
| min_pwm | 180 | 最小PWM |
| max_follow_pwm | 200 | FOLLOWING時の前後進PWM上限 |
| max_steering_w | 80 | 旋回成分wの最大値 |
| min_confidence | 0.3 | これを下回ると停止 |
| lost_timeout_sec | 5.0秒 | ロスト継続でLOST_TIMEOUTへ遷移 |
| control_rate_hz | 10.0 | 検出ループ頻度（制御コマンドは12.5Hz上限でレート制限） |

`FollowState`（follow_controller.py:11-19）は8状態:

```
FOLLOWING          # 通常追従（距離PID + ヘディングブレンド）
TURNING            # 大きな旋回が必要
WAITING            # 距離帯外で待機
SEARCHING          # bbox未検出中
HEAD_ON_HOLD       # 対象が正面を向いている等の特殊姿勢
HOLDING            # 距離帯(32-48cm)内で保持
APPROACHING_BLIND  # bboxロスト直後の慣性接近
LOST_TIMEOUT       # ロストが規定時間継続 → 停止
```

状態遷移は `resolve_follow_state()` + `StateHysteresis`（3フレーム連続確認、HEAD_ON_HOLDのみヒステリシスを迂回）で解決される。

### 12.2 制御ロジック

通常のFOLLOWING時は連続速度制御。距離PID（Kp=70, Ki=0.4, Kd=10）とヘディング項（画像上のyaw誤差15% + ジンバルpanのズレ85%のブレンド）から `v`（前後進）と `w`（旋回）を計算し、`drive:{v},{w}` を送信する。ヘディング誤差が大きい場合や距離帯内での向き微調整時は、両輪逆回転のパルス旋回（`_pulsed_spin_command()`、on/off比 0.15s/0.2s）を使う。離散 `stop` はSEARCHING/LOST_TIMEOUT/HOLDING/低信頼度の場合のみ。詳細は §3.3 参照。

---

## 13. app2との違い

| 項目 | robot-desktop-app-tokura（メインアプリ） | app2 |
|------|-------------------|------|
| 検出器 | FollowDetector (YOLOv8-pose) | RcCarPoseDetector |
| 制御 | FollowController（距離PID + ヘディングブレンド、`drive:v,w`連続制御） | FollowController (Stanley) |
| 通信 | RoverWebSocket（実機接続） | print（仮実装、実機未接続） |
| 状態遷移 | あり（8状態、§12.1参照） | あり（4状態: FOLLOWING/TURNING/WAITING/SEARCHING） |
| 後ろ向き対応 | なし | あり |
| ジンバル連携 | あり（フィードフォワード補正＋pan優先旋回、GimbalThread） | 別体系 |

メインアプリの状態遷移はapp2より状態数が多いが、これは「後ろ向き（バック走行）対応」のための遷移ではなく、距離帯・ロスト検知・正面姿勢などをきめ細かく扱うためのもの。後ろ向き対応の状態遷移はapp2側のみに存在する。

---

## 14. 統合時の注意点

### 14.1 実装済みのもの（旧版ドキュメントでは未実装と記載していたが完了済み）

- **状態マシン**: メインアプリはすでに8状態のステートマシンを持つ（§12.1）。ただし「後ろ向き対応」の遷移はapp2側のみで、メインアプリには未統合。
- **ジンバルのフィードフォワード補正**: 旋回時に推定回転角からジンバルpanを先読み補正する仕組みは実装済み（`_pulsed_spin_command()` 内、`feedforward_enabled`）。
- **連続速度制御**: `drive:v,w` による距離PID＋ヘディングブレンドはすでに主経路。

### 14.2 まだ残っているギャップ（今後の課題）

1. **Stanley制御との比較統合**: 本体は距離PID＋ヘディングブレンドのみで、Stanleyの数式（§3.3の技術的負債欄参照）は使われていない。`app2/follow_controller.py` の `StanleyController` を移植し、同一入力でA/B比較できるようにすることが未着手。
2. **後ろ向き（バック走行）対応の状態遷移**: app2にはあるが本体には未統合。
3. **安全機能の統合**: 超音波オブスタクル検知・オートブレーキ（`esp32_api.get_distance()`/`set_brake()`）はfollow-modeの停止条件と連携していない。距離が安全閾値を下回った場合にfollow-modeを自動停止させる配線が必要。
4. **状態推定・予測の活用**: `rccar_pose_inference/pose_kalman.py`（Kalmanフィルタ）や `pose_fusion.py`（ArUco距離融合）は存在し `FollowDetector` に組み込まれているが、`ControlThread` が実際にフィルタ済み推定値（速度・将来位置）を制御入力として使っているかは要検証。速度に基づく将来位置予測は未実装。
5. ~~UIチューニングの配線バグ~~ — **[修正済み]** §3.3参照。`FollowConfig.kp_lin`/`ki_lin`/`kd_lin` を追加し、UIスライダーが実際の距離PIDゲインに反映されるようにした。

### 14.3 既存コードの活用

- `FollowDetector`: そのまま使用可能
- `RoverWebSocket`: そのまま使用可能
- `ESP32API`: 障害物検知・ファームウェア側PID制御に使用可能
- `rccar_pose_inference/pose_kalman.py` / `pose_fusion.py`: 状態推定・予測の土台として再利用可能（新規実装不要）
