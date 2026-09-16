# Rover Telemetry API

Everything about the `rover-telemetry-backend` REST API in one place: endpoints, request/response formats, error codes, and deployment/implementation notes.

- **Base path**: `/api/v1` (the frontend reaches it via `APP_CONFIG.API_BASE_URL` in `rover-telemetry-frontend/public/js/config.js`)
- **Body format**: JSON, UTF-8. Only photo/video/firmware uploads use `multipart/form-data`.
- **Authentication**: none. This is a training project and authentication was never implemented — reconsider before any production use.
- **Source of truth**: `public/index.php` (routing) and `src/Controllers/*` (one class per endpoint). Field-level design rationale is in `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md`, section "6. API Contract".
- **Related docs**: [`database.md`](./database.md) (schema), [`README.md`](./README.md) (system overview), [`raspi-mysql-setup.md`](./raspi-mysql-setup.md) (deployment setup).

## Endpoint Index

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/telemetry` | Ingest telemetry data (rover → server) |
| GET | `/api/v1/rovers` | List rovers, with status |
| GET | `/api/v1/rovers/{device_uid}/latest` | Latest reading for a rover |
| GET | `/api/v1/rovers/{device_uid}/readings` | Raw or aggregated readings, by count or time range |
| GET | `/api/v1/rovers/{device_uid}/summary` | Minute/hour/day aggregate statistics |
| GET | `/api/v1/rovers/{device_uid}/export` | Export readings as CSV or JSON |
| GET | `/api/v1/rovers/{device_uid}/events` | Derived events (threshold breaches, auto-brake, reconnects) |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/system` | Current server/DB resource snapshot |
| GET | `/api/v1/system/history` | Time series of server resource usage |
| GET | `/api/v1/validation-errors/summary` | Validation-error counts by code |
| GET | `/api/v1/validation-errors` | List of validation errors |
| GET | `/api/v1/config/sensor-limits` | Get sensor validation ranges |
| PUT | `/api/v1/config/sensor-limits/{field}` | Update a sensor's validation range |
| POST | `/api/v1/rovers/{device_uid}/media` | Upload a photo/video |
| GET | `/api/v1/rovers/{device_uid}/media` | List a rover's photos/videos |
| GET | `/api/v1/rovers/{device_uid}/media/{id}` | Stream a photo/video binary |
| DELETE | `/api/v1/rovers/{device_uid}/media/{id}` | Delete a photo/video |
| POST | `/api/v1/firmware` | Upload a firmware release |
| GET | `/api/v1/firmware` | List firmware releases |
| GET | `/api/v1/firmware/latest` | Latest firmware release metadata |
| GET | `/api/v1/firmware/{id}/download` | Download a firmware binary |

> **Implementation note**: uploads (`POST /media`, `POST /firmware`) and binary-serving endpoints (`GET /media/{id}`, `GET /firmware/{id}/download`) are handled directly inside `public/index.php`, bypassing the normal JSON `Router`, because they need `multipart/form-data` parsing or raw binary streaming instead of a JSON response body.

---

## Telemetry & Rovers

### `POST /api/v1/telemetry`

Accepts a periodic transmission from a rover.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `device_uid` | string | ✓ | Rover identifier. Auto-registers a new `rovers` row on first use. |
| `temperature_c` | number | conditional | Required only if listed in the rover's `enabled_sensors` |
| `humidity_pct` | number | conditional | Same |
| `gas_ppm` | number | conditional | Same |
| `distance_cm` | number | conditional | Same |
| `auto_brake` | boolean | ✓ | Auto-brake engaged flag |

`recorded_at` is **not** part of the request — the ESP32 build has no RTC, so the server stamps the receipt time itself (UTC).

**Response `201 Created`**

```json
{
  "success": true,
  "device_uid": "rover-001",
  "recorded_at": "2026-09-15T08:12:03.451Z"
}
```

