# Rover Telemetry API リファレンス（日本語版）

ベースパス: `/api/v1`（フロントエンドからは `public/js/config.js` の `APP_CONFIG.API_BASE_URL` 経由でアクセス）
- ボディ形式: JSON（UTF-8）。写真/動画/ファームウェアのアップロードのみ `multipart/form-data`。
- 認証: なし（学習用途のため未実装。本番導入時は要検討）。
- 実装元: `public/index.php`（ルーティング）、`src/Controllers/*`（各エンドポイントごとに1クラス）。

本ドキュメントは実装（`public/index.php`, `src/Controllers`）と既存の `docs/api-contract.md` を突き合わせて日本語でまとめたものです。厳密なフィールド定義は `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md` の「6. API Contract」も参照してください。

## エンドポイント一覧

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/api/v1/telemetry` | テレメトリデータの受信（ローバー→サーバー） |
| GET | `/api/v1/rovers` | ローバー一覧（状態つき） |
| GET | `/api/v1/rovers/{device_uid}/latest` | 指定ローバーの最新データ |
| GET | `/api/v1/rovers/{device_uid}/readings` | 生データ/集計データの範囲・件数指定取得 |
| GET | `/api/v1/rovers/{device_uid}/summary` | 分/時/日単位の統計サマリ |
| GET | `/api/v1/rovers/{device_uid}/export` | CSV/JSON形式でのエクスポート |
| GET | `/api/v1/rovers/{device_uid}/events` | 派生イベント一覧（しきい値超過・自動ブレーキ等） |
| GET | `/api/v1/health` | ヘルスチェック |
| GET | `/api/v1/system` | サーバー・DBの現在のリソース状況 |
| GET | `/api/v1/system/history` | サーバーリソースの時系列履歴 |
| GET | `/api/v1/validation-errors/summary` | バリデーションエラーの集計 |
| GET | `/api/v1/validation-errors` | バリデーションエラーの一覧 |
| GET | `/api/v1/config/sensor-limits` | センサー値の許容範囲設定を取得 |
| PUT | `/api/v1/config/sensor-limits/{field}` | センサー値の許容範囲設定を更新 |
| POST | `/api/v1/rovers/{device_uid}/media` | 写真/動画のアップロード |
| GET | `/api/v1/rovers/{device_uid}/media` | 写真/動画の一覧 |
| GET | `/api/v1/rovers/{device_uid}/media/{id}` | 写真/動画バイナリの配信 |
| DELETE | `/api/v1/rovers/{device_uid}/media/{id}` | 写真/動画の削除 |
| POST | `/api/v1/firmware` | ファームウェアのアップロード |
| GET | `/api/v1/firmware` | ファームウェア一覧 |
| GET | `/api/v1/firmware/latest` | 最新ファームウェア情報 |
| GET | `/api/v1/firmware/{id}/download` | ファームウェアバイナリのダウンロード |

> 実装補足: アップロード系（`POST /media`, `POST /firmware`）とバイナリ配信系（`GET /media/{id}`, `GET /firmware/{id}/download`）は `public/index.php` 内で、通常のJSON往復を行う `Router` を経由せず個別に処理されています（`multipart/form-data` の受信、および生バイナリのストリーム配信を行うため）。

---

## テレメトリ・ローバー系

### `POST /api/v1/telemetry`
ローバーからの定期送信を受け付けます。

**リクエストボディ**
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `device_uid` | string | ✓ | ローバー識別子 |
| `temperature_c` | number | △ | `rovers.enabled_sensors` に含まれる場合のみ必須 |
| `humidity_pct` | number | △ | 同上 |
| `gas_ppm` | number | △ | 同上 |
| `distance_cm` | number | △ | 同上 |
| `auto_brake` | boolean | ✓ | 自動ブレーキ作動フラグ |

- `recorded_at` はリクエストに含めません。**受信時刻（ゲートウェイ側）がサーバーで打刻されます。**
- 常に `201 Created` を返し、**同一内容の再送でも別レコードとして新規保存**されます（重複排除なし）。
- 許容範囲外の値は `validation_errors` テーブルに記録され、`OUT_OF_RANGE` 等のエラーになります。

### `GET /api/v1/rovers`
登録済みローバーの一覧を返します。各ローバーの `status` は `rovers.last_seen_at` から動的に算出（`ONLINE` / `DEGRADED` / `OFFLINE`）。しきい値は `config.js` の `ONLINE_THRESHOLD_SECONDS`（15秒）/ `DEGRADED_THRESHOLD_SECONDS`（60秒）に対応。

### `GET /api/v1/rovers/{device_uid}/latest`
最新1件のテレメトリと `age_seconds`（何秒前のデータか）を返します。未登録・未送信のローバーは `404`。

### `GET /api/v1/rovers/{device_uid}/readings`
| クエリ | 説明 |
|---|---|
| `limit` | 件数モード（既定）。`start`/`end` 未指定時、最新N件を返す |
| `start`, `end` | 範囲モード。両方指定時に有効 |
| `resolution` | `auto`（既定・期間長に応じ自動選択） / `raw`（生データ） / `minute` / `hour` / `day` |
| `gaps` | データが存在しない期間を結果に含めるか |

範囲モード時は、`raw_rows_in_range`（範囲内の生データ行数）、`query_time_ms`（クエリ所要時間）など、コスト情報も付与されます。

### `GET /api/v1/rovers/{device_uid}/summary`
| クエリ | 説明 |
|---|---|
| `granularity` | `minute` / `hour` / `day` |
| `start`, `end` | 集計対象期間 |

`telemetry_summaries` テーブルから事前計算済みのmin/avg/maxを返し、`obstacle_events`（`auto_brake` の立ち上がりエッジ回数＝障害物検知回数）も含みます。

### `GET /api/v1/rovers/{device_uid}/export`
`format=csv|json` と `start`/`end` を指定してエクスポート。非バッファPDO接続でストリーミングし、大量データでもメモリを圧迫しません。CSVは `Content-Disposition: attachment` 付き。

### `GET /api/v1/rovers/{device_uid}/events`
`telemetry_readings` から**都度算出される**（保存されない）イベント一覧。`since`, `limit` クエリ対応。

| イベント種別 | 意味 |
|---|---|
| `threshold_exceeded` | センサー値がしきい値を超過 |
| `auto_brake_engaged` | 自動ブレーキ作動開始 |
| `auto_brake_cleared` | 自動ブレーキ解除 |
| `reconnected` | 通信断からの復帰 |

---

## システム監視系

### `GET /api/v1/health`
`{status, database, api, uptime_seconds}` を返却。通常 `200`、DB接続不可時は `503`。

### `GET /api/v1/system`
Pi5のライブメトリクス（`cpu_load_percent`, `cpu_temperature_c`, メモリ/ディスク使用率、`ingest_rate_per_minute`、DBサイズ・行数）に加え、`services`（api / database / aggregate_job / retention_job の稼働状況。バッチ系は `storage/*.lastrun` マーカーファイルから判定）、しきい値超過時の `warnings` 配列を返します。

### `GET /api/v1/system/history`
`gateway_metrics` テーブル（`bin/aggregate.php` が毎分1行ずつ記録）から、`start`/`end` 指定でサーバーリソースの時系列を取得します。

### `GET /api/v1/validation-errors/summary?window=24h`
`validation_errors` を `error_code` 別に集計したカウントを返します。

### `GET /api/v1/validation-errors`
バリデーションエラーの一覧（`ValidationErrorController::list`）。

---

## 設定系

### `GET /api/v1/config/sensor-limits`
現在の許容範囲設定（`min`, `max`, `updated_at`）一覧を返します。

### `PUT /api/v1/config/sensor-limits/{field}`
ボディ `{min, max}`（`min < max` 必須）で更新。**以後の受信データにのみ適用され、過去データには遡及適用されません。**

---

## メディア（写真・動画）系

### `POST /api/v1/rovers/{device_uid}/media`
`multipart/form-data`、フィールド名 `file`。`201` でメタデータ（`id`, `media_type`, `file_path`, `captured_at`, `file_size_bytes`, `mime_type`）を返却。`media_type` はMIMEタイプから自動判定、SHA-256ハッシュはサーバー側で計算。

### `GET /api/v1/rovers/{device_uid}/media`
一覧（新しい順）。ゲートウェイのファイルシステム詳細である `file_path` は含みません。

### `GET /api/v1/rovers/{device_uid}/media/{id}`
`Content-Type`/`Content-Length` 付きでバイナリをストリーム配信。

### `DELETE /api/v1/rovers/{device_uid}/media/{id}`
`204`。DBレコードと実ファイルを同時に削除。

---

## ファームウェア系（ローバー全体で共通、ローバー個別ではない）

### `POST /api/v1/firmware`
`multipart/form-data`、`version`（必須・重複不可）、`file`、`release_notes`（任意）。`201` でメタデータ返却、SHA-256ハッシュをサーバー側で計算。`version` 未指定は `422`、重複は `409`。

### `GET /api/v1/firmware`
アップロード済み全ファームウェアの一覧（新しい順）。`file_path` は含みません。

### `GET /api/v1/firmware/latest`
最新版のメタデータ。未アップロード時は `404`。

### `GET /api/v1/firmware/{id}/download`
`Content-Type`/`Content-Length`/`Content-Disposition: attachment` 付きでバイナリ配信。

---

## エラーレスポンス形式（全エンドポイント共通）

```json
{
  "error": {
    "code": "OUT_OF_RANGE",
    "message": "...",
    "request_id": "..."
  }
}
```

| エラーコード | 意味 |
|---|---|
| `MISSING_FIELD` | 必須フィールド欠落 |
| `OUT_OF_RANGE` | 値がセンサー許容範囲外 |
| `MALFORMED_PAYLOAD` | JSONとして不正なボディ |
| `INVALID_PARAMETER` | クエリパラメータが不正 |
| `NOT_FOUND` | リソースが存在しない |
| `ALREADY_EXISTS` | 一意制約違反（例: ファームウェアバージョン重複） |
| `SERVICE_UNAVAILABLE` | DB接続不可など |
| `INTERNAL_ERROR` | 想定外のサーバーエラー |

## スコープ外の機能（本APIには含まれない）

- ローバーの遠隔操作（テレオペレーション）そのもの。フロントエンドのCOCKPITタブは、このREST APIではなく `robot-desktop-app` 側のWebSocketリレーに直接接続します。
- ダッシュボードUIの実装詳細（設計書§11は参考デザインとして提示されているのみ）。
