# スレッド一覧まとめ（機能別）

---

## 1. 映像機能（カメラ映像の取得・表示）

ESP32-CamからのMJPEGストリームを受信し、Desktop上にリアルタイムで表示する機能に使われるスレッド。アプリ起動時にすべて生成される。

| スレッド名 | 種類 | 生成タイミング | 周期 | 何をしているか |
|-----------|------|---------------|------|----------------|
| **ReceiveThread** | QThread | `MJPEGReceiver.start()` | 連続 | ESP32-CamのMJPEGストリームをHTTPで受信。`MjpegParser`でフレームをパースし、複数あれば最新1枚だけ`raw_slot`に保存。古いフレームは破棄 |
| **DecodeThread** | QThread | `MJPEGReceiver.start()`（ReceiveThreadと同時） | 連続 | `raw_slot`からJPEGデータを取得し`QImage`にデコード。`if raw_slot._has_item: continue`で古いフレームをスキップし、常に最新1フレームのみ`display_slot`に渡す |
| **PingThread** | QThread | `MJPEGReceiver.start()`（ReceiveThreadと同時） | 1秒ごと | `requests.head()`でHEADリクエストを送り、ESP32-Camとのレイテンシーを測定。結果を`ping_updated`シグナルでUIに渡す |

**対応ファイル**: `mjpeg_receiver.py`

---

## 2. ローバー操作機能（ESP32-MCUとの通信）

キーボード・ボタン・マウスからの操作コマンドをESP32-MCUに送信し、WebSocket通信を管理する機能に使われるスレッド。アプリ起動時に生成される。

| スレッド名 | 種類 | 生成タイミング | 周期 | 何をしているか |
|-----------|------|---------------|------|----------------|
| **RoverWebSocket** | QThread | `ConnectionManager.start_all()`（アプリ起動時） | 連続 | ESP32-MCUとのWebSocket接続を管理。`websocket.run_forever()`で接続を維持。受信メッセージを`message_received`シグナルで発行。切断時は2秒後に自動再接続 |
| **_send_thread** | threading.Thread | `RoverWebSocket._on_open()`（WebSocket接続確立時のみ） | 連続 | WebSocketの非ブロッキング送信。`_send_queue`からコマンドを取り出し、0.3秒以上古いスタレーコマンドは破棄して`ws.send()`で送信 |

**対応ファイル**: `rover_ws.py`

---

## 3. テレメトリ機能（センサー監視）

ESP32に搭載されたセンサー（温度・湿度・ガス・距離・障害物）のデータを定期的に取得し、UIに表示する機能に使われるスレッド。アプリ起動時に生成される。

| スレッド名 | 種類 | 生成タイミング | 周期 | 何をしているか |
|-----------|------|---------------|------|----------------|
| **TelemetryPoller** | QThread | `ConnectionManager.start_all()`（アプリ起動時） | 200ms間隔 | `GET /api/telemetry`でESP32の温度・湿度・ガス・距離・障害物データを取得。`_driving`フラグがTrueの場合は100msスリープしてポーリングを減速 |

**対応ファイル**: `telemetry_poller.py`

---

## 4. Webリモート制御機能（ブラウザからの操作）

WebブラウザからWebSocket経由でロボットを操作できるようにする機能に使われるスレッド。アプリ起動時に生成される。

| スレッド名 | 種類 | 生成タイミング | 周期 | 何をしているか |
|-----------|------|---------------|------|----------------|
| **RemoteControlServer** | QThread + asyncio | `app.py`初期化時 | 連続 | ポート8765でWebSocketサーバーを起動。Webブラウザからの接続を受け付け、コマンドを`command_received`シグナルで`_relay_command()`に渡す。`_allowed`フラグで認可制御 |

**対応ファイル**: `remote_control_server.py`

---

## 5. フォロー走行機能（自律走行）

YOLOv8-poseによる人物検知・姿勢推定を基に、ロボットカーが自動的に対象を追従する機能に使われるスレッド。フォロー走行モードがONの時にのみ生成される。

| スレッド名 | 種類 | 生成タイミング | 周期 | 何をしているか |
|-----------|------|---------------|------|----------------|
| **DetectionThread** | threading.Thread | `FollowController.start()`（フォロー走行ON時のみ） | ~30fps | YOLOv8-poseモデルでカメラフレームから人物のバウンディングボックスとキーポイントを推論。結果を`ControlThread`/`GimbalThread`に渡す |
| **GimbalThread** | threading.Thread | `FollowController.start()`（フォロー走行ON時のみ） | ~20Hz | 対象のパン角度を計算し、サーボコマンドでジンバルを自動追従。パン優先補正・クールダウン（0.6秒）・フィードフォワード機能あり |
| **ControlThread** | threading.Thread | `FollowController.start()`（フォロー走行ON時のみ） | ~10Hz | 対象までの距離をPID制御（kp=70, ki=0.4, kd=10）で調整。8状態ステートマシン（FOLLOWING, TURNING, SEARCHING等）でフォロー走行の状態遷移を制御。障害物30cm以内で自動ブレーキ |
| **CommandThread** | threading.Thread | `FollowController.start()`（フォロー走行ON時のみ） | 連続 | `ControlThread`が生成したモーターコマンドを`ConnectionManager.send_command()`に渡し、WebSocket経由でESP32に送信 |

**対応ファイル**: `follow_controller.py`

---

## 6. 録画・スナップショット機能（記録・保存）

