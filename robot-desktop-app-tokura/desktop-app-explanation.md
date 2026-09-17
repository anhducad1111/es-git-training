# Rover Teleop Cockpit 詳細概要ドキュメント

## このドキュメントは何をするアプリか

**Space Rover Desktop Teleoperation Cockpit** は、ESP32マイコンに搭載されたロボットカーを、**一つのDesktop画面から完全に操作・監視・記録・分析するための統合遠隔操作システム**です。

### 何をするアプリか（詳細説明）

このアプリは、以下のことを**同時に実行する統合ツール**です：

**1. リアルタイム映像の取得と表示**
- ESP32-Camから送られてくるMJPEGストリームをデコードし、Desktop上にリアルタイムで表示する
- 映像のフリップ（水平・垂直）をボタン一つで切り替え、カメラの向きを直感的に調整できる
- 映像のFPS、WebSocketのPing、レイテンシーを画面下部に常に表示し、接続の品質を確認できる
- 映像キャンバス上でマウスをドラッグすることで、ジンバル（カメラの向き）を直接操作できる
- フォロー走行モード時には、対象のバウンディングボックスを映像上にオーバーレイ表示する

**2. ロボットの遠隔操作**
- キーボードのWASDキーでロボットカーの前進・後退・左旋回・右旋回を操作する
- サイドバーのD-pad（上下左右キー）でも操作でき、タッチ操作にも対応する
- 速度スライダーで180〜255の範囲でモーターの速度を連続的に調整できる
- E-STOPボタンで緊急時に即座にモーターを停止できる
- ジンバルのパン（左右）とチルト（上下）を別々の数値入力ボックスで微調整できる
- 中央合わせボタンを押すと、ジンバルを即座に中央位置に戻せる
- 映像キャンバス上でマウスをドラッグすることで、ジンバルを直接操作できる

**3. センサー情報のリアルタイム監視**
- ESP32に搭載された温度、湿度、ガスセンサーの値をリアルタイムで表示する
- 超音波センサーによる障害物までの距離をcm単位で表示する
- センサー値が異常な場合、サイドバーの色分けで警告を知らせる
- センサーの時系列データをmatplotlibのグラフで表示し、傾向を分析できる
- テレメトリデータは10秒ごとに自動的にクラウドサーバーに送信される

**4. スナップショットの撮影・後処理・管理**
- 画面のSNAPボタンを押すと、現在のカメラ映像のフレームをキャプチャする
- キャプチャした画像には、撮影時のセンサー情報やフォロー走行のバウンディングボックスがオーバーレイされる
- 画像の後処理として、CLAHEによるコントラスト強調、ノイズ除去、Bicubicによる4xアップスケールを適用できる
- 処理後の画像はローカルに保存し、クラウドサーバーにアップロードすることもできる
- 過去に撮影したスナップショットを、サムネイル一覧でページングして閲覧・ダウンロード・削除できる

**5. 動画の録画と管理**
- RECボタンを押すと、バックグラウンドスレッドでカメラ映像をMP4形式で録画し始める
- 録画中も映像の表示やロボットの操作に影響しない
- 録画された動画はローカルに保存され、クラウドにアップロードすることもできる
- 録画キューがいっぱいの場合、古いフレームを自動的にドロップし、最新の映像を優先して保存する

**6. 自律走行（フォロー走行）**
- FOLLOW MODEボタンを押すと、YOLOv8-poseモデルがカメラ映像の中から人物を検知し、自動的にロボットカーを追従させる
- 検知された対象までの距離をPID制御で調整し、目標距離に保つ
- 対象の方向に応じてジンバルを自動的に調整し、カメラが対象を常に正面に向ける
- 障害物が30cm以内に近づいた場合、自動的にブレーキをかけて停止する
- 8状態のステートマシン（SEARCHING, TURNING, FOLLOWING, HEAD_ON_HOLD, HOLDING, APPROACHING_BLIND, LOST_TIMEOUT）で、対象を失っても再検索を自動で行う
- 設定画面でPIDパラメータ（kp, ki, kd）やフォロー走行の速度・距離・クールダウン等を微調整できる

**7. AIによるセンサー分析**
- Gemini AI（gemini-3.5-flash-lite）と対話し、センサーデータの分析や改善提案を得る
- カスタムチャート作成ツールを呼び出し、AIにセンサーの傾向を視覚化してもらえる
- 診断ビューのチャットインターフェースから、センサーデータをコンテキストとしてAIに質問できる

**8. Webブラウザからのリモート制御**
- WebSocketサーバーをポート8765で起動し、Webブラウザからロボットを操作できる
- ブラウザ側からコマンドを送信すると、ロボットのモーターやサーボを遠隔操作できる
- Webリモート制御を有効にした場合、カメラ映像は停止し、帯域を節約する
- 認可トークンでWebリモート制御のアクセスを制限する

**9. 開発・デバッグ・チューニング**
- キャリブレーション: ジャイロのキャリブレーションを行い、ロボットの傾きや回転量を正確に測定する
- PID調整: ジャイロのPIDパラメータをスライダーで調整し、400msのデバウンスでESP32に送信する
- OTAファームウェア更新: クラウドサーバーから新しいファームウェアをダウンロードし、ESP32にアップロードする
- フォロー走行チューニング: フォロー走行の全パラメータを設定画面で調整し、リアルタイムで反映する
- すべてのキャリブレーション結果はCSVファイルに自動保存される

### アプリの目的

| 目的 | 説明 |
|------|------|
| **遠隔操作** | ロボットカーが物理的に離れた場所にいても、Desktop上からキーボード・ボタン・マウスで操作できるようにする |
| **状況確認** | カメラ映像・センサーデータ・テレメトリをリアルタイムで確認し、ロボットの現在の状態を一目で把握できるようにする |
| **自律化** | フォロー走行・障害物回避などの自律機能を有効にして、人の手を離してロボットに自律的に行動させる |
| **記録・分析** | スナップショット・動画で状況を記録し、AI（Gemini）でセンサーデータを分析して改善提案を得る |
| **開発・チューニング** | PIDパラメータやジャイロのキャリブレーションをDesktop上で行い、ロボットの動作を最適化する |
| **デバッグ** | キャリブレーションやフォロー走行のチューニング結果をCSVで記録し、過去のデータを振り返れるようにする |

### 誰が使うか

| ユーザー | 使い方 | 場面 |
|----------|--------|------|
| **ロボットオペレーター** | キーボード（WASD）・ボタン・マウスでロボットを操作し、カメラ映像で状況を確認 | 遠隔地のロボットを操作する場合、障害物回避しながら進む場合 |
| **エンジニア/開発者** | PID調整、キャリブレーション、フォロー走行のチューニング | ロボットの動作を最適化したい場合、新しい機能をテストしたい場合 |
| **AI分析担当者** | Gemini AIと対話し、センサーデータを分析 | センサーデータの傾向を把握したい場合、改善策を提案してもらいたい場合 |
| **Webリモートユーザー** | ブラウザからWebSocket経由でリモート操作 | Desktopから離れた場所でロボットを操作したい場合 |
| **テスト担当者** | テスト手順に従ってジャイロやフォロー走行の動作確認 | 品質確認やバグ検出のためにテストを実行する場合 |