- Always `201`; there is **no dedup on retry** — an identical resend is stored as a distinct new row with a new `recorded_at`.
- A value outside its configured range (see `sensor_limits`) is rejected with `422 OUT_OF_RANGE` and logged to `validation_errors`; a missing required field is rejected with `422 MISSING_FIELD`; a non-JSON body is rejected with `400 MALFORMED_PAYLOAD`.

### `GET /api/v1/rovers`

Lists every registered rover.

**Response `200`**

```json
[
  {
    "device_uid": "rover-001",
    "name": null,
    "firmware_version": "1.1.1",
    "last_reading_at": "2026-09-15T08:12:03.451Z",
    "status": "ONLINE"
  }
]
```

`status` is computed live from `rovers.last_seen_at`: `ONLINE` if within `ONLINE_THRESHOLD_SECONDS` (default 15s), `DEGRADED` if within `DEGRADED_THRESHOLD_SECONDS` (default 60s), otherwise `OFFLINE` (or if the rover has never reported).

### `GET /api/v1/rovers/{device_uid}/latest`

**Response `200`**

```json
{
  "device_uid": "rover-001",
  "recorded_at": "2026-09-15T08:12:03.451Z",
  "age_seconds": 4.2,
  "temperature_c": 24.6,
  "humidity_pct": 51.2,
  "gas_ppm": 410.0,
  "distance_cm": 87.5,
  "auto_brake": false
}
```

Sensor fields are `null` (not omitted) when that sensor isn't enabled for the rover. `404 NOT_FOUND` if `device_uid` is unregistered, or if it exists but has never sent a reading.

### `GET /api/v1/rovers/{device_uid}/readings`

Two modes, selected by which query parameters are present.

| Query | Description |
|---|---|
| `limit` | Count mode (default when `start`/`end` are absent). Most recent N rows. 1–5000, default 100. |
| `order` | Count mode only: `asc` or `desc` (default `desc`). |
| `start`, `end` | Range mode. Both required to activate it. ISO-8601 timestamps. |
| `resolution` | Range mode only: `auto` (default), `raw`, `minute`, `hour`, or `day`. |
| `gaps` | Periods with no data are always returned in range mode; see below. |

**Count mode response `200`**

```json
{
  "device_uid": "rover-001",
  "count": 2,
  "readings": [
    {
      "recorded_at": "2026-09-15T08:12:03.451Z",
      "temperature_c": 24.6,
      "humidity_pct": 51.2,
      "gas_ppm": 410.0,
      "distance_cm": 87.5,
      "auto_brake": false
    }
  ]
}
```

**Range mode response `200`** — resolution auto-selects `raw` if the range contains ≤5000 raw rows, otherwise `minute`; requesting `raw` explicitly over a range that would exceed 5000 rows returns `400 INVALID_PARAMETER`.

```json
{
  "device_uid": "rover-001",
  "resolution": "minute",
  "count": 120,
  "buckets_populated": 118,
  "gaps": [
    { "start": "...", "end": "...", "duration_seconds": 120, "missing_readings": 2 }
  ],
  "query": { "raw_rows_in_range": 14032, "query_time_ms": 6 },
  "readings": [
    {
      "recorded_at": "2026-09-15T08:00:00Z",
      "temperature_c": { "min": 24.1, "avg": 24.5, "max": 24.9 },
      "humidity_pct": { "min": 50.0, "avg": 51.0, "max": 52.1 },
      "gas_ppm": { "min": 400.0, "avg": 410.0, "max": 420.0 },
      "distance_cm": { "min": 80.0, "avg": 87.5, "max": 95.0 }
    }
  ]
}
```

At `resolution=raw`, each `readings` entry has the flat count-mode shape (single values, plus `auto_brake`) instead of `min/avg/max` objects. `gaps` in raw mode are detected wherever the interval between consecutive readings exceeds 2× `EXPECTED_INTERVAL_SECONDS`; in bucketed mode, any bucket with no aggregated row is a gap.

### `GET /api/v1/rovers/{device_uid}/summary?granularity=minute|hour|day&start=&end=`

`start` and `end` are required; `granularity` defaults to `day`.

