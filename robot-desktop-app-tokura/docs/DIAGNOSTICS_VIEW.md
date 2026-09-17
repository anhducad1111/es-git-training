# Diagnostics View (診断ビュー) 説明

## 構成

Diagnosticsビューは、左側の「DATA VIEW」エリアと右側の「AI SENSOR ANALYST」チャットエリアで構成されます。

---

## 左側: DATA VIEW

### タブ切り替え
- **CHARTS**: グラフ表示モード
- **TABLE**: テーブル表示モード



### テーブル (Table)
- テレメトリデータの一覧表示
- 列: 記録時刻、温度、湿度、ガス、距離など
- ページネーション機能付き

### 履歴 (History)
- 過去のテレメトリデータを読み込み・表示
- チャートとテーブルを切り替えて確認可能

---


---

# Snapshots (スナップショット) タブ

## 構成

Snapshotsタブは、クラウドから取得したスナップショット（写真・動画）を閲覧・操作・ダウンロード・削除・画像処理できるタブです。

---

## レイアウト

### 左側: スナップショット一覧

- **タイトル**: "SNAPSHOT GALLERY"
- **REFRESHボタン**: クラウドからスナップショットを再読み込み
- **ページネーション**: ページ番号ボタン（1, 2, 3...）
- **ナビゲーション**: PREV / NEXTボタン
- **グリッド**: スナップショットのサムネイルをグリッド表示
  - 1ページあたりPAGE_SIZE枚表示
  - サムネイルをクリックで選択・プレビュー表示

### 右側: プレビュー・操作パネル

- **PREVIEW**: 選択したスナップショットのプレビュー
  - 写真: QPixmapで表示
  - 動画: OpenCVで最初のフレームを抽出して表示
- **INFO**: 選択したスナップショットの情報表示
  - ID, Type, MIME, Size, Captured時刻
- **IMAGE PROCESSING**: 画像処理ボタン群
  - AUTO CORRECT: 自動色補正
  - ENHANCE CONTRAST: コントラスト強調
  - DENOISE: ノイズ除去
  - BICUBIC (1.5x): バイリニアアップスケール
- **APPLY SELECTEDボタン**: 選択した処理をまとめて適用
- **DOWNLOADボタン**: 処理済み画像をローカルに保存
- **DELETEボタン**: クラウドからスナップショットを削除

---

## 機能

### スナップショット読み込み

1. **REFRESHボタン**をクリック
2. `QProgressDialog`で「Loading snapshots...」を表示
3. `cloud_api.get_media()`でクラウドからメディア一覧を取得
4. 読み込み完了後、ページネーションを更新しグリッドを表示

### プレビュー表示

1. グリッドのサムネイルをクリック
2. `cloud_api.get_media_item(snap_id)`でメディアデータを取得
3. メディアタイプに応じて表示:
   - **写真**: QPixmap.loadFromData()で表示
   - **動画**: OpenCVでVideoCaptureし、最初のフレームを取得してQImageに変換

### 画像処理

- **個別処理**: ボタンをクリックして個別に処理を実行
- **まとめて処理**: 複数の処理を選択し「APPLY SELECTED」をクリック
- **処理エンジン**: `ImageProcessor`クラスを使用（OpenCV）
- **処理モード**:
  - `auto`: 自動色補正
  - `contrast`: コントラスト強調
  - `denoise`: ノイズ除去
  - `bicubic`: バイリニアアップスケール (1.5x)
- **処理結果**: プレビューに即座に反映

### ダウンロード

1. **個別ダウンロード**: 選択したスナップショットをダウンロード
2. **処理済み画像ダウンロード**: `_processed_image`が存在する場合、ファイルダイアログで保存先を選択
   - フォーマット: PNGまたはJPG
   - 保存先: `snapshot/`ディレクトリ

### 削除

1. スナップショットを選択
2. **DELETEボタン**をクリック
3. `cloud_api.delete_media(snap_id)`でクラウドから削除
4. 削除後に一覧を再読み込み

### クラウドアップロード

スナップショット撮影時、自動的にクラウドにアップロード:
1. `video_manager.take_snapshot()`で画像を保存
2. `_upload_snapshot()`で`cloud_api.upload_media()`を呼び出し
3. クラウドにPOSTリクエストでアップロード

---

## フロー図

```
REFRESHクリック
    ↓
QProgressDialog表示
    ↓
cloud_api.get_media()
    ↓
_snapshots_loaded()
    ↓
ページネーション更新 + グリッド表示
    ↓
ユーザーがサムネイルをクリック
    ↓
cloud_api.get_media_item(snap_id)
    ↓
プレビュー表示 (写真/動画)
    ↓
画像処理ボタンをクリック
    ↓
ImageProcessor実行 (QThread)
    ↓
処理結果をプレビューに反映
    ↓
DOWNLOAD/DELETE実行
```

---

## ファイル構成

| ファイル | 役割 |
|----------|------|
| `views/snapshots_view.py` | Snapshotsビュー全体の構築 |
| `cloud_api.py` | クラウドとのメディア通信 |
| `video_manager.py` | スナップショット撮影とアップロード |
| `image_processor.py` | 画像処理エンジン (OpenCV) |

---

## 必要なパッケージ

```bash
pip install opencv-python
```

---

## 設定

クラウドとの通信には`config.json`の以下の設定が必要:
```json
{
  "cloud_api_url": "http://192.168.1.77/es-git-training/rover-telemetry-backend/public/api/v1",
  "device_uid": "rover-001"
}
```
