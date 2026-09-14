# Rover Telemetry データベース設計（日本語版）

出典: `sql/schema.sql`（実装済みDDL）。より詳しい設計意図は `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md` の「5. Database Design」を参照してください。

エンジンは全テーブル `InnoDB`、文字コードは `utf8mb4`。

## ER概要

```
rovers 1 ──< telemetry_readings   （device_id で紐付け、複合PK: device_id + recorded_at）
rovers 1 ──< telemetry_summaries  （device_id + granularity + bucket_start が複合PK）
rovers 1 ──< media_files          （device_id で紐付け）
validation_errors                  （device_uid を保持するが外部キー制約なし＝未登録ローバーの不正データも記録できる）
gateway_metrics                    （ローバーに依存しない、ゲートウェイ本体のメトリクス）
sensor_limits                      （field名をPKとする設定テーブル、マスタデータ）
firmware_releases                  （ローバーに依存しない、フリート全体で共有）
```

---

## `rovers` — ローバー本体の登録情報

| カラム | 型 | 説明 |
|---|---|---|
| `id` | BIGINT UNSIGNED AUTO_INCREMENT PK | 内部ID |
| `device_uid` | VARCHAR(64) UNIQUE | ローバー識別子（APIのパスパラメータに使用） |
| `name` | VARCHAR(100) NULL | 表示名 |
| `firmware_version` | VARCHAR(30) NULL | 現在のファームウェアバージョン |
| `enabled_sensors` | SET(...) | 搭載センサー種別。既定は4種すべて有効 |
| `last_seen_at` | DATETIME(3) NULL | 最終受信時刻。`GET /rovers` の状態判定（ONLINE/DEGRADED/OFFLINE）に使用 |
| `created_at` | DATETIME | 登録日時 |

## `telemetry_readings` — 生のテレメトリデータ（最も頻繁に書き込まれるテーブル）

| カラム | 型 | 説明 |
|---|---|---|
| `device_id` | BIGINT UNSIGNED | `rovers.id` への外部キー（複合PKの一部） |
| `recorded_at` | DATETIME(3) | サーバー側で打刻された受信時刻（複合PKの一部） |
| `temperature_c` | FLOAT NULL | 温度 |
| `humidity_pct` | FLOAT NULL | 湿度 |
| `gas_ppm` | FLOAT NULL | ガス濃度 |
| `distance_cm` | FLOAT NULL | 距離センサー値 |
| `auto_brake` | TINYINT(1) | 自動ブレーキ作動フラグ |

- **PK**: `(device_id, recorded_at)` — ローバーごとの時系列データとして自然にクラスタ化される設計。
- **インデックス**: `ix_reading_brake (device_id, auto_brake, recorded_at)` — `auto_brake` の立ち上がりエッジ検出（障害物イベント抽出、`GET /events` や `summary` の `obstacle_events`）を高速化するため。
- 各センサー値が `NULL` を許容するのは、ローバーごとに `enabled_sensors` が異なり得るため（未搭載センサーの列はNULLのまま）。

## `telemetry_summaries` — 事前計算済みの統計サマリ（`bin/aggregate.php` が生成）

| カラム | 型 | 説明 |
|---|---|---|
| `device_id` | BIGINT UNSIGNED | `rovers.id` への外部キー |
| `granularity` | ENUM('minute','hour','day') | 集計粒度 |
| `bucket_start` | DATETIME | 集計バケットの開始時刻 |
| `sample_count` | INT UNSIGNED | バケット内のサンプル数 |
| `temp_min/avg/max`, `hum_min/avg/max`, `gas_min/avg/max`, `dist_min/avg/max` | FLOAT NULL | 各センサーの統計値 |
| `obstacle_events` | INT UNSIGNED | バケット内の障害物検知回数 |
| `computed_at` | DATETIME | 集計実行時刻 |

- **PK**: `(device_id, granularity, bucket_start)`。
- `GET /rovers/{uid}/summary` や `readings?resolution=minute|hour|day` の高速化のために、生データを毎分集計してこのテーブルへ書き込む（生データを都度集計するとレスポンスが遅くなるための事前計算）。

## `gateway_metrics` — ゲートウェイ（Pi5本体）のリソース推移

| カラム | 型 | 説明 |
|---|---|---|
| `sampled_at` | DATETIME PK | サンプリング時刻（1分1行） |
| `cpu_load_percent` | FLOAT | CPU使用率 |
| `cpu_temperature_c` | FLOAT | CPU温度 |
| `memory_used_percent` | FLOAT | メモリ使用率 |
| `disk_used_percent` | FLOAT | ディスク使用率 |
| `ingest_rate_per_min` | INT UNSIGNED | 直近1分間のテレメトリ受信件数 |
| `database_size_mb` | FLOAT | DBサイズ（MB） |