### アプリの全体像

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  ┌─── ヘッダー（52px）───┐                                                       │
│  │ [ROVER COCKPIT v2.4]                                              │
│  │ [MAIN] [DIAG] [SNAPSHOTS] [SETTINGS] [DEBUG]                     │
│  │ [ROVER IP:___] [CAM IP:___] [CONNECT]                              │
│  │ [WEB IP:___] [CLOUD URL:___]                                       │
│  │ [ROVER: OFFLINE] [CAM: OFFLINE] [DIST: -- cm] [TARGET: 0°]           │
│  └──────────────────────────────────────────────────────────────────────────┘
│  ┌──────────────────────────────────────────────────────────────────────────┐
│  │                                                                        │
│  │  センタースタック（QStackedWidget）                                     │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  │  [0] MAIN VIEW                                                     │ │
│  │  │  ┌──────────────────────────────────────────────────────────────┐│ │
│  │  │  │  VideoCanvas（カメラ映像）                                     ││ │
│  │  │  │    [GimbalHUD（オーバーレイ）]                                ││ │
│  │  │  │    [FPS] [PING] [LATENCY]                                   ││ │
│  │  │  │    [FollowModeOverlay: DIST cm, TARGET°]                   ││ │
│  │  │  │    [警告バナー: WEB CONTROLLED / OBSTACLE / TARGET]          ││ │
│  │  │  └──────────────────────────────────────────────────────────────┘│ │
│  │  │    [解像度] [FLIP H] [FLIP V]                                     │
│  │  └──────────────────────────────────────────────────────────────────┘ │
│  │                                                                        │
│  │  [1] DIAGNOSTICS VIEW    [2] SNAPSHOTS VIEW                          │
│  │  [3] SETTINGS VIEW       [4] DEBUG VIEW                               │
│  │                                                                        │
│  └──────────────────────────────────────────────────────────────────────────┘
│  ┌─────── サイドバー（320px）─────────────────────────────────────────────┐
│  │                                                                        │
│  │  [E-STOP]                                                             │
│  │                                                                        │
│  │  ┌─ CONTROLS ────────────────────────────────────────┐                │
│  │  │ Speed: [====●====] 220                              │                │
│  │  │ [BRAKE] [PAN:85] [TILT:70] [CENTER]              │                │
│  │  │ [MOUSE GIMBAL: OFF] [Super Resolution: OFF]       │                │
│  │  └────────────────────────────────────────────────────────┘                │
│  │                                                                        │
│  │  ┌─ Sensors Page ────────────────────────────────────┐                │
│  │  │ Temp: 25°C  Humidity: 45%                         │                │
│  │  │ Gas: 100ppm  Distance: 50cm                        │                │
│  │  │ [▼][◀][■][▶][▼] D-pad                              │                │
│  │  └────────────────────────────────────────────────────────┘                │
│  │                                                                        │
│  │  ┌─ Snapshots Page ────────────────────────────────┐                │
│  │  │ [サムネイル一覧]                                   │                │
│  │  └────────────────────────────────────────────────────────┘                │
│  │                                                                        │
│  │  [LED: OFF] [SNAP] [PID: ON] [REC]                                 │
│  │  [WEB CTRL: OFF] [FOLLOW MODE]                                     │
│  └──────────────────────────────────────────────────────────────────────────┘
│                                                                        │
│  ── ESP32-MCU ── ESP32-Cam ── Cloud ── (オプション) ── Gemini AI ── │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 技術スタックの概要

| 層 | 技術 | 用途 | 対象箇所 |
|----|------|------|----------|
| GUI | PyQt6 | ウィンドウ、ウィジェット、レイアウト | `app.py`, `views/*`, `widgets/*` |
| スタイリング | QSS (Qt Style Sheet) | ダークテーマ、CSSベースのデザイン | `styles.py`, 全UIファイル |
| 映像ストリーム | MJPEG (HTTP) | ESP32-Camからのリアルタイム映像 | `mjpeg_receiver.py`, `video_canvas.py` |
| ロボット通信 | WebSocket | ESP32-MCUとの双方向コマンド送受信 | `rover_ws.py`, `connection_manager.py` |
| REST API | requests / HTTP | ESP32のREST API、クラウドAPI | `esp32_api.py`, `cloud_api.py` |
| 画像処理 | OpenCV (cv2) | フレーム処理、ArUco検知、スナップショット後処理 | `detection_manager.py`, `snapshots_view.py` |
| 画像操作 | PIL (Pillow) | 画像リサイズ、フィルター | `video_manager.py` |
| 物体検知 | HOG + SVM | 人物検知（従来方式） | `detection_manager.py` |
| 物体検知 | YOLOv8-pose | 姿勢推定（フォロー走行） | `follow_mode/`, `detection_manager.py` |
| 画像超解像 | Hugging Face API | 4xスーパー解像度 | `video_manager.py` |
| AI | google-genai (Gemini 3.5 Flash Lite) | センサー分析チャット、チャート生成ツール | `gemini_chat.py` |
| データ可視化 | matplotlib | センサー時系列チャート | `widgets/sensor_chart.py` |
| カスタム描画 | QPainter | ジンバルHUD、速度メーターの描画 | `widgets/gimbal_hud.py`, `widgets/speed_meter.py` |
| アニメーション | QTimer | 定期更新（20Hz、30ms等） | `app.py`, `widgets/gimbal_hud.py` |
| クラウド | HTTP REST + CloudWorker | テレメトリ送信、メディア管理 | `cloud_manager.py`, `cloud_worker.py` |
| リモート制御 | asyncio + WebSocket | Webブラウザからのリモート操作 | `remote_control_server.py` |
| スレッド | QThread, QThreadPool | バックグラウンド処理 | 全ワーカークラス |
| データベース | SQLite (JSON) | ローカル設定保存 | `config.py` |
| データ保存 | CSV | キャリブレーションログ | `calibration.py` |
| デバッグ | unittest, pytest | 単体テスト | `tests/` |
| ロギング | logging | ログ出力、エラートラッキング | `app.py` |
| 設定管理 | config.py, secrets.py | 実行時設定とAPIキーの分離 | `config.py`, `secrets.py` |

---

## 1. アプリケーション概要

**Space Rover Desktop Teleoperation Cockpit (tokura branch)** は、PythonとPyQt6で構築されたロボットカーの遠隔操作デスクトップアプリケーションです。ESP32マイコンに搭載されたカメラ、モーター、センサーを遠隔操作し、リアルタイムの映像ストリーム、テレメトリデータの表示、自律走行（フォロー走行）、パラメータ調整、スナップショット・動画のキャプチャと管理、AIによるセンサー分析、Webブラウザからのリモート操作を一つのダークテーマGUIで統合的に提供します。

### 核心機能一覧

| カテゴリ | 機能 | 説明 |
|----------|------|------|
| **映像** | リアルタイムカメラ映像表示 | MJPEGストリームをデコードし60fps表示 |
| **映像** | フリップ操作 | 水平・垂直フリップ（カメラ角度調整） |
| **映像** | FPS・Ping・レイテンシ表示 | 映像パフォーマンスのリアルタイム監視 |
| **映像** | ジンバルHUD | パン/チルトの方向をコンパス形式で表示 |
| **操作** | WASDキーボード操作 | キーボードによる前進・後退・旋回 |
| **操作** | D-pad操作 | サイドバーの十字キーによる操作 |
| **操作** | マウスクリックジンバル | 映像キャンバス上でドラッグしてジンバル操作 |
| **操作** | E-STOP緊急停止 | 赤いボタンで即座にモーター停止 |
| **操作** | Webブラウザリモート制御 | WebSocket経由でWebから操作 |
| **自動運転** | フォロー走行 | YOLOv8-poseによる人物追従 |
| **自動運転** | 障害物回避 | 超音波センサーによる自動ブレーキ |
| **診断** | センサーグラフ | matplotlibによる時系列データ表示 |
| **診断** | Gemini AI分析 | センサーデータに対するAIチャット |
| **スナップショット** | 写真キャプチャ | フレーム保存・クラウドアップロード |
| **スナップショット** | 画像後処理 | 自動補正、コントラスト、ノイズ除去、アップスケール |
| **録画** | 動画録画 | バックグラウンドスレッドでMP4録画 |
| **設定** | PID調整 | kp/ki/kd/biasのスライダー操作 |
| **設定** | LED制御 | カメラLEDの輝度調整 |
| **設定** | OTAファームウェア更新 | クラウドからのファームウェアアップロード |
| **設定** | フォロー走行パラメータ調整 | 速度、距離、ゲイン等の細かい調整 |
| **デバッグ** | キャリブレーション | ジャイロ、モーターのキャリブレーションテスト |
| **デバッグ** | フォロー走行チューニング | FollowConfig全パラメータのリアルタイム調整 |
| **クラウド** | テレメトリ送信 | 10秒間隔でクラウドにデータ送信 |
| **クラウド** | メディア管理 | スナップショット・動画のアップロード・閲覧・削除 |
| **クラウド** | センサーデータ履歴 | 過去のテレメトリデータの取得 |

---

## 2. システムアーキテクチャ

### 2.1 全体アーキテクチャ図

