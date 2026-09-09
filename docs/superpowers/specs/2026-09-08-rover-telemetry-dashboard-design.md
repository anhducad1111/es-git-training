# Rover Telemetry Web Dashboard — Design

**Date:** 2026-09-08
**Branch:** `feat/rover-telemetry-dashboard` (based on `develop`)
**Reference:** `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md` §11
**Backend:** `rover-telemetry-backend` (already merged into `develop` via PR #25), API base `/api/v1`

## 1. Scope

Build the reference dashboard described in the backend design proposal §11, covering three views:

- **Live** (§11.1) — rover pilot
- **History** (§11.2) — ops/science analyst
- **System** (§11.3) — administrator

**Out of scope:** Cockpit/teleoperation (§11.4). It talks directly to the rover over UDP, does not use this API, and teleoperation already has a working implementation in `robot-desktop-app-tokura`. No Cockpit tab, placeholder, or proxy is built here.

## 2. Delivery constraints (per §11.6)

- Static HTML, CSS, vanilla JavaScript. No build step, no Node toolchain.
- Chart.js loaded from a local vendored file, not a CDN (the gateway may be on an isolated field network).
- Polling: 1 s on Live, 5 s on System, on-demand on History. Each poll loop uses a `setTimeout` chain re-armed after the response resolves, never `setInterval`, so a slow gateway response is never queued behind itself.
- No auth (matches the API's current state).
- Single-column stacking below 700px.

## 3. File layout

```
rover-telemetry-frontend/public/
├── index.html          # tab shell (LIVE / HISTORY / SYSTEM), shared header
├── css/style.css        # layout, cards, tables, responsive breakpoint
├── js/
│   ├── config.js        # API_BASE_URL, polling intervals, thresholds
│   ├── api.js            # fetch wrapper: JSON parsing, error shape, request_id surfacing
│   ├── charts.js         # Chart.js helpers shared by all views (gap shading, threshold lines)
│   ├── live.js
│   ├── history.js
│   └── system.js
└── vendor/chart.js       # vendored Chart.js UMD build
```

`config.js` holds `API_BASE_URL` as the only place that changes between local development (a full URL to the backend's `public/` directory) and the eventual same-origin Pi deployment (`/api/v1`).

## 4. Live view

**Data sources:** `GET /rovers` (fleet list, 1 s), `GET /rovers/{uid}/latest` (1 s, selected rover only), `GET /rovers/{uid}/readings?resolution=auto` (on rover selection and on range change), `GET /rovers/{uid}/events`, `GET /validation-errors/summary`, `GET /config/sensor-limits`.

**Layout (from the UI sketch):**
- Left rail: fleet list with `status` and age (`ONLINE · 1.4 s ago`), rejected-payload count for the last 24h.
- Five metric cards: temperature, humidity, gas, distance, auto-brake state — each showing today's min/max alongside the current value.
- Telemetry chart: temperature + humidity over a selectable range (10m/1h/6h/24h/7d/30d), average line with min/max band, shaded gaps, resolution badge (e.g. `minute · 360 pts · auto`), CSV/JSON export shortcuts (reuse History's export logic against the current rover/range).
- Obstacle-distance chart: last 5 minutes, raw resolution, auto-brake threshold line, shaded brake-engaged bands (rising→falling edges of `auto_brake`).
- Incoming-readings table: newest-first, last ~10 polls of `/latest`, client-side ring buffer (no dedicated endpoint). Each row is annotated `stored` / `gas spike` (a `threshold_exceeded` event from `/events` at that timestamp) / `brake` (`auto_brake_engaged` event at that timestamp). **Correction from the UI sketch:** the sketch shows an inline `rejected` row with sensor values, but no endpoint exposes per-row rejected-payload detail (device, values, timestamp) — `GET /validation-errors/summary` only returns counts grouped by error code, and rejected payloads never reach `telemetry_readings` so `/events` can't surface them either. A rejected row cannot be rendered with real data and is not fabricated; rejection visibility stays in the sidebar's aggregate count (below).
- Sensor-limit bars: current value against `min`/`max` from `/config/sensor-limits`.
- Recent-events list from `/rovers/{uid}/events`.

**Selection state:** selecting a fleet rover switches every panel to that `device_uid`; state lives in a single `selectedRover` variable in `live.js`, not in the URL (no routing needed for this scope).

**Degraded/offline rover:** when `status !== "ONLINE"`, cards show the value's timestamp instead of implying freshness (`at 10:04:13Z`), matching the sketch's degraded state — this is a rendering rule based on `status`/`age_seconds`, not a separate code path per state.

## 5. History view

**Data sources:** `GET /rovers/{uid}/readings?resolution=auto&start=&end=`, `GET /rovers/{uid}/summary?granularity=&start=&end=`, `GET /rovers/{uid}/export`.

**Controls:** rover selector, sensor checkboxes (temperature/humidity/gas/distance — hide/show chart series, client-side only), range presets (1h/6h/24h/7d/30d) plus a custom start/end pair, resolution selector defaulting to `auto` with the server's chosen resolution shown and a manual override.

**Panels:**
- Query-cost line: `rows returned`, `raw rows in range`, `query time`, `gaps found` — straight from the `readings` response's `count`, `query.raw_rows_in_range`, `query.query_time_ms`, and `gaps.length`.
- Aggregated chart: avg line + min/max band per selected sensor, gaps shaded and the line broken across them (never interpolated).
- Statistics table from `/summary`: min/avg/max/samples/last per sensor, header states `X of Y buckets populated`.
- Obstacle-events bar chart: `obstacle_events` per bucket from `/summary`.
- Gap list: each gap's start/end/duration/estimated missing readings, from the `gaps` array.
- Export buttons: call `/export?format=csv|json` with the current rover/range and trigger a browser download.

## 6. System view

**Data sources:** `GET /system` (5 s), `GET /health` (5 s), `GET /system/history?start=&end=&resolution=`.

**Panels:**
- Services panel: api/database/aggregate_job/retention_job status and last-run, from `/system.services`.
- Database panel: size, row count, growth/day, `projected_days_remaining`.
- Rejected-payloads panel (reuses `/validation-errors/summary`, same component as the Live sidebar).
- Four metric cards: CPU load, CPU temperature (with the configured warning threshold drawn as a reference line when charted), memory, disk.
- Resource history chart: CPU temp / CPU load / memory over a selectable range (1h/6h/24h/7d), throttle-limit reference line.
- Ingest-rate chart: shades periods with `ingest_rate_per_min = 0` distinctly from a gap (no-telemetry vs. gateway-down are visually different, per §11.3).
- Database-growth chart: historical `database_size_mb` plus a naive linear projection forward (client-side, from the same growth-rate figure `/system` already reports — no new endpoint needed).

**Warnings:** the header's warning count and per-card warning styling come directly from `/system.warnings`; no threshold values are hard-coded client-side beyond what's needed to draw the reference lines (which also come from `/system`'s reported limits where available, falling back to `config.js` constants otherwise).

**Sensor-limit editor:** a panel backed by `GET /config/sensor-limits` and `PUT /config/sensor-limits/{field}`. Lists the four numeric fields (`temperature_c`, `humidity_pct`, `gas_ppm`, `distance_cm`) with editable min/max inputs and each field's `updated_at`. Saving one field calls `PUT` for that field only; a validation failure from the API (`min` not less than `max`) is shown inline on that field's row rather than blocking the others. This is not in the rendered UI sketch, so it gets a plain, undecorated form consistent with the rest of the System view rather than a specific mocked-up treatment.

## 7. Shared error handling

- `api.js` wraps `fetch`; a non-2xx response is parsed for the `{error: {code, message, request_id}}` shape and surfaced as a small inline banner in the relevant panel, not a global alert.
- Network failure or `SERVICE_UNAVAILABLE` on `/health` flips a header badge from `api ok · db ok` to a red `api down` state; polling continues (retry, not stop) so the dashboard recovers automatically when the gateway returns.
- Each view keeps its last-successful render on screen during a failed poll rather than clearing to empty, with a "stale since HH:MM:SS" indicator once a poll has failed.
- A 404 on `/rovers/{uid}/latest` (rover never reported) renders an explicit empty state, not an error banner.

## 8. Testing

No backend changes are made, so backend test suite is untouched. For the dashboard itself (plain JS, no framework, no build):

- Manual verification against the live backend (already running locally with real load-test data) for each view, each control (range/resolution/export), and the degraded/offline/rejected-payload visual states — using Chrome browser automation to click through and screenshot each view.
- A short `docs/` note (or PR description) records which scenarios were checked, since there is no automated UI test harness in this stack (matches the "no build tooling" constraint — introducing a JS test runner would be a bigger change than this dashboard justifies).

## 9. Out of scope / explicitly deferred

- Cockpit tab (§4 above).
- Authentication (matches current API state; §11.6 "Auth: None").
- Media (photo/video) browsing UI was originally out of scope (not part of §11's three views or its mockups), but a basic media gallery (list + delete) was later added to the Live view as a deliberate, explicitly-requested addition beyond this design — see commit `85863b0` and the final-review hardening pass.

## 10. Manual QA record

Verified by browser walkthrough (Chrome automation) against the local backend at
`http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1`:

- All three tabs render with real data from `rover-001` and switch without leaking timers.
- Responsive layout at 375px width: single column, no horizontal overflow, on Live and History.
  System view initially overflowed (the sensor-limit editor table, with two 70px number inputs
  per row, forced the page 448px wide against a 356px viewport); fixed by scoping
  `overflow-x: auto` to that table's containing panel (`.panel:has(#sensor-limits-editor-body)`
  in `style.css`) so only that panel scrolls horizontally instead of the whole page.
- Live view: fleet selection, five metric cards, both charts, incoming-readings table, sensor-limit bars, recent events.
- History view: range/resolution/sensor controls, query-cost panel, aggregated chart, statistics table, obstacle-events chart, gap list, CSV export URL.
- System view: metric cards, services/database/rejected panels, three history charts, sensor-limit editor round-trip (write-then-restore verified against `distance_cm`).
- Degraded/offline rendering confirmed via a forced `/latest` failure.
- Media gallery panel (Live view, added post-design per commit `85863b0`, hardened in the
  final-review fix pass): confirmed it renders `rover-001`'s 3 media items with no console
  errors, and confirmed its own responsive behavior at a narrow (~375px) viewport does not
  overflow (`scrollWidth`/`clientWidth` matched on the containing panel and the gallery
  itself, same check used above for the sensor-limit editor table).
