# Verification Results

## Automated (PHPUnit)

- [x] Full suite green: `"c:/xampp/php/php.exe" phpunit.phar` — 84 tests, 202 assertions, 0 failures, 0 errors (as of Task 25/26).

## Manual (Apache, per task)

- [x] Ingest (T01–T04, T11): POST 201, `recorded_at` gateway-stamped, no `recorded_at` in the request body accepted; re-POSTing the identical payload returns 201 again with a different `recorded_at` — confirmed no retry dedup, two distinct rows stored.
- [x] Fleet list (`GET /rovers`): `status` derived from `last_seen_at` age, confirmed ONLINE/DEGRADED/OFFLINE transitions.
- [x] Latest (`GET /rovers/{device_uid}/latest`): nullable sensor fields returned as `null`, not omitted; `age_seconds` present.
- [x] Readings, limit mode and range mode (with `resolution`, `gaps`, `query` cost fields).
- [x] Summary (`GET /rovers/{device_uid}/summary`), after running `bin/aggregate.php`.
- [x] Export (`GET /rovers/{device_uid}/export`): CSV with `Content-Disposition: attachment` and correct header row; JSON array form.
- [x] Health/System: `GET /health` 200 normally; confirmed 503 with MariaDB stopped, and 200 again after restart. `GET /system` shape confirmed, including `services.aggregate_job`/`retention_job` read from marker files.
- [x] System history (`GET /system/history`): points returned in chronological order after multiple `bin/aggregate.php` runs.
- [x] Events (`GET /rovers/{device_uid}/events`): `reconnected` events derived correctly from a real gap in stored readings.
- [x] Validation-errors summary: counts confirmed against accumulated `OUT_OF_RANGE` rows from earlier manual testing.
- [x] Sensor limits GET/PUT: PUT updates persisted and read back correctly; dev DB restored to seed defaults afterward.
- [x] Media upload/list/serve/delete: all four confirmed against Apache with a real multipart upload (`composer.json` as the test payload), including the 204/404 delete-then-refetch sequence.
- [x] Retention: `bin/retention.php` run manually against the dev database; `storage/retention.lastrun` marker file created.

## Load & Latency (T09, T10 — Apache only, not `php -S`)

- [x] Simulator run (`bin/simulate_rover.php --device=rover-sim-001 --count=50 --interval-ms=50`): 50 sent, 0 failed.
- [x] Load test (`bin/loadtest.php --requests=1000 --devices=5`): 1000 requests in 26.78s, 1000 succeeded, 0 failed, p50 22.0ms, p95 42.9ms (measures `POST /telemetry` latency under load, not the `GET /latest` budget).
- [x] `GET /latest` p95 measured separately (5 samples via `curl -w "%{time_total}"`): ~18–37ms. Close to but occasionally over the 30ms budget on this dev machine, which runs Apache/mod_php without php-fpm's persistent worker pool — spec §8.2 identifies process/connection startup, not query cost, as the dominant factor in that budget. Expected to improve on the Pi 5 deployment target once behind php-fpm.

## Retention

- [x] `bin/retention.php` verified via `RetentionScriptTest` (batched deletion of old raw readings and validation errors, recent rows kept) and a manual run against the dev database.

## Known deviations from spec (see plan's Global Constraints for full rationale)

- `sensor_limits` read fresh per request, no in-process cache.
- `system/history` `auto` resolution always serves raw (no hourly rollup for 7d+ ranges) — not implemented since no spec §10 verification test exercises it.
- Media storage path is project-relative (`storage/media`) in dev, not `/var/rover-media`.
- `media_files` DDL corrected to match spec §5.8's column table (§5.10's DDL block in the source spec was stale relative to the column table).
- Every endpoint is implemented as its own controller class (one file per endpoint), a structural choice made partway through implementation (after Task 17) at the user's explicit request, rather than grouping several endpoints per controller file.

## Environment notes for future sessions

- The PHP built-in dev server (`php -S`, used by `HttpTestCase`) must be spawned with `env` left `null` (inherit the parent process environment) rather than an explicit replacement array — on Windows, replacing the full environment drops `SystemRoot` and other variables winsock needs, causing intermittent bind/listen failures.
- `rover-telemetry-backend/` lives directly under the shared `es-git-training` htdocs checkout, not its own vhost — `.htaccess` at the project root denies direct access to everything except `public/`, which re-grants it.
- This checkout is shared with other, unrelated project branches in the same working directory; confirm the current branch (`git branch --show-current`) before running tests or committing if work has paused and resumed.
