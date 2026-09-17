# Rover Teleop Cockpit 技術ドキュメント

## 全機能・使用技術一覧

---

## 1. アプリケーションフレームワーク

| 技術 | 用途 | 対象箇所 |
|------|------|----------|
| **Python 3.x** | 全アプリケーション言語 | 全体 |
| **PyQt6** | GUIフレームワーク | `app.py`, `views/*`, `widgets/*`, `main.py` |
| **PyQt6.QtCore** | シグナル/スロット、タイマー、Qt基本クラス | 全UIファイル |
| **PyQt6.QtWidgets** | UIウィジェット（QPushButton, QLabel, QVBoxLayout等） | 全UIファイル |
| **PyQt6.QtGui** | QPainter, QFont, QImage, QPixmap, QTransform | `widgets/video_canvas.py`, `widgets/gimbal_hud.py` |
| **PyQt6.QtMultimedia** | メディア処理 | 映像関連 |

---

## 2. ネットワーク通信

### 2.1 WebSocket（ESP32との双方向通信）

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **websocket-client** | WebSocketクライアント | `rover_ws.py`, `connection_manager.py` |
| **websockets** | 非同期WebSocketサーバー | `remote_control_server.py` |
| **asyncio** | 非同期イベントループ | `remote_control_server.py`, `connection_manager.py` |

**機能**: ローバーコマンドの送受信、Webブラウザからのリモート制御

### 2.2 HTTP REST

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **requests** | HTTPクライアント | `esp32_api.py`, `cloud_api.py`, `telemetry_poller.py` |
| **HTTP 1.1** | REST API通信 | ESP32 REST API、クラウドAPI |

**機能**: ESP32のREST API（サーボ制御、センサーデータ）、クラウドAPI（テレメトリ、メディア）

### 2.3 MJPEGストリーム

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **HTTP** | MJPEGストリーム取得 | `mjpeg_receiver.py` |
| **multipart/x-mixed-replace** | マルチパートJPEGパース | `mjpeg_receiver.py` |
| **JPEGデコード** | フレームデコード | `mjpeg_receiver.py`, `video_worker.py` |

**機能**: ESP32-Camからのリアルタイム映像ストリーム取得

---

## 3. 画像処理・コンピュータビジョン

### 3.1 OpenCV

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **OpenCV (cv2)** | 画像処理、コンピュータビジョン | `detection_manager.py`, `widgets/video_canvas.py` |
| **cv2.aruco** | ArUcoマーカー検出 | `detection_manager.py` |

**機能**: 物体検知、マーカー追従、バウンディングボックス描画

### 3.2 YOLO / HOG 検知

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **HOG + SVM** | 人物検知（従来方式） | `detection_manager.py` |
| **YOLOv8-pose** | 姿勢推定（フォロー走行） | `follow_mode/` |

**機能**: 人物検知、フォロー走行におけるポーズ推定

### 3.3 画像処理ライブラリ

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **PIL (Pillow)** | 画像操作（リサイズ、フィルター） | `video_manager.py` |
| **numpy** | 数値計算 | `video_manager.py`, `follow_controller.py` |
| **cv2** | CLAHE（コントラスト強調）、ノイズ除去 | `snapshots_view.py` |

**機能**: スナップショットの後処理（AUTO CORRECT、コントラスト強調、ノイズ除去、Bicubicアップスケール）

### 3.4 スーパー解像度

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **Hugging Face Gradio API** | 4xスーパー解像度 | `video_manager.py` |
| **Bicubic + Unsharp Mask** | API障害時のフォールバック | `video_manager.py` |

---

## 4. AI・機械学習

### 4.1 Gemini AI

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **google-genai** | Gemini APIクライアント | `gemini_chat.py` |
| **gemini-3.5-flash-lite** | モデル名 | `gemini_chat.py` |

**機能**: センサーデータのAI分析チャット、カスタムチャート作成ツール

### 4.2 Pose Inference（rccar_pose_inference）

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **OpenCV ArUco** | マーカー検出と姿勢推定 | `rccar_pose_inference/` |
| **光線幾何計算** | カメラ位置非依存の角度計算 | `follow-mode/raybasedcorrection.py` |
| **Kalman Filter** | 位置推定（予測制御） | `app2/`, `follow_controller.py` |

**機能**: ロボットの位置・速度・方向の推定、フォロー走行の制御

### 4.3 Hugging Face

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **HF_TOKEN** | API認証 | `secrets.py`, `video_manager.py` |
| **SuperResolutionWorker** | 画像アップスケール | `video_manager.py` |

---

## 5. データ可視化

### 5.1 Matplotlib

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **matplotlib** | 時系列チャート | `widgets/sensor_chart.py` |
| **FigureCanvasQTAgg** | PyQt6統合キャンバス | `widgets/sensor_chart.py` |

**機能**: センサーデータのリアルタイムグラフ表示

### 5.2 QTableWidget

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **PyQt6.QtWidgets.QTableWidget** | データテーブル表示 | `views/diagnostics_view.py` |

---