カメラ映像を動画として録画し、またはフレームをスナップショットとしてキャプチャ・保存する機能に使われるスレッド。RECボタンやSNAPボタンが押された時に生成される。

| スレッド名 | 種類 | 生成タイミング | 周期 | 何をしているか |
|-----------|------|---------------|------|----------------|
| **録画スレッド** | threading.Thread | `VideoManager.start_recording()`（RECボタンON時のみ） | 連続 | `Queue(maxsize=30)`にフレームをバッファリングし、OpenCVで`rec_YYYYMMDD_HHMMSS.avi`に書き込み。キューがfullの場合は古いフレームをドロップ |

**対応ファイル**: `video_manager.py`

---

## 7. クラウド連携機能（データ送信・管理）

テレメトリデータをクラウドサーバーに送信したり、スナップショット・動画をアップロード・管理したりする機能に使われるスレッド。オンデマンドで生成され、処理完了後に自動削除される。

| スレッド名 | 種類 | 生成タイミング | 何をしているか |
|-----------|------|---------------|----------------|
| **CloudWorker** | QThread | CloudManager.send_telemetry()、スナップショット/動画アップロード、OTA更新時 | GET/POST/DELETE/UPLOADでクラウドサーバーへHTTPリクエスト。進行状況を`progress`シグナルでUIに渡す |

**対応ファイル**: `cloud_worker.py`, `cloud_manager.py`

---

## 8. AI分析機能（センサー分析・チャート生成）

Gemini AIと対話し、センサーデータの分析やチャート作成を依頼する機能に使われるスレッド。オンデマンドで生成される。

| スレッド名 | 種類 | 生成タイミング | 何をしているか |
|-----------|------|---------------|----------------|
| **GeminiChat** | QThread | 診断ビューでAIチャットのSENDボタン押下時 | `gemini-3.5-flash-lite`モデルにセンサーデータ+質問を送信し、AIの分析結果を返す。カスタムツール`create_custom_charts`でチャート生成も可能 |

**対応ファイル**: `gemini_chat.py`

---

## 9. 画像処理機能（スーパー解像度）

カメラ映像を4xアップスケールして高解像度にする機能に使われるスレッド。Super ResolutionチェックがONの時に生成される。

| スレッド名 | 種類 | 生成タイミング | 何をしているか |
|-----------|------|---------------|----------------|
| **SuperResolutionWorker** | QThread | Super ResolutionチェックON時 | Hugging Face Gradio APIにフレームを送り4xアップスケール。API障害時はPillowのBicubic補間でフォールバック |

**対応ファイル**: `video_manager.py`

---

## 10. デバッグ・キャリブレーション機能（開発・調整）

ジャイロのキャリブレーションやフォロー走行のパラメータ調整を行う機能に使われるスレッド。デバッグビューのボタンが押された時に生成される。

| スレッド名 | 種類 | 生成タイミング | 何をしているか |
|-----------|------|---------------|----------------|
| **OTA Worker** | QThread | OTAファームウェア更新ボタン押下時 | クラウドサーバーからファームウェアをダウンロードしESP32にアップロード |
| **SnapshotWorker** | QThread | スナップショット一覧の読み込み・削除・ダウンロード時 | クラウドAPIとの通信でスナップショットの管理を行う |
| **CalibrationWorker** | QThread | デバッグビューでREFRESHボタン押下時 | ジャイロのキャリブレーションやPIDパラメータの調整計算を行う |

**対応ファイル**: `upload_panel.py`, `snapshots_view.py`, `debug_view.py`

---

## 状態別スレッド数まとめ

| 状態 | スレッド数 | 構成 |
|------|-----------|------|
| **通常モード** | **8本** | GUI + ReceiveThread + DecodeThread + PingThread + RoverWebSocket + _send_thread + TelemetryPoller + RemoteControlServer |
| **フォロー走行ON** | **12本** | 上記8本 + DetectionThread + GimbalThread + ControlThread + CommandThread |
| **フォロー走行+録画ON** | **13本** | 上記12本 + 録画スレッド |
| **+ CloudWorker等** | **13+n本** | 上記 + CloudWorker(n個同時)、GeminiChat、SuperResWorker等 |

---

## デーモンスレッド一覧

| スレッド名 | 終了条件 |
|-----------|----------|
| `_send_thread` | WebSocket接続が切断された時 |
| 録画スレッド | RECボタンが再び押された時、またはアプリ終了時 |

---

## 全スレッドのファイル対応表

| スレッド名 | 定義ファイル |
|-----------|-------------|
| ReceiveThread, DecodeThread, PingThread, LatestSlot | `mjpeg_receiver.py` |
| RoverWebSocket | `rover_ws.py` |
| TelemetryPoller | `telemetry_poller.py` |
| RemoteControlServer | `remote_control_server.py` |
| DetectionThread, GimbalThread, ControlThread, CommandThread | `follow_controller.py` |
| 録画スレッド | `video_manager.py` |
| CloudWorker | `cloud_worker.py` |
| CloudManager | `cloud_manager.py` |
| GeminiChat | `gemini_chat.py` |
| SuperResolutionWorker | `video_manager.py` |
| OTA Worker | `upload_panel.py` |
| SnapshotWorker | `snapshots_view.py` |
| CalibrationWorker | `debug_view.py` |
| FollowController | `follow_controller.py` |
| ConnectionManager | `connection_manager.py` |
