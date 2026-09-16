# Rover Telemetry System Overview

This document summarizes the full "Rover Telemetry" system — made up of `rover-telemetry-backend` (a plain PHP REST API) and `rover-telemetry-frontend` (a plain HTML/CSS/JS dashboard) — from a functionality and usage perspective.

See also:

- Full API reference (endpoints, usage, responses) → [`api.md`](./api.md)
- Database design details → [`database.md`](./database.md)
- Original design spec (full database/API/implementation plan) → `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md`
- UI design notes → `rover-telemetry-frontend/docs/2026-09-08-rover-telemetry-dashboard-design.md`

## 1. Purpose of the System

The system aggregates telemetry sensor data (temperature, humidity, gas concentration, distance, etc.) sent periodically by a rover into MySQL running on a single Raspberry Pi 5, and exposes it through a web dashboard for real-time monitoring, historical analysis, a photo/video gallery, remote operation (teleoperation), and system health monitoring.

```
[Rover] --HTTP POST--> [rover-telemetry-backend (PHP API)] --MySQL--> [telemetry_readings, etc.]
                                     ^
                                     | HTTP GET (fetch)
                                     |
                          [rover-telemetry-frontend (browser SPA)]
```

- The backend is plain PHP with no framework (lightweight routing via `src/Router.php`).
- The frontend is build-free plain JS (fetch calls via `window.Api`), structured as a single-page app with 5 tabs.
- The one exception is rover teleoperation (the COCKPIT tab): it does not go through this backend API at all, and instead connects the browser directly to the rover over WebSocket (via the relay on the `robot-desktop-app` side).

## 2. Backend Structure (rover-telemetry-backend)

```
public/index.php       Routing definitions / entry point
src/Router.php          Simple regex-based router
src/Config.php           Loads configuration from .env
src/Database.php         PDO connections (buffered / unbuffered)
src/Controllers/         One class per endpoint (e.g. RoverListController)
src/Repositories/        DB access (queries) layer
src/Support/             Shared utilities (ApiException, ReadingFormatter, etc.)
src/Validation/          Request validation
sql/schema.sql           Database schema (DDL)
bin/aggregate.php        Runs every minute: aggregates telemetry_summaries / gateway_metrics
bin/retention.php        Runs nightly: thins out / deletes old data
bin/simulate_rover.php   Dev tool: sends dummy telemetry
bin/loadtest.php         Load-testing script
storage/media/           Uploaded photo/video files
storage/firmware/        Uploaded firmware files
tests/                   PHPUnit unit / integration tests
```

**Architecture highlights**

- No authentication (also noted in `api.md` as an unresolved open item) — a simple setup intended for a training project.
- All responses are JSON (`application/json; charset=UTF-8`). Photo/video/firmware binaries are streamed.
- `GET /rovers/{uid}/readings` can auto-select or explicitly choose raw data, minute/hour/day resolution via the `resolution` parameter, keeping charts responsive even with large datasets.
- `bin/aggregate.php` updates `telemetry_summaries` (statistical summaries) and `gateway_metrics` (system load history) every minute, powering fast dashboard rendering.
- `bin/retention.php` progressively thins old raw data (see `sql/schema.sql` / design spec §8.4 for the retention policy).

## 3. Frontend Structure (rover-telemetry-frontend)

```
public/index.html        Skeleton of the tab-based SPA (5 tabs)
public/js/config.js       Config values such as the API base URL and polling interval
public/js/api.js          window.Api: a thin wrapper for calling the backend API
public/js/roverselection.js  Small store sharing the currently selected rover ID across screens
public/js/app.js          Tab-switching control (mount/start/stop calls per tab)
public/js/live.js         LIVE tab (real-time monitoring)
public/js/history.js      HISTORY tab (historical search, charts, CSV/JSON export)
public/js/gallery.js      GALLERY tab (photo/video gallery)
public/js/control.js      COCKPIT tab (teleoperation / WebSocket)
public/js/system.js       SYSTEM tab (server health monitoring, threshold settings)
public/js/charts.js       Shared chart-rendering logic using Chart.js
public/js/rejectchips.js  Badges showing rejected/invalid validation data
public/js/timeutil.js     Shared date/time formatting utilities
public/css/style.css      All styles
```

The API base URL is configured via `APP_CONFIG.API_BASE_URL` in `public/js/config.js`. The default is:

```js
API_BASE_URL: '/es-git-training/rover-telemetry-backend/public/api/v1'
```

(This assumes the backend is placed under the XAMPP document root.)

## 4. Screen (Tab) Functionality and Usage