```
┌──────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                              │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    MAIN WINDOW (QWidget)                        │ │
│  │  ┌──────────────────────────────────┐ ┌──────────────────────┐ │ │
│  │  │         HEADER (52px)            │ │   SIDEBAR (320px)    │ │ │
│  │  │  Tabs, IP, Status, CLOUD API     │ │  Controls, Sensors,  │ │ │
│  │  │  Tab: MAIN/DIAG/SNAP/SETTINGS/   │ │  Buttons, D-pad,     │ │ │
│  │  │  DEBUG                           │ │  LED/SNAP/REC/PID    │ │ │
│  │  └──────────────────────────────────┘ │  WEB CTRL, FOLLOW    │ │ │
│  │                                        └──────────────────────┘ │ │
│  │                                                                  │ │
│  │  ┌────────────────────────────────────────────────────────────┐ │ │
│  │  │              CENTER STACK (QStackedWidget)                  │ │ │
│  │  │  [0] MAIN VIEW        [1] DIAGNOSTICS  [2] SNAPSHOTS       │ │ │
│  │  │  [3] SETTINGS         [4] DEBUG                                │ │ │
│  │  └────────────────────────────────────────────────────────────┘ │ │
│  │                                                                  │ │
│  │  ┌─────────────┐  ┌────────────────┐  ┌──────────────────────┐ │ │
│  │  │ KEY LEGEND  │  │   LOG PANEL    │  │   STATUS BAR         │ │ │
│  │  └─────────────┘  └────────────────┘  └──────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                     MANAGER LAYER (ビジネスロジック)                  │
│                                                                      │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐ │
│  │ ConnectionManager │ │ VideoManager     │ │ DetectionManager   │ │
│  │ - WebSocket       │ │ - Recording      │ │ - HOG/YOLO         │ │
│  │ - MJPEG           │ │ - Snapshots      │ │ - Follow           │ │
│  │ - Telemetry       │ │ - Upload         │ │ - ArUco            │ │
│  └──────────────────┘ └──────────────────┘ └────────────────────┘ │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐ │
│  │ CloudManager     │ │ RemoteControlSrv │ │ InputHandler       │ │
│  │ - API calls      │ │ - WebSocket srv  │ │ - Keyboard         │ │
│  │ - Telemetry send │ │ - Auth           │ │ - Mouse            │ │
│  └──────────────────┘ └──────────────────┘ └────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│                     TRANSPORT LAYER (通信層)                          │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ RoverWebSocket│ │ MJPEGReceiver│ │ ESP32API     │               │
│  │ - ws://port  │ │ - HTTP GET   │ │ - HTTP REST  │               │
│  │ - Auto reconnect│ │ - Decode   │ │ - Servo/LED  │               │
│  │ - Queue      │ │ - Ping       │ │ - Distance   │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ RemoteCtrlSrv│ │ TelemetryPoller│ │ CloudWorker  │               │
│  │ - asyncio    │ │ - HTTP GET   │ │ - QThread    │               │
│  │ - Auth       │ │ - 10s interval│ │ - Upload     │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
├──────────────────────────────────────────────────────────────────────┤
│                     EXTERNAL SYSTEMS                                  │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐│
│  │ ESP32-MCU    │ │ ESP32-Cam    │ │ Cloud Server │ │ Gemini API ││
│  │ - Motors     │ │ - Video      │ │ - Telemetry  │ │ - AI Chat  ││
│  │ - Servos     │ │ - MJPEG      │ │ - Media      │ │ - Charts   ││
│  │ - Sensors    │ │ - Sensors    │ │ - History    │ │ - Tools    ││
│  │ - MPU-6050   │ │ - LED        │ │              │ │            ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 データフロー

```
ESP32-Cam ──MJPEG──→ MJPEGReceiver ──Decode──→ VideoCanvas ──→ UI表示
                                                         │
                                                         ↓
ESP32-MCU ──WebSocket──→ RoverWS ──受信──→ ConnectionManager ──→ UI更新
                                                         │
ESP32-MCU ──HTTP──→ ESP32API ──リクエスト──→ ConnectionManager ──→ データ表示
                                                         │
TelemetryPoller ──10秒ごと──→ GET /api/telemetry ──→ テレメトリ表示 ──→ クラウド送信
                                                         │
UI操作 ──コマンド──→ ConnectionManager.send_command ──→ RoverWS ──→ ESP32-MCU
                                                         │