**Response `200`**

```json
{
  "device_uid": "rover-001",
  "granularity": "hour",
  "buckets": [
    {
      "bucket_start": "2026-09-15T08:00:00Z",
      "sample_count": 3600,
      "temperature_c": { "min": 24.1, "avg": 24.5, "max": 24.9 },
      "humidity_pct": { "min": 50.0, "avg": 51.0, "max": 52.1 },
      "gas_ppm": { "min": 400.0, "avg": 410.0, "max": 420.0 },
      "distance_cm": { "min": 80.0, "avg": 87.5, "max": 95.0 },
      "obstacle_events": 2
    }
  ]
}
```

Served from the precomputed `telemetry_summaries` table (populated every minute by `bin/aggregate.php`), not computed from raw data on each request. `obstacle_events` counts `auto_brake` rising edges (0→1 transitions) within the bucket.

### `GET /api/v1/rovers/{device_uid}/export?format=csv|json&start=&end=`

Streams the full range via an **unbuffered** PDO connection, so memory stays flat regardless of range size. `format` defaults to `csv`.

- **CSV**: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="{device_uid}-export.csv"`. Header row: `device_uid,recorded_at,temperature_c,humidity_pct,gas_ppm,distance_cm,auto_brake`.
- **JSON**: `Content-Type: application/json`, a streamed JSON array of the same objects `GET /readings` returns in count mode.

### `GET /api/v1/rovers/{device_uid}/events?since=&limit=`

Events are **derived on the fly** from `telemetry_readings` — nothing is stored. `since` defaults to 24 hours ago; `limit` defaults to 100 (most recent first).

| Event `type` | Meaning | Extra fields |
|---|---|---|
| `threshold_exceeded` | A sensor value was outside `sensor_limits` | `sensor`, `value`, `limit` |
| `auto_brake_engaged` | `auto_brake` transitioned 0→1 | `value` (distance_cm at the time, if available) |
| `auto_brake_cleared` | `auto_brake` transitioned 1→0 | — |
| `reconnected` | Gap between consecutive readings exceeded 2× the expected interval | `gap_seconds` |

**Response `200`**

```json
{
  "events": [
    { "at": "2026-09-15T08:12:00Z", "type": "auto_brake_engaged", "value": 12.4 },
    { "at": "2026-09-15T08:11:00Z", "type": "threshold_exceeded", "sensor": "gas_ppm", "value": 10500.0, "limit": 10000.0 }
  ]
}
```

---

## System Monitoring

### `GET /api/v1/health`

**Response** `200` normally, `503` if the database is unreachable.

```json
{ "status": "ok", "database": "ok", "api": "ok", "uptime_seconds": 431200 }
```

### `GET /api/v1/system`

**Response `200`**

```json
{
  "cpu_load_percent": 12.4,
  "cpu_temperature_c": 52.1,
  "memory": { "used_percent": 41.0 },
  "disk": { "used_percent": 63.2 },
  "ingest_rate_per_minute": 60,
  "database": { "size_mb": 812.4, "row_count": 4213000 },
  "services": {
    "api": "ok",
    "database": "ok",
    "aggregate_job": { "status": "ok", "last_run": "2026-09-15T08:12:00Z" },
    "retention_job": { "status": "ok", "last_run": "2026-09-15T03:00:01Z" }
  },
  "warnings": []
}
```

- `aggregate_job` / `retention_job` status is read from marker files (`storage/aggregate.lastrun`, `storage/retention.lastrun`) written by the corresponding cron scripts — `never_run` if the marker file doesn't exist yet.
- `warnings` lists any metric currently past its configured threshold (`CPU_TEMP_WARNING_C`, `DISK_USED_WARNING_PERCENT`, `MEMORY_USED_WARNING_PERCENT`), e.g. `{"metric": "cpu_temperature_c", "value": 84.0, "limit": 80}`.

### `GET /api/v1/system/history?start=&end=`

**Response `200`**

```json
{
  "resolution": "raw",
  "count": 60,
  "points": [
    {
      "sampled_at": "2026-09-15T08:00:00Z",
      "cpu_load_percent": 11.2,
      "cpu_temperature_c": 51.0,
      "memory_used_percent": 40.5,
      "disk_used_percent": 63.1,
      "ingest_rate_per_min": 60,
      "database_size_mb": 812.1
    }
  ]
}
```

One row per minute, sourced from `gateway_metrics` (written by `bin/aggregate.php`). `start`/`end` are required.

### `GET /api/v1/validation-errors/summary?window=24h`

`window` matches `\d+[hd]` (e.g. `24h`, `7d`).

**Response `200`**

```json
{ "window": "24h", "total": 14, "by_code": { "OUT_OF_RANGE": 11, "MISSING_FIELD": 3 } }
```

### `GET /api/v1/validation-errors?window=24h&error_code=&limit=`

`limit` is 1–200, default 50.

**Response `200`**

```json
{
  "window": "24h",
  "count": 1,
  "errors": [
    {
      "id": 42,
      "device_uid": "rover-001",
      "received_at": "2026-09-15T08:09:00Z",
      "error_code": "OUT_OF_RANGE",
      "detail": "gas_ppm 10500 exceeds max 10000",
      "raw_payload": "{...}"
    }
  ]
}
```

---

## Configuration

### `GET /api/v1/config/sensor-limits`

**Response `200`**

```json
{
  "temperature_c": { "min": -40, "max": 85, "updated_at": "2026-08-24T00:00:00Z" },
  "humidity_pct":   { "min": 0,   "max": 100, "updated_at": "2026-08-24T00:00:00Z" },
  "gas_ppm":        { "min": 0,   "max": 10000, "updated_at": "2026-08-24T00:00:00Z" },
  "distance_cm":    { "min": 2,   "max": 400, "updated_at": "2026-08-24T00:00:00Z" }
}
```

### `PUT /api/v1/config/sensor-limits/{field}`

**Request body**: `{"min": <number>, "max": <number>}`, `min < max` required.

**Response `200`**

```json
{ "field": "gas_ppm", "min": 0, "max": 12000, "updated_at": "2026-09-15T08:20:00Z" }
```

`404 NOT_FOUND` for an unknown `field`. **Applies only to data received after the update — never retroactive** to existing `telemetry_readings`.

---

## Media (Photos & Videos)

### `POST /api/v1/rovers/{device_uid}/media`

`multipart/form-data`, field name `file`. Auto-registers the rover if `device_uid` is new. `media_type` (`photo`/`video`) is inferred from the MIME type; a SHA-256 hash is computed server-side.

**Response `201`**

```json
{
  "id": 501,
  "device_uid": "rover-001",
  "media_type": "photo",
  "file_path": "rover-001/2026/09/15/143201-snapshot.jpg",
  "captured_at": "2026-09-15T14:32:01.000Z",
  "file_size_bytes": 184320,
  "mime_type": "image/jpeg"
}
```

### `GET /api/v1/rovers/{device_uid}/media?media_type=photo|video&start=&end=&limit=`

`limit` is 1–500, default 100.

**Response `200`**

```json
{
  "device_uid": "rover-001",
  "count": 1,
  "media": [
    { "id": 501, "media_type": "photo", "captured_at": "2026-09-15T14:32:01.000Z", "file_size_bytes": 184320, "mime_type": "image/jpeg" }
  ]
}
```

`file_path` is intentionally omitted (a gateway filesystem detail).

### `GET /api/v1/rovers/{device_uid}/media/{id}`

Streams the binary with `Content-Type` and `Accept-Ranges: bytes`, and honors `Range` requests (`206 Partial Content` / `416 Range Not Satisfiable`) — required for `<video>` playback and seeking, since a recording's `moov` atom often sits at the end of the file rather than the front. `404 NOT_FOUND` if the DB record or the underlying file is missing.

### `DELETE /api/v1/rovers/{device_uid}/media/{id}`

**Response `204`**, no body. Deletes the DB row and the stored file together.

---

## Firmware (fleet-wide — not per-rover)

### `POST /api/v1/firmware`

`multipart/form-data`. Fields: `version` (required, must be unique), `file` (required), `release_notes` (optional).

**Response `201`**

```json
{
  "id": 7,
  "version": "1.2.0",
  "file_size_bytes": 933184,
  "mime_type": "application/octet-stream",
  "file_hash": "a1b2c3...",
  "release_notes": "Fixes obstacle-brake threshold.",
  "created_at": "2026-09-15T09:00:00Z"
}
```

`422 MISSING_FIELD` if `version` is missing; `409 ALREADY_EXISTS` if it's a duplicate.

### `GET /api/v1/firmware`

**Response `200`**

```json
{ "count": 1, "firmware": [ { "id": 7, "version": "1.2.0", "file_size_bytes": 933184, "mime_type": "application/octet-stream", "file_hash": "a1b2c3...", "release_notes": "...", "created_at": "2026-09-15T09:00:00Z" } ] }
```

`file_path` is omitted, same rationale as media.

### `GET /api/v1/firmware/latest`

Same object shape as one entry of `GET /firmware`, for the most recently uploaded release. `404 NOT_FOUND` if nothing has been uploaded yet.

### `GET /api/v1/firmware/{id}/download`

Streams the binary with `Content-Type`, `Content-Length`, and `Content-Disposition: attachment`.

---

## Error Response Shape (all endpoints)

```json
{
  "error": {
    "code": "OUT_OF_RANGE",
    "message": "...",
    "request_id": "..."
  }
}
```

| Code | HTTP status | Meaning |
|---|---|---|
| `MISSING_FIELD` | 422 | Required field missing |
| `OUT_OF_RANGE` | 422 | Value outside the sensor's allowed range |
| `MALFORMED_PAYLOAD` | 400 | Body is not valid JSON, or an upload is missing its file |
| `INVALID_PARAMETER` | 400 | Invalid/inconsistent query parameter |
| `NOT_FOUND` | 404 | Resource does not exist |
| `ALREADY_EXISTS` | 409 | Unique-constraint violation (e.g. duplicate firmware version) |
| `SERVICE_UNAVAILABLE` | 503 | Database unreachable |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

`request_id` is a fresh random hex string generated per request (`public/index.php`), useful for correlating a client-reported error with server logs.

## Out of Scope (explicitly not part of this API)

- Rover teleoperation itself. The frontend's COCKPIT tab connects directly to the `robot-desktop-app` WebSocket relay, never through this REST API.
- Dashboard UI implementation details (design spec §11 is a reference design only, not a contract this API implements).

## Controller Layout

Each endpoint is implemented as its own single-purpose controller class under `src/Controllers/` (e.g. `RoverListController`, `RoverLatestController`, `RoverReadingsController`, `MediaUploadController`, `SensorLimitsGetController`/`SensorLimitsPutController`) — a structural choice made partway through implementation, favoring one file per endpoint over grouping several endpoints into a shared controller. Shared response formatting lives in `RoverTelemetry\Support\ReadingFormatter`. Firmware controllers (`FirmwareUploadController`, `FirmwareListController`, `FirmwareLatestController`, `FirmwareServeController`, backed by `FirmwareRepository`) mirror the same upload/list/latest/serve pattern used for media.

## Deployment Notes

- On the Pi 5 target: run behind php-fpm with a warm process pool and persistent PDO connections — this is what the ~30 ms `GET /latest` response-time budget assumes (spec §8.2), not raw query cost.
- `MEDIA_STORAGE_PATH` → `/var/rover-media`, `FIRMWARE_STORAGE_PATH` → `/var/rover-firmware` in production (dev uses the project-relative `storage/media` / `storage/firmware`).
- Schedule `bin/aggregate.php` every minute and `bin/retention.php` nightly via cron — see [`raspi-mysql-setup.md`](./raspi-mysql-setup.md) §8.
