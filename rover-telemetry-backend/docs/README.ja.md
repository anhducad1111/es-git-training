# Rover Telemetry システム概要（日本語ドキュメント）

このドキュメントは `rover-telemetry-backend`（PHP製REST API）と `rover-telemetry-frontend`（素のHTML/CSS/JSダッシュボード）から成る「Rover Telemetry」システム全体を、機能・使い方の観点から日本語でまとめたものです。

より詳しい情報は以下も参照してください。

- API仕様の詳細一覧 → [`api-reference.ja.md`](./api-reference.ja.md)
- データベース設計の詳細 → [`database.ja.md`](./database.ja.md)
- 実装済みAPIの英語版コントラクト（実装準拠） → [`api-contract.md`](./api-contract.md)
- 元設計書（データベース／API／実装計画のフルスペック） → `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md`
- UIデザイン検討メモ → `rover-telemetry-frontend/docs/2026-09-08-rover-telemetry-dashboard-design.md`

## 1. システムの目的

ローバー（探査ロボット）が定期的に送信するセンサーデータ（温度・湿度・ガス濃度・距離など）を1台のPi5上のMySQLに集約し、Webダッシュボードでリアルタイム監視・過去データ分析・写真/動画ギャラリー閲覧・遠隔操作（テレオペレーション）・システム状態監視ができるようにするものです。

```
[ローバー] --HTTP POST--> [rover-telemetry-backend (PHP API)] --MySQL--> [telemetry_readings ほか]
                                     ^
                                     | HTTP GET (fetch)
                                     |
                          [rover-telemetry-frontend (ブラウザSPA)]
```

- バックエンドはフレームワークを使わない素のPHP実装（`src/Router.php` による軽量ルーティング）。
- フロントエンドはビルド不要の素のJS（`window.Api` 経由でfetch呼び出し）で、5つのタブ（画面）から構成されるシングルページ構成。
- ローバーの遠隔操作（COCKPITタブ）だけは、このバックエンドAPIを経由せず、ブラウザから直接WebSocket（`robot-desktop-app` 側のリレー）でローバーに接続します。

## 2. バックエンドの構成（rover-telemetry-backend）

```
public/index.php       ルーティング定義・エントリーポイント
src/Router.php          正規表現ベースの簡易ルーター
src/Config.php           .env から設定を読み込む
src/Database.php         PDO接続（通常/非バッファ接続）
src/Controllers/         エンドポイントごとに1クラス（例: RoverListController）
src/Repositories/        DBアクセス（クエリ）をまとめる層
src/Support/             共通処理（ApiException, ReadingFormatterなど）
src/Validation/          リクエストのバリデーション
sql/schema.sql           DBスキーマ（DDL）
bin/aggregate.php        毎分実行: telemetry_summaries / gateway_metrics の集計バッチ
bin/retention.php        夜間実行: 古いデータの間引き・削除バッチ
bin/simulate_rover.php   開発用: ダミーのテレメトリ送信スクリプト
bin/loadtest.php         負荷テスト用スクリプト
storage/media/           アップロードされた写真・動画の実体ファイル
storage/firmware/        アップロードされたファームウェアファイルの実体
tests/                   PHPUnitによるユニット/結合テスト
```

**アーキテクチャの要点**

- 認証なし（`api-contract.md` にも明記の通り、要確認事項として未確定）。学内トレーニング用途を想定したシンプル構成。
- 全レスポンスはJSON（`application/json; charset=UTF-8`）。写真・動画・ファームウェアのバイナリはストリーム配信。
- `GET /rovers/{uid}/readings` は `resolution` パラメータにより、生データ・分足・時間足・日足を自動/明示選択できる（大量データでもチャートが重くならない設計）。
- `bin/aggregate.php` が毎分 `telemetry_summaries`（統計サマリ）と `gateway_metrics`（システム負荷履歴）を更新し、ダッシュボードの高速表示を支えている。
- `bin/retention.php` が古い生データを段階的に間引く（保存期間ポリシーは `sql/schema.sql` / 設計書 §8.4 参照）。

## 3. フロントエンドの構成（rover-telemetry-frontend）

```
public/index.html        タブ切り替え式SPAの骨格（5タブ）
public/js/config.js       APIのベースURLやポーリング間隔などの設定値
public/js/api.js          window.Api: バックエンドAPIを呼び出す薄いラッパー
public/js/roverselection.js  現在選択中のローバーIDを全画面で共有する小さなストア
public/js/app.js          タブ切り替えの制御（各タブのmount/start/stop呼び出し）
public/js/live.js         LIVEタブ（リアルタイム監視）
public/js/history.js      HISTORYタブ（過去データ検索・グラフ・CSV/JSONエクスポート）
public/js/gallery.js      GALLERYタブ（写真・動画ギャラリー）
public/js/control.js      COCKPITタブ（遠隔操作・WebSocket）
public/js/system.js       SYSTEMタブ（サーバー状態監視・しきい値設定）
public/js/charts.js       Chart.jsを使ったグラフ描画の共通処理
public/js/rejectchips.js  バリデーションエラー（弾かれたデータ）の表示バッジ
public/js/timeutil.js     日時フォーマット共通処理
public/css/style.css      スタイル一式
```

APIのベースURLは `public/js/config.js` の `APP_CONFIG.API_BASE_URL` で設定されており、既定値は次の通りです（XAMPPのドキュメントルート配下にバックエンドを配置する前提のパス）。

```js
API_BASE_URL: '/es-git-training/rover-telemetry-backend/public/api/v1'
```

