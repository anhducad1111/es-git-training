# Rover Telemetry Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the static, no-build Live/History/System telemetry dashboard for the `rover-telemetry-backend` API, per the existing design doc.

**Architecture:** Plain HTML/CSS/vanilla JS, one file per concern (`config`, `api`, `charts`, `live`, `history`, `system`), Chart.js vendored locally, tab-switch shell with three independently-polling views. No framework, no bundler, no package.json.

**Tech Stack:** HTML5, CSS3, vanilla ES2017+ JavaScript (`fetch`, template literals, no modules — plain `<script>` tags loaded in dependency order so everything shares `window` scope), Chart.js (UMD build, vendored).

**Spec:** `rover-telemetry-frontend/docs/2026-09-08-rover-telemetry-dashboard-design.md` (the plan below implements it section by section); API contract source: `rover-telemetry-frontend/docs/Central_Telemetry_Backend_Design_Proposal_v1.1.md` §6, §11.

## Global Constraints

- Static HTML, CSS, vanilla JavaScript. No build step, no Node toolchain, no `package.json`.
- Chart.js loaded from a local vendored file at `public/vendor/chart.js` — never a CDN `<script src>`.
- Polling: 1 s on Live, 5 s on System, on-demand on History. Every poll loop uses a `setTimeout` chain re-armed after the previous request settles — never `setInterval`.
- No auth.
- Single-column stacking below 700px viewport width.
- `config.js` is the only file containing `API_BASE_URL`; dev value is `http://localhost/es-git-training/rover-telemetry-backend/public/api/v1` (this repo lives under XAMPP's htdocs at that path).
- No JS test framework is introduced (matches the design doc's explicit "no build tooling" call) — every task's verification step is a manual check against the running backend via `run` or Chrome browser automation, not a unit test.
- `api.js`'s non-2xx handling always parses `{error:{code,message,request_id}}` and never throws an unhandled exception into a view — every view keeps its last-successful render on a failed poll.

---

## File Structure

```
rover-telemetry-frontend/public/
├── index.html           # Task 3: tab shell (LIVE/HISTORY/SYSTEM), shared header (api/db badge, warning count)
├── css/style.css         # Task 3: layout, cards, tables, 700px breakpoint
├── js/
│   ├── config.js         # Task 1: API_BASE_URL, poll intervals, fallback thresholds
│   ├── api.js             # Task 1: fetch wrapper, error-shape parsing, query-string builder
│   ├── charts.js          # Task 2: Chart.js dataset/plugin helpers shared by all 3 views
│   ├── live.js            # Task 4
│   ├── history.js         # Task 5
│   └── system.js          # Task 6
└── vendor/chart.js        # Task 1: vendored Chart.js UMD build
```

Load order in `index.html`: `vendor/chart.js` → `js/config.js` → `js/api.js` → `js/charts.js` → `js/live.js` → `js/history.js` → `js/system.js` → a small inline bootstrap that wires the tab bar and starts the active view's poll loop.

---

### Task 1: Config, API wrapper, vendored Chart.js

**Files:**
- Create: `rover-telemetry-frontend/public/vendor/chart.js`
- Create: `rover-telemetry-frontend/public/js/config.js`
- Create: `rover-telemetry-frontend/public/js/api.js`

**Interfaces:**
- Produces: `window.CONFIG = { API_BASE_URL, POLL_MS: { live, system }, FALLBACK_LIMITS: { cpu_temperature_c, disk_used_percent, memory_used_percent } }`
- Produces: `window.Api.get(path, params) => Promise<data>` — resolves with the parsed JSON body on 2xx, rejects with `{code, message, request_id, status}` on non-2xx or network failure (network failure gets `code: "NETWORK_ERROR"`, `status: 0`).
- Produces: `window.Api.put(path, body) => Promise<data>` — same error shape.
- Produces: `window.Api.buildQuery(params)` — turns `{start:"2026-09-03T00:00:00Z", limit:50}` into `?start=2026-09-03T00%3A00%3A00Z&limit=50`, skipping keys whose value is `undefined`/`null`.

- [ ] **Step 1: Vendor Chart.js**

Download the Chart.js 4.x UMD production build and save it verbatim to `rover-telemetry-frontend/public/vendor/chart.js` (no CDN reference anywhere in the app — this file must be self-contained on disk).

- [ ] **Step 2: Write `config.js`**

```javascript
window.CONFIG = {
  API_BASE_URL: "http://localhost/es-git-training/rover-telemetry-backend/public/api/v1",
  POLL_MS: {
    live: 1000,
    system: 5000
  },
  // Used only when /system's own warnings/limits are unavailable (e.g. before first poll succeeds).
  FALLBACK_LIMITS: {
    cpu_temperature_c: 80,
    disk_used_percent: 90,
    memory_used_percent: 90
  }
};
```

- [ ] **Step 3: Write `api.js`**

```javascript
window.Api = (function () {
  function buildQuery(params) {
    if (!params) return "";
    const parts = [];
    for (const key in params) {
      const value = params[key];
      if (value === undefined || value === null) continue;
      parts.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
    }
    return parts.length ? "?" + parts.join("&") : "";
  }

  async function request(method, path, { params, body } = {}) {
    const url = window.CONFIG.API_BASE_URL + path + buildQuery(params);
    let response;
    try {
      response = await fetch(url, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined
      });
    } catch (networkError) {
      throw { code: "NETWORK_ERROR", message: networkError.message, request_id: null, status: 0 };
    }

    if (response.status === 204) return null;

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json().catch(() => null)
      : await response.text();

    if (!response.ok) {
      const err = (payload && payload.error) || {};
      throw {
        code: err.code || "UNKNOWN_ERROR",
        message: err.message || "Request failed with status " + response.status,
        request_id: err.request_id || null,
        status: response.status
      };
    }

    return payload;
  }

  return {
    buildQuery,
    get: (path, params) => request("GET", path, { params }),
    put: (path, body) => request("PUT", path, { body })
  };
})();
```

- [ ] **Step 4: Manual verification**

Serve `rover-telemetry-frontend/public/` (e.g. `php -S localhost:8090 -t rover-telemetry-frontend/public`) with the backend running, open a blank page that just loads the three scripts, and in the DevTools console run:

```javascript
Api.get("/rovers").then(console.log).catch(console.error);
```

Expected: either a JSON array of rovers logged, or a rejected promise with a `{code, message, ...}` shape (never an uncaught exception).

- [ ] **Step 5: Commit**

```bash
git add rover-telemetry-frontend/public/vendor/chart.js rover-telemetry-frontend/public/js/config.js rover-telemetry-frontend/public/js/api.js
git commit -m "feat: vendor chart.js and add config/api layer for rover telemetry dashboard"
```

---

### Task 2: Shared chart helpers

**Files:**
- Create: `rover-telemetry-frontend/public/js/charts.js`

**Interfaces:**
- Consumes: global `Chart` (from vendored Chart.js), nothing from Task 1.
- Produces: `window.Charts.buildAvgMinMaxDataset(readings, field)` → `{ avgPoints, bandPoints }` where each point is `{x: isoString, y: number|null}`, `null` inserted at gap boundaries so Chart.js draws a break instead of connecting across a gap (readings already omit gap periods per the API contract, so a gap is detected as a time delta between consecutive points wider than 1.5× the median delta).
- Produces: `window.Charts.thresholdLinePlugin(value, label)` → a Chart.js plugin object that draws one horizontal reference line with a label at `value` on the y-axis.
- Produces: `window.Charts.shadeBandsPlugin(bands, color)` → a Chart.js plugin object that fills vertical bands between `{start, end}` (ISO timestamps, x-axis pixel-mapped) — used for auto-brake-engaged bands and ingest-rate-zero bands.
- Produces: `window.Charts.timeAxisOptions()` → the shared `scales.x` config (`type: "time"`, no adapter bundled — see Step 1 note) used by every chart in the app, so tick formatting is consistent.

- [ ] **Step 1: Confirm the vendored Chart.js build includes a time-scale adapter, or vendor one**

Chart.js's `time` scale needs a date adapter (`chartjs-adapter-date-fns` or similar) to parse ISO strings. Check `vendor/chart.js`'s version; if it does not bundle one, download `chartjs-adapter-date-fns` UMD build too and save it as `rover-telemetry-frontend/public/vendor/chartjs-adapter-date-fns.js`, loaded in `index.html` right after `chart.js`. Confirm by opening a throwaway page with a `type:"time"` axis and checking the console for `"This method is not implemented"` errors — absence of that error means the adapter is wired correctly.

- [ ] **Step 2: Write `charts.js`**

```javascript
window.Charts = (function () {
  function buildAvgMinMaxDataset(readings, field) {
    const points = readings
      .map(r => {
        const raw = r[field];
        if (raw === null || raw === undefined) return null;
        const value = typeof raw === "object" ? raw.avg : raw;
        const min = typeof raw === "object" ? raw.min : raw;
        const max = typeof raw === "object" ? raw.max : raw;
        return { x: r.recorded_at, y: value, min, max };
      })
      .filter(Boolean);

    if (points.length < 2) {
      return {
        avgPoints: points.map(p => ({ x: p.x, y: p.y })),
        bandPoints: points.map(p => ({ x: p.x, yMin: p.min, yMax: p.max }))
      };
    }

    const deltas = [];
    for (let i = 1; i < points.length; i++) {
      deltas.push(new Date(points[i].x) - new Date(points[i - 1].x));
    }
    deltas.sort((a, b) => a - b);
    const median = deltas[Math.floor(deltas.length / 2)];
    const gapThreshold = median * 1.5;

    const avgPoints = [];
    const bandPoints = [];
    for (let i = 0; i < points.length; i++) {
      if (i > 0) {
        const delta = new Date(points[i].x) - new Date(points[i - 1].x);
        if (delta > gapThreshold) {
          avgPoints.push({ x: points[i - 1].x, y: null });
        }
      }
      avgPoints.push({ x: points[i].x, y: points[i].y });
      bandPoints.push({ x: points[i].x, yMin: points[i].min, yMax: points[i].max });
    }
    return { avgPoints, bandPoints };
  }

  function thresholdLinePlugin(value, label) {
    return {
      id: "thresholdLine_" + label.replace(/\s+/g, "_"),
      afterDatasetsDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        if (!chartArea || !scales.y) return;
        const y = scales.y.getPixelForValue(value);
        ctx.save();
        ctx.strokeStyle = "#d9534f";
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(chartArea.left, y);
        ctx.lineTo(chartArea.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "#d9534f";
        ctx.font = "11px sans-serif";
        ctx.fillText(label, chartArea.right - ctx.measureText(label).width - 4, y - 4);
        ctx.restore();
      }
    };
  }

  function shadeBandsPlugin(bands, color) {
    return {
      id: "shadeBands_" + color.replace(/[^a-z0-9]/gi, ""),
      beforeDatasetsDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        if (!chartArea || !scales.x) return;
        ctx.save();
        ctx.fillStyle = color;
        bands.forEach(band => {
          const x1 = scales.x.getPixelForValue(new Date(band.start).getTime());
          const x2 = scales.x.getPixelForValue(new Date(band.end).getTime());
          ctx.fillRect(x1, chartArea.top, Math.max(x2 - x1, 1), chartArea.bottom - chartArea.top);
        });
        ctx.restore();
      }
    };
  }

  function timeAxisOptions() {
    return {
      type: "time",
      time: { tooltipFormat: "yyyy-MM-dd HH:mm:ss" },
      ticks: { maxRotation: 0 }
    };
  }

  return { buildAvgMinMaxDataset, thresholdLinePlugin, shadeBandsPlugin, timeAxisOptions };
})();
```

- [ ] **Step 3: Manual verification**

Build a throwaway HTML page that loads `vendor/chart.js`, the date adapter, and `charts.js`, feeds `buildAvgMinMaxDataset` a small array with one deliberate 20-minute gap in 1-minute-interval data, and renders it as a `line` chart. Expected: the line visibly breaks at the gap instead of connecting straight across it.

- [ ] **Step 4: Commit**

```bash
git add rover-telemetry-frontend/public/js/charts.js rover-telemetry-frontend/public/vendor/chartjs-adapter-date-fns.js
git commit -m "feat: add shared chart helpers for gap-aware series and threshold/band overlays"
```

---

### Task 3: Page shell and styles

**Files:**
- Create: `rover-telemetry-frontend/public/index.html`
- Create: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Produces DOM contract every view script relies on:
  - `<header>` contains `#health-badge` (text content toggled between `api ok · db ok` and `api down` by whichever view's poll loop is active) and `#warning-count`.
  - Tab buttons `#tab-live`, `#tab-history`, `#tab-system`, each toggling a `.active` class and the matching `<section id="view-live|view-history|view-system">`'s `hidden` attribute.
  - Each view's root `<section>` is empty except for a static skeleton of container `<div>`s with fixed ids (defined per-view in Tasks 4–6) that the view script fills in — no view script creates its own root container.
- Consumes: nothing (this is the leaf of the dependency graph other than global CSS classes views will reference: `.card`, `.card--warning`, `.stale`, `.rejected-row`, `.badge-online/.badge-degraded/.badge-offline`).

- [ ] **Step 1: Write `index.html`**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rover Telemetry Dashboard</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <header class="app-header">
    <h1>Rover Telemetry</h1>
    <nav class="tabs">
      <button id="tab-live" class="tab active" data-view="live">LIVE</button>
      <button id="tab-history" class="tab" data-view="history">HISTORY</button>
      <button id="tab-system" class="tab" data-view="system">SYSTEM</button>
    </nav>
    <div class="status-strip">
      <span id="health-badge" class="badge badge-online">api ok · db ok</span>
      <span id="warning-count" class="badge badge-warning" hidden></span>
    </div>
  </header>

  <main>
    <section id="view-live" class="view">
      <aside id="live-fleet-list" class="fleet-rail"></aside>
      <div class="view-body">
        <div id="live-metric-cards" class="card-row"></div>
        <div id="live-telemetry-chart" class="chart-panel"></div>
        <div id="live-distance-chart" class="chart-panel"></div>
        <div id="live-readings-table" class="table-panel"></div>
        <div id="live-sensor-limits" class="bars-panel"></div>
        <div id="live-events" class="list-panel"></div>
      </div>
    </section>

    <section id="view-history" class="view" hidden>
      <div id="history-controls" class="controls-row"></div>
      <div id="history-query-cost" class="query-cost-line"></div>
      <div id="history-chart" class="chart-panel"></div>
      <div id="history-stats-table" class="table-panel"></div>
      <div id="history-events-chart" class="chart-panel"></div>
      <div id="history-gap-list" class="list-panel"></div>
      <div id="history-export" class="export-row"></div>
    </section>

    <section id="view-system" class="view" hidden>
      <div id="system-services" class="card-row"></div>
      <div id="system-database" class="card-row"></div>
      <div id="system-rejected" class="card-row"></div>
      <div id="system-metric-cards" class="card-row"></div>
      <div id="system-resource-chart" class="chart-panel"></div>
      <div id="system-ingest-chart" class="chart-panel"></div>
      <div id="system-growth-chart" class="chart-panel"></div>
      <div id="system-limit-editor" class="form-panel"></div>
    </section>
  </main>

  <script src="vendor/chart.js"></script>
  <script src="vendor/chartjs-adapter-date-fns.js"></script>
  <script src="js/config.js"></script>
  <script src="js/api.js"></script>
  <script src="js/charts.js"></script>
  <script src="js/live.js"></script>
  <script src="js/history.js"></script>
  <script src="js/system.js"></script>
  <script>
    const views = { live: LiveView, history: HistoryView, system: SystemView };
    let activeView = null;

    document.querySelectorAll(".tab").forEach(btn => {
      btn.addEventListener("click", () => {
        const name = btn.dataset.view;
        document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b === btn));
        document.querySelectorAll(".view").forEach(sec => sec.hidden = sec.id !== "view-" + name);
        if (activeView && activeView.stop) activeView.stop();
        activeView = views[name];
        activeView.start();
      });
    });

    activeView = LiveView;
    activeView.start();
  </script>
</body>
</html>
```

- [ ] **Step 2: Write `css/style.css`**

```css
:root {
  color-scheme: light;
  --bg: #f4f5f7;
  --card-bg: #ffffff;
  --border: #d8dbe0;
  --text: #1b1e24;
  --muted: #6b7280;
  --online: #2e7d32;
  --degraded: #b8860b;
  --offline: #b91c1c;
  --warning-bg: #fff3cd;
  --danger: #d9534f;
}

* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }

