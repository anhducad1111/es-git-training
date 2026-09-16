# Rover Telemetry — Cloud System User Guide

**Subsystem:** Cloud (backend API + web dashboard)
**Owner:** Shodai
**Related deliverables:** Deployed & Operational Cloud System (CLD-001–CLD-007)

This guide covers two audiences:

1. **Operators** — how to use the web dashboard day to day.
2. **Administrators** — how to set up and run the cloud system itself (on a Raspberry Pi or any LAMP-style host).

For the full API and database reference, see:
- [`api.md`](./api.md) — API endpoints, usage, and response formats
- [`database.md`](./database.md) — database schema
- [`raspi-mysql-setup.md`](./raspi-mysql-setup.md) — Raspberry Pi + MariaDB setup steps

---

## 1. What the Cloud System Does

The cloud system is made of two parts:

| Component | Tech | Role |
|---|---|---|
| `rover-telemetry-backend` | Plain PHP + PDO/MySQL (MariaDB) | Receives telemetry from the rover, stores it, exposes a REST API |
| `rover-telemetry-frontend` | Plain HTML/CSS/JS (no build step), Chart.js | Web dashboard that reads the API and lets an operator monitor and browse rover data |

Data flow:

```
Rover  --HTTP POST /api/v1/telemetry-->  Backend (PHP)  --MySQL-->  Database
                                              ^
                                              | HTTP GET (fetch)
                                              |
                                     Web Dashboard (browser)
```

The **Cockpit (teleoperation)** tab is the one exception: it does not go through this backend API at all. It connects the browser directly, over WebSocket, to the same relay used by `robot-desktop-app`, so the drive/gimbal command path is shared with the desktop controller by design.

---

## 2. Administrator Guide — Setting Up the Cloud System

### 2.1 Requirements

- A host that can run PHP (built-in server, or php-fpm behind Apache/nginx). Raspberry Pi 5 is the reference deployment target.
- MariaDB (MySQL-compatible) — see the step-by-step Raspberry Pi install guide in [`raspi-mysql-setup.md`](./raspi-mysql-setup.md) if it isn't installed yet.
- Enough disk space for stored media/firmware files and telemetry history (see "Storage growth" in the design proposal, §8.3).

### 2.2 Quick setup checklist

1. **Install and start MariaDB** on the host (see `raspi-mysql-setup.md` §1.5 if starting from scratch).
2. **Create the database and app user**:
   ```sql
   CREATE DATABASE rover_telemetry CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
   CREATE USER 'rover_app'@'localhost' IDENTIFIED BY '<strong-password>';
   GRANT ALL PRIVILEGES ON rover_telemetry.* TO 'rover_app'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. **Load the schema**:
   ```bash
   mysql -u rover_app -p rover_telemetry < sql/schema.sql
   ```
4. **Configure the backend**: copy `env.example` to `.env` and fill in `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, plus storage paths (`MEDIA_STORAGE_PATH`, `FIRMWARE_STORAGE_PATH`) and thresholds.
5. **Create storage directories** and make sure the PHP process user (e.g. `www-data`) can write to them:
   ```bash
   sudo mkdir -p /var/rover-media /var/rover-firmware
   sudo chown -R www-data:www-data /var/rover-media /var/rover-firmware
   ```
6. **Serve `public/index.php`** through Apache/nginx + php-fpm (recommended for production — persistent PDO connections keep `GET /latest` inside its ~30 ms budget), or `php -S 0.0.0.0:8000 -t public` for quick local testing.
7. **Verify**: `curl http://<host>/api/v1/health` should return `{"status":"ok","database":"ok",...}`.
8. **Schedule the background jobs** (cron):
   ```
   * * * * * php /path/to/rover-telemetry-backend/bin/aggregate.php   # aggregation, every minute
   0 3 * * * php /path/to/rover-telemetry-backend/bin/retention.php   # data retention, nightly
   ```
9. **Point the dashboard at the API**: edit `rover-telemetry-frontend/public/js/config.js` → `API_BASE_URL` so it matches wherever the backend is actually served (e.g. `/api/v1` if same-origin, or a full URL if cross-origin).
10. **Serve the dashboard**: `rover-telemetry-frontend/public/` is static — any web server (or the same Apache instance) can host it directly, no build step required.

### 2.3 Registering a rover

A rover record (`rovers` table) is created automatically the first time it posts to `POST /api/v1/telemetry` with a new `device_uid` — no manual admin step is required. `enabled_sensors` defaults to all four sensors; adjust via direct SQL if a rover only has a subset installed.

### 2.4 Adjusting sensor validation ranges

Default ranges (`sensor_limits` table, seeded by `sql/schema.sql`):