## 6. データベース・ストレージ

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **SQLite (JSON)** | ローカル設定保存 | `config.py` |
| **CSV** | キャリブレーションログ | `calibration.py` |
| **ファイルシステム** | スナップショット・録画保存 | `video_manager.py` |

---

## 7. シリアル通信（ESP32 MCU）

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **UART/シリアル** | ジャイロデータ取得 | `follow_controller.py` |
| **MPU-6050** | 6軸IMU（ジャイロ+加速度計） | ESP32ハードウェア |

---

## 8. センサー・ハードウェアAPI

### 8.1 ESP32 API

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **ESP32API** | HTTP RESTクライアント | `esp32_api.py` |
| **servo:{pan},{tilt}** | サーボ制御 | `esp32_api.py` |
| **set_led()** | LED輝度制御 | `esp32_api.py` |
| **set_quality()** | カメラ画質設定 | `esp32_api.py` |
| **get_distance()** | 超音波距離取得 | `esp32_api.py` |
| **set_brake()** | ブレーキ制御 | `esp32_api.py` |

### 8.2 テレメトリ

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **TelemetryPoller** | HTTP REST定期ポーリング | `telemetry_poller.py` |
| **GET /api/telemetry** | センサーデータ取得 | `telemetry_poller.py` |

---

## 9. ロボット制御

### 9.1 フォロー走行制御

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **FollowController** | 8状態ステートマシン | `follow_controller.py` |
| **ControlThread** | モーター制御スレッド (~10Hz) | `follow_controller.py` |
| **GimbalThread** | ジンバル追従スレッド (~20Hz) | `follow_controller.py` |
| **PID制御** | 距離制御、航法制御 | `follow_controller.py` |
| **FollowConfig** | フォロー走行パラメータ設定 | `follow_controller.py` |

### 9.2 距離PIDパラメータ

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| kp_lin | 70 | 距離比例ゲイン |
| ki_lin | 0.4 | 距離積分ゲイン |
| kd_lin | 10 | 距離微分ゲイン |

### 9.3 モーター制御

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **PWM** | モーター速度制御 | ESP32ハードウェア |
| **差動駆動** | 左右独立モーター制御 | `follow_controller.py` |
| **min_pwm** | 最小PWM (180) | `follow_controller.py` |
| **max_follow_pwm** | 最大フォローPWM (200) | `follow_controller.py` |
| **body_deg_per_sec_per_pwm** | PWM->速度変換係数 | `follow_controller.py` |

---

## 10. 動画・録画

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **JPEGエンコーディング** | フレーム圧縮 | `video_manager.py`, `mjpeg_receiver.py` |
| **QPixmap** | フレーム表示 | `widgets/video_canvas.py` |
| **QThread** | 録画スレッド | `video_manager.py` |
| **キュー** | フレームバッファリング | `video_manager.py` |
| **H.264/MP4** | 録画動画フォーマット（想定） | `video_manager.py` |

---

## 11. リモート制御

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **WebSocket** | ブラウザとの双方向通信 | `remote_control_server.py` |
| **asyncio** | 非同期サーバー | `remote_control_server.py` |
| **QLineEdit** | IP/ポート入力 | `views/header.py` |
| **認証トークン** | リモート制御の承認 | `views/sidebar.py` |

---

## 12. UI/UX技術

### 12.1 スタイリング

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **QSS (Qt Style Sheet)** | CSSベースのUIスタイリング | `styles.py`, 全views・widgets |
| **DARK_STYLE** | ダークテーマ定義 | `styles.py` |
| **rgba()** | 透過色指定 | 全スタイルシート |

### 12.2 カスタム描画

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **QPainter** | カスタム描画（ジンバルHUD、速度メーター） | `widgets/gimbal_hud.py`, `widgets/speed_meter.py` |
| **QTransform** | 座標変換（映像フリップ） | `widgets/video_canvas.py` |
| **QPen, QBrush** | 図形描画 | `widgets/gimbal_hud.py` |
| **QFont** | フォント設定 | 全UIファイル |
| **QRadialGradient** | グラデーション | `widgets/camera_direction.py` |

### 12.3 アニメーション

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **QTimer** | 定期的更新（30ms、33ms、10s） | `app.py`, `widgets/gimbal_hud.py` |
| **指数減衰補間** | スムーズな値遷移 | `widgets/gimbal_hud.py` |

---

## 13. デバッグ・テスト

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **Python unittest** | 単体テスト | `tests/*` |
| **pytest** | テスト実行 | テストファイル |
| **logging** | ログ出力 | `app.py` |
| **CalibrationLogger** | キャリブレーションログ | `calibration.py` |
| **CSV** | テスト結果保存 | `logs/calibration.csv` |

---

## 14. 外部ライブラリ・依存関係

### `requirements.txt` に記載されている主なライブラリ

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| PyQt6 | 6.11.0 | GUIフレームワーク |
| websocket-client | - | WebSocketクライアント |
| websockets | - | 非同期WebSocketサーバー |
| requests | - | HTTPクライアント |
| opencv-python | 4.10.0.84 | 画像処理 |
| numpy | - | 数値計算 |
| google-genai | - | Gemini AI API |
| matplotlib | - | データ可視化 |
| Pillow | - | 画像操作 |