.app-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.app-header h1 { font-size: 16px; margin: 0; }
.tabs { display: flex; gap: 4px; }
.tab { padding: 6px 12px; border: 1px solid var(--border); background: var(--bg); cursor: pointer; border-radius: 4px; }
.tab.active { background: var(--text); color: #fff; }
.status-strip { margin-left: auto; display: flex; gap: 8px; }

.badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge-online { background: #e6f4ea; color: var(--online); }
.badge-degraded { background: #fdf3dd; color: var(--degraded); }
.badge-offline { background: #fdecea; color: var(--offline); }
.badge-warning { background: var(--warning-bg); color: #7a5b00; }

main { padding: 16px; }
.view { display: flex; gap: 16px; }
.view-body { flex: 1; display: flex; flex-direction: column; gap: 16px; min-width: 0; }
#view-history, #view-system { flex-direction: column; }

.fleet-rail { width: 220px; flex-shrink: 0; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px; }

.card-row { display: flex; gap: 12px; flex-wrap: wrap; }
.card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; min-width: 140px; flex: 1; }
.card--warning { border-color: var(--danger); background: #fff5f5; }
.card .value { font-size: 22px; font-weight: 600; }
.card .label { font-size: 12px; color: var(--muted); }
.card .as-of { font-size: 11px; color: var(--muted); }

.chart-panel, .table-panel, .list-panel, .bars-panel, .form-panel, .controls-row, .query-cost-line, .export-row {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
}
.chart-panel canvas { max-height: 320px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--border); }
tr.rejected-row { color: var(--muted); background: #f7f7f7; }
tr.rejected-row td::after { content: ""; }

.stale-banner { background: var(--warning-bg); color: #7a5b00; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 8px; }
.error-banner { background: #fdecea; color: var(--offline); padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 8px; }

@media (max-width: 700px) {
  .view { flex-direction: column; }
  .fleet-rail { width: 100%; }
  .card-row { flex-direction: column; }
}
```

- [ ] **Step 3: Manual verification**

Open `index.html` directly in Chrome via browser automation (empty `LiveView`/`HistoryView`/`SystemView` stubs are fine for this task — add temporary `window.LiveView = {start(){}, stop(){}}` etc. if Tasks 4–6 aren't done yet, then delete the stubs once those tasks land). Screenshot each tab switch. Expected: tab bar switches the visible section, header renders, no console errors, layout stacks to one column under 700px width (resize the window to verify).

- [ ] **Step 4: Commit**

```bash
git add rover-telemetry-frontend/public/index.html rover-telemetry-frontend/public/css/style.css
git commit -m "feat: add tab shell and shared styles for rover telemetry dashboard"
```

---

### Task 4: Live view

**Files:**
- Create: `rover-telemetry-frontend/public/js/live.js`

**Interfaces:**
- Consumes: `Api.get`, `Charts.buildAvgMinMaxDataset`, `Charts.thresholdLinePlugin`, `Charts.shadeBandsPlugin`, `Charts.timeAxisOptions`, `CONFIG.POLL_MS.live`, DOM ids from Task 3 (`#live-fleet-list`, `#live-metric-cards`, `#live-telemetry-chart`, `#live-distance-chart`, `#live-readings-table`, `#live-sensor-limits`, `#live-events`, `#health-badge`, `#warning-count`).
- Produces: `window.LiveView = { start(), stop() }`.

**Endpoints used:** `GET /rovers`, `GET /rovers/{uid}/latest`, `GET /rovers/{uid}/readings?resolution=auto&start=&end=` (last 6h for the telemetry chart, last 5m raw for the distance chart), `GET /rovers/{uid}/events`, `GET /validation-errors/summary`, `GET /config/sensor-limits`.

- [ ] **Step 1: Write `live.js`**

```javascript
window.LiveView = (function () {
  let selectedRover = null;
  let timerId = null;
  let running = false;
  let telemetryChart = null;
  let distanceChart = null;
  let lastGoodByPanel = {};
  const readingsHistory = [];

  function setHealthBadge(ok) {
    const badge = document.getElementById("health-badge");
    badge.textContent = ok ? "api ok · db ok" : "api down";
    badge.className = "badge " + (ok ? "badge-online" : "badge-offline");
  }

  function statusClass(status) {
    if (status === "ONLINE") return "badge-online";
    if (status === "DEGRADED") return "badge-degraded";
    return "badge-offline";
  }

  async function renderFleetList() {
    const el = document.getElementById("live-fleet-list");
    try {
      const rovers = await Api.get("/rovers");
      lastGoodByPanel.fleet = rovers;
      if (!selectedRover && rovers.length) selectedRover = rovers[0].device_uid;
      el.innerHTML = rovers.map(r => `
        <div class="fleet-item ${r.device_uid === selectedRover ? "selected" : ""}" data-uid="${r.device_uid}">
          <span class="badge ${statusClass(r.status)}">${r.status}</span>
          <div>${r.name || r.device_uid}</div>
        </div>
      `).join("");
      el.querySelectorAll(".fleet-item").forEach(item => {
        item.addEventListener("click", () => {
          selectedRover = item.dataset.uid;
          readingsHistory.length = 0;
          renderFleetList();
        });
      });
      setHealthBadge(true);
    } catch (err) {
      setHealthBadge(false);
      if (!el.innerHTML) el.innerHTML = `<div class="error-banner">${err.message}</div>`;
    }
  }

  async function renderMetricCards() {
    if (!selectedRover) return;
    const el = document.getElementById("live-metric-cards");
    try {
      const latest = await Api.get(`/rovers/${selectedRover}/latest`);
      readingsHistory.unshift({ ...latest, rejected: false });
      readingsHistory.splice(10);
      lastGoodByPanel.latest = latest;
      const fields = [
        ["temperature_c", "Temp (°C)"],
        ["humidity_pct", "Humidity (%)"],
        ["gas_ppm", "Gas (ppm)"],
        ["distance_cm", "Distance (cm)"],
        ["auto_brake", "Auto-brake"]
      ];
      const stale = latest.age_seconds > 15;
      el.innerHTML = fields.map(([field, label]) => {
        const value = latest[field];
        const display = field === "auto_brake" ? (value ? "ENGAGED" : "clear") : (value ?? "—");
        const asOf = stale ? `at ${new Date(latest.recorded_at).toLocaleTimeString()}` : `${latest.age_seconds.toFixed(1)}s ago`;
        return `<div class="card"><div class="label">${label}</div><div class="value">${display}</div><div class="as-of">${asOf}</div></div>`;
      }).join("");
      renderReadingsTable();
    } catch (err) {
      if (err.status === 404) {
        el.innerHTML = `<div class="card">No data reported yet for ${selectedRover}</div>`;
      } else {
        setHealthBadge(false);
      }
    }
  }

  function renderReadingsTable() {
    const el = document.getElementById("live-readings-table");
    const rows = readingsHistory.map(r => `
      <tr class="${r.rejected ? "rejected-row" : ""}">
        <td>${new Date(r.recorded_at).toLocaleTimeString()}</td>
        <td>${r.temperature_c ?? "—"}</td>
        <td>${r.humidity_pct ?? "—"}</td>
        <td>${r.gas_ppm ?? "—"}</td>
        <td>${r.distance_cm ?? "—"}</td>
        <td>${r.rejected ? "rejected" : "ok"}</td>
      </tr>
    `).join("");
    el.innerHTML = `<table><thead><tr><th>Time</th><th>Temp</th><th>Hum</th><th>Gas</th><th>Dist</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  async function renderTelemetryChart() {
    if (!selectedRover) return;
    try {
      const end = new Date().toISOString();
      const start = new Date(Date.now() - 6 * 3600 * 1000).toISOString();
      const data = await Api.get(`/rovers/${selectedRover}/readings`, { resolution: "auto", start, end });
      const temp = Charts.buildAvgMinMaxDataset(data.readings, "temperature_c");
      const hum = Charts.buildAvgMinMaxDataset(data.readings, "humidity_pct");
      const el = document.getElementById("live-telemetry-chart");
      if (!el.querySelector("canvas")) {
        el.innerHTML = `<div class="resolution-badge"></div><canvas></canvas>`;
      }
      el.querySelector(".resolution-badge").textContent = `${data.resolution} · ${data.count} pts · auto`;
      const canvas = el.querySelector("canvas");
      const datasets = [
        { label: "Temp avg", data: temp.avgPoints, borderColor: "#2563eb", spanGaps: false },
        { label: "Humidity avg", data: hum.avgPoints, borderColor: "#16a34a", spanGaps: false }
      ];
      if (!telemetryChart) {
        telemetryChart = new Chart(canvas, {
          type: "line",
          data: { datasets },
          options: { parsing: false, scales: { x: Charts.timeAxisOptions() } }
        });
      } else {
        telemetryChart.data.datasets = datasets;
        telemetryChart.update();
      }
    } catch (err) {
      setHealthBadge(false);
    }
  }

  async function renderDistanceChart() {
    if (!selectedRover) return;
    try {
      const end = new Date().toISOString();
      const start = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      const data = await Api.get(`/rovers/${selectedRover}/readings`, { resolution: "raw", start, end });
      const dist = Charts.buildAvgMinMaxDataset(data.readings, "distance_cm");
      const bands = [];
      let bandStart = null;
      data.readings.forEach((r, i) => {
        if (r.auto_brake && bandStart === null) bandStart = r.recorded_at;
        if (!r.auto_brake && bandStart !== null) {
          bands.push({ start: bandStart, end: r.recorded_at });
          bandStart = null;
        }
        if (i === data.readings.length - 1 && bandStart !== null) {
          bands.push({ start: bandStart, end: r.recorded_at });
        }
      });
      const el = document.getElementById("live-distance-chart");
      if (!el.querySelector("canvas")) el.innerHTML = `<canvas></canvas>`;
      const canvas = el.querySelector("canvas");
      if (distanceChart) distanceChart.destroy();
      distanceChart = new Chart(canvas, {
        type: "line",
        data: { datasets: [{ label: "Distance (cm)", data: dist.avgPoints, borderColor: "#ea580c", spanGaps: false }] },
        options: {
          parsing: false,
          scales: { x: Charts.timeAxisOptions() },
          plugins: {}
        },
        plugins: [Charts.shadeBandsPlugin(bands, "rgba(217,83,79,0.15)")]
      });
    } catch (err) {
      setHealthBadge(false);
    }
  }

  async function renderSensorLimits() {
    if (!selectedRover) return;
    try {
      const [limits, latest] = await Promise.all([
        Api.get("/config/sensor-limits"),
        lastGoodByPanel.latest ? Promise.resolve(lastGoodByPanel.latest) : Api.get(`/rovers/${selectedRover}/latest`)
      ]);
      const el = document.getElementById("live-sensor-limits");
      el.innerHTML = Object.keys(limits).map(field => {
        const { min, max } = limits[field];
        const value = latest[field];
        const pct = value == null ? 0 : Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
        return `<div class="limit-bar"><div class="label">${field}: ${value ?? "—"} (${min}–${max})</div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div></div>`;
      }).join("");
    } catch (err) { /* keep last render */ }
  }

  async function renderEvents() {
    if (!selectedRover) return;
    try {
      const data = await Api.get(`/rovers/${selectedRover}/events`);
      const el = document.getElementById("live-events");
      el.innerHTML = "<ul>" + data.events.map(e =>
        `<li>${new Date(e.at).toLocaleTimeString()} — ${e.type}${e.sensor ? " (" + e.sensor + ")" : ""}</li>`
      ).join("") + "</ul>";
    } catch (err) { /* keep last render */ }
  }

  async function poll() {
    if (!running) return;
    await Promise.all([renderFleetList(), renderMetricCards(), renderSensorLimits(), renderEvents()]);
    timerId = setTimeout(poll, window.CONFIG.POLL_MS.live);
  }

  async function slowPoll() {
    if (!running) return;
    await Promise.all([renderTelemetryChart(), renderDistanceChart()]);
    setTimeout(slowPoll, 5000);
  }

  function start() {
    running = true;
    poll();
    slowPoll();
  }

  function stop() {
    running = false;
    clearTimeout(timerId);
  }

  return { start, stop };
})();
```

- [ ] **Step 2: Manual verification**

With the backend running and seeded with at least one rover reporting, open the app in Chrome (browser automation), select the Live tab, and confirm over ~10 seconds: the fleet list shows a status badge and updates, the five metric cards update every second, the telemetry chart renders with a resolution badge, the distance chart renders, the readings table grows newest-first, sensor-limit bars show current values against min/max, and the events list populates (send one out-of-range `POST /telemetry` via `curl` during the check and confirm the readings table shows a `rejected` row — note the API does not echo rejected payloads back on `/latest`, so this is verified via the events list's `threshold_exceeded` entry and the validation-errors summary count rather than a table row, since the table here is built from successful `/latest` polls only; if this mismatches the design doc's "reject inline" intent, note it in the verification log for a follow-up rather than blocking this task). Screenshot the tab.

- [ ] **Step 3: Commit**

```bash
git add rover-telemetry-frontend/public/js/live.js
git commit -m "feat: implement live view with fleet list, metric cards, charts, and events"
```

---

### Task 5: History view

**Files:**
- Create: `rover-telemetry-frontend/public/js/history.js`

**Interfaces:**
- Consumes: `Api.get`, `Charts.buildAvgMinMaxDataset`, `Charts.timeAxisOptions`, DOM ids `#history-controls`, `#history-query-cost`, `#history-chart`, `#history-stats-table`, `#history-events-chart`, `#history-gap-list`, `#history-export`.
- Produces: `window.HistoryView = { start(), stop() }` (`start`/`stop` here just wire/unwire control listeners — History has no poll loop, everything is on-demand per the design doc).

**Endpoints used:** `GET /rovers` (populate the rover selector), `GET /rovers/{uid}/readings?resolution=&start=&end=`, `GET /rovers/{uid}/summary?granularity=&start=&end=`, `GET /rovers/{uid}/export?format=&start=&end=`.

- [ ] **Step 1: Write `history.js`**

```javascript
window.HistoryView = (function () {
  let rover = null;
  let range = "24h";
  let resolutionOverride = "auto";
  let chart = null;
  let eventsChart = null;
  const sensors = ["temperature_c", "humidity_pct", "gas_ppm", "distance_cm"];
  let visibleSensors = new Set(sensors);

  function rangeToStartEnd(r) {
    const end = new Date();
    const hours = { "1h": 1, "6h": 6, "24h": 24, "7d": 24 * 7, "30d": 24 * 30 }[r] || 24;
    const start = new Date(end.getTime() - hours * 3600 * 1000);
    return { start: start.toISOString(), end: end.toISOString() };
  }

  async function renderControls() {
    const el = document.getElementById("history-controls");
    let rovers = [];
    try { rovers = await Api.get("/rovers"); } catch (e) { /* leave selector empty */ }
    if (!rover && rovers.length) rover = rovers[0].device_uid;
    el.innerHTML = `
      <select id="hist-rover">${rovers.map(r => `<option value="${r.device_uid}" ${r.device_uid === rover ? "selected" : ""}>${r.device_uid}</option>`).join("")}</select>
      <select id="hist-range">
        ${["1h", "6h", "24h", "7d", "30d"].map(r => `<option value="${r}" ${r === range ? "selected" : ""}>${r}</option>`).join("")}
      </select>
      <select id="hist-resolution">
        ${["auto", "raw", "minute", "hour", "day"].map(r => `<option value="${r}" ${r === resolutionOverride ? "selected" : ""}>${r}</option>`).join("")}
      </select>
      ${sensors.map(s => `<label><input type="checkbox" data-sensor="${s}" ${visibleSensors.has(s) ? "checked" : ""}> ${s}</label>`).join("")}
    `;
    document.getElementById("hist-rover").addEventListener("change", e => { rover = e.target.value; refresh(); });
    document.getElementById("hist-range").addEventListener("change", e => { range = e.target.value; refresh(); });
    document.getElementById("hist-resolution").addEventListener("change", e => { resolutionOverride = e.target.value; refresh(); });
    el.querySelectorAll("input[data-sensor]").forEach(cb => {
      cb.addEventListener("change", () => {
        if (cb.checked) visibleSensors.add(cb.dataset.sensor); else visibleSensors.delete(cb.dataset.sensor);
        renderChart(window.__lastReadings);
      });
    });
  }

  function renderQueryCost(data) {
    document.getElementById("history-query-cost").innerHTML =
      `rows returned ${data.count} / raw rows in range ${data.query?.raw_rows_in_range ?? "—"} / query time ${data.query?.query_time_ms ?? "—"} ms / gaps found ${data.gaps?.length ?? 0}`;
  }

  function renderChart(data) {
    window.__lastReadings = data;
    const el = document.getElementById("history-chart");
    if (!el.querySelector("canvas")) el.innerHTML = `<canvas></canvas>`;
    const colors = { temperature_c: "#2563eb", humidity_pct: "#16a34a", gas_ppm: "#9333ea", distance_cm: "#ea580c" };
    const datasets = sensors.filter(s => visibleSensors.has(s)).map(field => {
      const built = Charts.buildAvgMinMaxDataset(data.readings, field);
      return { label: field, data: built.avgPoints, borderColor: colors[field], spanGaps: false };
    });
    if (chart) chart.destroy();
    chart = new Chart(el.querySelector("canvas"), {
      type: "line",
      data: { datasets },
      options: { parsing: false, scales: { x: Charts.timeAxisOptions() } }
    });
  }

  function renderGapList(data) {
    const el = document.getElementById("history-gap-list");
    el.innerHTML = "<ul>" + (data.gaps || []).map(g =>
      `<li>${g.start} → ${g.end} (${g.duration_seconds}s, ~${g.missing_readings} missing)</li>`
    ).join("") + "</ul>";
  }

  async function renderStatsAndEvents() {
    if (!rover) return;
    const { start, end } = rangeToStartEnd(range);
    try {
      const summary = await Api.get(`/rovers/${rover}/summary`, { granularity: range === "30d" ? "day" : range === "7d" ? "hour" : "minute", start, end });
      const populated = summary.buckets.filter(b => b.sample_count > 0).length;
      const rows = sensors.map(field => {
        const key = { temperature_c: "temperature_c", humidity_pct: "humidity_pct", gas_ppm: "gas_ppm", distance_cm: "distance_cm" }[field];
        const vals = summary.buckets.map(b => b[key]).filter(Boolean);
        const min = vals.length ? Math.min(...vals.map(v => v.min)) : "—";
        const max = vals.length ? Math.max(...vals.map(v => v.max)) : "—";
        const avg = vals.length ? (vals.reduce((s, v) => s + v.avg, 0) / vals.length).toFixed(1) : "—";
        return `<tr><td>${field}</td><td>${min}</td><td>${avg}</td><td>${max}</td></tr>`;
      }).join("");
      document.getElementById("history-stats-table").innerHTML =
        `<div>${populated} of ${summary.buckets.length} buckets populated</div>
         <table><thead><tr><th>Sensor</th><th>Min</th><th>Avg</th><th>Max</th></tr></thead><tbody>${rows}</tbody></table>`;

      const el = document.getElementById("history-events-chart");
      if (!el.querySelector("canvas")) el.innerHTML = `<canvas></canvas>`;
      if (eventsChart) eventsChart.destroy();
      eventsChart = new Chart(el.querySelector("canvas"), {
        type: "bar",
        data: {
          labels: summary.buckets.map(b => new Date(b.bucket_start).toLocaleString()),
          datasets: [{ label: "Obstacle events", data: summary.buckets.map(b => b.obstacle_events), backgroundColor: "#ea580c" }]
        }
      });
    } catch (err) { /* keep last render */ }
  }

  function renderExportButtons() {
    document.getElementById("history-export").innerHTML = `
      <button id="export-csv">Export CSV</button>
      <button id="export-json">Export JSON</button>
    `;
    document.getElementById("export-csv").addEventListener("click", () => triggerExport("csv"));
    document.getElementById("export-json").addEventListener("click", () => triggerExport("json"));
  }

  function triggerExport(format) {
    if (!rover) return;
    const { start, end } = rangeToStartEnd(range);
    const query = Api.buildQuery({ format, start, end });
    window.open(window.CONFIG.API_BASE_URL + `/rovers/${rover}/export` + query, "_blank");
  }

  async function refresh() {
    if (!rover) return;
    const { start, end } = rangeToStartEnd(range);
    try {
      const data = await Api.get(`/rovers/${rover}/readings`, { resolution: resolutionOverride, start, end });
      renderQueryCost(data);
      renderChart(data);
      renderGapList(data);
    } catch (err) { /* keep last render */ }
    await renderStatsAndEvents();
  }

  async function start() {
    await renderControls();
    renderExportButtons();
    await refresh();
  }

  function stop() {}

  return { start, stop };
})();
```

- [ ] **Step 2: Manual verification**

Open the History tab in Chrome, select a rover, cycle through each range preset and confirm the chart, query-cost line, stats table, obstacle-events bar chart, and gap list all update. Toggle a sensor checkbox off and confirm its line disappears from the chart without a refetch. Click both export buttons and confirm a file download / new tab with CSV or JSON content starts. Screenshot the view with all panels populated.

- [ ] **Step 3: Commit**

```bash
git add rover-telemetry-frontend/public/js/history.js
git commit -m "feat: implement history view with range/resolution controls, gap list, and export"
```

---

### Task 6: System view

**Files:**
- Create: `rover-telemetry-frontend/public/js/system.js`

**Interfaces:**
- Consumes: `Api.get`, `Api.put`, `Charts.buildAvgMinMaxDataset`, `Charts.thresholdLinePlugin`, `Charts.timeAxisOptions`, `CONFIG.POLL_MS.system`, `CONFIG.FALLBACK_LIMITS`, DOM ids `#system-services`, `#system-database`, `#system-rejected`, `#system-metric-cards`, `#system-resource-chart`, `#system-ingest-chart`, `#system-growth-chart`, `#system-limit-editor`, `#warning-count`.
- Produces: `window.SystemView = { start(), stop() }`.

**Endpoints used:** `GET /system`, `GET /health`, `GET /system/history?start=&end=&resolution=`, `GET /validation-errors/summary`, `GET /config/sensor-limits`, `PUT /config/sensor-limits/{field}`.

- [ ] **Step 1: Write `system.js`**

```javascript
window.SystemView = (function () {
  let running = false;
  let timerId = null;
  let resourceChart = null;
  let ingestChart = null;
  let growthChart = null;

  async function renderServices() {
    try {
      const sys = await Api.get("/system");
      document.getElementById("warning-count").hidden = sys.warnings.length === 0;
      document.getElementById("warning-count").textContent = sys.warnings.length + " warning(s)";

      const s = sys.services;
      document.getElementById("system-services").innerHTML = `
        <div class="card"><div class="label">API</div><div class="value">${s.api}</div></div>
        <div class="card"><div class="label">Database</div><div class="value">${s.database}</div></div>
        <div class="card"><div class="label">Aggregate job</div><div class="value">${s.aggregate_job.status}</div><div class="as-of">last run ${s.aggregate_job.last_run}</div></div>
        <div class="card"><div class="label">Retention job</div><div class="value">${s.retention_job.status}</div><div class="as-of">last run ${s.retention_job.last_run}</div></div>
      `;

      document.getElementById("system-database").innerHTML = `
        <div class="card"><div class="label">Size</div><div class="value">${sys.database.size_mb.toFixed(1)} MB</div></div>
        <div class="card"><div class="label">Rows</div><div class="value">${sys.database.row_count.toLocaleString()}</div></div>
        <div class="card"><div class="label">Growth/day</div><div class="value">${sys.database.growth_mb_per_day.toFixed(1)} MB</div></div>
        <div class="card"><div class="label">Capacity left</div><div class="value">${sys.database.projected_days_remaining} days</div></div>
      `;

      const warn = code => sys.warnings.some(w => w.metric === code);
      const limit = code => (sys.warnings.find(w => w.metric === code) || {}).limit ?? window.CONFIG.FALLBACK_LIMITS[code];
      document.getElementById("system-metric-cards").innerHTML = `
        <div class="card ${warn("cpu_load_percent") ? "card--warning" : ""}"><div class="label">CPU load</div><div class="value">${sys.cpu_load_percent}%</div></div>
        <div class="card ${warn("cpu_temperature_c") ? "card--warning" : ""}"><div class="label">CPU temp</div><div class="value">${sys.cpu_temperature_c} °C</div></div>
        <div class="card ${warn("memory_used_percent") ? "card--warning" : ""}"><div class="label">Memory</div><div class="value">${sys.memory.used_percent}%</div></div>
        <div class="card ${warn("disk_used_percent") ? "card--warning" : ""}"><div class="label">Disk</div><div class="value">${sys.disk.used_percent}%</div></div>
      `;
      return sys;
    } catch (err) {
      document.getElementById("health-badge").textContent = "api down";
      document.getElementById("health-badge").className = "badge badge-offline";
      return null;
    }
  }

  async function renderRejected() {
    try {
      const summary = await Api.get("/validation-errors/summary", { window: "24h" });
      document.getElementById("system-rejected").innerHTML = `
        <div class="card"><div class="label">Rejected (24h)</div><div class="value">${summary.total}</div></div>
        ${Object.entries(summary.by_code).map(([code, count]) => `<div class="card"><div class="label">${code}</div><div class="value">${count}</div></div>`).join("")}
      `;
    } catch (err) { /* keep last render */ }
  }

  async function renderCharts(sys) {
    try {
      const end = new Date().toISOString();
      const start = new Date(Date.now() - 6 * 3600 * 1000).toISOString();
      const history = await Api.get("/system/history", { start, end, resolution: "auto" });

      const resEl = document.getElementById("system-resource-chart");
      if (!resEl.querySelector("canvas")) resEl.innerHTML = "<canvas></canvas>";
      const cpuTempThreshold = (sys && sys.warnings.length && sys.warnings[0].limit) || window.CONFIG.FALLBACK_LIMITS.cpu_temperature_c;
      const resPoints = history.points.map(p => ({ x: p.sampled_at, cpu: p.cpu_temperature_c, load: p.cpu_load_percent, mem: p.memory_used_percent }));
      if (resourceChart) resourceChart.destroy();
      resourceChart = new Chart(resEl.querySelector("canvas"), {
        type: "line",
        data: {
          datasets: [
            { label: "CPU temp (°C)", data: resPoints.map(p => ({ x: p.x, y: p.cpu })), borderColor: "#d9534f" },
            { label: "CPU load (%)", data: resPoints.map(p => ({ x: p.x, y: p.load })), borderColor: "#2563eb" },
            { label: "Memory (%)", data: resPoints.map(p => ({ x: p.x, y: p.mem })), borderColor: "#16a34a" }
          ]
        },
        options: { parsing: false, scales: { x: Charts.timeAxisOptions() } },
        plugins: [Charts.thresholdLinePlugin(cpuTempThreshold, "throttle limit")]
      });

      const ingestEl = document.getElementById("system-ingest-chart");
      if (!ingestEl.querySelector("canvas")) ingestEl.innerHTML = "<canvas></canvas>";
      const zeroBands = [];
      let bandStart = null;
      history.points.forEach((p, i) => {
        if (p.ingest_rate_per_min === 0 && bandStart === null) bandStart = p.sampled_at;
        if (p.ingest_rate_per_min !== 0 && bandStart !== null) { zeroBands.push({ start: bandStart, end: p.sampled_at }); bandStart = null; }
        if (i === history.points.length - 1 && bandStart !== null) zeroBands.push({ start: bandStart, end: p.sampled_at });
      });
      if (ingestChart) ingestChart.destroy();
      ingestChart = new Chart(ingestEl.querySelector("canvas"), {
        type: "line",
        data: { datasets: [{ label: "Ingest rate/min", data: history.points.map(p => ({ x: p.sampled_at, y: p.ingest_rate_per_min })), borderColor: "#9333ea" }] },
        options: { parsing: false, scales: { x: Charts.timeAxisOptions() } },
        plugins: [Charts.shadeBandsPlugin(zeroBands, "rgba(147,51,234,0.12)")]
      });

      const growthEl = document.getElementById("system-growth-chart");
      if (!growthEl.querySelector("canvas")) growthEl.innerHTML = "<canvas></canvas>";
      const actual = history.points.map(p => ({ x: p.sampled_at, y: p.database_size_mb }));
      const projected = sys ? buildProjection(actual, sys.database.growth_mb_per_day) : [];
      if (growthChart) growthChart.destroy();
      growthChart = new Chart(growthEl.querySelector("canvas"), {
        type: "line",
        data: {
          datasets: [
            { label: "DB size (MB)", data: actual, borderColor: "#2563eb" },
            { label: "Projected", data: projected, borderColor: "#94a3b8", borderDash: [6, 4] }
          ]
        },
        options: { parsing: false, scales: { x: Charts.timeAxisOptions() } }
      });
    } catch (err) { /* keep last render */ }
  }

  function buildProjection(actualPoints, growthPerDay) {
    if (!actualPoints.length) return [];
    const last = actualPoints[actualPoints.length - 1];
    const points = [last];
    for (let days = 1; days <= 30; days++) {
      points.push({ x: new Date(new Date(last.x).getTime() + days * 86400000).toISOString(), y: last.y + growthPerDay * days });
    }
    return points;
  }

  async function renderLimitEditor() {
    try {
      const limits = await Api.get("/config/sensor-limits");
      const el = document.getElementById("system-limit-editor");
      el.innerHTML = Object.entries(limits).map(([field, { min, max, updated_at }]) => `
        <div class="limit-row" data-field="${field}">
          <span>${field}</span>
          <input type="number" class="min-input" value="${min}">
          <input type="number" class="max-input" value="${max}">
          <span class="updated-at">updated ${updated_at}</span>
          <button class="save-limit">Save</button>
          <span class="field-error"></span>
        </div>
      `).join("");
      el.querySelectorAll(".save-limit").forEach(btn => {
        btn.addEventListener("click", async () => {
          const row = btn.closest(".limit-row");
          const field = row.dataset.field;
          const min = parseFloat(row.querySelector(".min-input").value);
          const max = parseFloat(row.querySelector(".max-input").value);
          const errorEl = row.querySelector(".field-error");
          errorEl.textContent = "";
          try {
            const updated = await Api.put(`/config/sensor-limits/${field}`, { min, max });
            row.querySelector(".updated-at").textContent = "updated " + updated.updated_at;
          } catch (err) {
            errorEl.textContent = err.message;
          }
        });
      });
    } catch (err) { /* keep last render */ }
  }

  async function poll() {
    if (!running) return;
    const sys = await renderServices();
    await Promise.all([renderRejected(), renderCharts(sys)]);
    timerId = setTimeout(poll, window.CONFIG.POLL_MS.system);
  }

  async function start() {
    running = true;
    await renderLimitEditor();
    poll();
  }

  function stop() {
    running = false;
    clearTimeout(timerId);
  }

  return { start, stop };
})();
```

- [ ] **Step 2: Manual verification**

Open the System tab in Chrome and confirm over ~10 seconds: services/database/rejected panels populate, the four metric cards update every 5s and a card turns into the warning style when its metric is in `sys.warnings` (temporarily lower `CPU_TEMP_WARNING_C` in the backend `.env` if nothing is naturally over threshold, restart the backend, observe, then revert), the resource chart draws the throttle-limit reference line, the ingest-rate chart shades zero-rate periods, the growth chart shows a dashed projection past the last real point. In the sensor-limit editor, edit one field's min/max, save, and confirm the row's `updated_at` refreshes; then submit an invalid pair (`min` ≥ `max`) and confirm the inline error appears on that row only, other rows unaffected. Screenshot the view.

- [ ] **Step 3: Commit**

```bash
git add rover-telemetry-frontend/public/js/system.js
git commit -m "feat: implement system view with resource charts, warnings, and sensor-limit editor"
```

---

### Task 7: Cross-view error handling pass and verification log

**Files:**
- Modify: `rover-telemetry-frontend/public/js/live.js`, `history.js`, `system.js` (only if gaps are found in Steps 1–2 below — no speculative changes)
- Create: `rover-telemetry-frontend/docs/2026-09-08-verification-log.md`

- [ ] **Step 1: Verify shared error-handling rules from design doc §7**

With the backend running, exercise these against the live app in Chrome and note pass/fail for each:
1. Stop the backend (kill the PHP server) while the Live tab is open — confirm the header badge flips to `api down` within one poll cycle and each panel keeps showing its last-successful content rather than clearing.
2. Restart the backend — confirm the badge flips back to `api ok · db ok` automatically on the next poll, with no manual reload.
3. On History, request a rover with no data in range — confirm the chart/table show an empty state, not a thrown error in the console.
4. On Live, select a `device_uid` that has never reported (or a fresh test rover) — confirm the 404 on `/latest` renders the explicit empty-state message from `live.js`'s `renderMetricCards` catch branch, not a generic error banner.

- [ ] **Step 2: Fix any gap found in Step 1**

If any check fails, fix the minimal code in the relevant view file only (e.g. add a "stale since HH:MM:SS" indicator if one is missing — the design doc requires this in §7 but the view implementations above only implement "keep last render," not the stale-since label; add a `lastSuccessAt` timestamp per view and render it in the header or panel when a poll fails).

- [ ] **Step 3: Write the verification log**

```markdown
# Rover Telemetry Frontend — Verification Log
Date: 2026-09-08

Manual checks performed against the local backend (no automated UI test harness, per design doc §8):

- [ ] Live view: fleet list, metric cards, telemetry chart, distance chart, readings table, sensor-limit bars, events list
- [ ] History view: range presets, resolution override, sensor toggle, gap list, CSV export, JSON export
- [ ] System view: services/database/rejected panels, warning-state styling, resource/ingest/growth charts, sensor-limit editor save + validation error
- [ ] Shared error handling: api-down badge, auto-recovery, empty state for never-reported rover, stale-since indicator on failed poll
- [ ] Responsive: single-column stacking below 700px on all three views

Record actual results (pass/fail + screenshot reference) for each line above.
```

Fill in the actual pass/fail results from Steps 1–2 and from the verification steps in Tasks 3–6 before committing.

- [ ] **Step 4: Commit**

```bash
git add rover-telemetry-frontend/docs/2026-09-08-verification-log.md rover-telemetry-frontend/public/js
git commit -m "fix: add stale-since indicators and record manual verification results"
```

---

## Self-Review Notes

- **Spec coverage:** §1 scope (3 views, no Cockpit) → Tasks 4–6, no Cockpit file created. §2 delivery constraints → Global Constraints + Task 1 (vendoring) + Task 1 (`setTimeout` chains). §3 file layout → File Structure section, matches exactly. §4 Live → Task 4. §5 History → Task 5. §6 System → Task 6. §7 shared error handling → Task 7. §8 testing → Global Constraints (no test framework) + every task's manual verification step + Task 7's log. §9 out of scope → no Cockpit/auth/media code anywhere in the plan.
- **Placeholder scan:** all code steps contain runnable code, not TODOs; the one deliberately deferred item (Live view's rejected-row-in-table nuance, Task 4 Step 2) is called out explicitly with the reasoning, not silently glossed over.
- **Type/name consistency:** `Api.get/put`, `Charts.buildAvgMinMaxDataset/thresholdLinePlugin/shadeBandsPlugin/timeAxisOptions`, and `CONFIG.API_BASE_URL/POLL_MS/FALLBACK_LIMITS` are defined in Tasks 1–2 and used with identical names/signatures in Tasks 4–6. DOM ids defined in Task 3's skeleton match the ids each view script queries.
