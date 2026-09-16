# Setting Up the MySQL Database on a Raspberry Pi (rover_telemetry)

Target: steps to set up the `rover_telemetry` database used by `rover-telemetry-backend` on a Raspberry Pi (Raspberry Pi OS).

Prerequisites: you can SSH into the Raspberry Pi and use `sudo`.

> **2026-09-15 note**: if both `mysql --version` and `mariadb --version` return `command not found`,
> MySQL/MariaDB is not yet installed. Install it first using step 1.5 below.

---

## 1. SSH into the Raspberry Pi

```bash
ssh <username>@<raspberry-pi-ip-address>
```

## 1.5. Installing MariaDB (if not already installed)

Raspberry Pi OS (Debian-based)'s default repository ships **MariaDB** (MySQL-compatible), not `mysql-server`. Unless you have a specific reason not to, MariaDB works fine.

```bash
sudo apt update
sudo apt install -y mariadb-server mariadb-client
```

After installation, enable it to start on boot and start it.

```bash
sudo systemctl enable mariadb
sudo systemctl start mariadb
sudo systemctl status mariadb      # OK if it shows "active (running)"
```

Run the initial security setup (set the root password, remove anonymous users, disable remote root, etc.). It's interactive — answering `Y` (yes) to everything is fine for this setup.

```bash
sudo mysql_secure_installation
```

> On Raspberry Pi OS, MariaDB's `root` account is often set up with `unix_socket` authentication by default (i.e. `sudo mysql` logs in without a password, while `mysql -u root -p` fails). The steps below assume you're using `sudo mysql`.

Verify the install:

```bash
mariadb --version
```

## 2. Checking Service Status (if already installed)

```bash
mariadb --version
sudo systemctl status mariadb
```

Start it if it's stopped.

```bash
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

## 3. Create the Database and a Dedicated User

Connect as root (if the password hasn't been set yet, `sudo mysql` usually gets you in).

```bash
sudo mysql -u root -p
```

Inside the MySQL prompt, run the following to create the database and a dedicated application user (avoid using root directly from the application):

```sql
CREATE DATABASE rover_telemetry
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

CREATE USER 'rover_app'@'localhost' IDENTIFIED BY '<replace-with-a-strong-password>';
GRANT ALL PRIVILEGES ON rover_telemetry.* TO 'rover_app'@'localhost';
FLUSH PRIVILEGES;

EXIT;
```

> `'rover_app'@'localhost'` assumes the backend (PHP) runs on the same Raspberry Pi.
> If the backend runs on a different host, change the host part to that host's IP (e.g. `'rover_app'@'192.168.1.50'`).

## 4. Load the Schema (Table Definitions)

The DDL is in this repository's `sql/schema.sql` (8 tables: `rovers`, `telemetry_readings`, `telemetry_summaries`, `gateway_metrics`, `validation_errors`, `media_files`, `sensor_limits`, `firmware_releases`).

If `rover-telemetry-backend` is already deployed on the Raspberry Pi, run this from that directory:

```bash
cd /path/to/rover-telemetry-backend
mysql -u rover_app -p rover_telemetry < sql/schema.sql
```

If you haven't transferred the full repository to the Raspberry Pi yet, you can transfer just `sql/schema.sql` first (e.g. via `scp` from your Windows dev machine):

```bash
# Run this on the dev machine (Windows/Git Bash)
scp "C:/xampp/htdocs/es-git-training/rover-telemetry-backend/sql/schema.sql" <username>@<raspberry-pi-ip>:/tmp/schema.sql
```

```bash
# Run this on the Raspberry Pi
mysql -u rover_app -p rover_telemetry < /tmp/schema.sql
```

## 5. Verify the Tables Were Created

```bash
mysql -u rover_app -p rover_telemetry -e "SHOW TABLES;"
```

You should see these 8 tables:

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

`sensor_limits` is automatically seeded with default values (temperature -40 to 85°C, humidity 0-100%, gas 0-10000 ppm, distance 2-400 cm) — it's worth checking the contents too.

```bash
mysql -u rover_app -p rover_telemetry -e "SELECT * FROM sensor_limits;"
```

## 6. Configure the Backend's Connection (`.env`)

Copy `rover-telemetry-backend/env.example` to `.env` and fill in the Raspberry Pi's DB connection details.

```bash
cp env.example .env
```

```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=rover_telemetry
DB_USER=rover_app
DB_PASSWORD=(the password set in step 3)

ONLINE_THRESHOLD_SECONDS=15
DEGRADED_THRESHOLD_SECONDS=60
RAW_RETENTION_DAYS=90
VALIDATION_ERROR_RETENTION_DAYS=30
GATEWAY_METRICS_RETENTION_DAYS=365
EXPECTED_INTERVAL_SECONDS=5
CPU_TEMP_WARNING_C=80
DISK_USED_WARNING_PERCENT=90
MEMORY_USED_WARNING_PERCENT=90

# On the Raspberry Pi in production, dedicated paths are recommended over project-relative ones
MEDIA_STORAGE_PATH=/var/rover-media
FIRMWARE_STORAGE_PATH=/var/rover-firmware
```

Create the storage directories and make sure the PHP process user (typically `www-data` for php-fpm) can write to them.

```bash
sudo mkdir -p /var/rover-media /var/rover-firmware
sudo chown -R www-data:www-data /var/rover-media /var/rover-firmware
```

## 7. Verify It Works

Start `public/index.php` via the PHP built-in server, or php-fpm + nginx/Apache, and hit the health check to confirm connectivity.

```bash
curl http://localhost/api/v1/health
```

If you get a response like `{"status":"ok","database":"ok","api":"ok","uptime_seconds":...}`, everything is working, including the DB connection. If `database` shows `"unreachable"` or similar, double-check the DB connection details in `.env`.

## 8. (Optional) Register Batch Jobs with cron

`telemetry_summaries` / `gateway_metrics`, created by `sql/schema.sql`, are populated by the following batch jobs (see "Deployment Notes" in `docs/api.md`).

```bash
crontab -e
```

```
* * * * * php /path/to/rover-telemetry-backend/bin/aggregate.php >> /var/log/rover-aggregate.log 2>&1
0 3 * * * php /path/to/rover-telemetry-backend/bin/retention.php >> /var/log/rover-retention.log 2>&1
```

---

## Troubleshooting

| Symptom | What to check |
|---|---|
| `mysql: command not found` | The package name may differ for MariaDB — try `sudo apt install mariadb-client` |
| `Access denied for user` | Confirm that the username/password/host part (`'rover_app'@'localhost'`) from step 3 matches `.env` |
| `Unknown database 'rover_telemetry'` | Confirm the `CREATE DATABASE` from step 3 actually ran (`SHOW DATABASES;`) |
| Changes to `.env` aren't taking effect | If using php-fpm, you may need `sudo systemctl restart php*-fpm` |
| Garbled characters (mojibake) | Confirm the database was created with `CHARACTER SET utf8mb4` (`SHOW CREATE DATABASE rover_telemetry;`) |