UI操作 ──HTTPリクエスト──→ CloudWorker ──→ CloudAPI ──→ クラウドサーバー
```

---

## 3. アプリケーション起動シーケンス

### 3.1 初期化フロー（詳細）

```
main.py
  │
  ├─ sys.path.insert(0, プロジェクトディレクトリ)
  │
  ├─ QApplication(sys.argv) を作成
  │
  ├─ RoverTeleopApp() をインスタンス化
  │     │
  │     ├─ load_config() → config.json または DEFAULT_CONFIG
  │     │     │
  │     │     ├─ ファイル存在チェック
  │     │     ├─ JSONパース
  │     │     ├─ デフォルト値とのマージ
  │     │     └─ 設定辞書返却
  │     │
  │     ├─ secrets.py から GEMINI_API_KEY, HF_TOKEN をインポート
  │     │
  │     ├─ 各種タイマー初期化
  │     │     ├─ _pid_apply_timer (SingleShot, 400ms)
  │     │     ├─ _led_apply_timer (SingleShot, 300ms)
  │     │     ├─ _speed_apply_timer (SingleShot, 150ms)
  │     │     └─ _pid_workers, _led_workers, _speed_workers リスト初期化
  │     │
  │     ├─ ログファイル初期化
  │     │     ├─ logs/ ディレクトリ作成 (os.makedirs)
  │     │     ├─ logs/follow_YYYYMMDD_HHMMSS.log を開く
  │     │     └─ print("[LOG] Log file: ...") でログファイルパス表示
  │     │
  │     ├─ マネージャー初期化
  │     │     ├─ ConnectionManager(config, log_callback)
  │     │     │     ├─ ESP32API を作成
  │     │     │     ├─ RoverWebSocket を作成
  │     │     │     ├─ MJPEGReceiver を作成
  │     │     │     ├─ TelemetryPoller を作成
  │     │     │     └─ シグナル接続
  │     │     │
  │     │     ├─ VideoManager(None, log_callback)
  │     │     │     ├─ 録画キュー初期化
  │     │     │     ├─ 録画スレッドプール初期化
  │     │     │     └─ is_recording = False
  │     │     │
  │     │     ├─ DetectionManager(log_callback, app=self)
  │     │     │     ├─ follow_controller = None
  │     │     │     ├─ detection_active = False
  │     │     │     └─ シグナル接続
  │     │     │
  │     │     ├─ InputHandler(send_command_cb, log_cb, ...)
  │     │     │     ├─ キーマッピング初期化
  │     │     │     └─ speed = config['motor_speed']
  │     │     │
  │     │     ├─ CloudManager(config, log_callback)
  │     │     │     ├─ _cloud_api = None
  │     │     │     └─ _cloud_workers = []
  │     │     │
  │     │     └─ RemoteControlServer("0.0.0.0", port)
  │     │           ├─ asyncioサーバー作成
  │     │           └─ command_received シグナル接続
  │     │
  │     ├─ UI初期化 (init_ui())
  │     │     ├─ create_header(app) → ヘッダー作成
  │     │     │     ├─ QHBoxLayout にタイトル, タブ, IP入力を配置
  │     │     │     ├─ タブボタンのシグナル接続
  │     │     │     └─ ステータス表示の初期化
  │     │     │
  │     │     ├─ QStackedWidget を作成し5ページ追加
  │     │     │     ├─ create_main_view(app) → メインビュー
  │     │     │     ├─ create_diagnostics_view(app) → 診断ビュー
  │     │     │     ├─ create_snapshots_view(app) → スナップショットビュー
  │     │     │     ├─ create_settings_view(app) → 設定ビュー
  │     │     │     └─ create_debug_view(app) → デバッグビュー
  │     │     │
  │     │     ├─ create_sidebar(app) → サイドバー作成
  │     │     │     ├─ QStackedWidget でセンサー/スナップショットページ切替
  │     │     │     ├─ CONTROLS グループボックス作成
  │     │     │     ├─ E-STOP ボタン作成
  │     │     │     ├─ センサーCard, D-pad作成
  │     │     │     └─ ボタン群(LED/SNAP/PID/REC/WEB/FOLLOW)作成
  │     │     │
  │     │     ├─ create_key_legend(app) → キーレジェンド作成
  │     │     │
  │     │     └─ create_log_panel(app) → ログパネル作成
  │     │
  │     ├─ シグナル接続 (connect_signals())
  │     │     ├─ log_message → _add_log
  │     │     ├─ detections_updated → _on_detections_updated
  │     │     ├─ follow_detected → _on_follow_detected
  │     │     ├─ target_lost/found → 関連ハンドラ
  │     │     ├─ aruco_lost/found → 関連ハンドラ
  │     │     ├─ target_angle_updated → _on_target_angle_updated
  │     │     ├─ camera_connected → _on_camera_connected
  │     │     ├─ camera_disconnected → _on_camera_disconnected
  │     │     ├─ rover_connected → _on_rover_connected
  │     │     └─ rover_disconnected → _on_rover_disconnected
  │     │
  │     └─ 接続開始 (start_connections())
  │           ├─ _conn_mgr.start_all()
  │           │     ├─ RoverWebSocket.start()
  │           │     │     ├─ 接続試行 (ws://{car_ip}:81/)
  │           │     │     ├─ メッセージ送信: servo:85,70 (センター)
  │           │     │     └─ 自動再接続開始
  │           │     ├─ MJPEGReceiver.start()
  │           │     ├─ TelemetryPoller.start()
  │           │     └─ _esp32_api = _conn_mgr.esp32_api
  │           │
  │           ├─ CloudManager.initialize()
  │           │     ├─ CloudAPI() を作成
  │           │     └─ test_connection() (非同期)
  │           │
  │           ├─ VideoManager._cloud_api = CloudManager.cloud_api
  │           │
  │           ├─ RemoteControlServer 起動
  │           │     ├─ ポート8765でリスニング開始
  │           │     └─ WebSocketクライアントの接続を待受
  │           │
  │           └─ 各種ステータス表示の初期化
  │                 ├─ _rover_status = "OFFLINE"
  │                 ├─ _cam_status = "OFFLINE"
  │                 ├─ _distance_display = "-- cm"
  │                 └─ _target_angle_display = "0°"
  │
  ├─ window.show() でウィンドウ表示
  │
  └─ sys.exit(app.exec()) でイベントループ開始
```

### 3.2 メインループでの処理フロー

```
毎フレーム (約16msごと):
  │
  ├─ QTimer が _update_video_frame() を呼ぶ (33msごと)
  │     │
  │     ├─ VideoWorker から最新フレームを取得
  │     │     ├─ BGR配列 → QPixmap変換
  │     │     └─ フレームのフリップ適用
  │     │
  │     ├─ VideoCanvas にフレームをセット
  │     │     ├─ QLabelにpixmapを設定
  │     │     ├─ GimbalHUD を再配置
  │     │     ├─ FPS/遅延表示を更新
  │     │     └─ フォロー検知バウンディングボックスを描画
  │     │
  │     ├─ FPS, Ping, Latency表示を更新
  │     │
  │     ├─ FollowModeが有効な場合:
  │     │     ├─ FollowController にフレームを渡す
  │     │     ├─ ControlThread がPID制御を実行
  │     │     │     ├─ 距離PID計算
  │     │     │     ├─ 航向補正計算
  │     │     │     └─ モーターコマンド生成
  │     │     ├─ GimbalThread がジンバル追従を実行
  │     │     │     ├─ 対象の角度計算
  │     │     │     └─ サーボコマンド生成
  │     │     └─ コマンドをConnectionManagerを通じて送信
  │     │
  │     └─ 障害物検知が行われた場合:
  │           ├─ 速度制限を適用
  │           ├─ ブレーキを発動
  │           └─ 警告バナーを表示
  │
  │
  ├─ 毎10秒: TelemetryPoller が GET /api/telemetry を実行
  │     │
  │     ├─ temperature, humidity, gas, distance, obstacle を取得
  │     ├─ サイドバーのセンサー表示を更新
  │     ├─ header.py の距離表示を更新
  │     └─ CloudManager.send_telemetry() でクラウドに送信
  │
  │
  ├─ ユーザー操作が発生した場合:
  │     │
  │     ├─ キー入力 → InputHandler → ConnectionManager.send_command()
  │     │     ├─ RoverWebSocket.send() でWebSocket経由で送信
  │     │     └─ デバウンス適用 (_speed_apply_timer, _led_apply_timer)
  │     │
  │     ├─ スライド変更 → _schedule_pid_apply() → 400ms後に
  │     │     CloudWorker で GET /api/pid を実行
  │     │
  │     ├─ ボタンクリック → 対応するメソッドを実行
  │     │     ├─ 録画開始/停止 → VideoManager
  │     │     ├─ スナップショット → _take_snapshot()
  │     │     ├─ フォロー走行 → DetectionManager.toggle_follow_mode()
  │     │     └─ 設定変更 → 対応するハンドラ
  │     │
  │     └─ Webリモート → RemoteControlServer → WebSocket → コマンド送信
```

---

## 4. ビューの詳細

### 4.1 ヘッダー (`views/header.py`)

**高さ**: 52px  
**役割**: アプリケーションのトップバー。タブ切り替え、ステータス表示、接続制御を行う。

**構成要素と配置順序（左から右）:**

```
[ROVER COCKPIT v2.4] | [MAIN] [DIAGNOSTICS] [SNAPSHOTS] [SETTINGS] [DEBUG]
| [ROVER IP入力] | [CAM IP入力] | [CONNECT] | [WEB IP表示] | [CLOUD URL入力]
| [ROVER: OFFLINE] | [CAM: OFFLINE] | separator | [DIST: -- cm] | [TARGET: 0°]
```

**各要素の詳細:**

| 要素 | 種類 | 機能 |
|------|------|------|
| ROVER COCKPIT | QLabel | アプリタイトル。色はシアン(#06b6d4) |
| v2.4 | QLabel | バージョン表示。ダークグレー背景 |
| MAIN〜DEBUG | QPushButton | センタースタックのページ切り替え。checkable |
| ROVER IP入力 | QLineEdit | ESP32のIPアドレス入力。returnで接続 |
| CAM IP入力 | QLineEdit | カメラのIPアドレス入力。returnで接続 |
| CONNECT | QPushButton | IPを保存し、ローバーとカメラを再接続 |
| WEB IP表示 | QLineEdit | リモート制御のURL（読み取り専用） |
| CLOUD URL入力 | QLineEdit | クラウドAPIのURL入力 |
| ROVER/CAM ステータス | QLabel | 接続状態表示。赤:OFFLINE/緑:ONLINE |
| DIST | QLabel | 超音波センサーの距離表示 |
| TARGET | QLabel | ジンバルの目標角度表示 |

**主要メソッド:**

- `_on_connect_clicked(app)`: 設定を保存し、`ConnectionManager.reconnect_rover()` と `reconnect_camera()` を呼び出す
- `create_header(app)`: ヘッダー全体を構築して返す

---

### 4.2 サイドバー (`views/sidebar.py`)

**幅**: 320px  
**役割**: コントロール、センサー表示、操作ボタンを配置する。

**構成:**

```
┌─── SIDEBAR ──────────────────────────┐
│ [E-STOP]                              │
│ ┌──── CONTROLS ───────────────────┐   │
│ │ Speed: [====●====] 220         │   │
│ │ [BRAKE]  [PAN:85] [TILT:70]    │   │
│ │ [CENTER] [MOUSE GIMBAL: OFF]   │   │
│ │ [Super Resolution: OFF]        │   │
│ └───────────────────────────────────┘   │
│ ┌──── Sensors Page ─────────────────┐   │
│ │ Temp: 25°C  Humidity: 45%         │   │
│ │ Gas: 100ppm  Distance: 50cm       │   │
│ │ [▼][◀][■][▶][▼] D-pad            │   │
│ │ Link: 98% (Optimal) [削除済み]     │   │
│ └───────────────────────────────────┘   │
│ ┌──── Snapshots Page ───────────────┐   │
│ │ [サムネイル一覧]                   │   │
│ └───────────────────────────────────┘   │
│ [LED: OFF] [SNAP] [PID: ON] [REC]     │
│ [WEB CONTROL: OFF] [FOLLOW MODE]      │
└─────────────────────────────────────────┘
```

**詳細機能:**

#### CONTROLS グループボックス
- **Speed スライダー**: 180-255の範囲でモーター速度を調整。150msデバウンス。
- **BRAKE トグル**: 自動ブレーキの有効/無効。30cm未満で自動ブレーキ発動。
- **PAN/TILT 入力**: ジンバルのパン(85)とチルト(70)を数値入力。CENTERボタンで中央に復帰。
- **MOUSE GIMBAL トグル**: 映像上のマウスドラッグでジンバルを操作可能にする。
- **Super Resolution チェックボックス**: 有効にすると画像を4xアップスケール。

#### センサーページ
- SensorCard × 4: Temperature, Humidity, Gas, Distance のゲージ表示
- D-pad: ▲(前進)/◀(左)/■(停止)/▶(右)/▼(後退) の十字キー。press-to-drive方式。
- リンクステータス（以前表示されていたが削除済み）

#### ボタン（最下部）
- **E-STOP**: 赤背景の緊急停止ボタン。クリックで即座にモーター停止。
- **LED: ON/OFF**: カメラLEDのトグル。300msデバウンス。
- **SNAP**: スナップショット撮影ボタン。クリックでフレームキャプチャ。
- **PID: ON/OFF**: ジャイロPIDの有効/無効。400msデバウンスでパラメータを送信。
- **REC**: 録画開始/停止。バックグラウンドスレッドで動画を保存。
- **WEB CONTROL: ON/OFF**: Webリモート制御の認可。ONにするとカメラストリームが停止。
- **FOLLOW MODE**: フォロー走行のトグル。Vキーでも操作可能。

**サイドバーのページ切り替え:**
- `QStackedWidget` (`_sidebar_stack`) で「Sensors」と「Snapshots」のページを切り替える
- タブボタンでページを切り替える

---

### 4.3 メインビュー (`views/main_view.py`)

**役割**: デフォルトのセンター画面。カメラ映像と各種オーバーレイを表示。

**構成要素:**

```
┌──────────────────────────────────────────────────┐
│ ┌──────────────────────────────────────────────┐ │
│ │                                              │ │
│ │         VideoCanvas (メイン映像)               │ │
│ │                                              │ │
│ │  ┌─ GimbalHUD (オーバーレイ) ───────────┐   │ │
│ │  │  CAM [PAN:85°]                        │   │ │
│ │  │       ↑                               │   │ │
│ │  │    ◁──●──▷    (パン円)                │   │ │
│ │  │       ↑                               │   │ │
│ │  │    ◁──●──▷    (チルト円)              │   │ │
│ │  │       ↑                               │   │ │
│ │  └──────────────────────────────────────┘   │ │
│ │                                              │ │
│ │  [FPS: 30] [PING: 45ms] [LATENCY: 16ms]    │ │
│ │                                              │ │
│ │  ┌─ FollowModeOverlay ──────────────────┐   │ │
│ │  │ DIST: 50 cm   TARGET: +4.5°           │   │ │
│ │  └──────────────────────────────────────┘   │ │
│ │                                              │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ [解像度: 640x480] [FLIP H] [FLIP V] [JPEG: 14]   │
│ ───────────────────────────────────────────────── │
│ [警告バナー: WEB CONTROLLED / OBSTACLE / TARGET] │
└──────────────────────────────────────────────────┘
```

**VideoCanvas の詳細:**
- QLabelを継承し、映像フレームを表示
- `_apply_flip()`: QTransformによる水平・垂直フリップ
- マウスドラッグでジンバル操作（`mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent`）
- フォロー走行時のバウンディングボックス描画（`paintEvent`）
- 中心十字線、対象追跡マーカーの描画

**GimbalHUD の詳細:**
- 固定サイズ 120x210px
- 20Hzのアニメーションタイマー（`_timer.start(30)`）
- 指数減衰補間で滑らかな針の移動
- パン円（12時=N、6時=S、9時=W、3時=E）
- チルト円（UP/LVL/DN ラベル）
- 内部に度数表示（`+4°`等）

---

### 4.4 診断ビュー (`views/diagnostics_view.py`)

**役割**: センサーデータの可視化とAI分析。

**構成:**

```
┌─────────────────────────────────────────────────────────┐
│ ┌─ DATA VIEW ──────────────────┐ ┌─ AI SENSOR ─────┐ │
│ │                                │ │   ANALYST       │ │
│ │  ┌─ CHARTS / TABLE ────────┐ │ │                 │ │
│ │  │                          │ │ │  Chat表示       │ │
│ │  │  ┌──────────────────┐    │ │ │                 │ │
│ │  │  │ SensorChart      │    │ │ │  入力欄 [SEND]  │ │
│ │  │  │ (matplotlib)     │    │ │ │                 │ │
│ │  │  └──────────────────┘    │ │ └─────────────────┘ │
│ │  │                          │ │                     │ │
│ │  │  QTableWidget            │ │                     │ │
│ │  │  (タイムスタンプ/値)      │ │                     │ │
│ │  │                          │ │                     │ │
│ │  └──────────────────────────┘ │                     │ │
│ │                                │                     │ │
│ └────────────────────────────────┴─────────────────────┘
```

**SensorChart の詳細:**
- `FigureCanvasQTAgg` を継承
- matplotlibで時系列チャートを描画
- デフォルトチャートグループとカスタムチャートグループをサポート
- AIが`create_custom_charts`ツールを呼び出すことでカスタムチャートを生成可能
- 色分け: temperature(#ef4444), humidity(#3b82f6), gas(#f59e0b), distance(#10b981)

**GeminiChat の詳細:**
- `gemini_chat.py`の`GeminiChat(QThread)`クラスを使用
- `model="gemini-3.5-flash-lite"`
- システムプロンプト: "You are a sensor data analyst for a rover robot"
- カスタムツール: `create_custom_charts` (チャート作成)
- センサーデータ + ユーザー質問をコンテキストとして送信

---

### 4.5 スナップショットビュー (`views/snapshots_view.py`)

**役割**: スナップショットのギャラリー管理と後処理。

**構成:**

```
┌──────────────────────────────────────────────────────────────┐
│  SNAPSHOT GALLERY                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [ページング: ◀ ◄ 1/10 ▶ ▌]                          │   │
│  │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │   │
│  │ │Thumb │ │Thumb │ │Thumb │ │Thumb │ │Thumb │     │   │
│  │ │      │ │      │ │      │ │      │ │      │     │   │
│  │ │2025  │ │2025  │ │2025  │ │2025  │ │2025  │     │   │
│  │ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ PREVIEW ──────────────┐  ┌─ INFO ───────────────┐   │
│  │  ┌────────────────────┐ │  │ ID: xxxxx            │   │
│  │  │ サムネイル/動画     │ │  │ Type: photo/video     │   │
│  │  └────────────────────┘ │  │ Size: 1.2MB            │   │
│  │                        │  │ Time: 2025-01-01       │   │
│  │                        │  │ MIME: image/jpeg       │   │
│  │                        │  │                        │   │
│  │  [DOWNLOAD] [DELETE]   │  │                        │   │
│  └────────────────────────┘  └────────────────────────┘   │
│                                                              │
│  ┌─ IMAGE PROCESSING ────────────────────────────────┐   │
│  │ [AUTO CORRECT] [ENHANCE] [DENOISE] [BICUBIC] [APPLY]│   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**機能詳細:**
- クラウドAPIから6件ずつページネーションで読み込み
- CloudWorkerで非同期にスナップショットリストを取得
- 選択したスナップショットのプレビュー表示
- 画像処理:
  - **AUTO CORRECT**: CLAHE (Contrast Limited Adaptive Histogram Equalization)
  - **ENHANCE CONTRAST**: コントラスト強調フィルター
  - **DENOISE**: ノイズ除去フィルター
  - **BICUBIC**: 1.5xアップスケール（PIL）
- ダウンロード: ローカルファイルシステムに保存
- 削除: クラウドから削除
- CloudWorkerを介したクラウドとの通信

---

### 4.6 設定ビュー (`views/settings_view.py`)

**役割**: システムパラメータの調整。

**構成:**

```
┌──────────────────────────────────────────────────────────────┐
│ ┌─ SETTINGS (左パネル) ──────────┐ ┌─ RIGHT ──────┐        │
│ │                                  │ │              │        │
│ │ ┌─ PID STRAIGHT ─────────────┐ │ │ CLOUD       │        │
│ │ │ kp: [====●====] 0.2        │ │ │ [SEND][DATA]│        │
│ │ │ ki: [====●====] 0.05       │ │ │              │        │
│ │ │ kd: [====●====] 0.1        │ │ │              │        │
│ │ │ bias: [====●====] 0        │ │ │              │        │
│ │ │ [PID: ON] [APPLY]          │ │ │              │        │
│ │ └────────────────────────────┘ │ │              │        │
│ │                                  │ │              │        │
│ │ ┌─ CAMERA ───────────────────┐ │ │ FOLLOW MODE │        │
│ │ │ LED: [====●====] 0         │ │ │ kp, ki, kd  │        │
│ │ │ [LED: ON]                  │ │ │ cam_offset  │        │
│ │ └────────────────────────────┘ │ │ [predict]   │        │
│ │                                  │ │              │        │
│ │ ┌─ OTA FIRMWARE ─────────────┐ │ │              │        │
│ │ │ [ファイル選択]              │ │ │              │        │
│ │ │ Version: 1.0.0             │ │ │              │        │
│ │ │ URL: [入力欄]              │ │ │              │        │
│ │ │ [UPLOAD] [進行バー]        │ │ │              │        │
│ │ └────────────────────────────┘ │ │              │        │
│ └──────────────────────────────────┘ └──────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

**PID調整の詳細:**
- スライダーは0-100の範囲で表示され、内部では `/100.0` で0-1.0に変換
- デフォルト: kp=0.2, ki=0.05, kd=0.1, bias=15
- 変更時に`_schedule_pid_apply()`が400msのデバウンスタイマーを開始
- タイマー到期後に`CloudWorker`で`GET /api/pid?kp=&ki=&kd=&enabled=&bias=`を送信
- `_enforce_gyro_pid_defaults()`でデフォルト値の適用も可能

**OTA更新の詳細:**
- ファームウェアファイルの選択
- クラウドサーバーへのアップロード
- 進行状況バーの表示
- `cloud_worker.py`の`_UploadFileWrapper`で進行状況を追跡

---

### 4.7 デバッグビュー (`views/debug_view.py`)

**役割**: 開発・キャリブレーション専用タブ。

**構成:**

```
┌──────────────────────────────────────────────────────────────┐
│ ┌─ CALIBRATION ──────────────────┐ ┌─ FOLLOW ──────────┐  │
│ │                                  │ │                    │  │
│ │ Spin Test [ボタン]              │ │ Turn Speed        │  │
│ │ Forward Test [ボタン]           │ │ Max PWM           │  │
│ │                                  │ │ Min PWM           │  │
│ │ ┌────────────────────────────┐   │ Blind Approach    │  │
│ │ │ Calibration History        │   │ Search Step       │  │
│ │ │ CSV形式のログ              │   │ Cooldown          │  │
│ │ └────────────────────────────┘   │                    │  │
│ │ ┌────────────────────────────┐   │ Predictive Ctrl   │  │
│ │ │ Calibration Results        │   │ [チェックボックス] │  │
│ │ └────────────────────────────┘   │                    │  │
│ └──────────────────────────────────┘ └────────────────────┘  │
│ ┌─ GYRO PID ─────────────────────┐                          │
│ │ [REFRESH] [APPLY]               │                          │
│ │ kp: [入力] ki: [入力]           │                          │
│ │ kd: [入力] bias: [入力]         │                          │
│ │ enabled: [トグル]               │                          │
│ └──────────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────┘
```

**詳細機能:**
- **CALIBRATION**: スピンテスト（`drive:0,w`でジャイロyawを積分）、フォワードテスト（速度+方向を指定して測定距離を記録）
- **FOLLOW TUNING**: `FollowConfig`クラスの全パラメータをスライダーで調整。simple turn direction flipのチェックボックス
- **GYRO PID**: ESP32のジャイロPIDパラメータを表示・変更。`REFRESH`で現在値を取得、`APPLY`で新しい値を送信
- すべての結果は`CalibrationLogger`で`logs/calibration.csv`にCSV形式で保存

---

## 5. ウィジェットの詳細

### 5.1 VideoCanvas (`widgets/video_canvas.py`)

- **継承**: `QLabel`
- **役割**: メイン映像表示キャンバス
- **機能**:
  - `update_frame()`: JPEGデータをデコードしてフレームを表示
  - `_apply_flip()`: QTransformによるフリップ
  - `mousePressEvent()`: マウスドラッグ開始
  - `mouseMoveEvent()`: ドラッグ中のジンバル操作
  - `mouseReleaseEvent()`: ドラッグ終了
  - `paintEvent()`: 中心十字線、検知バウンディングボックスの描画
  - `set_follow_detections()`: フォロー走行のバウンディングボックス設定
- **シグナル**: `gimbal_changed(pan, tilt)`

### 5.2 GimbalHUD (`widgets/gimbal_hud.py`)

- **継承**: `QWidget`
- **サイズ**: 120x210px
- **役割**: ジンバルのパン/チルト方向をコンパス形式で表示
- **アニメーション**: 20Hzタイマー、指数減衰補間（0.22の減衰係数）
- **描画内容**:
  - ヘッダー: "CAM" / "GIMBAL" / パン角度
  - パン円: 12時=N, 6時=S, 9時=W, 3時=E。15度刻みのマーク
  - チルト円: UP/LVL/DNラベル。12度刻みのマーク
  - パン針: パン円上の指し示す線
  - チルト針: チルト円上の指し示す線
  - 内部表示: `+4°`等の度数値
- **座標系**: `scale(1, -1)`のY軸反転トランスフォームを使用。テキストは`restore()`後に描画

### 5.3 FollowModeOverlay (`widgets/follow_overlay.py`)

- **継承**: `QLabel`
- **サイズ**: 半透明背景（rgba(15, 23, 42, 0.85)）
- **役割**: フォロー走行時の距離と目標角度を映像上に表示
- **表示内容**: DIST (cm), TARGET (角度)
- **色分け**: 距離 <30cm: 赤, <60cm: 黄色, それ以外: 緑。角度: 緑(<10°), 黄色(<30°), 赤(それ以上)

### 5.4 SensorCard (`widgets/sensor_card.py`)

- **継承**: `QWidget`
- **役割**: センサー値のゲージ表示
- **表示内容**: 温度、湿度、ガス、距離
- **色分け**: 値の範囲に応じてカラーコードでステータス表示

### 5.5 SensorChart (`widgets/sensor_chart.py`)

- **継承**: `FigureCanvasQTAgg`
- **役割**: matplotlibによるセンサー時系列チャート
- **機能**:
  - 時系列データの描画
  - カスタムチャートグループの作成
  - AIツール呼び出しによるチャート生成

### 5.6 その他のオーバーレイ

| ウィジェット | サイズ | 表示内容 | 色分け |
|-------------|--------|----------|--------|
| `FPSDisplay` | 小 | 現在のFPS | 緑(高)/黄(中)/赤(低) |
| `PingDisplay` | 小 | WebSocketレイテンシ | 緑/黄/赤 |
| `LatencyDisplay` | 小 | フレーム到着レイテンシ | 緑/黄/赤 |
| `SpeedMeter` | 円形 | 現在の速度ゲージ | アナログ針 |

---

## 6. マネージャーの詳細

### 6.1 ConnectionManager (`connection_manager.py`)

**役割**: ESP32との全通信を一元管理。

**構成要素:**
- `RoverWebSocket`: WebSocketクライアント（ESP32-MCUとの通信）
- `MJPEGReceiver`: MJPEGストリーム受信（ESP32-Camとの通信）
- `ESP32API`: HTTP RESTクライアント（サーボ制御等）
- `TelemetryPoller`: テレメトリ定期ポーリング

**主要メソッド:**
- `start_all()`: 全接続を開始
- `reconnect_rover()`: WebSocketとテレメトリを再接続
- `reconnect_camera()`: MJPEGストリームを再接続
- `send_command(command)`: WebSocket経由でコマンド送信
- `take_frame()`: 最新フレームの取得

**シグナル:**
- `rover_connected/disconnected`: ローバーの接続状態
- `camera_connected/disconnected`: カメラの接続状態
- `video_stats`: 映像統計情報（FPS等）
- `telemetry_data`: テレメトリデータ

### 6.2 VideoManager (`video_manager.py`)

**役割**: 録画とスナップショットの管理。

**録画機能:**
- `start_recording()`: バックグラウンドスレッドで録画開始
- `stop_recording()`: 録画停止
- キューアーキテクチャでフレームバッファリング
- キューがいっぱいの場合、古いフレームをドロップ
- `is_recording` プロパティで録画状態を確認

**スナップショット機能:**
- `take_snapshot()`: 現在のフレームをキャプチャ
- テレメトリ情報とバウンディングボックスをオーバーレイ
- ローカル保存とクラウドアップロード

### 6.3 DetectionManager (`detection_manager.py`)

**役割**: 全検知モードの制御。

**検知モード:**
- **HOG**: 伝統的なHOG + SVMによる人物検知
- **YOLO**: YOLOv8による物体検知
- **Follow**: YOLOv8-poseによるフォロー走行

**フォロー走行の構成:**
- `FollowDetector`: YOLOv8-poseによる姿勢推定
- `FollowController`: 8状態ステートマシン
  - FOLLOWING: 対象を追従中
  - TURNING: 旋回中
  - WAITING: 待機中
  - SEARCHING: 対象を探している
  - HEAD_ON_HOLD: 正面で停止
  - HOLDING: 停止して保持
  - APPROACHING_BLIND: 盲点に接近
  - LOST_TIMEOUT: 対象を失ったタイムアウト
- `GimbalThread`: 約20Hzでジンバル追従
- `ControlThread`: 距離PID制御 + 航法誤差ステアリング

**シグナル:**
- `detections_updated`: 検知結果更新
- `follow_detected`: フォロー走行開始
- `target_lost/found`: 対象のロスト/検出
- `aruco_lost/found`: ArUcoマーカーのロスト/検出
- `target_angle_updated`: 目標角度更新

### 6.4 CloudManager (`cloud_manager.py`)

**役割**: クラウドAPIとの通信を管理。

**機能:**
- `initialize()`: CloudAPIインスタンスを作成し、接続テスト
- `test_connection()`: 接続テスト（非同期）
- `send_telemetry()`: テレメトリデータをクラウドにPOST（Fire-and-forget）
- CloudWorkerのライフサイクル管理

### 6.5 RemoteControlServer (`remote_control_server.py`)

**役割**: Webブラウザからのリモート操作を受け付けるWebSocketサーバー。

**技術:**
- `asyncio`ベースの非同期サーバー
- ポート8765（デフォルト、`config.json`から変更可能）
- 認可機能（`_allow_remote_control`フラグ）
- クライアント接続時のローバー状態のブロードキャスト
- `command_received` シグナルでコマンドを`_relay_command()`に渡す

### 6.6 InputHandler (`input_handler.py`)

**役割**: キーボードとマウスの入力を処理。

**キーマッピング:**
- W/S/A/D: 前進/後退/左/右
- Space: 緊急停止
- V: フォロー走行トグル
- I/K: ジンバルアップ/ダウン
- J/L: ジンバルパン左/右
- C: ジンバルセンター
- Shift/Ctrl: 速度アップ/ダウン

---

## 7. 通信プロトコルの詳細

### 7.1 WebSocketコマンド（アプリ → ESP32）

| コマンド | フォーマット | 説明 |
|----------|-------------|------|
| 前進 | `forward` | 前進走行 |
| 後退 | `backward` | 後退走行 |
| 左旋回 | `left` | 左に旋回 |
| 右旋回 | `right` | 右に旋回 |
| 停止 | `stop` | モーター停止 |
| サーボ設定 | `servo:{pan},{tilt}` | ジンバルのパンとチルトを設定（0-180） |
| 速度指定 | `drive:{speed},{turn}` | speed(180-255), turn(-100~100) |
| 速度制限 | `speed:{N}` | N(180-255)で速度を制限 |

### 7.2 HTTP REST API（ESP32）

| エンドポイント | メソッド | パラメータ | 説明 |
|---------------|----------|-----------|------|
| `/api/pid` | GET | kp, ki, kd, enabled, bias | ジャイロPIDパラメータを設定/取得 |
| `/api/telemetry` | GET | - | センサーデータ取得 |
| `/api/servo` | GET | pan, tilt | サーボ位置設定 |
| `/api/distance` | GET | - | 超音波距離取得 |
| `/api/brake` | GET | value | ブレーキ設定 |
| `/api/led` | GET | value | LED輝度設定 |
| `/api/quality` | GET | value | カメラ画質設定 |

### 7.3 クラウドAPI

| エンドポイント | メソッド | 説明 |
|---------------|----------|------|
| `/telemetry` | POST | テレメトリデータ送信 |
| `/rovers` | GET | ローバー一覧取得 |
| `/rovers/{uid}/latest` | GET | 最新データ取得 |
| `/rovers/{uid}/readings` | GET | 読み取り履歴取得 |
| `/rovers/{uid}/media` | GET/POST | メディア一覧/アップロード |
| `/rovers/{uid}/media/{id}` | GET/DELETE | メディア取得/削除 |

### 7.4 MJPEG ストリーム

```
ESP32-Cam → HTTP GET → MJPEGReceiver
  │
  ├─ ReceiveThread: HTTPでマルチパートストリームを取得
  │     ├─ Content-Length ヘッダーでフレーム境界を解析
  │     └─ MjpegParser: フレームバッファリング
  │
  ├─ DecodeThread: JPEGデータをQImage/QPixmapにデコード
  │     └─ 最新フレームのみ保持（LatestSlotパターン）
  │
  └─ PingThread: HEADリクエストでレイテンシ測定
```

---

## 8. スレッドアーキテクチャ

### 8.1 スレッド一覧

| スレッド | 種別 | 周期 | 責任範囲 | プロトコル |
|----------|------|------|----------|-----------|
| **メインスレッド** | GUI | ~16ms | UIイベント、描画 | PyQt6 |
| **ReceiveThread** | QThread | 連続 | MJPEGフレーム受信 | HTTP |
| **DecodeThread** | QThread | 連続 | JPEGデコード | ローカル |
| **RoverWS Sender** | QThread | 連続 | WebSocketコマンド送信 | WebSocket |
| **TelemetryPoller** | QThread | 10s | センサーポーリング | HTTP REST |
| **CloudWorker** | QThread | 要望 | 非同期HTTPリクエスト | HTTP REST |
| **GimbalThread** | Thread | ~20Hz | ジンバル追従制御 | ローカル |
| **ControlThread** | Thread | ~10Hz | モーター制御 | ローカル |
| **DetectionThread** | Thread | 30fps | 画像検知 | ローカル |
| **RemoteControlServer** | asyncio | 連続 | WebSocketサーバー | WebSocket |
| **Recording Thread** | QThread | 要望 | 動画録画 | ローカル |
| **SuperResolutionWorker** | QThread | 要望 | 画像アップスケール | HTTP |
| **GeminiChat** | QThread | 要望 | AIチャット | HTTP |

### 8.2 スレッド間通信

```
Worker Threads ──pyqtSignal──→ Main Thread (GUI)
  │
  ├─ CloudWorker.result  → データ表示更新
  ├─ CloudWorker.error   → エラーログ表示
  ├─ RoverWS.message     → コマンド応答処理
  ├─ TelemetryPoller.data → センサー表示更新
  ├─ FollowController    → target_angle_updated シグナル
  └─ DetectionManager    → detections_updated シグナル
```

### 8.3 スレッド安全性

- 全てのUI更新はメインスレッドで実行
- `pyqtSignal`は任意のスレッドから安全に接続先を呼び出せる
- `QThread`の`result`, `error`, `message_received`などのシグナルで安全に通信
- `LatestSlot`パターンでスレッドセーフなフレームバッファを実現
- `QTimer`は常にメインスレッドで動作

---

## 9. フォロー走行モードの詳細

### 9.1 状態遷移図

```
                    ┌─────────────┐
                    │   LOST_TIMEOUT │
                    └──────┬──────┘
                           │ 対象検出
                           ↓
┌──────────┐    ┌──────────────┐    ┌─────────────┐
│  SEARCHING│───→│  HEAD_ON_HOLD │───→│  FOLLOWING  │
│(対象検索) │    │  (正面停止)    │    │(追従中)      │
└──────────┘    └──────────────┘    └──────┬──────┘
     ↑                                      │
     │                                      │ 対象ロスト
     │                                      ↓
┌──────────┐                    ┌──────────────┐
│  TURNING │←───────────────────│   APPROACHING │
│ (旋回中) │                    │   _BLIND      │
└──────────┘                    │ (盲点接近)    │
                                └──────────────┘
                                        │
                                        ↓
                                ┌──────────────┐
                                │    HOLDING    │
                                │ (停止保持)     │
                                └──────────────┘
```

### 9.2 コントロールの詳細

**距離PID制御:**
- kp_lin=70, ki_lin=0.4, kd_lin=10
- 距離帯の外側ではmin_pwm(180)寄りの低速
- 距離帯に近づくとmax_follow_pwm(200)まで加速
- `_distance_proportional_pwm()`で距離に比例した速度減速

**ジンバル制御:**
- `GimbalThread`: 約20Hzで動作
- パン優先補正: `pan_offset`が閾値以上の場合、パンのみを補正
- クールダウン: 角度変更後に`search_step_wait_sec`(0.6秒)待機
- フィードフォワード: 回転時にパンを前補償

**単純旋回モード:**
- `simple_turn_direction_flipped`: 旋回方向のフラグ
- PWM1あたりの回転角度: `body_deg_per_sec_per_pwm`

### 9.3 データフロー

```
YOLOv8-pose → FollowDetector → PoseInference
                                     │
                                     ↓
                            yaw_deg, dist_m, confidence
                                     │
                                     ↓
                            ControlThread._compute_command()
                                     │
                                     ├─ 距離PID計算
                                     ├─ 航向誤差計算
                                     ├─ 速度制限
                                     └─ モーターコマンド生成
                                     │
                                     ↓
                            GimbalThread._update()
                                     │
                                     ├─ 対象のパン角度計算
                                     ├─ クールダウン確認
                                     └─ サーボコマンド生成
```

---

## 10. エラーハンドリングとフォールバック

### 10.1 設定のフォールバック

```python
load_config():
  if config.json が存在:
    try: JSONをパース → デフォルト値とマージ
    except (JSONDecodeError, IOError): pass
  return DEFAULT_CONFIG.copy()  # 常にデフォルト値で初期化
```

### 10.2 API障害時のフォールバック

```python
CloudManager.initialize():
  try:
    CloudAPI() を作成
    test_connection()  # 非同期テスト
  except Exception as e:
    ログに "[WARNING] CloudManager initialize failed: {e}" を出力
    _add_log("API", f"Cloud API unavailable: {e}")
    # アプリはそのまま動作続行

VideoManager._cloud_api:
  try: cloud_mgr.cloud_api を設定
  except: _cloud_api = None
  # _cloud_api が None の場合は upload がスキップされる

RemoteControlServer:
  try: サーバーを作成
  except Exception as e: _remote_server = None
```

### 10.3 映像ストリーム障害

```python
MJPEGReceiver:
  - ReceiveThread: 接続が失敗した場合、自動再接続
  - DecodeThread: フレームがデコードできない場合はスキップ
  - PingThread: レイテンシ測定でタイムアウトを検出
  - タイムアウト: 10秒
```

### 10.4 WebSocket障害

```python
RoverWebSocket:
  - 接続が切断された場合、自動再接続
  - 再接続間隔: 100ms
  - メッセージキューでスタレーコマンドをフィルタリング（0.3秒）
  - sender_thread を分離して送信を非同期化
```

---

## 11. パフォーマンス最適化

### 11.1 デバウンス

| アクション | デバウンス時間 | 目的 |
|-----------|--------------|------|
| PIDパラメータ送信 | 400ms | スライダー操作中のHTTP送信を抑制 |
| LED輝度送信 | 300ms | スライダー操作中のHTTP送信を抑制 |
| 速度コマンド送信 | 150ms | キー入力中のWebSocket送信を抑制 |

### 11.2 フレーム処理

| 技術 | 効果 |
|------|------|
| `LatestSlot` パターン | 古いフレームを破棄し最新フレームのみ保持 |
| キューのフレームドロップ | 録画キューがいっぱいの場合、フレームを破棄 |
| デコードスレッドの分離 | JPEGデコードをメインスレッドから分離 |
| `_apply_flip()` のQTransform | GPUアクセラレーションされたフリップ |

### 11.3 アニメーション

| 技術 | 効果 |
|------|------|
| 指数減衰補間 (0.22) | 滑らかな針の移動、急激なジャンプを防止 |
| 20Hzタイマー | 十分な更新頻度、過度なCPU負荷を防止 |
| `SingleShot` タイマー | 一定間隔でのみ処理を実行 |

---

## 12. セキュリティ設計

| 機能 | 実装 |
|------|------|
| **secrets.py の分離** | APIキーを `secrets.py` に分離し、`.gitignore` で除外 |
| **config.json の分離** | 実行時設定を `config.json` に分離 |
| **Webリモート認証** | `_allow_remote_control` フラグでWeb制御の承認・拒否 |
| **E-STOP** | 物理的に即座にモーターを停止する緊急ボタン |
| **自動ブレーキ** | 超音波センサーの距離が閾値未満の場合、自動ブレーキ |
| **速度制限** | `_speed_limit_active` フラグで速度を制限 |

---

## 13. ビルド・デプロイ手順

### 13.1 前提条件

```bash
# Python 3.x をインストール
# 必要なライブラリをインストール
pip install -r requirements.txt
```

### 13.2 実行

```bash
# プロジェクトディレクトリ内で実行
cd robot-desktop-app-tokura
python main.py
```

### 13.3 設定の変更

```bash
# 1. config.json を直接編集するか、アプリ内で設定を変更
# 2. secrets.py はローカルでのみ存在（Gitに上げない）
# 3. 変更は自動的に反映される
```

### 13.4 ログの確認

```bash
# ログは logs/ ディレクトリに自動保存
ls logs/
# キャリブレーション結果は logs/calibration.csv
```

---

## 14. トラブルシューティング

### 14.1 ModuleNotFoundError: No module named 'config'

**原因**: `main.py` が異なるディレクトリから実行され、Pythonパスにプロジェクトディレクトリが含まれていない  
**解決**: `main.py` に `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` が追加済み。またはプロジェクトディレクトリ内で実行

### 14.2 Camera not connecting

**原因**: ESP32-CamのMJPEGストリームが正しく取得できない  
**確認**: 
- ESP32-CamのIPアドレスが正しいか確認
- `ConnectionManager.reconnect_camera()` が呼ばれているか確認
- MJPEGストリームのURLが正しいか確認

### 14.3 Follow mode not working

**原因**: 対象が検知されていない、またはPIDパラメータが不正  
**確認**: 
- YOLO/Person検知が有効になっているか確認
- `DetectionManager` のシグナルが正しく接続されているか確認
- PIDパラメータが設定されているか確認（Settingsタブ）

### 14.4 Cloud API not responding

**原因**: クラウドサーバーがオフライン、またはAPIキーが不正  
**確認**: 
- `CloudManager.initialize()` がエラーをキャッチしているか確認
- `secrets.py` のAPIキーが正しいか確認
- クラウドサーバーのURLが正しいか確認

---

## 15. バージョン履歴

| バージョン | 日付 | 変更点 |
|-----------|------|--------|
| v2.5.0 | 2026-09-16 | メインビューのオーバーレイ統合 |
| v2.4 | - | ヘッダー、サイドバー、ビューの統合 |
| v2.0 | - | PyQt6への移行、ダークテーマの導入 |
| v1.0 | - | 初期リリース |

---

## 16. ライセンス

プロジェクトのライセンス情報はリポジトリのルートに配置されています。

---

## 17. 参照

- **メインエントリ**: `main.py`
- **アプリケーションコア**: `app.py` (~980行)
- **設定管理**: `config.py`, `secrets.py`
- **テーマ**: `styles.py`
- **全ビュー**: `views/`
- **全ウィジェット**: `widgets/`
- **全マネージャー**: `connection_manager.py`, `video_manager.py`, `detection_manager.py`
- **API**: `esp32_api.py`, `cloud_api.py`, `cloud_worker.py`, `rover_ws.py`, `mjpeg_receiver.py`
- **フォロー走行**: `follow_controller.py`, `follow_mode/`
- **AI**: `gemini_chat.py`, `rccar_pose_inference/`
- **デバッグ**: `calibration.py`, `views/debug_view.py`
- **テスト**: `tests/`