| Sensor | Min | Max |
|---|---|---|
| `temperature_c` | -40 | 85 |
| `humidity_pct` | 0 | 100 |
| `gas_ppm` | 0 | 10000 |
| `distance_cm` | 2 | 400 |

These can be changed live from the **System** tab of the dashboard (see §3.5), or via `PUT /api/v1/config/sensor-limits/{field}`. Changes apply to future ingested readings only — they are not retroactive.

---

## 3. Operator Guide — Using the Web Dashboard

Open the dashboard in a browser. The header has 5 tabs plus a health indicator (top right) that reflects `GET /api/v1/health`.

```
[ROVER TELEMETRY]   LIVE | HISTORY | GALLERY | COCKPIT | SYSTEM        [health: ok]
```

The currently selected rover is shared across all tabs — pick it once (fleet list on the LIVE tab, or the dropdown on other tabs) and it stays selected as you switch tabs.

### 3.1 LIVE — Real-time monitoring

- Polls the selected rover's latest reading every second.
- Shows current temperature, humidity, gas level, and distance as cards, plus a live-updating chart.
- Warning bars highlight any sensor value approaching or past its configured limit.
- A recent-events panel lists threshold breaches, auto-brake engage/clear, and reconnect events.
- The fleet list shows every registered rover with a colored status dot:
  - **Online** — reported within the last 15 seconds
  - **Degraded** — reported within the last 60 seconds
  - **Offline** — no data for longer than that

### 3.2 HISTORY — Past data & analysis

- Choose a rover and a start/end time range, then run the query.
- The chart automatically adapts resolution to the range length (raw data for short windows, minute/hour/day aggregates for longer ones) so it stays responsive even over long histories.
- Multiple sensors can be shown at once; each gets its own axis since units differ (°C vs. % vs. ppm vs. cm).
- Any period with no data in the selected range is listed separately as a **gap**, instead of being silently drawn as a flat/zero line.
- A summary panel shows min/avg/max statistics and the obstacle-event count for the range.
- **Export**: download the selected range as CSV or JSON for offline analysis.

### 3.3 GALLERY — Photos & videos

- Shows thumbnails of media captured by the selected rover, most recent first.
- Click a thumbnail to open a full-size lightbox viewer; use the arrows (or arrow keys) to move to the next/previous item.
- Media can be deleted from the gallery; this removes both the database record and the stored file.

### 3.4 COCKPIT — Teleoperation

> This tab talks directly to the rover's WebSocket relay (the same one `robot-desktop-app` uses) — **not** through the cloud REST API. It requires that relay to be running and reachable from the browser.

- Enter the relay address once; it's remembered locally in the browser for next time.
- **Drive**: W / S / A / D (forward / back / left / right), Space = emergency stop.
- **Camera gimbal**: I / J / K / L pan/tilt in 5° steps, C = re-center.
- Two dial gauges show the current pan and tilt position.
- A live camera preview is shown when connected; horizontal/vertical flip of the *display* (not the physical camera) is available and works regardless of connection state.
- A read-only telemetry strip at the bottom shows the same sensor values as the LIVE tab (via the normal HTTP API), independent of the WebSocket connection.
- Connection status (disconnected / connecting / connected / error) is always visible.

### 3.5 SYSTEM — Server health & configuration

- Shows the host's live CPU load, CPU temperature, memory and disk usage, current ingest rate, and database size/row count. Values past their configured warning threshold are highlighted.
- Shows whether the API, database, and the two background jobs (`aggregate`, `retention`) are healthy, including when each background job last ran.
- Resource-usage history charts, plus a simple projection of database growth.
- **Sensor limit editor**: view and update the min/max validation range for each sensor field directly from the UI (calls `PUT /config/sensor-limits/{field}` under the hood).

---

## 4. Troubleshooting (Operator-facing)

| Symptom | Likely cause / what to check |
|---|---|
| Health badge shows an error | Backend unreachable, or database down — check the SYSTEM tab / `GET /api/v1/health` directly |
| A rover never shows "Online" | It hasn't posted to `POST /api/v1/telemetry` yet, or its clock/network is broken |
| HISTORY chart is empty for a range | Check the "gaps" list — the rover may not have been reporting during that window |
| Sensor value flagged as out-of-range | Either a real sensor fault, or the configured limit (SYSTEM tab) needs adjusting for that rover's hardware |
| COCKPIT won't connect | The WebSocket relay (`robot-desktop-app`) isn't running or isn't reachable from the browser — this is independent of the cloud API being up |
| Gallery item missing | It may have been deleted, or the upload (`POST /rovers/{uid}/media`) failed — check for a corresponding entry in validation/error logs |