Five screens are switched via the tabs at the top of the header. Every screen shares a `health-badge` in the top-right corner (backend liveness via `GET /api/v1/health`). The selected rover (`RoverSelection`) is shared across tabs.

### 4.1 LIVE (Real-time monitoring)

- Polls every second (`POLL_INTERVAL_LIVE_MS`) and displays the selected rover's latest telemetry as cards.
- Shows recent temperature, humidity, gas concentration, and distance on a real-time line chart (`loadTelemetryChart`).
- Visualizes the number of obstacle-detection (`auto_brake`) events over time (`loadObstacleChart`).
- Displays a warning bar when a sensor value is near or past its configured threshold (`sensor_limits`) (`renderSensorLimitBars`).
- Lists recent events (threshold breaches, auto-brake on/off, reconnects, etc.) (`renderRecentEvents`).
- Shows the full fleet with color-coded online/degraded/offline status (`renderFleet`, `statusDotClass`).

### 4.2 HISTORY (Past data & analysis)

- Search past data by specifying a rover and a time range (start/end).
- `resolution=auto|raw|minute|hour|day` automatically switches the aggregation granularity of the chart based on the range length (`runQuery` → `Api.readings`).
- When multiple sensors are shown together, since their units differ (°C, %, ppm, cm), each is overlaid as a plain average line on its own axis (no min/max band rendering by design — see the comment inside `renderHistoryChart`).
- Lists periods with no data (gaps) (`renderGapsList`).
- Shows aggregate statistics as panels (the `/summary` endpoint: min/avg/max, obstacle-event count) (`loadSummaryPanels`).
- Export to CSV/JSON (`triggerExport` → `Api.exportUrl`, `GET /rovers/{uid}/export`).

### 4.3 GALLERY (Photo/video gallery)

- Shows thumbnails of photos/videos uploaded by the selected rover (`loadMediaGallery`).
- Click to open a lightbox view; navigate to adjacent items with arrow keys, etc. (`openLightbox`/`showAdjacent`).
- Supports deletion (`DELETE /rovers/{uid}/media/{id}`).

### 4.4 COCKPIT (Remote operation / teleoperation)

- **This is the only tab that bypasses the backend API entirely** and connects the browser directly to the robot-side relay (`robot-desktop-app`) over WebSocket (`ws://<address>/`) (see `connect()` in `control.js`).
- W/S/A/D keys drive the vehicle, I/J/K/L keys pan/tilt the camera (5° steps), C re-centers the gimbal, and Space triggers an emergency stop. Key bindings are kept consistent with the `robot-desktop-app` side.
- Current pan (N/S/W/E) and tilt (UP/DN/LVL) angles are shown on semicircular dial gauges (`gimbalDialSvg`, `setDialNeedle`).
- A live camera preview is shown, along with a display-only horizontal/vertical flip (`updateFlipTransform` — this is a rendering-side operation, not a relay command, so it works regardless of connection state).
- Connection state (disconnected/connecting/connected/error) is displayed (`renderConnectionState`).
- A simple, read-only telemetry strip at the bottom uses the existing `GET /rovers/{uid}/latest` API (independent of the WebSocket relay, `pollTelemetry`).
- Connection settings (address, etc.) are saved to `localStorage` and reused next time (this is designed so that private browsing, etc., where storage is unavailable, does not affect the connection itself).

### 4.5 SYSTEM (Server/system health monitoring)

- Shows the Pi 5's CPU load, CPU temperature, memory/disk usage, database size/row count, recent ingest rate, and more (`GET /api/v1/system`).
- Items past a configured threshold are highlighted in a warning color (`cardClass`).
- Shows service status such as the last run time of background jobs like `aggregate_job` / `retention_job` (`renderServices`).
- Historical resource-usage charts (`GET /api/v1/system/history`, `loadResourceCharts`) and a simple linear projection of database growth (`projectGrowth`).
- Sensor validation ranges (`sensor_limits`) can be edited from the GUI (`loadSensorLimitEditor`/`wireSensorLimitEditor` → `PUT /config/sensor-limits/{field}`).

## 5. Development/Operations Notes

- `bin/simulate_rover.php` can be used during development to send dummy data.
- Tests use PHPUnit (`tests/Unit`, `tests/Integration`); scripts are expected to be defined in `composer.json`.
- Production deployment (Raspberry Pi 5) assumes php-fpm with persistent PDO connections; `GET /latest` targets a 30 ms response-time budget (see "Deployment Notes" in `api.md`).
- Media/firmware storage locations can be switched via environment variables (`MEDIA_STORAGE_PATH` / `FIRMWARE_STORAGE_PATH`). The dev environment uses `storage/media` / `storage/firmware` under the project root.
