# Rover Telemetry Backend — API Contract (as implemented)

Base path: `/api/v1`. All bodies are JSON UTF-8 unless noted. No authentication (spec §11.6, `[To confirm]`).

## POST /telemetry
Body: `{device_uid, temperature_c?, humidity_pct?, gas_ppm?, distance_cm?, auto_brake}` — sensor fields required only if listed in the rover's `enabled_sensors`. **No `recorded_at` in the request** — the gateway stamps it. 201 always; no dedup on retry (a retried POST lands at a new receipt time and is stored as a second, distinct row).

## GET /rovers
Fleet list with `status` (`ONLINE`/`DEGRADED`/`OFFLINE`) derived from `rovers.last_seen_at`.

## GET /rovers/{device_uid}/latest
Latest reading with `age_seconds`. 404 if the rover is unknown or has never reported.

## GET /rovers/{device_uid}/readings
`limit` mode (default, most recent N) when `start`/`end` are absent; `start`+`end` range mode with `resolution=auto|raw|minute|hour|day`, `gaps` (periods with no data), and `query` cost fields (`raw_rows_in_range`, `query_time_ms`) when both are present.

## GET /rovers/{device_uid}/summary?granularity=minute|hour|day&start=&end=
Precomputed min/avg/max buckets from `telemetry_summaries`, plus `obstacle_events` (rising-edge count of `auto_brake`).

## GET /rovers/{device_uid}/export?format=csv|json&start=&end=
Streamed via an unbuffered PDO connection; `Content-Disposition: attachment` for CSV.

## GET /rovers/{device_uid}/events?since=&limit=
Derived at query time from `telemetry_readings`, not stored: `threshold_exceeded`, `auto_brake_engaged`/`auto_brake_cleared`, `reconnected`.

## GET /validation-errors/summary?window=24h
Counts from `validation_errors`, grouped by `error_code`.

## GET /config/sensor-limits
Current validation ranges with `updated_at`.

## PUT /config/sensor-limits/{field}
Body `{min, max}`, `min < max` required. Updates the bound used by the next ingest request onward (not retroactive).

## POST /rovers/{device_uid}/media
`multipart/form-data`, field `file`. 201 with metadata (id, media_type, file_path, captured_at, file_size_bytes, mime_type). `media_type` inferred from MIME type; SHA-256 hash computed server-side.

## GET /rovers/{device_uid}/media
List, most recent first. Omits `file_path` (a gateway filesystem detail).

## GET /rovers/{device_uid}/media/{id}
Streams the binary with `Content-Type`/`Content-Length` from the stored record.

## DELETE /rovers/{device_uid}/media/{id}
204, removes the row and the underlying file together.

## GET /health
`{status, database, api, uptime_seconds}`. 200 normally, 503 if the database is unreachable.

## GET /system
Live host metrics (`cpu_load_percent`, `cpu_temperature_c`, memory/disk used %, `ingest_rate_per_minute`, database size/row count), `services` block (api/database/aggregate_job/retention_job, the latter two read from `storage/*.lastrun` marker files), and a `warnings` array for any metric past its configured threshold.

## GET /system/history?start=&end=
Sampled host metrics over time from `gateway_metrics` (one row per minute, written by `bin/aggregate.php`).

## Error shape (all endpoints)

```json
{"error": {"code": "OUT_OF_RANGE", "message": "...", "request_id": "..."}}
```

Codes: `MISSING_FIELD`, `OUT_OF_RANGE`, `MALFORMED_PAYLOAD`, `INVALID_PARAMETER`, `NOT_FOUND`, `SERVICE_UNAVAILABLE`, `INTERNAL_ERROR`.

## Out of scope (explicit)

Rover control/teleoperation and dashboard UI implementation are not part of this backend — the reference dashboard in the design spec (§11) is presented as a reference design only, and the Cockpit teleoperation view talks directly to the rover over UDP, never through this API.

## Controller layout note

Each endpoint is implemented as its own controller class (one file per endpoint), e.g. `RoverListController`, `RoverLatestController`, `RoverReadingsController`, `MediaUploadController`, `SensorLimitsGetController`/`SensorLimitsPutController`. Shared formatting logic lives in `RoverTelemetry\Support\ReadingFormatter`.

## Deployment note

On the Pi 5: run behind php-fpm with a warm process pool and persistent PDO connections (spec §8.2 — this is what the 30 ms `GET /latest` budget assumes, not raw query cost). Point `MEDIA_STORAGE_PATH` at `/var/rover-media` (dev uses a project-relative `storage/media`). Schedule `bin/aggregate.php` (every minute) and `bin/retention.php` (nightly) via cron.