- ローバー個別ではなくゲートウェイ全体の値のため、`device_id` 列を持たない。
- `bin/aggregate.php` が毎分書き込み、`GET /api/v1/system/history` で参照される。SYSTEMタブのDBサイズ将来予測グラフの元データでもある。

## `validation_errors` — バリデーションで弾かれたデータの記録

| カラム | 型 | 説明 |
|---|---|---|
| `id` | BIGINT UNSIGNED AUTO_INCREMENT PK | |
| `device_uid` | VARCHAR(64) NULL | 送信元（未登録ローバーの可能性もあるため外部キー制約なし） |
| `received_at` | DATETIME(3) | 受信時刻 |
| `error_code` | VARCHAR(40) | 例: `OUT_OF_RANGE`, `MISSING_FIELD` |
| `detail` | VARCHAR(255) | エラー詳細メッセージ |
| `raw_payload` | TEXT NULL | 受信した生ペイロード（調査用） |

- インデックス `ix_validation_time (received_at)` は、`GET /validation-errors/summary?window=24h` のような期間集計を高速化するため。
- `device_id` ではなく `device_uid`（文字列）を保持し、外部キー制約を付けていない点に注意。**存在しないローバーからの不正な送信も記録できるようにする設計判断。**

## `media_files` — 写真・動画のメタデータ

| カラム | 型 | 説明 |
|---|---|---|
| `id` | BIGINT UNSIGNED AUTO_INCREMENT PK | |
| `device_id` | BIGINT UNSIGNED | `rovers.id` への外部キー |
| `media_type` | ENUM('photo','video') | MIMEタイプから自動判定 |
| `file_path` | VARCHAR(255) | 実ファイルの保存パス（APIレスポンスには含めない＝ゲートウェイのファイルシステム詳細を隠蔽） |
| `captured_at` | DATETIME(3) | 撮影/取得時刻 |
| `file_size_bytes` | INT UNSIGNED | ファイルサイズ |
| `mime_type` | VARCHAR(50) | MIMEタイプ |
| `original_filename` | VARCHAR(200) NULL | 元のファイル名 |
| `file_hash` | CHAR(64) NULL | SHA-256ハッシュ（サーバー側計算、改ざん検知・重複検出用） |

- インデックス `ix_media_device_time (device_id, captured_at)` はGALLERYタブの一覧取得（ローバー別・時系列順）を高速化。

## `sensor_limits` — センサー許容範囲のマスタ設定

| カラム | 型 | 説明 |
|---|---|---|
| `field` | VARCHAR(30) PK | センサー項目名（`temperature_c` など） |
| `min_value` | FLOAT | 下限 |
| `max_value` | FLOAT | 上限 |
| `updated_at` | DATETIME ON UPDATE CURRENT_TIMESTAMP | 最終更新時刻 |

初期値（`sql/schema.sql` の `INSERT ... ON DUPLICATE KEY UPDATE`）:

| field | min | max |
|---|---|---|
| `temperature_c` | -40 | 85 |
| `humidity_pct` | 0 | 100 |
| `gas_ppm` | 0 | 10000 |
| `distance_cm` | 2 | 400 |

- `PUT /config/sensor-limits/{field}` による更新は、**以後の受信データの検証にのみ影響し、既存の `telemetry_readings` には遡及しません。**

## `firmware_releases` — ファームウェア配布用メタデータ

| カラム | 型 | 説明 |
|---|---|---|
| `id` | BIGINT UNSIGNED AUTO_INCREMENT PK | |
| `version` | VARCHAR(30) UNIQUE | バージョン文字列（重複不可） |
| `file_path` | VARCHAR(255) | 実ファイル保存パス（APIレスポンスには含めない） |
| `file_size_bytes` | INT UNSIGNED | ファイルサイズ |
| `mime_type` | VARCHAR(50) | 既定 `application/octet-stream` |
| `file_hash` | CHAR(64) NULL | SHA-256ハッシュ |
| `release_notes` | TEXT NULL | リリースノート |
| `created_at` | DATETIME | アップロード日時 |

- ローバー個別ではなく**フリート全体で共有**されるテーブル（`device_id` を持たない）。`media_files` のアップロード/配信パターンを踏襲した設計。

---

## 設計上の補足事項

- **タイムスタンプの精度**: `telemetry_readings.recorded_at` や `rovers.last_seen_at`, `media_files.captured_at` はミリ秒精度（`DATETIME(3)`）。高頻度送信でも同時刻の衝突を避けるため。
- **保存容量とデータ保持（retention）**: `bin/retention.php` が夜間バッチで古い生データを間引く。運用上の容量見積もりは設計書「8.3 Storage growth on the Pi 5」「8.4 Retention」を参照。
- **保存先パスの規約**: メディア/ファームウェアの実ファイルは `MEDIA_STORAGE_PATH` / `FIRMWARE_STORAGE_PATH`（開発環境では `storage/media` / `storage/firmware`）配下に保存され、DBにはパスとメタデータのみを保持する設計（バイナリをDBに直接入れない）。