---

## 15. ハードウェア仕様

| コンポーネント | 仕様 | 接続方式 |
|---------------|------|----------|
| ESP32-MCU | Wi-Fiマイコン | Wi-Fi (WebSocket + HTTP) |
| ESP32-Cam | カメラモジュール | Wi-Fi (MJPEGストリーム) |
| MPU-6050 | 6軸IMU | UART（ESP32内蔵） |
| 超音波センサー | 距離測定 | GPIO（ESP32内蔵） |
| モーター | 差動駆動 | PWM（ESP32内蔵） |
| サーボ | ジンバル制御 | PWM（ESP32内蔵） |
| LED | カメラLED | GPIO（ESP32内蔵） |

---

## 16. プロジェクト構造技術

| 技術 | 用途 | 対象 |
|------|------|------|
| **Pythonモジュール** | コードのモジュール化 | 全パッケージ |
| **QStackedWidget** | ページ切り替え | `app.py` |
| **QThreadPool** | スレッドプール | `cloud_worker.py` |
| **pyqtSignal** | イベント通知 | 全マネージャー・UI間通信 |
| **CloudWorker** | 非同期HTTPワーカー | `cloud_worker.py` |
| **QIntValidator** | 数値入力バリデーター | `views/main_view.py` |

---

## 17. デバッグ・開発技術

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **print()** | デバッグ出力 | `app.py`, `video_canvas.py` |
| **f-string** | ログメッセージフォーマット | 全ファイル |
| **hasattr()** | 動的チェック | `app.py`, `views/*` |
| **try/except** | エラーハンドリング | `app.py`, `cloud_api.py` |
| **QTimer (SingleShot)** | デバウンス | `app.py` |
| **QThread** | バックグラウンド処理 | 全ワーカー |

---

## 18. セキュリティ

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **secrets.py** | APIキーの分離 | `secrets.py` |
| **.gitignore** | 秘密情報のGit除外 | `.gitignore` |
| **config.json** | 設定ファイルの分離 | `config.py` |
| **認証トークン** | Webリモート制御の認可 | `remote_control_server.py` |

---

## 19. パフォーマンス技術

| 技術 | 用途 | 対象ファイル |
|------|------|-------------|
| **デバウンス** | 不要なHTTP送信の抑制 | `app.py` (400ms/300ms/150ms) |
| **CloudWorker** | 非同期HTTPリクエスト | `cloud_worker.py` |
| **QThread** | メインスレッドの分離 | 全ワーカー |
| **フレームドロップ** | 録画キューのオーバーフロー処理 | `video_manager.py` |
| **LatestSlot** | スレッドセーフなフレームバッファ | `mjpeg_receiver.py` |
| **指数減衰補間** | スムーズなアニメーション | `widgets/gimbal_hud.py` |
| **スタレーコマンドフィルタ** | 不要な重複コマンドの排除 | `rover_ws.py` |

---

## 20. 使用言語・フォント

| 項目 | 内容 |
|------|------|
| **プログラミング言語** | Python 3.x |
| **メインプリンフォント** | JetBrains Mono |
| **代替フォント** | Consolas |
| **UIデザイン言語** | Qt Style Sheet (QSS) |
| **カラーパレット** | Tailwind CSS 色名準拠 |

---

## 21. ビルド・デプロイ

| 技術 | 用途 |
|------|------|
| **Python (インタプリタ)** | 実行環境 |
| **requirements.txt** | 依存関係管理 |
| **config.json** | ランタイム設定 |
| **secrets.py** | 秘密情報（ローカルのみ） |

---

## 機能・技術マッピング表

| 機能 | 主要技術 |
|------|----------|
| メイン画面（カメラ映像） | PyQt6, MJPEG, QPainter, VideoCanvas |
| ジンバルHUD | PyQt6, QPainter, QTimer, 三角関数 |
| フォロー走行 | YOLOv8-pose, PID制御, ControlThread, GimbalThread |
| センサーグラフ | matplotlib, FigureCanvasQTAgg |
| Gemini AI分析 | google-genai, gemini-3.5-flash-lite |
| スナップショット | QPixmap, PIL, OpenCV, クラウドAPI |
| 録画 | QThread, キュー, JPEGエンコーディング |
| リモート制御 | WebSocket, asyncio, RemoteControlServer |
| PID調整 | QSlider, デバウンスTimer, CloudWorker |
| キャリブレーション | CSV, CalibrationLogger |
| スーパー解像度 | Hugging Face API, PILフォールバック |
| テレメトリ | HTTP REST, TelemetryPoller |
| エラー処理 | try/except, hasattr, デフォルト値 |
| ダークテーマ | QSS (Qt Style Sheet), DARK_STYLE |
| キーボード入力 | PyQt6 keyPressEvent, InputHandler |
| マウス操作 | PyQt6 mousePress/Move/ReleaseEvent |
