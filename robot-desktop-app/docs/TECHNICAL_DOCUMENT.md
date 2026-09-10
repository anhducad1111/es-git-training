# ロボットデスクトップアプリ - テクニカルドキュメント

## 目次

1. [システム概要](#1-システム概要)
2. [アーキテクチャ](#2-アーキテクチャ)
3. [追従モードアルゴリズム](#3-追従モードアルゴリズム)
4. [後ろ向き対応アルゴリズム](#4-後ろ向き対応アルゴリズム)
5. [技術仕様](#5-技術仕様)
6. [データフロー](#6-データフロー)

---

## 1. システム概要

### 1.1 機能

- ESP32-CAMからのMJPEGストリーム受信
- YOLOv8-Poseによる車検出・ポーズ推定
- Stanley制御による自動追従
- キャリブレーション機能
- 画像キャプチャ機能

### 1.2 対象ハードウェア

| デバイス | 用途 |
|---------|------|
| ESP32-CAM | 前の車（カメラ付き） |
| ESP32 | 後ろの車（制御対象） |
| ArUcoマーカー | 前の車に設置、検出用 |

---

## 2. アーキテクチャ

### 2.1 ファイル構成

```
app2/
├── app.py                  # メインアプリケーション（GUI）
├── detectors.py            # 検出器クラス群
├── follow_controller.py    # Stanley制御追従コントローラー
├── workers.py              # ワーカースレッド
├── capture.py              # 画像キャプチャ
├── calibration.py          # キャリブレーション
├── marker_tracking.py      # マーカートラッキング
├── latest_frame.py         # フレーム管理
├── mjpeg.py                # MJPEGパーサー
└── rccar_pose_model/       # 学習済みモデル
```

### 2.2 クラス構成

```
MainWindow (app.py)
├── CaptureWorker (workers.py)      # ネットワークI/O
├── InferenceWorker (workers.py)    # 検出処理
├── FollowController (follow_controller.py)  # 追従制御
└── MarkerTracker (marker_tracking.py)       # マーカートラッキング

Detector (detectors.py)
├── NullDetector
├── HogDetector
├── ArucoDetector
├── UltralyticsDetector
└── RcCarPoseDetector              # 車検出・ポーズ推定
```

---

## 3. 追従モードアルゴリズム

### 3.1 Stanley制御の原理

Stanley制御は自律走行で広く使用される追従アルゴリズムです。

```
制御式: δ = ψ + atan(k × e / v)

δ: ステアリング角度
ψ: ヘディングエラー（車の向きと目標の角度差）
e: クロストラックエラー（横方向のズレ）
k: ゲインパラメータ
v: 車速
```

### 3.2 計算ロジック

```python
def control(self, yaw_deg, dist_m, speed):
    # 1. ヘディングエラーをラジアンに変換
    psi = math.radians(yaw_deg)
    
    # 2. クロストラックエラーを計算
    e = dist_m * math.sin(psi)
    
    # 3. Stanley制御式を適用
    if speed > 0.1:
        delta = psi + math.atan2(self.k * e, speed)
    else:
        delta = psi  # 低速時はシンプルな比例制御
    
    # 4. ステアリング角度を制限
    delta_deg = max(-self.max_steer, min(self.max_steer, math.degrees(delta)))
    
    # 5. スロットルを計算
    if abs(delta_deg) < 10 and dist_m > 0.5:
        throttle = min(1.0, dist_m / 2.0)
    elif dist_m < 0.3:
        throttle = 0.0
    else:
        throttle = 0.3
    
    return delta_deg, throttle
```

### 3.3 パラメータ

| パラメータ | 初期値 | 調整指針 |
|-----------|--------|---------|
| k (ゲイン) | 0.5 | 大きいほど横方向の補正が強くなる |
| max_steer | 30度 | 最大旋回角 |
| target_speed | 100 | 基準速度 |

---

## 4. 後ろ向き対応アルゴリズム

### 4.1 課題

前の車が後ろから来る場合、通常のPID制御では対応困難：
- 後ろを向いた状態での追従が不安定
- 旋回中の追跡を失う可能性
- 壁との衝突リスク

### 4.2 状態マシン設計

```
┌─────────────────────────────────────────────────────┐
│                    FOLLOWING                        │
│  (Stanley追従 - 車が前方にいる)                      │
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

### 4.3 状態定義

```python
class FollowState(Enum):
    FOLLOWING = "following"      # 通常のStanley追従
    TURNING = "turning"          # 低速で旋回中
    WAITING = "waiting"          # 停止して車を待つ
    SEARCHING = "searching"      # 車を探索中
```

### 4.4 状態遷移条件

| 現在の状態 | 条件 | 次の状態 | 説明 |
|-----------|------|---------|------|
| FOLLOWING | `abs(yaw) > 90° && dist > 1.0m` | TURNING | 車が後ろで遠い → 旋回開始 |
| FOLLOWING | `abs(yaw) > 90° && dist <= 1.0m` | WAITING | 車が後ろで近い → 停止して待つ |
| FOLLOWING | 検出なし | SEARCHING | 車を見失った → 探索 |
| TURNING | `abs(yaw) < 30°` | FOLLOWING | 旋回完了 → 通常追従に戻る |
| TURNING | タイムアウト（5秒） | WAITING | 旋回が長すぎる → 停止 |
| TURNING | `dist < 0.3m` | WAITING | 近づきすぎ → 停止 |
| WAITING | `abs(yaw) < 30°` | FOLLOWING | 車が前方に来た → 追従開始 |
| SEARCHING | 検出成功 && `abs(yaw) < 60°` | FOLLOWING | 車を発見（前方） |
| SEARCHING | 検出成功 && `abs(yaw) >= 60°` | TURNING | 車を発見（後方） |

### 4.5 各状態の制御ロジック

#### FOLLOWING（通常追従）

```python
def _control_following(self, yaw_deg, dist_m):
    steering, throttle = self.stanley.control(yaw_deg, dist_m, self.target_speed / 100.0)
    if abs(steering) < 5:
        self.send_command("forward")
    elif steering > 0:
        self.send_command("right")
    else:
        self.send_command("left")
    self.send_command(f"speed:{int(throttle * self.target_speed)}")
```

- **入力**: yaw_deg（角度）、dist_m（距離）
- **出力**: forward/right/left + speed
- **特徴**: Stanley制御による滑らかな追従

#### TURNING（旋回）

```python
def _control_turning(self, yaw_deg):
    direction = "right" if yaw_deg > 0 else "left"
    self.send_command(direction)
    self.send_command("speed:80")
```

- **入力**: yaw_deg（角度）
- **出力**: right/left + speed:80
- **特徴**: 低速で安全に旋回

#### WAITING（停止待機）

```python
def _control_waiting(self):
    self.send_command("stop")
```

- **入力**: なし
- **出力**: stop
- **特徴**: 車が前方に来るまで停止

#### SEARCHING（探索）

```python
def _control_searching(self):
    self.send_command("forward")
    self.send_command("speed:50")
```

- **入力**: なし
- **出力**: forward + speed:50
- **特徴**: 低速で前進しながら車を探す

### 4.6 安全機能

```python
def update(self, yaw_deg, dist_m, obstacle_dist=None):
    # 障害物検出
    if obstacle_dist is not None and obstacle_dist < 0.3:
        self.send_command("stop")
        return
    
    # 距離チェック
    if dist_m < 0.2:
        self.send_command("stop")
        return
    
    # 通常の制御ロジック
    self._check_transitions(yaw_deg, dist_m)
    # ...
```

- **障害物検出**: 距離センサーで障害物を検出 → 即停止
- **最小距離**: 0.2m以下で停止
- **壁衝突回避**: 後退操作なし

---

## 5. 技術仕様

### 5.1 検出器仕様

| 検出器 | 使用技術 | 検出対象 | ポーズ推定 |
|--------|---------|---------|-----------|
| UltralyticsDetector | YOLOv8 | オブジェクト | なし |
| RcCarPoseDetector | YOLOv8-Pose | 車 | yaw, 距離 |
| ArucoDetector | ArUco | マーカー | 3Dポーズ |
| HogDetector | HOG+SVM | 人物 | なし |

### 5.2 RcCarPoseDetectorの仕様

```
入力: 画像フレーム
  ↓
YOLOv8-Pose推論
  ↓
キーポイント検出 (L/R wheel, front ground contact)
  ↓
Ground Plane Model → yaw_deg, dist_m
  ↓
ArUco補正（マーカー検出時）
  ↓
出力: Detection(yaw_deg, dist_m)
```

### 5.3 通信仕様

| プロトコル | 用途 | コマンド |
|-----------|------|---------|
| MJPEG | 映像ストリーム | - |
| WebSocket | 車制御 | forward, backward, left, right, stop, drive:v,w, speed:N |
| REST API | 設定 | /speed, /api/distance, /api/pid, /servo/angle |

### 5.4 パラメータ調整ガイド

#### Stanley制御のパラメータ調整

| 症状 | 調整対象 | 変更方向 |
|------|---------|---------|
| 横振れが大きい | k を小さく | 0.3 → 0.1 |
| 追従が遅すぎる | k を大きく | 0.5 → 1.0 |
| 旋回が激しい | max_steer を小さく | 30 → 15 |
| 直進で不安定 | max_steer を大きく | 30 → 45 |

#### 状態遷移のパラメータ調整

| パラメータ | 初期値 | 調整指針 |
|-----------|--------|---------|
| turn_start_dist | 1.0m | 旋回開始距離 |
| stop_dist | 0.3m | 停止距離 |
| turn_complete_yaw | 30度 | 旋回完了判定 |
| follow_max_yaw | 60度 | 追従可能最大角度 |

---

## 6. データフロー

### 6.1 全体フロー

```
ESP32-CAM (MJPEG)
  ↓
CaptureWorker (JPEGデコード)
  ↓
InferenceWorker (RcCarPoseDetector)
  ↓
Detection(yaw_deg, dist_m)
  ↓
FollowController (Stanley制御)
  ↓
rover_ws.send("left"/"right"/"forward")
  ↓
rover_ws.send("speed:N")
  ↓
ESP32 → モーター制御
```

### 6.2 詳細フロー

```
1. フレーム受信
   - CaptureWorker: MJPEG受信 → JPEGデコード
   - LatestFrameに格納

2. 検出処理
   - InferenceWorker: フレーム取得 → RcCarPoseDetector.detect()
   - Detectionオブジェクト生成

3. 追従制御
   - FollowController.update(yaw_deg, dist_m)
   - 状態遷移判定
   - 制御コマンド生成

4. コマンド送信
   - WebSocket経由でESP32に送信
   - モーター制御実行
```

---

## 付録: 用語集

| 用語 | 定義 |
|------|------|
| Yaw角 | 車体の向き（左右の回転角度） |
| Pitch角 | 車体の前後の傾き |
| Roll角 | 車体の左右の傾き |
| クロストラックエラー | 目標パスからの横方向のズレ |
| ヘディングエラー | 目標方向との角度差 |
| Stanley制御 | 自律走行で使用される追従アルゴリズム |
| PID制御 | 比例・積分・微分制御 |
