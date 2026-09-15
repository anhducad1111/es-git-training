# ラズパイでのMySQLデータベース構築手順（rover_telemetry）

対象: Raspberry Pi（Raspberry Pi OS）に、`rover-telemetry-backend` が使うデータベース `rover_telemetry` を新規構築する手順です。

前提: ラズパイにSSHでログインできること、`sudo` が使えること。

> **2026-09-15 追記**: `mysql --version` / `mariadb --version` がどちらも `command not found` の場合、
> MySQL/MariaDBが未インストールの状態です。手順1.5でインストールしてから先に進んでください。

---

## 1. SSHでラズパイへ接続

```bash
ssh <ユーザー名>@<ラズパイのIPアドレス>
```

## 1.5. MariaDBのインストール（未導入の場合）

Raspberry Pi OS（Debian系）の標準リポジトリには `mysql-server` ではなく **MariaDB**（MySQL互換）が入っています。特別な理由がなければMariaDBで問題ありません。

```bash
sudo apt update
sudo apt install -y mariadb-server mariadb-client
```

インストール後、自動起動を有効にして起動します。

```bash
sudo systemctl enable mariadb
sudo systemctl start mariadb
sudo systemctl status mariadb      # active (running) になっていればOK
```

初回セキュリティ設定（rootパスワード設定・匿名ユーザー削除・リモートroot禁止など）を行っておきます。対話式で質問されるので、基本的にはすべて `Y`（yes）で進めてOKです。

```bash
sudo mysql_secure_installation
```

> Raspberry Pi OS の MariaDB はデフォルトで `root` が `unix_socket` 認証（＝`sudo mysql` でパスワード無しログイン、`mysql -u root -p` は失敗する）になっていることがあります。以降の手順では `sudo mysql` を使う前提で進めます。

インストール確認:

```bash
mariadb --version
```

## 2. サービス状態の確認（インストール済みの場合の再確認）

```bash
mariadb --version
sudo systemctl status mariadb
```

停止していれば起動しておきます。

```bash
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

## 3. データベースと専用ユーザーを作成

rootで接続します（初回はパスワードが未設定の場合 `sudo mysql` を使うと入れることが多いです）。

```bash
sudo mysql -u root -p
```

MySQLプロンプト内で以下を実行し、データベースと、アプリ専用ユーザーを作成します（rootを直接アプリに使うのは避けます）。

```sql
CREATE DATABASE rover_telemetry
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

CREATE USER 'rover_app'@'localhost' IDENTIFIED BY '（強力なパスワードに置き換える）';
GRANT ALL PRIVILEGES ON rover_telemetry.* TO 'rover_app'@'localhost';
FLUSH PRIVILEGES;

EXIT;
```

> バックエンド（PHP）と同じラズパイ上で動かす前提のため `'rover_app'@'localhost'` としています。
> バックエンドを別ホストに置く場合は、そのホストのIPを許可するホスト部（例: `'rover_app'@'192.168.1.50'`）に変更してください。

## 4. スキーマ（テーブル定義）を投入

このリポジトリの `sql/schema.sql` にDDLがまとまっています（`rovers`, `telemetry_readings`, `telemetry_summaries`, `gateway_metrics`, `validation_errors`, `media_files`, `sensor_limits`, `firmware_releases` の8テーブル）。

`rover-telemetry-backend` をラズパイ上に配置済みであれば、そのディレクトリで実行します。

```bash
cd /path/to/rover-telemetry-backend
mysql -u rover_app -p rover_telemetry < sql/schema.sql
```

まだリポジトリ一式をラズパイに転送していない場合は、`sql/schema.sql` だけを先に転送しても構いません（開発機のWindowsから、例えば `scp` で）。

```bash
# 開発機（Windows/Git Bash）側で実行する例
scp "C:/xampp/htdocs/es-git-training/rover-telemetry-backend/sql/schema.sql" <ユーザー名>@<ラズパイのIP>:/tmp/schema.sql
```

```bash
# ラズパイ側で実行
mysql -u rover_app -p rover_telemetry < /tmp/schema.sql
```

## 5. テーブルが作成されたか確認

```bash
mysql -u rover_app -p rover_telemetry -e "SHOW TABLES;"
```

以下の8テーブルが表示されればOKです。

```
firmware_releases
gateway_metrics
media_files
rovers
sensor_limits
telemetry_readings
telemetry_summaries
validation_errors
```

`sensor_limits` には初期値（温度 -40〜85℃、湿度 0〜100%、ガス 0〜10000ppm、距離 2〜400cm）が自動投入されるので、念のため中身も確認しておくと安心です。

```bash
mysql -u rover_app -p rover_telemetry -e "SELECT * FROM sensor_limits;"
```

## 6. バックエンド（PHP）の接続設定（`.env`）

`rover-telemetry-backend/env.example` をコピーして `.env` を作成し、ラズパイのDB接続情報に書き換えます。

```bash
cp env.example .env
```

```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=rover_telemetry
DB_USER=rover_app
DB_PASSWORD=（手順3で設定したパスワード）