## 4. 画面（タブ）ごとの機能・使い方

ヘッダー上部のタブから5つの画面を切り替えます。全画面共通で、右上に `health-badge`（`GET /api/v1/health` によるバックエンド死活状態）が表示されます。ローバーの選択状態（`RoverSelection`）はタブをまたいで共有されます。

### 4.1 LIVE（リアルタイム監視）

- 1秒間隔（`POLL_INTERVAL_LIVE_MS`）でポーリングし、選択中ローバーの最新テレメトリをカード表示。
- 直近の温度・湿度・ガス濃度・距離をリアルタイムの折れ線チャートで表示（`loadTelemetryChart`）。
- 障害物検知（`auto_brake`）の発生回数を時系列で可視化（`loadObstacleChart`）。
- センサー値がしきい値（`sensor_limits`）に近い/超えている場合、警告バーで表示（`renderSensorLimitBars`）。
- 直近のイベント（しきい値超過・自動ブレーキON/OFF・再接続など）を一覧表示（`renderRecentEvents`）。
- 全ローバーの一覧をフリート表示し、オンライン/劣化/オフライン状態を色分け（`renderFleet`、`statusDotClass`）。

### 4.2 HISTORY（過去データ・分析）

- ローバーと期間（開始/終了日時）を指定して過去データを検索。
- `resolution=auto|raw|minute|hour|day` により、期間の長さに応じて自動的に集計粒度を切り替えたグラフを描画（`runQuery` → `Api.readings`）。
- 複数センサーを同時表示する場合は、単位（℃・%・ppm・cm）が異なるため、それぞれ別軸のプレーンな平均線として重ね描画（min/maxの帯グラフは表示しない設計、`renderHistoryChart` 内コメント参照）。
- データが存在しない期間（欠測区間 `gaps`）を一覧表示（`renderGapsList`）。
- 集計統計（`/summary` エンドポイント、min/avg/max、障害物イベント数）をパネル表示（`loadSummaryPanels`）。
- CSV/JSON形式でのエクスポート機能（`triggerExport` → `Api.exportUrl`、`GET /rovers/{uid}/export`）。

### 4.3 GALLERY（写真・動画ギャラリー）

- 選択中ローバーがアップロードした写真・動画の一覧をサムネイル表示（`loadMediaGallery`）。
- クリックでライトボックス表示、前後の画像・動画に矢印キー等で移動可能（`openLightbox`/`showAdjacent`）。
- 削除操作（`DELETE /rovers/{uid}/media/{id}`）に対応。

### 4.4 COCKPIT（遠隔操作／テレオペレーション）

- **このタブのみ、バックエンドAPIを経由せず、ブラウザから直接WebSocket（`ws://<address>/`）でロボット側のリレー（`robot-desktop-app`）に接続**します（`control.js` の `connect()`）。
- W/S/A/D キーで走行、I/J/K/L キーでカメラのパン・チルト操作（±5°刻み）、Cキーでジンバル中央復帰、Spaceキーで緊急停止。キー割り当ては `robot-desktop-app` 側と統一。
- パン（N/S/W/E）・チルト（UP/DN/LVL）の現在角度を半円形のダイヤルUIで表示（`gimbalDialSvg`、`setDialNeedle`）。
- カメラ映像のプレビュー表示、および表示のみの水平/垂直反転（`updateFlipTransform`。これはリレーではなく描画側の処理のため、接続許可状態に関わらず操作可能）。
- 接続状態（未接続/接続中/接続済み/エラー）の表示（`renderConnectionState`）。
- 画面下部に、既存の `GET /rovers/{uid}/latest` テレメトリAPIを使った読み取り専用の簡易テレメトリ表示もあり（WebSocketリレーとは独立、`pollTelemetry`）。
- 接続設定（アドレス等）は `localStorage` に保存され次回も再利用されます（プライベートブラウジング等で使えない場合は接続自体には影響しない設計）。

### 4.5 SYSTEM（サーバー・システム状態監視）

- Pi5本体のCPU使用率・CPU温度・メモリ/ディスク使用率、データベースサイズ・行数、直近の受信レート等を表示（`GET /api/v1/system`）。
- しきい値を超えた項目は警告色で強調表示（`cardClass`）。
- `aggregate_job` / `retention_job` といったバックグラウンドジョブの最終実行時刻など、サービス稼働状況を表示（`renderServices`）。
- 過去のリソース推移グラフ（`GET /api/v1/system/history`、`loadResourceCharts`）と、DBサイズの将来予測（簡易線形予測、`projectGrowth`）。
- センサーのバリデーション範囲（`sensor_limits`）をGUIから編集可能（`loadSensorLimitEditor`/`wireSensorLimitEditor` → `PUT /config/sensor-limits/{field}`）。

## 5. 開発・運用時の補足

- 開発時はダミーデータ送信用に `bin/simulate_rover.php` を利用できます。
- テストは PHPUnit（`tests/Unit`, `tests/Integration`）。`composer.json` にスクリプトが定義されている想定。
- 本番運用（Raspberry Pi 5）では php-fpm + 永続PDO接続を前提とし、`GET /latest` は30msの応答時間バジェットを想定（詳細は `api-contract.md` の「Deployment note」参照）。
- メディア/ファームウェアの保存先は環境変数（`MEDIA_STORAGE_PATH` / `FIRMWARE_STORAGE_PATH`）で切り替え可能。開発環境ではプロジェクト直下の `storage/media` / `storage/firmware` を使用。