ONLINE_THRESHOLD_SECONDS=15
DEGRADED_THRESHOLD_SECONDS=60
RAW_RETENTION_DAYS=90
VALIDATION_ERROR_RETENTION_DAYS=30
GATEWAY_METRICS_RETENTION_DAYS=365
EXPECTED_INTERVAL_SECONDS=5
CPU_TEMP_WARNING_C=80
DISK_USED_WARNING_PERCENT=90
MEMORY_USED_WARNING_PERCENT=90

# 本番（ラズパイ）では project-relative ではなく専用パスを推奨
MEDIA_STORAGE_PATH=/var/rover-media
FIRMWARE_STORAGE_PATH=/var/rover-firmware
```

保存先ディレクトリを作成し、PHP実行ユーザー（php-fpmのプロセスユーザー、通常 `www-data`）が書き込めるようにしておきます。

```bash
sudo mkdir -p /var/rover-media /var/rover-firmware
sudo chown -R www-data:www-data /var/rover-media /var/rover-firmware
```

## 7. 動作確認

PHP組み込みサーバー、または php-fpm+nginx/Apache経由で `public/index.php` を起動し、ヘルスチェックを叩いて疎通を確認します。

```bash
curl http://localhost/api/v1/health
```

`{"status":"ok","database":"ok","api":"ok","uptime_seconds":...}` のようなレスポンスが返れば、DB接続まで含めて正常です。`database` が `"unreachable"` 等になる場合は `.env` のDB接続情報を再確認してください。

## 8. （任意）バッチ処理をcronに登録

`sql/schema.sql` で作った `telemetry_summaries` / `gateway_metrics` は、以下のバッチが埋めてくれます（`docs/api-contract.md` の「Deployment note」参照）。

```bash
crontab -e
```

```
* * * * * php /path/to/rover-telemetry-backend/bin/aggregate.php >> /var/log/rover-aggregate.log 2>&1
0 3 * * * php /path/to/rover-telemetry-backend/bin/retention.php >> /var/log/rover-retention.log 2>&1
```

---

## トラブルシューティング

| 症状 | 確認事項 |
|---|---|
| `mysql: command not found` | MariaDBの場合パッケージ名が異なることがある。`sudo apt install mariadb-client` |
| `Access denied for user` | 手順3のユーザー名/パスワード/ホスト部（`'rover_app'@'localhost'`）が `.env` と一致しているか確認 |
| `Unknown database 'rover_telemetry'` | 手順3のCREATE DATABASEが実行されているか確認（`SHOW DATABASES;`） |
| `.env` を変更しても反映されない | php-fpmを使っている場合 `sudo systemctl restart php*-fpm` が必要なことがある |
| 文字化け | `CHARACTER SET utf8mb4` でDB作成しているか確認（`SHOW CREATE DATABASE rover_telemetry;`） |
