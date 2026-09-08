# Rover Telemetry Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Live / History / System reference dashboard (backend design proposal §11) as a static HTML/CSS/vanilla-JS site under `rover-telemetry-frontend/public/`, driven entirely by the already-implemented `rover-telemetry-backend` REST API.

**Architecture:** One `index.html` tab shell with three view modules (`live.js`, `history.js`, `system.js`), each exposing `mount(el)` / `start()` / `stop()`. A shared `api.js` wraps `fetch` against `/api/v1`, and a shared `charts.js` wraps Chart.js for the line+band / threshold-line / shaded-band chart patterns every view reuses. No build step, no framework, no bundler — files are loaded as plain `<script>` tags in dependency order.

**Tech Stack:** HTML5, CSS3, vanilla ES2017+ JavaScript, Chart.js (vendored UMD build, no CDN, no time-scale adapter — x-axes use pre-formatted string labels, not a `time` scale, so no `chartjs-adapter-date-fns` dependency is needed).

**Spec:** `docs/superpowers/specs/2026-09-08-rover-telemetry-dashboard-design.md`

## Global Constraints

- No build step, no Node toolchain, no npm packages — every third-party file is vendored under `rover-telemetry-frontend/public/vendor/` and loaded via `<script src="...">`.
- Chart.js loaded from a local vendored file, never a CDN.
- Polling: 1 s on Live, 5 s on System, on-demand on History. Every poll loop re-arms with `setTimeout` after its `fetch` resolves (success or failure) — never `setInterval`.
- No authentication (matches the API's current state).
- Single-column layout below 700px (CSS media query, no JS).
- Cockpit/teleoperation is out of scope — no tab, no code for it.
- `config.js` is the only file containing the API's base URL; nothing else hard-codes a host or port.
- **Test strategy for this project (per spec §8):** there is no JS test runner (introducing one would be a bigger change than this dashboard justifies). Each task's "test" step is: (a) a `curl` against the real local backend showing the exact JSON shape the code must handle, and (b) a Chrome-browser check (via `mcp__claude-in-chrome__*` tools) that reloads the page, exercises the new UI, and confirms rendered values match what `curl` returned. Do this instead of writing `*.test.js` files.
- The local backend for all manual verification in this plan is already running and reachable at:
  `http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1`
  It has real historical data for `rover-001` (and several `loadtest-rover-*` / `rover-sim-001` devices) from prior load tests — no seeding step is needed.
- Every `git commit` in this plan runs from `C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard` (the dashboard worktree), on branch `feat/rover-telemetry-dashboard`.

## Shared interfaces (defined in Task 2–4, consumed by every later task)

```js
// api.js — window.Api
Api.health()                              // GET /health
Api.rovers()                              // GET /rovers
Api.latest(uid)                           // GET /rovers/{uid}/latest
Api.readings(uid, params)                 // GET /rovers/{uid}/readings?<params>
Api.summary(uid, params)                  // GET /rovers/{uid}/summary?<params>
Api.events(uid, params)                   // GET /rovers/{uid}/events?<params>
Api.validationErrorsSummary(windowStr)    // GET /validation-errors/summary?window=<windowStr>
Api.sensorLimits()                        // GET /config/sensor-limits
Api.putSensorLimit(field, {min, max})     // PUT /config/sensor-limits/{field}
Api.system()                              // GET /system
Api.systemHistory(params)                 // GET /system/history?<params>
Api.exportUrl(uid, params)                // -> string URL (not fetched, used as a download href)
// All of the above except exportUrl return a Promise resolving to the parsed JSON body,
// or rejecting with {code, message, request_id} (request_id may be null on network failure).

// charts.js — window.Charts
Charts.lineWithBand({ canvasId, labels, avg, min, max, avgLabel, colorRgb }) -> Chart instance
Charts.thresholdDataset(label, value, count, colorRgb) -> Chart.js dataset object
Charts.bandDataset(label, flags, yMax, colorRgba) -> Chart.js dataset object (bar type, for shading)
Charts.updateChart(chart, labels, datasetsData) // datasetsData: array of arrays, one per existing dataset, in order

// Each view module — window.LiveView / window.HistoryView / window.SystemView
View.mount(el)   // build DOM once, cache element refs, wire static (non-polling) listeners
View.start()     // begin/resume polling; idempotent — calling twice does not double the timers
View.stop()      // cancel any pending setTimeout; safe to call even if not started
```

---

### Task 1: Project scaffold — vendor Chart.js, HTML shell, base CSS, config

**Files:**
- Create: `rover-telemetry-frontend/public/vendor/chart.js`
- Create: `rover-telemetry-frontend/public/index.html`
- Create: `rover-telemetry-frontend/public/css/style.css`
- Create: `rover-telemetry-frontend/public/js/config.js`

**Interfaces:**
- Produces: `window.APP_CONFIG` (`API_BASE_URL`, `POLL_INTERVAL_LIVE_MS`, `POLL_INTERVAL_SYSTEM_MS`, `ONLINE_THRESHOLD_SECONDS`, `DEGRADED_THRESHOLD_SECONDS`), the `index.html` tab shell with `#view-live` / `#view-history` / `#view-system` sections and `.tab-btn` buttons, and `css/style.css`'s base layout classes (`.app-header`, `.tabs`, `.tab-btn`, `.view`, `.card`, `.card-grid`).

- [ ] **Step 1: Download and vendor Chart.js**

```bash
curl -sL "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.js" \
  -o "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard/rover-telemetry-frontend/public/vendor/chart.js"
```

- [ ] **Step 2: Verify the vendored file is a real UMD build**

Run: `node -e "const fs=require('fs'); const s=fs.readFileSync('C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard/rover-telemetry-frontend/public/vendor/chart.js','utf8'); console.log(s.length, s.slice(0,60));"`
Expected: a length over 100000 and output starting with something like `/*!\n * Chart.js v4.4.4`. If the download failed (e.g. an HTML error page was saved instead), the length will be a few hundred bytes — re-run Step 1 and check network access.

- [ ] **Step 3: Write `config.js`**

```js
window.APP_CONFIG = {
  API_BASE_URL: '/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1',
  POLL_INTERVAL_LIVE_MS: 1000,
  POLL_INTERVAL_SYSTEM_MS: 5000,
  ONLINE_THRESHOLD_SECONDS: 15,
  DEGRADED_THRESHOLD_SECONDS: 60,
};
```

- [ ] **Step 4: Write `index.html`**

```html
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rover Telemetry</title>
<link rel="stylesheet" href="css/style.css">
</head>
<body>
<header class="app-header">
  <div class="brand">ROVER TELEMETRY</div>
  <nav class="tabs">
    <button class="tab-btn active" data-tab="live">LIVE</button>
    <button class="tab-btn" data-tab="history">HISTORY</button>
    <button class="tab-btn" data-tab="system">SYSTEM</button>
  </nav>
  <div class="health-badge" id="health-badge">checking…</div>
</header>

<main>
  <section id="view-live" class="view active"></section>
  <section id="view-history" class="view"></section>
  <section id="view-system" class="view"></section>
</main>

<script src="vendor/chart.js"></script>
<script src="js/config.js"></script>
<script src="js/api.js"></script>
<script src="js/charts.js"></script>
<script src="js/live.js"></script>
<script src="js/history.js"></script>
<script src="js/system.js"></script>
<script src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Write base `css/style.css`**

```css
:root {
  color-scheme: light;
  --bg: #f4f5f7;
  --panel: #ffffff;
  --border: #d9dce1;
  --text: #1c2128;
  --text-dim: #5b6270;
  --accent: #2f6fed;
  --ok: #1a7f37;
  --warn: #b35900;
  --bad: #cf222e;
  --font: "Segoe UI", -apple-system, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--font); font-size: 14px; }

.app-header {
  display: flex; align-items: center; gap: 24px;
  padding: 10px 20px; background: var(--panel); border-bottom: 1px solid var(--border);
}
.app-header .brand { font-weight: 700; letter-spacing: 0.05em; }
.tabs { display: flex; gap: 4px; flex: 1; }
.tab-btn {
  background: transparent; border: none; padding: 8px 14px; border-radius: 4px;
  font-weight: 600; letter-spacing: 0.03em; color: var(--text-dim); cursor: pointer;
}
.tab-btn.active { background: var(--accent); color: #fff; }
.health-badge { font-size: 12px; color: var(--text-dim); }
.health-badge.down { color: var(--bad); font-weight: 700; }

main { padding: 16px 20px; }
.view { display: none; }
.view.active { display: block; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.card {
  background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px;
}
.card .card-label { font-size: 11px; letter-spacing: 0.06em; color: var(--text-dim); text-transform: uppercase; }
.card .card-value { font-size: 26px; font-weight: 700; margin-top: 4px; }
.card .card-sub { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
.card.warn { border-color: var(--warn); }
.card.bad { border-color: var(--bad); }

.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px; margin-top: 12px; }
.panel-title { font-size: 12px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 8px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid var(--border); }
tr.rejected td { color: #9096a2; }

.error-banner { background: #fdeceb; border: 1px solid var(--bad); color: var(--bad); padding: 6px 10px; border-radius: 4px; font-size: 12px; margin-bottom: 8px; }
.stale-banner { background: #fff6e5; border: 1px solid var(--warn); color: var(--warn); padding: 6px 10px; border-radius: 4px; font-size: 12px; margin-bottom: 8px; }

@media (max-width: 700px) {
  .app-header { flex-wrap: wrap; }
  .card-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 6: Verify the shell loads without errors**

Open `http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-frontend/public/index.html` with the Chrome browser tool, take a screenshot, and read console messages (`mcp__claude-in-chrome__read_console_messages`). Expected: header with three tab buttons and "checking…" badge visible, and console shows only the expected errors from missing `js/api.js` etc. (those are created in later tasks) — no Chart.js load error.

- [ ] **Step 7: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/vendor/chart.js rover-telemetry-frontend/public/index.html rover-telemetry-frontend/public/css/style.css rover-telemetry-frontend/public/js/config.js
git commit -m "feat: scaffold dashboard shell, vendor Chart.js, base config"
```

---

### Task 2: `api.js` — fetch wrapper for all backend endpoints

**Files:**
- Create: `rover-telemetry-frontend/public/js/api.js`

**Interfaces:**
- Consumes: `window.APP_CONFIG.API_BASE_URL` (Task 1).
- Produces: `window.Api` with the full method list in "Shared interfaces" above.

- [ ] **Step 1: Confirm the real API shapes this wrapper must handle**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/health"
curl -s "$BASE/rovers/does-not-exist/latest"
```
Expected: `health` returns `{"status":"ok","database":"ok","api":"ok","uptime_seconds":...}`; the unknown rover returns HTTP 404 with body `{"error":{"code":"NOT_FOUND","message":"...","request_id":"..."}}`.

- [ ] **Step 2: Write `api.js`**

```js
window.Api = (function () {
  function buildQuery(params) {
    const usp = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        usp.set(key, value);
      }
    });
    const qs = usp.toString();
    return qs ? `?${qs}` : '';
  }

  async function request(path, options) {
    const url = `${window.APP_CONFIG.API_BASE_URL}${path}`;
    let response;
    try {
      response = await fetch(url, options || {});
    } catch (networkError) {
      throw { code: 'NETWORK_ERROR', message: networkError.message, request_id: null };
    }
    const contentType = response.headers.get('content-type') || '';
    const body = contentType.includes('application/json') ? await response.json() : null;
    if (!response.ok) {
      throw (body && body.error) || { code: 'UNKNOWN_ERROR', message: `HTTP ${response.status}`, request_id: null };
    }
    return body;
  }

  function jsonBody(data) {
    return { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
  }

  return {
    health: () => request('/health'),
    rovers: () => request('/rovers'),
    latest: (uid) => request(`/rovers/${uid}/latest`),
    readings: (uid, params) => request(`/rovers/${uid}/readings${buildQuery(params)}`),
    summary: (uid, params) => request(`/rovers/${uid}/summary${buildQuery(params)}`),
    events: (uid, params) => request(`/rovers/${uid}/events${buildQuery(params)}`),
    validationErrorsSummary: (windowStr) => request(`/validation-errors/summary${buildQuery({ window: windowStr })}`),
    sensorLimits: () => request('/config/sensor-limits'),
    putSensorLimit: (field, minMax) => request(`/config/sensor-limits/${field}`, jsonBody(minMax)),
    system: () => request('/system'),
    systemHistory: (params) => request(`/system/history${buildQuery(params)}`),
    exportUrl: (uid, params) => `${window.APP_CONFIG.API_BASE_URL}/rovers/${uid}/export${buildQuery(params)}`,
  };
})();
```

- [ ] **Step 3: Verify in the browser console**

Reload `index.html` in Chrome, open the console via `mcp__claude-in-chrome__javascript_tool`, and run:
```js
Api.health().then(r => console.log('health', r));
Api.rovers().then(r => console.log('rovers', r));
Api.latest('does-not-exist').catch(e => console.log('expected-error', e));
```
Expected: `health` logs `{status: "ok", ...}`; `rovers` logs an array of rover objects; `expected-error` logs an object with `code: "NOT_FOUND"`.

- [ ] **Step 4: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/api.js
git commit -m "feat: add api.js fetch wrapper for backend endpoints"
```

---

### Task 3: `app.js` — tab switching, header health badge, view lifecycle wiring

**Files:**
- Create: `rover-telemetry-frontend/public/js/app.js`
- Modify: `rover-telemetry-frontend/public/js/live.js` (create as a stub — full implementation is Tasks 5–9)
- Modify: `rover-telemetry-frontend/public/js/history.js` (create as a stub — full implementation is Tasks 10–12)
- Modify: `rover-telemetry-frontend/public/js/system.js` (create as a stub — full implementation is Tasks 13–15)

**Interfaces:**
- Consumes: `Api.health()` (Task 2); `LiveView`/`HistoryView`/`SystemView` `.mount(el)` / `.start()` / `.stop()` (this task defines the stub shape every later task fills in).
- Produces: working tab switching and a live `#health-badge`, so every later task can be verified against a functioning shell.

- [ ] **Step 1: Write stub view modules**

```js
// live.js
window.LiveView = (function () {
  let el;
  function mount(rootEl) { el = rootEl; el.textContent = 'Live view (not yet implemented)'; }
  function start() {}
  function stop() {}
  return { mount, start, stop };
})();
```
```js
// history.js
window.HistoryView = (function () {
  let el;
  function mount(rootEl) { el = rootEl; el.textContent = 'History view (not yet implemented)'; }
  function start() {}
  function stop() {}
  return { mount, start, stop };
})();
```
```js
// system.js
window.SystemView = (function () {
  let el;
  function mount(rootEl) { el = rootEl; el.textContent = 'System view (not yet implemented)'; }
  function start() {}
  function stop() {}
  return { mount, start, stop };
})();
```

- [ ] **Step 2: Write `app.js`**

```js
(function () {
  const views = { live: window.LiveView, history: window.HistoryView, system: window.SystemView };
  let activeTab = 'live';

  function activateTabButton(tab, isActive) {
    document.getElementById(`view-${tab}`).classList.toggle('active', isActive);
    document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.toggle('active', isActive);
  }

  function switchTab(tab) {
    if (tab === activeTab) return;
    views[activeTab].stop();
    activateTabButton(activeTab, false);
    activeTab = tab;
    activateTabButton(activeTab, true);
    views[activeTab].start();
  }

  function pollHealth() {
    Api.health()
      .then((data) => {
        const badge = document.getElementById('health-badge');
        badge.textContent = `api ${data.api} · db ${data.database}`;
        badge.classList.toggle('down', data.status !== 'ok');
      })
      .catch(() => {
        const badge = document.getElementById('health-badge');
        badge.textContent = 'api down';
        badge.classList.add('down');
      })
      .finally(() => setTimeout(pollHealth, window.APP_CONFIG.POLL_INTERVAL_SYSTEM_MS));
  }

  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  views.live.mount(document.getElementById('view-live'));
  views.history.mount(document.getElementById('view-history'));
  views.system.mount(document.getElementById('view-system'));

  views[activeTab].start();
  pollHealth();
})();
```

- [ ] **Step 3: Verify tab switching and health badge in the browser**

Reload `index.html` in Chrome. Screenshot, then click the HISTORY tab, screenshot again, then SYSTEM, screenshot again. Expected: each screenshot shows the corresponding stub text and the clicked tab highlighted; the health badge reads `api ok · db ok` within 5 seconds (cross-check with `curl http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1/health`).

- [ ] **Step 4: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/app.js rover-telemetry-frontend/public/js/live.js rover-telemetry-frontend/public/js/history.js rover-telemetry-frontend/public/js/system.js
git commit -m "feat: add tab switching, health badge, and view module stubs"
```

---

### Task 4: `charts.js` — shared Chart.js helpers

**Files:**
- Create: `rover-telemetry-frontend/public/js/charts.js`
- Modify: `rover-telemetry-frontend/public/index.html:19` (add `<script src="js/charts.js"></script>` before `live.js`)

**Interfaces:**
- Consumes: global `Chart` (from vendored `chart.js`, Task 1).
- Produces: `window.Charts` with `lineWithBand`, `thresholdDataset`, `bandDataset`, `updateChart` (see "Shared interfaces" above).

- [ ] **Step 1: Write `charts.js`**

```js
window.Charts = (function () {
  function lineWithBand({ canvasId, labels, avg, min, max, avgLabel, colorRgb }) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: `${avgLabel} max`, data: max, borderWidth: 0, pointRadius: 0, fill: '+1', backgroundColor: `rgba(${colorRgb},0.15)`, spanGaps: false },
          { label: `${avgLabel} min`, data: min, borderWidth: 0, pointRadius: 0, fill: false, spanGaps: false },
          { label: avgLabel, data: avg, borderColor: `rgb(${colorRgb})`, backgroundColor: `rgb(${colorRgb})`, borderWidth: 2, pointRadius: 0, spanGaps: false },
        ],
      },
      options: {
        responsive: true,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: { x: { ticks: { maxTicksLimit: 8 } }, y: { beginAtZero: false } },
      },
    });
  }

  function thresholdDataset(label, value, count, colorRgb) {
    return { label, data: new Array(count).fill(value), borderColor: `rgb(${colorRgb})`, borderDash: [6, 4], borderWidth: 1, pointRadius: 0 };
  }

  function bandDataset(label, flags, yMax, colorRgba) {
    return {
      type: 'bar', label, data: flags.map((flag) => (flag ? yMax : 0)),
      backgroundColor: colorRgba, barPercentage: 1.0, categoryPercentage: 1.0, order: 5,
    };
  }

  function updateChart(chart, labels, datasetsData) {
    chart.data.labels = labels;
    datasetsData.forEach((data, i) => { chart.data.datasets[i].data = data; });
    chart.update('none');
  }

  return { lineWithBand, thresholdDataset, bandDataset, updateChart };
})();
```

- [ ] **Step 2: Add the script tag**

In `index.html`, insert `<script src="js/charts.js"></script>` immediately before `<script src="js/live.js"></script>`.

- [ ] **Step 3: Verify with a throwaway chart in the browser console**

Reload the page in Chrome, then in the console (`mcp__claude-in-chrome__javascript_tool`):
```js
document.querySelector('#view-live').innerHTML = '<canvas id="test-canvas" width="400" height="200"></canvas>';
const c = Charts.lineWithBand({ canvasId: 'test-canvas', labels: ['a','b','c'], avg: [1,2,3], min: [0,1,2], max: [2,3,4], avgLabel: 'Test', colorRgb: '47,111,237' });
console.log('chart created', !!c);
```
Screenshot afterward. Expected: `chart created true` logged and a visible line-with-band chart rendered in the Live tab area.

- [ ] **Step 4: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/charts.js rover-telemetry-frontend/public/index.html
git commit -m "feat: add shared Chart.js helpers (line+band, threshold, shaded band)"
```

---

### Task 5: Live view — fleet list, rover selection, rejected-payload sidebar

**Files:**
- Modify: `rover-telemetry-frontend/public/js/live.js` (replace the Task 3 stub)
- Modify: `rover-telemetry-frontend/public/css/style.css` (append Live-view-specific layout rules)

**Interfaces:**
- Consumes: `Api.rovers()`, `Api.validationErrorsSummary(windowStr)` (Task 2).
- Produces: `LiveView` now tracks `LiveView._selectedRover` internally (read by Tasks 6–9 through the DOM, not a public getter — each later task's poll functions read the currently-highlighted `.fleet-item.selected`'s `data-uid`).

- [ ] **Step 1: Confirm the real fleet-list and validation-summary shapes**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers"
curl -s "$BASE/validation-errors/summary?window=24h"
```
Expected: `rovers` is an array of `{device_uid, name, firmware_version, last_reading_at, status}`; `validation-errors/summary` is `{"window":"24h","total":<n>,"by_code":{"OUT_OF_RANGE":<n>, ...}}`.

- [ ] **Step 2: Write the Live view's HTML template and mount/fleet logic**

```js
window.LiveView = (function () {
  let el;
  let pollTimer = null;
  let selectedUid = null;

  const TEMPLATE = `
    <div class="live-layout">
      <aside class="live-rail">
        <div class="panel">
          <div class="panel-title">Fleet</div>
          <div id="fleet-list"></div>
        </div>
        <div class="panel">
          <div class="panel-title">Rejected payloads · 24h</div>
          <div class="card-value" id="rejected-total">–</div>
          <div class="card-sub" id="rejected-by-code"></div>
        </div>
      </aside>
      <div class="live-main" id="live-main">
        <div id="live-error-banner"></div>
        <p>Select a rover from the fleet list.</p>
      </div>
    </div>
  `;

  function statusDotClass(status) {
    if (status === 'ONLINE') return 'dot-ok';
    if (status === 'DEGRADED') return 'dot-warn';
    return 'dot-bad';
  }

  function ageLabel(lastReadingAt) {
    if (!lastReadingAt) return 'never reported';
    const seconds = Math.max(0, (Date.now() - new Date(lastReadingAt).getTime()) / 1000);
    if (seconds < 60) return `${seconds.toFixed(1)} s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    return `${Math.floor(seconds / 3600)} h ago`;
  }

  function renderFleet(rovers) {
    const list = document.getElementById('fleet-list');
    list.innerHTML = rovers.map((r) => `
      <div class="fleet-item ${r.device_uid === selectedUid ? 'selected' : ''}" data-uid="${r.device_uid}">
        <span class="dot ${statusDotClass(r.status)}"></span>
        <span class="fleet-uid">${r.device_uid}</span>
        <span class="fleet-status">${r.status} · ${ageLabel(r.last_reading_at)}</span>
      </div>
    `).join('');
    list.querySelectorAll('.fleet-item').forEach((item) => {
      item.addEventListener('click', () => selectRover(item.dataset.uid));
    });
    if (!selectedUid && rovers.length > 0) {
      selectRover(rovers[0].device_uid);
    }
  }

  function selectRover(uid) {
    selectedUid = uid;
    document.querySelectorAll('.fleet-item').forEach((item) => {
      item.classList.toggle('selected', item.dataset.uid === uid);
    });
    if (window.LiveView && window.LiveView.onRoverSelected) {
      window.LiveView.onRoverSelected(uid);
    }
  }

  function showError(message) {
    document.getElementById('live-error-banner').innerHTML = `<div class="error-banner">${message}</div>`;
  }

  function clearError() {
    document.getElementById('live-error-banner').innerHTML = '';
  }

  function pollFleetAndRejects() {
    Promise.all([Api.rovers(), Api.validationErrorsSummary('24h')])
      .then(([rovers, rejects]) => {
        clearError();
        renderFleet(rovers);
        document.getElementById('rejected-total').textContent = rejects.total;
        document.getElementById('rejected-by-code').textContent = Object.entries(rejects.by_code)
          .map(([code, count]) => `${code} ${count}`).join(' · ');
      })
      .catch((err) => showError(`Fleet list unavailable: ${err.message || err.code}`))
      .finally(() => { pollTimer = setTimeout(pollFleetAndRejects, window.APP_CONFIG.POLL_INTERVAL_LIVE_MS); });
  }

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;
  }

  function start() {
    if (pollTimer) return;
    pollFleetAndRejects();
  }

  function stop() {
    clearTimeout(pollTimer);
    pollTimer = null;
  }

  function getSelectedUid() {
    return selectedUid;
  }

  return { mount, start, stop, getSelectedUid, onRoverSelected: null };
})();
```

- [ ] **Step 3: Append Live-view CSS**

```css
.live-layout { display: grid; grid-template-columns: 240px 1fr; gap: 16px; }
.live-rail .fleet-item { display: flex; align-items: center; gap: 8px; padding: 6px 4px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.live-rail .fleet-item.selected { background: #eaf0fe; }
.live-rail .fleet-uid { font-weight: 600; }
.live-rail .fleet-status { margin-left: auto; color: var(--text-dim); font-size: 11px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-ok { background: var(--ok); }
.dot-warn { background: var(--warn); }
.dot-bad { background: var(--bad); }
@media (max-width: 700px) {
  .live-layout { grid-template-columns: 1fr; }
}
```

- [ ] **Step 4: Verify in the browser**

Reload `index.html`, screenshot the Live tab. Expected: fleet list shows all rovers from `curl .../rovers` with correct status dots and ages, the first rover auto-selected, and the rejected-payload sidebar numbers matching `curl .../validation-errors/summary?window=24h`. Click a different fleet row and screenshot again — expected: selection highlight moves.

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/live.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(live): add fleet list, rover selection, rejected-payload sidebar"
```

---

### Task 6: Live view — five metric cards with degraded/offline rendering

**Files:**
- Modify: `rover-telemetry-frontend/public/js/live.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.latest(uid)`, `Api.summary(uid, params)` (for today's min/max) (Task 2); `LiveView.onRoverSelected` hook (Task 5) to restart the card poll loop on selection change.

- [ ] **Step 1: Confirm the real `/latest` and `/summary` shapes**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers/rover-001/latest"
curl -s "$BASE/rovers/rover-001/summary?granularity=day&start=$(date -u +%Y-%m-%d)&end=$(date -u +%Y-%m-%d)"
```
Expected: `latest` is `{device_uid, recorded_at, age_seconds, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake}` (any sensor field may be `null`); `summary` for a day with no data yet is `{"device_uid":"...","granularity":"day","buckets":[]}` — the cards must handle an empty `buckets` array by showing `– / –` for today's min/max.

- [ ] **Step 2: Add the metric-cards template and rendering**

In `live.js`, change the `TEMPLATE`'s `live-main` div to:
```html
<div class="live-main" id="live-main">
  <div id="live-error-banner"></div>
  <div id="live-stale-banner"></div>
  <div class="card-grid" id="metric-cards"></div>
  <!-- charts and tables from later tasks go below this line -->
</div>
```

Add to the module body (inside the IIFE, before `return`):
```js
let cardsPollTimer = null;
let lastGoodCardsAt = null;

function fmt(value, digits) {
  return value === null || value === undefined ? '–' : Number(value).toFixed(digits === undefined ? 1 : digits);
}

function renderCards(latest, todayBuckets) {
  const today = todayBuckets[0];
  const rows = [
    { key: 'temperature_c', label: 'Temp °C' },
    { key: 'humidity_pct', label: 'Hum %' },
    { key: 'gas_ppm', label: 'Gas ppm' },
    { key: 'distance_cm', label: 'Dist cm' },
  ];
  const cardsHtml = rows.map(({ key, label }) => {
    const range = today && today[key] ? `${fmt(today[key].min)} / ${fmt(today[key].max)} today` : '– / – today';
    const stale = latest.age_seconds > window.APP_CONFIG.DEGRADED_THRESHOLD_SECONDS;
    return `
      <div class="card ${stale ? 'warn' : ''}">
        <div class="card-label">${label}</div>
        <div class="card-value">${fmt(latest[key])}</div>
        <div class="card-sub">${stale ? `at ${latest.recorded_at}` : range}</div>
      </div>
    `;
  }).join('') + `
    <div class="card">
      <div class="card-label">Auto-brake</div>
      <div class="card-value">${latest.auto_brake ? 'BRAKING' : 'CLEAR'}</div>
      <div class="card-sub">${today ? `${today.obstacle_events} obstacles today` : '– obstacles today'}</div>
    </div>
  `;
  document.getElementById('metric-cards').innerHTML = cardsHtml;
}

function showStale(message) {
  document.getElementById('live-stale-banner').innerHTML = message
    ? `<div class="stale-banner">${message}</div>` : '';
}

function pollCards(uid) {
  const today = new Date().toISOString().slice(0, 10);
  Promise.all([Api.latest(uid), Api.summary(uid, { granularity: 'day', start: today, end: today })])
    .then(([latest, summary]) => {
      lastGoodCardsAt = Date.now();
      showStale(null);
      renderCards(latest, summary.buckets);
    })
    .catch((err) => {
      const staleFor = lastGoodCardsAt ? `stale since ${new Date(lastGoodCardsAt).toLocaleTimeString()}` : 'no data yet';
      showStale(`${err.code === 'NOT_FOUND' ? 'Rover has never reported.' : `Live data unavailable (${err.message || err.code}).`} ${staleFor}`);
    })
    .finally(() => {
      if (document.getElementById('metric-cards')) {
        cardsPollTimer = setTimeout(() => pollCards(uid), window.APP_CONFIG.POLL_INTERVAL_LIVE_MS);
      }
    });
}
```

Wire it to selection: replace the module's `return` statement with:
```js
  return {
    mount,
    start,
    stop,
    getSelectedUid,
    onRoverSelected(uid) {
      clearTimeout(cardsPollTimer);
      lastGoodCardsAt = null;
      pollCards(uid);
    },
  };
```

And in `stop()`, add `clearTimeout(cardsPollTimer);`.

- [ ] **Step 3: Verify in the browser**

Reload, screenshot the Live tab. Expected: five cards render for the auto-selected rover with values matching `curl .../rovers/rover-001/latest`. Select `rover-002` (or any other listed rover) and screenshot again — expected: values update to that rover's `/latest`. If a selected rover has never reported (404), expected: a stale banner reading "Rover has never reported."

- [ ] **Step 4: Add card CSS refinements**

```css
.card.warn .card-sub { color: var(--warn); }
```

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/live.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(live): add five metric cards with stale/offline handling"
```

---

### Task 7: Live view — telemetry chart (temperature + humidity, range control)

**Files:**
- Modify: `rover-telemetry-frontend/public/js/live.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.readings(uid, params)` (Task 2), `Charts.lineWithBand` / `Charts.updateChart` (Task 4).
- Produces: nothing new consumed by later tasks (self-contained panel).

- [ ] **Step 1: Confirm the real `/readings` shape at both a raw and an aggregated resolution**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers/rover-001/readings?limit=5"
curl -s "$BASE/rovers/rover-001/readings?start=2026-09-01T00:00:00Z&end=2026-09-08T00:00:00Z&resolution=auto"
```
Expected: raw (`limit=5`) rows look like `{"recorded_at":"...","temperature_c":25,"humidity_pct":60,...}` (plain numbers); an aggregated response's rows look like `{"recorded_at":"...","temperature_c":{"avg":...,"min":...,"max":...},...}` (objects, not plain numbers) and the top-level response includes `"resolution"`, `"gaps"`, `"buckets_populated"`, `"query"`.

- [ ] **Step 2: Add the chart panel HTML and range control**

Append to the `live-main` div in the `TEMPLATE` (after `metric-cards`):
```html
<div class="panel">
  <div class="panel-title" id="telemetry-panel-title">Telemetry</div>
  <div class="range-controls" id="telemetry-range-controls">
    <button data-range="10m">10 m</button><button data-range="1h">1 h</button>
    <button data-range="6h" class="active">6 h</button><button data-range="24h">24 h</button>
    <button data-range="7d">7 d</button><button data-range="30d">30 d</button>
  </div>
  <canvas id="telemetry-chart" height="90"></canvas>
</div>
```

- [ ] **Step 3: Add the chart's data-loading and range logic**

Add to `live.js` (inside the IIFE):
```js
let telemetryChart = null;
let telemetryRange = '6h';

const RANGE_TO_MS = { '10m': 6e5, '1h': 36e5, '6h': 216e5, '24h': 864e5, '7d': 6048e5, '30d': 2592e6 };

function isoMinusMs(ms) {
  return new Date(Date.now() - ms).toISOString();
}

function labelFor(recordedAt) {
  return recordedAt.slice(11, 16);
}

function fieldSeries(readings, field, isAggregated) {
  return readings.map((r) => {
    const v = r[field];
    if (v === null || v === undefined) return null;
    return isAggregated ? v.avg : v;
  });
}
function fieldMin(readings, field, isAggregated) {
  return readings.map((r) => {
    const v = r[field];
    if (v === null || v === undefined) return null;
    return isAggregated ? v.min : v;
  });
}
function fieldMax(readings, field, isAggregated) {
  return readings.map((r) => {
    const v = r[field];
    if (v === null || v === undefined) return null;
    return isAggregated ? v.max : v;
  });
}

function loadTelemetryChart(uid) {
  const start = isoMinusMs(RANGE_TO_MS[telemetryRange]);
  const end = new Date().toISOString();
  Api.readings(uid, { start, end, resolution: 'auto' }).then((data) => {
    const isAggregated = data.resolution !== 'raw';
    const labels = data.readings.map((r) => labelFor(r.recorded_at));
    document.getElementById('telemetry-panel-title').textContent =
      `Telemetry · ${data.resolution} · ${data.count} pts`;
    const avg = fieldSeries(data.readings, 'temperature_c', isAggregated);
    const min = fieldMin(data.readings, 'temperature_c', isAggregated);
    const max = fieldMax(data.readings, 'temperature_c', isAggregated);
    if (!telemetryChart) {
      telemetryChart = Charts.lineWithBand({
        canvasId: 'telemetry-chart', labels, avg, min, max, avgLabel: 'Temperature (°C)', colorRgb: '47,111,237',
      });
    } else {
      Charts.updateChart(telemetryChart, labels, [max, min, avg]);
    }
  }).catch((err) => showError(`Telemetry chart unavailable: ${err.message || err.code}`));
}

document.addEventListener('click', (evt) => {
  const btn = evt.target.closest('#telemetry-range-controls button');
  if (!btn) return;
  document.querySelectorAll('#telemetry-range-controls button').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  telemetryRange = btn.dataset.range;
  const uid = getSelectedUid();
  if (uid) loadTelemetryChart(uid);
});
```

Update `onRoverSelected` to also call `loadTelemetryChart(uid)`, and have `pollCards`'s success branch also refresh the chart every poll tick so it stays live:
```js
// inside pollCards's .then, after renderCards(latest, summary.buckets):
loadTelemetryChart(uid);
```

- [ ] **Step 4: Add range-control CSS**

```css
.range-controls { display: flex; gap: 4px; margin-bottom: 8px; }
.range-controls button { padding: 4px 10px; border: 1px solid var(--border); background: var(--panel); border-radius: 4px; cursor: pointer; font-size: 12px; }
.range-controls button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
```

- [ ] **Step 5: Verify in the browser**

Reload, screenshot. Expected: a line-with-band chart renders under the metric cards, panel title reads something like `Telemetry · raw · N pts` or `Telemetry · minute · N pts` matching the `resolution` field from `curl .../readings?start=...&end=...&resolution=auto` for the same range. Click "24 h" and screenshot again — expected: panel title's point count and resolution change accordingly.

- [ ] **Step 6: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/live.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(live): add telemetry chart with range control"
```

---

### Task 8: Live view — obstacle-distance chart with auto-brake threshold and bands

**Files:**
- Modify: `rover-telemetry-frontend/public/js/live.js`

**Interfaces:**
- Consumes: `Api.readings(uid, { limit, order })` (Task 2), `Charts.lineWithBand`, `Charts.thresholdDataset`, `Charts.bandDataset`, `Charts.updateChart` (Task 4).
- Consumes: `sensor_limits.distance_cm.min` — fetched fresh each refresh from `Api.sensorLimits()` (also needed standalone by Task 9; duplicating the fetch here is acceptable since it's a cheap, cached-by-nothing config read at low poll frequency, not a shared-state dependency).

- [ ] **Step 1: Confirm raw last-5-minutes shape and the auto-brake threshold value**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers/rover-001/readings?limit=300&order=desc&resolution=raw"
curl -s "$BASE/config/sensor-limits"
```
Expected: readings include `distance_cm` and `auto_brake` (boolean) per row; `sensor-limits.distance_cm.min` gives the physical floor (2cm) — the auto-brake *threshold* itself is not in `sensor_limits` (it's a device behavior, not a validation range), so this panel draws the threshold from `window.APP_CONFIG` instead (see Step 2).

- [ ] **Step 2: Add a configurable auto-brake threshold constant**

In `config.js`, add: `AUTO_BRAKE_THRESHOLD_CM: 20,` (matches the seed value used across the backend design doc's examples; there is no API-served value for this, so it is a dashboard-side display constant, not a validation range).

- [ ] **Step 3: Add the obstacle-distance chart panel and logic**

Append to `live-main` in `TEMPLATE`, after the telemetry panel:
```html
<div class="panel">
  <div class="panel-title">Obstacle distance · live</div>
  <canvas id="obstacle-chart" height="70"></canvas>
</div>
```

Add to `live.js`:
```js
let obstacleChart = null;

function loadObstacleChart(uid) {
  Api.readings(uid, { limit: 150, order: 'desc', resolution: 'raw' }).then((data) => {
    const readings = data.readings.slice().reverse();
    const labels = readings.map((r) => labelFor(r.recorded_at));
    const distance = readings.map((r) => (r.distance_cm === null ? null : r.distance_cm));
    const brakeFlags = readings.map((r) => (r.auto_brake ? 1 : 0));
    const maxDistance = Math.max(120, ...distance.filter((v) => v !== null));
    if (!obstacleChart) {
      obstacleChart = Charts.lineWithBand({
        canvasId: 'obstacle-chart', labels, avg: distance, min: distance, max: distance,
        avgLabel: 'Distance (cm)', colorRgb: '26,127,55',
      });
      obstacleChart.data.datasets.push(Charts.thresholdDataset('Auto-brake threshold', window.APP_CONFIG.AUTO_BRAKE_THRESHOLD_CM, labels.length, '207,34,46'));
      obstacleChart.data.datasets.push(Charts.bandDataset('Brake engaged', brakeFlags, maxDistance, 'rgba(207,34,46,0.15)'));
      obstacleChart.update('none');
    } else {
      Charts.updateChart(obstacleChart, labels, [
        distance, distance, distance,
        new Array(labels.length).fill(window.APP_CONFIG.AUTO_BRAKE_THRESHOLD_CM),
        brakeFlags.map((f) => (f ? maxDistance : 0)),
      ]);
    }
  }).catch((err) => showError(`Obstacle chart unavailable: ${err.message || err.code}`));
}
```

Add `loadObstacleChart(uid);` to both `onRoverSelected` and the end of `pollCards`'s success branch (same places `loadTelemetryChart` was added in Task 7).

- [ ] **Step 4: Verify in the browser**

Reload, screenshot. Expected: a distance line chart appears below the telemetry chart, with a dashed red threshold line at 20cm and shaded red bands wherever `auto_brake` was `true` in the last 150 raw readings for the selected rover. Cross-check a couple of shaded-band timestamps against `curl .../readings?limit=150&order=desc&resolution=raw` rows where `"auto_brake":true`.

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/live.js rover-telemetry-frontend/public/js/config.js
git commit -m "feat(live): add obstacle-distance chart with auto-brake threshold and bands"
```

---

### Task 9: Live view — incoming-readings table, sensor-limit bars, recent events

**Files:**
- Modify: `rover-telemetry-frontend/public/js/live.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.events(uid, params)`, `Api.sensorLimits()` (Task 2).

- [ ] **Step 1: Confirm the real `/events` shape**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers/rover-001/events?limit=10"
```
Expected: `{"events":[{"at":"...","type":"threshold_exceeded"|"auto_brake_engaged"|"auto_brake_cleared"|"reconnected", ...}]}`.

- [ ] **Step 2: Add the two-column panel HTML**

Append to `live-main` in `TEMPLATE`, after the obstacle chart panel:
```html
<div class="live-bottom-grid">
  <div class="panel">
    <div class="panel-title">Incoming readings</div>
    <table>
      <thead><tr><th>Time (UTC)</th><th>Temp</th><th>Hum</th><th>Gas</th><th>Dist</th><th>State</th></tr></thead>
      <tbody id="incoming-readings-body"></tbody>
    </table>
  </div>
  <div>
    <div class="panel">
      <div class="panel-title">Sensor limits</div>
      <div id="sensor-limit-bars"></div>
    </div>
    <div class="panel">
      <div class="panel-title">Recent events</div>
      <ul id="recent-events-list" class="event-list"></ul>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add the incoming-readings ring buffer, sensor-limit bars, and events list logic**

Add to `live.js`:
```js
const incomingBuffers = {}; // uid -> array of {recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, state}
const MAX_INCOMING_ROWS = 8;

function classifyState(reading, recentEvents) {
  const nearEvent = (type) => recentEvents.some((e) => e.type === type && Math.abs(new Date(e.at) - new Date(reading.recorded_at)) < 2000);
  if (nearEvent('threshold_exceeded')) return 'gas spike';
  if (nearEvent('auto_brake_engaged') || reading.auto_brake) return 'brake';
  return 'stored';
}

function renderIncomingReadings(uid, recentEvents) {
  const rows = incomingBuffers[uid] || [];
  document.getElementById('incoming-readings-body').innerHTML = rows.map((r) => `
    <tr>
      <td>${r.recorded_at.slice(11, 19)}</td>
      <td>${fmt(r.temperature_c)}</td><td>${fmt(r.humidity_pct)}</td>
      <td>${fmt(r.gas_ppm, 0)}</td><td>${fmt(r.distance_cm)}</td>
      <td>${classifyState(r, recentEvents)}</td>
    </tr>
  `).join('');
}

function renderSensorLimitBars(latest, limits) {
  const rows = [
    ['temperature_c', 'temperature', '°C'],
    ['humidity_pct', 'humidity', '%'],
    ['gas_ppm', 'gas', 'ppm'],
    ['distance_cm', 'distance', 'cm'],
  ];
  document.getElementById('sensor-limit-bars').innerHTML = rows.map(([key, label, unit]) => {
    const limit = limits[key];
    const value = latest[key];
    const pct = value === null || !limit ? 0 : Math.min(100, Math.max(0, ((value - limit.min) / (limit.max - limit.min)) * 100));
    const over = value !== null && limit && (value < limit.min || value > limit.max);
    return `
      <div class="limit-row">
        <div class="limit-label">${label}</div>
        <div class="limit-track"><div class="limit-fill ${over ? 'over' : ''}" style="width:${pct}%"></div></div>
        <div class="limit-value">${fmt(value)} / ${limit ? limit.max : '–'} ${unit}</div>
      </div>
    `;
  }).join('');
}

function renderRecentEvents(events) {
  document.getElementById('recent-events-list').innerHTML = events.slice(0, 8).map((e) => `
    <li><span class="event-time">${e.at.slice(11, 19)}</span> ${describeEvent(e)}</li>
  `).join('');
}

function describeEvent(e) {
  if (e.type === 'threshold_exceeded') return `${e.sensor} ${e.value} above limit ${e.limit}`;
  if (e.type === 'auto_brake_engaged') return `auto-brake engaged · ${e.value} cm`;
  if (e.type === 'auto_brake_cleared') return 'obstacle cleared';
  if (e.type === 'reconnected') return `reconnected · gap ${e.gap_seconds}s`;
  return e.type;
}

function pollEventsAndLimits(uid, latest) {
  Promise.all([Api.events(uid, { limit: 20 }), Api.sensorLimits()]).then(([eventsResp, limits]) => {
    incomingBuffers[uid] = incomingBuffers[uid] || [];
    incomingBuffers[uid].unshift({ ...latest });
    incomingBuffers[uid] = incomingBuffers[uid].slice(0, MAX_INCOMING_ROWS);
    renderIncomingReadings(uid, eventsResp.events);
    renderSensorLimitBars(latest, limits);
    renderRecentEvents(eventsResp.events);
  }).catch((err) => showError(`Events/limits unavailable: ${err.message || err.code}`));
}
```

Hook it into `pollCards`'s success branch (same spot as the two chart loaders from Tasks 7–8):
```js
pollEventsAndLimits(uid, latest);
```
And reset `incomingBuffers[uid]` is intentionally *not* cleared on reselect, so switching rovers and back preserves recent history per rover for the session.

- [ ] **Step 4: Add CSS for the bottom grid, limit bars, and event list**

```css
.live-bottom-grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 12px; margin-top: 12px; }
.limit-row { margin-bottom: 10px; font-size: 12px; }
.limit-label { text-transform: uppercase; color: var(--text-dim); font-size: 11px; }
.limit-track { background: #eceef1; border-radius: 3px; height: 6px; margin: 3px 0; overflow: hidden; }
.limit-fill { background: var(--ok); height: 100%; }
.limit-fill.over { background: var(--bad); }
.event-list { list-style: none; margin: 0; padding: 0; font-size: 12px; }
.event-list li { padding: 3px 0; border-bottom: 1px solid var(--border); }
.event-time { color: var(--text-dim); margin-right: 6px; }
@media (max-width: 700px) {
  .live-bottom-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 5: Verify in the browser**

Reload, wait ~3 polling ticks (screenshot, wait, screenshot), and confirm: the incoming-readings table grows a new row each second up to 8 rows, sensor-limit bars' current values match `curl .../rovers/{uid}/latest`, and the fill bar for `gas_ppm` turns red (`over`) if the current gas reading exceeds `sensor-limits.gas_ppm.max`. Recent-events list matches `curl .../rovers/{uid}/events?limit=20`.

- [ ] **Step 6: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/live.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(live): add incoming-readings table, sensor-limit bars, recent events"
```

---

### Task 10: History view — controls and query-cost panel

**Files:**
- Modify: `rover-telemetry-frontend/public/js/history.js` (replace the Task 3 stub)
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.rovers()`, `Api.readings(uid, params)` (Task 2).
- Produces: `HistoryView`'s internal query-state (`uid`, `sensors`, `range`, `resolution`) that Tasks 11–12 read via module-level variables (this task defines them; no public getters needed since Tasks 11-12 add code inside the same IIFE).

- [ ] **Step 1: Confirm gap/query-cost fields on a wide real range**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers/rover-001/readings?start=2026-09-01T00:00:00Z&end=2026-09-08T00:00:00Z&resolution=auto"
```
Expected: top-level `resolution`, `count`, `buckets_populated`, `gaps` (array, possibly empty), `query.raw_rows_in_range`, `query.query_time_ms`.

- [ ] **Step 2: Write the History view's template and control wiring**

```js
window.HistoryView = (function () {
  let el;
  let uid = null;
  let sensors = { temperature_c: true, humidity_pct: true, gas_ppm: false, distance_cm: false };
  let range = '24h';
  let resolution = 'auto';
  let lastQuery = null;

  const RANGE_TO_MS = { '1h': 36e5, '6h': 216e5, '24h': 864e5, '7d': 6048e5, '30d': 2592e6 };

  const TEMPLATE = `
    <div id="history-error-banner"></div>
    <div class="panel">
      <div class="history-controls">
        <label>Rover
          <select id="history-rover"></select>
        </label>
        <span class="range-controls" id="history-range-controls">
          <button data-range="1h">1 h</button><button data-range="6h">6 h</button>
          <button data-range="24h" class="active">24 h</button>
          <button data-range="7d">7 d</button><button data-range="30d">30 d</button>
        </span>
        <label>Resolution
          <select id="history-resolution">
            <option value="auto">auto</option><option value="raw">raw</option>
            <option value="minute">minute</option><option value="hour">hour</option><option value="day">day</option>
          </select>
        </label>
        <span id="history-sensor-toggles"></span>
      </div>
    </div>
    <div class="panel">
      <div class="panel-title">Query</div>
      <div id="history-query-cost">–</div>
    </div>
    <div class="panel">
      <canvas id="history-chart" height="90"></canvas>
    </div>
  `;

  function populateRoverSelect(rovers) {
    const select = document.getElementById('history-rover');
    select.innerHTML = rovers.map((r) => `<option value="${r.device_uid}">${r.device_uid}</option>`).join('');
    if (!uid && rovers.length > 0) uid = rovers[0].device_uid;
    select.value = uid;
  }

  function renderSensorToggles() {
    const labels = { temperature_c: 'temperature', humidity_pct: 'humidity', gas_ppm: 'gas', distance_cm: 'distance' };
    document.getElementById('history-sensor-toggles').innerHTML = Object.entries(labels).map(([key, label]) => `
      <label class="sensor-toggle"><input type="checkbox" data-sensor="${key}" ${sensors[key] ? 'checked' : ''}> ${label}</label>
    `).join('');
  }

  function showError(message) {
    document.getElementById('history-error-banner').innerHTML = message ? `<div class="error-banner">${message}</div>` : '';
  }

  function runQuery() {
    if (!uid) return;
    const start = new Date(Date.now() - RANGE_TO_MS[range]).toISOString();
    const end = new Date().toISOString();
    Api.readings(uid, { start, end, resolution }).then((data) => {
      showError(null);
      lastQuery = data;
      document.getElementById('history-query-cost').textContent =
        `rows returned ${data.count} · raw rows in range ${data.query.raw_rows_in_range} · ` +
        `query time ${data.query.query_time_ms} ms · gaps found ${data.gaps.length} · ` +
        `${data.buckets_populated} of ${data.count} buckets populated`;
      if (window.HistoryView._onData) window.HistoryView._onData(data);
    }).catch((err) => showError(`Query failed: ${err.message || err.code}`));
  }

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;
    renderSensorToggles();
    Api.rovers().then((rovers) => { populateRoverSelect(rovers); runQuery(); }).catch((err) => showError(`Rover list unavailable: ${err.message || err.code}`));

    document.getElementById('history-rover').addEventListener('change', (evt) => { uid = evt.target.value; runQuery(); });
    document.getElementById('history-resolution').addEventListener('change', (evt) => { resolution = evt.target.value; runQuery(); });
    document.getElementById('history-range-controls').addEventListener('click', (evt) => {
      const btn = evt.target.closest('button');
      if (!btn) return;
      document.querySelectorAll('#history-range-controls button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      range = btn.dataset.range;
      runQuery();
    });
    document.getElementById('history-sensor-toggles').addEventListener('change', (evt) => {
      const input = evt.target.closest('input[data-sensor]');
      if (!input) return;
      sensors[input.dataset.sensor] = input.checked;
      if (window.HistoryView._onSensorsChanged) window.HistoryView._onSensorsChanged();
    });
  }

  function start() {}
  function stop() {}

  return { mount, start, stop, getState: () => ({ uid, sensors, range, resolution, lastQuery }) };
})();
```

- [ ] **Step 3: Add History-view CSS**

```css
.history-controls { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; font-size: 13px; }
.sensor-toggle { margin-right: 10px; font-size: 12px; }
```

- [ ] **Step 4: Verify in the browser**

Reload, click the HISTORY tab, screenshot. Expected: rover dropdown populated from `curl .../rovers`, range buttons with "24 h" active, resolution dropdown, sensor checkboxes (temperature and humidity checked by default), and a query-cost line whose numbers match `curl .../rovers/{selected-uid}/readings?start=...&end=...&resolution=auto` for the last 24h. Change the range to "7 d" and screenshot again — expected: the query-cost line updates.

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/history.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(history): add rover/range/resolution/sensor controls and query-cost panel"
```

---

### Task 11: History view — aggregated chart, statistics table, obstacle-events chart, gap list

**Files:**
- Modify: `rover-telemetry-frontend/public/js/history.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.summary(uid, params)` (Task 2), `Charts.lineWithBand` / `Charts.updateChart` (Task 4), `HistoryView._onData` / `_onSensorsChanged` hooks defined in Task 10.

- [ ] **Step 1: Confirm the real `/summary` shape over a multi-day range**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/rovers/rover-001/summary?granularity=day&start=2026-09-01&end=2026-09-08"
```
Expected: `{"device_uid":"...","granularity":"day","buckets":[{"bucket_start":"...","sample_count":...,"temperature_c":{"min":...,"avg":...,"max":...},...,"obstacle_events":...}]}`.

- [ ] **Step 2: Add the statistics/obstacle/gaps panel HTML**

Append to `TEMPLATE` in `history.js`, after the chart panel:
```html
<div class="panel">
  <div class="panel-title">Statistics · selected range</div>
  <table>
    <thead><tr><th>Sensor</th><th>Min</th><th>Avg</th><th>Max</th><th>Samples</th></tr></thead>
    <tbody id="history-stats-body"></tbody>
  </table>
</div>
<div class="panel">
  <div class="panel-title">Obstacle events per bucket</div>
  <canvas id="history-obstacle-chart" height="60"></canvas>
</div>
<div class="panel">
  <div class="panel-title">Gaps in range</div>
  <ul id="history-gaps-list" class="event-list"></ul>
</div>
```

- [ ] **Step 3: Add the chart, stats table, obstacle chart, and gap list logic**

Add to `history.js` (inside the IIFE, before `return`):
```js
let historyChart = null;
let historyObstacleChart = null;

const SENSOR_META = {
  temperature_c: { label: 'Temperature (°C)', colorRgb: '47,111,237' },
  humidity_pct: { label: 'Humidity (%)', colorRgb: '130,80,223' },
  gas_ppm: { label: 'Gas (ppm)', colorRgb: '184,120,20' },
  distance_cm: { label: 'Distance (cm)', colorRgb: '26,127,55' },
};

function firstActiveSensor() {
  return Object.keys(sensors).find((key) => sensors[key]) || 'temperature_c';
}

function renderHistoryChart(data) {
  const field = firstActiveSensor();
  const meta = SENSOR_META[field];
  const labels = data.readings.map((r) => r.recorded_at.slice(0, 16).replace('T', ' '));
  const isAgg = data.resolution !== 'raw';
  const avg = fieldSeriesHistory(data.readings, field, isAgg);
  const min = fieldMinHistory(data.readings, field, isAgg);
  const max = fieldMaxHistory(data.readings, field, isAgg);
  if (!historyChart) {
    historyChart = Charts.lineWithBand({ canvasId: 'history-chart', labels, avg, min, max, avgLabel: meta.label, colorRgb: meta.colorRgb });
  } else {
    Charts.updateChart(historyChart, labels, [max, min, avg]);
  }
}
function fieldSeriesHistory(readings, field, isAgg) { return readings.map((r) => (r[field] == null ? null : (isAgg ? r[field].avg : r[field]))); }
function fieldMinHistory(readings, field, isAgg) { return readings.map((r) => (r[field] == null ? null : (isAgg ? r[field].min : r[field]))); }
function fieldMaxHistory(readings, field, isAgg) { return readings.map((r) => (r[field] == null ? null : (isAgg ? r[field].max : r[field]))); }

function renderGapsList(gaps) {
  document.getElementById('history-gaps-list').innerHTML = gaps.length === 0
    ? '<li>No gaps in this range.</li>'
    : gaps.map((g) => `<li>${g.start} → ${g.end} · ${g.duration_seconds}s · ${g.missing_readings} readings missing</li>`).join('');
}

function loadSummaryPanels() {
  if (!uid) return;
  const start = new Date(Date.now() - RANGE_TO_MS[range]).toISOString().slice(0, 10);
  const end = new Date().toISOString().slice(0, 10);
  const granularity = resolution === 'raw' ? 'hour' : (resolution === 'auto' ? 'day' : resolution);
  Api.summary(uid, { granularity, start, end }).then((summaryData) => {
    const buckets = summaryData.buckets;
    document.getElementById('history-stats-body').innerHTML = Object.entries(SENSOR_META).map(([key, meta]) => {
      const values = buckets.map((b) => b[key]).filter((v) => v && v.avg !== null);
      if (values.length === 0) return `<tr><td>${meta.label}</td><td>–</td><td>–</td><td>–</td><td>–</td></tr>`;
      const min = Math.min(...values.map((v) => v.min));
      const max = Math.max(...values.map((v) => v.max));
      const avg = values.reduce((sum, v) => sum + v.avg, 0) / values.length;
      const samples = buckets.reduce((sum, b) => sum + b.sample_count, 0);
      return `<tr><td>${meta.label}</td><td>${min.toFixed(1)}</td><td>${avg.toFixed(1)}</td><td>${max.toFixed(1)}</td><td>${samples}</td></tr>`;
    }).join('');

    const obsLabels = buckets.map((b) => b.bucket_start.slice(0, 10));
    const obsCounts = buckets.map((b) => b.obstacle_events);
    if (!historyObstacleChart) {
      const ctx = document.getElementById('history-obstacle-chart').getContext('2d');
      historyObstacleChart = new Chart(ctx, {
        type: 'bar',
        data: { labels: obsLabels, datasets: [{ label: 'Obstacle events', data: obsCounts, backgroundColor: 'rgba(207,34,46,0.6)' }] },
        options: { responsive: true, animation: false },
      });
    } else {
      historyObstacleChart.data.labels = obsLabels;
      historyObstacleChart.data.datasets[0].data = obsCounts;
      historyObstacleChart.update('none');
    }
  }).catch((err) => showError(`Summary unavailable: ${err.message || err.code}`));
}
```

Wire it up: at the bottom of the IIFE, before `return`, add:
```js
window.HistoryView = window.HistoryView || {};
```
Then change the module's final `return` to also assign the hooks used by Task 10's `runQuery`:
```js
const api = { mount, start, stop, getState: () => ({ uid, sensors, range, resolution, lastQuery }) };
api._onData = (data) => { renderHistoryChart(data); renderGapsList(data.gaps); loadSummaryPanels(); };
api._onSensorsChanged = () => { if (lastQuery) renderHistoryChart(lastQuery); };
return api;
```
(This replaces the plain `return { mount, start, stop, getState: ... };` line from Task 10 — `_onData` and `_onSensorsChanged` must be assigned after all the functions they reference are defined, so keep this block as the last thing before the closing `})();`.)

- [ ] **Step 4: Verify in the browser**

Reload, HISTORY tab, screenshot. Expected: an aggregated line-with-band chart for the default sensor (temperature), a statistics table with min/avg/max/samples matching `curl .../summary?granularity=day&start=...&end=...` for the same range, an obstacle-events bar chart, and a gap list (or "No gaps in this range."). Toggle the "gas" checkbox on and screenshot — expected: the chart switches to plotting gas.

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/history.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(history): add aggregated chart, statistics table, obstacle chart, gap list"
```

---

### Task 12: History view — CSV/JSON export buttons

**Files:**
- Modify: `rover-telemetry-frontend/public/js/history.js`

**Interfaces:**
- Consumes: `Api.exportUrl(uid, params)` (Task 2).

- [ ] **Step 1: Confirm the export endpoint responds with the right content type**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -sI "$BASE/rovers/rover-001/export?format=csv&start=2026-09-07T00:00:00Z&end=2026-09-08T00:00:00Z" | head -5
```
Expected: `Content-Type: text/csv` and a `Content-Disposition: attachment` header.

- [ ] **Step 2: Add export buttons to the controls panel**

In `history.js`'s `TEMPLATE`, inside `.history-controls`, add after the sensor toggles span:
```html
<span class="export-buttons">
  <button id="export-csv">Export CSV</button>
  <button id="export-json">Export JSON</button>
</span>
```

Add to the IIFE body:
```js
function currentRangeIso() {
  return { start: new Date(Date.now() - RANGE_TO_MS[range]).toISOString(), end: new Date().toISOString() };
}

function triggerExport(format) {
  if (!uid) return;
  const { start, end } = currentRangeIso();
  const url = Api.exportUrl(uid, { format, start, end });
  const link = document.createElement('a');
  link.href = url;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
}
```

In `mount()`, after the existing `addEventListener` calls, add:
```js
document.getElementById('export-csv').addEventListener('click', () => triggerExport('csv'));
document.getElementById('export-json').addEventListener('click', () => triggerExport('json'));
```

- [ ] **Step 3: Verify in the browser**

Reload, HISTORY tab. Click "Export CSV" — since the sandboxed browser tool cannot save downloads, instead verify by reading the constructed URL: run in the console `Api.exportUrl(document.getElementById('history-rover').value, {format:'csv', start: new Date(Date.now()-864e5).toISOString(), end: new Date().toISOString()})` and `curl` that exact URL to confirm it returns CSV text starting with the header row `device_uid,recorded_at,temperature_c,humidity_pct,gas_ppm,distance_cm,auto_brake`.

- [ ] **Step 4: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/history.js
git commit -m "feat(history): add CSV/JSON export buttons"
```

---

### Task 13: System view — services, database, rejected-payloads panels, and metric cards

**Files:**
- Modify: `rover-telemetry-frontend/public/js/system.js` (replace the Task 3 stub)
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.system()`, `Api.validationErrorsSummary(windowStr)` (Task 2).

- [ ] **Step 1: Confirm the real `/system` shape**

```bash
curl -s "http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1/system"
```
Expected fields (this backend, running on Windows/XAMPP rather than a Pi, may report 0 for CPU load/temp — that's real data, not a bug to fix here): `cpu_load_percent`, `cpu_temperature_c`, `memory.used_percent`, `disk.used_percent`, `ingest_rate_per_minute`, `database.{size_mb,row_count,growth_mb_per_day,projected_days_remaining}`, `services.{api,database,aggregate_job,retention_job}`, `warnings` (array).

- [ ] **Step 2: Write the System view's template and polling**

```js
window.SystemView = (function () {
  let el;
  let pollTimer = null;

  const TEMPLATE = `
    <div id="system-error-banner"></div>
    <div class="card-grid" id="system-cards"></div>
    <div class="system-panels-grid">
      <div class="panel">
        <div class="panel-title">Services</div>
        <table><tbody id="services-body"></tbody></table>
      </div>
      <div class="panel">
        <div class="panel-title">Database</div>
        <div id="database-panel"></div>
      </div>
      <div class="panel">
        <div class="panel-title">Rejected · 24h</div>
        <div class="card-value" id="system-rejected-total">–</div>
        <div class="card-sub" id="system-rejected-by-code"></div>
      </div>
    </div>
  `;

  function fmt(value, digits) { return value === null || value === undefined ? '–' : Number(value).toFixed(digits === undefined ? 1 : digits); }

  function cardClass(value, warnAt) { return value >= warnAt ? 'warn' : ''; }

  function renderCards(system) {
    document.getElementById('system-cards').innerHTML = `
      <div class="card ${cardClass(system.cpu_load_percent, 80)}">
        <div class="card-label">CPU load</div><div class="card-value">${fmt(system.cpu_load_percent)}%</div>
      </div>
      <div class="card ${cardClass(system.cpu_temperature_c, 80)}">
        <div class="card-label">CPU temp</div><div class="card-value">${fmt(system.cpu_temperature_c)}°C</div>
      </div>
      <div class="card ${cardClass(system.memory.used_percent, 90)}">
        <div class="card-label">Memory</div><div class="card-value">${fmt(system.memory.used_percent)}%</div>
      </div>
      <div class="card ${cardClass(system.disk.used_percent, 90)}">
        <div class="card-label">Disk</div><div class="card-value">${fmt(system.disk.used_percent)}%</div>
      </div>
    `;
  }

  function renderServices(services) {
    document.getElementById('services-body').innerHTML = Object.entries(services).map(([name, info]) => {
      const status = typeof info === 'string' ? info : info.status;
      const lastRun = typeof info === 'object' && info.last_run ? ` · last run ${info.last_run}` : '';
      return `<tr><td>${name}</td><td>${status}${lastRun}</td></tr>`;
    }).join('');
  }

  function renderDatabase(db) {
    document.getElementById('database-panel').innerHTML = `
      <div>size ${fmt(db.size_mb)} MB</div>
      <div>rows ${db.row_count.toLocaleString()}</div>
      <div>growth ${fmt(db.growth_mb_per_day)} MB/day</div>
      <div>capacity ≈ ${db.projected_days_remaining === null ? 'n/a' : `${db.projected_days_remaining} days`}</div>
    `;
  }

  function showError(message) {
    document.getElementById('system-error-banner').innerHTML = message ? `<div class="error-banner">${message}</div>` : '';
  }

  function poll() {
    Promise.all([Api.system(), Api.validationErrorsSummary('24h')]).then(([system, rejects]) => {
      showError(null);
      renderCards(system);
      renderServices(system.services);
      renderDatabase(system.database);
      document.getElementById('system-rejected-total').textContent = rejects.total;
      document.getElementById('system-rejected-by-code').textContent = Object.entries(rejects.by_code).map(([c, n]) => `${c} ${n}`).join(' · ');
      if (window.SystemView._onSystemData) window.SystemView._onSystemData(system);
    }).catch((err) => showError(`System data unavailable: ${err.message || err.code}`))
      .finally(() => { pollTimer = setTimeout(poll, window.APP_CONFIG.POLL_INTERVAL_SYSTEM_MS); });
  }

  function mount(rootEl) { el = rootEl; el.innerHTML = TEMPLATE; }
  function start() { if (pollTimer) return; poll(); }
  function stop() { clearTimeout(pollTimer); pollTimer = null; }

  return { mount, start, stop };
})();
```

- [ ] **Step 3: Add System-view CSS**

```css
.system-panels-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 12px; }
@media (max-width: 700px) { .system-panels-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: Verify in the browser**

Reload, click SYSTEM tab, screenshot. Expected: four metric cards, a services table listing `api`/`database`/`aggregate_job`/`retention_job`, a database panel with size/rows/growth/capacity, and a rejected-payloads count — all matching `curl .../system` and `curl .../validation-errors/summary?window=24h`.

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/system.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(system): add services, database, rejected-payloads panels and metric cards"
```

---

### Task 14: System view — resource history, ingest-rate, and database-growth charts

**Files:**
- Modify: `rover-telemetry-frontend/public/js/system.js`

**Interfaces:**
- Consumes: `Api.systemHistory(params)` (Task 2), `Charts.thresholdDataset` (Task 4), `SystemView._onSystemData` hook (Task 13, for the growth-projection's current `growth_mb_per_day`/`size_mb`).

- [ ] **Step 1: Confirm the real `/system/history` shape over 24h**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/system/history?start=2026-09-07T00:00:00Z&end=2026-09-08T00:00:00Z&resolution=auto"
```
Expected: `{"resolution":"raw"|"hour","count":N,"points":[{"sampled_at":"...","cpu_load_percent":...,"cpu_temperature_c":...,"memory_used_percent":...,"disk_used_percent":...,"ingest_rate_per_min":...,"database_size_mb":...}]}`.

- [ ] **Step 2: Add the three chart panels**

Append to `TEMPLATE` in `system.js`, after `system-panels-grid`:
```html
<div class="panel">
  <div class="panel-title">Gateway resources</div>
  <span class="range-controls" id="system-range-controls">
    <button data-range="1h">1 h</button><button data-range="6h" class="active">6 h</button>
    <button data-range="24h">24 h</button><button data-range="7d">7 d</button>
  </span>
  <canvas id="resources-chart" height="80"></canvas>
</div>
<div class="panel">
  <div class="panel-title">Ingest rate</div>
  <canvas id="ingest-chart" height="60"></canvas>
</div>
<div class="panel">
  <div class="panel-title">Database growth</div>
  <canvas id="growth-chart" height="60"></canvas>
</div>
```

- [ ] **Step 3: Add the chart-loading logic**

Add to `system.js` (inside the IIFE, before `return`):
```js
let resourcesChart = null;
let ingestChart = null;
let growthChart = null;
let historyRange = '6h';
let latestSystem = null;

const HIST_RANGE_TO_MS = { '1h': 36e5, '6h': 216e5, '24h': 864e5, '7d': 6048e5 };

function loadResourceCharts() {
  const start = new Date(Date.now() - HIST_RANGE_TO_MS[historyRange]).toISOString();
  const end = new Date().toISOString();
  Api.systemHistory({ start, end, resolution: 'auto' }).then((data) => {
    const labels = data.points.map((p) => p.sampled_at.slice(11, 16));
    const cpuTemp = data.points.map((p) => p.cpu_temperature_c);
    const cpuLoad = data.points.map((p) => p.cpu_load_percent);
    const memUsed = data.points.map((p) => p.memory_used_percent);
    const ingestRate = data.points.map((p) => p.ingest_rate_per_min);
    const dbSize = data.points.map((p) => p.database_size_mb);

    if (!resourcesChart) {
      const ctx = document.getElementById('resources-chart').getContext('2d');
      resourcesChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'CPU temp (°C)', data: cpuTemp, borderColor: 'rgb(207,34,46)', pointRadius: 0, borderWidth: 2 },
            { label: 'CPU load (%)', data: cpuLoad, borderColor: 'rgb(47,111,237)', pointRadius: 0, borderWidth: 2 },
            { label: 'Memory used (%)', data: memUsed, borderColor: 'rgb(130,80,223)', pointRadius: 0, borderWidth: 2 },
            Charts.thresholdDataset('Throttle limit 80°C', 80, labels.length, '207,34,46'),
          ],
        },
        options: { responsive: true, animation: false },
      });
    } else {
      resourcesChart.data.labels = labels;
      resourcesChart.data.datasets[0].data = cpuTemp;
      resourcesChart.data.datasets[1].data = cpuLoad;
      resourcesChart.data.datasets[2].data = memUsed;
      resourcesChart.data.datasets[3].data = new Array(labels.length).fill(80);
      resourcesChart.update('none');
    }

    if (!ingestChart) {
      const ctx2 = document.getElementById('ingest-chart').getContext('2d');
      ingestChart = new Chart(ctx2, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Accepted (rec/min)', data: ingestRate, backgroundColor: ingestRate.map((v) => (v === 0 ? 'rgba(207,34,46,0.4)' : 'rgba(26,127,55,0.6)')) }] },
        options: { responsive: true, animation: false },
      });
    } else {
      ingestChart.data.labels = labels;
      ingestChart.data.datasets[0].data = ingestRate;
      ingestChart.data.datasets[0].backgroundColor = ingestRate.map((v) => (v === 0 ? 'rgba(207,34,46,0.4)' : 'rgba(26,127,55,0.6)'));
      ingestChart.update('none');
    }

    const projected = latestSystem ? projectGrowth(dbSize, latestSystem.database.growth_mb_per_day) : [];
    if (!growthChart) {
      const ctx3 = document.getElementById('growth-chart').getContext('2d');
      growthChart = new Chart(ctx3, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'Size (MB)', data: dbSize, borderColor: 'rgb(184,120,20)', pointRadius: 0, borderWidth: 2 },
            { label: 'Projected', data: projected, borderColor: 'rgb(184,120,20)', borderDash: [4, 4], pointRadius: 0, borderWidth: 1 },
          ],
        },
        options: { responsive: true, animation: false },
      });
    } else {
      growthChart.data.labels = labels;
      growthChart.data.datasets[0].data = dbSize;
      growthChart.data.datasets[1].data = projected;
      growthChart.update('none');
    }
  }).catch((err) => showError(`Resource history unavailable: ${err.message || err.code}`));
}

function projectGrowth(dbSizeSeries, growthPerDay) {
  const last = dbSizeSeries.filter((v) => v !== null).slice(-1)[0] || 0;
  const perPoint = (growthPerDay || 0) / dbSizeSeries.length;
  return dbSizeSeries.map((_, i) => Number((last + perPoint * i).toFixed(2)));
}
```

Wire range buttons and the `_onSystemData` hook: add to `mount()`:
```js
document.getElementById('system-range-controls').addEventListener('click', (evt) => {
  const btn = evt.target.closest('button');
  if (!btn) return;
  document.querySelectorAll('#system-range-controls button').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  historyRange = btn.dataset.range;
  loadResourceCharts();
});
```
And in `poll()`'s `.then`, after `renderDatabase(system.database);`, add:
```js
latestSystem = system;
loadResourceCharts();
```
(Remove the standalone `if (window.SystemView._onSystemData) ...` line from Task 13 — this direct call replaces that hook, since both live in the same closure.)

- [ ] **Step 4: Verify in the browser**

Reload, SYSTEM tab, screenshot. Expected: three charts render below the panels — resources (CPU temp/load, memory, throttle line), ingest rate (bars, red for zero-ingest periods), database growth (solid + dashed projection). Cross-check point counts against `curl .../system/history?start=...&end=...&resolution=auto` for the active range.

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/system.js
git commit -m "feat(system): add resource history, ingest-rate, and database-growth charts"
```

---

### Task 15: System view — sensor-limit editor

**Files:**
- Modify: `rover-telemetry-frontend/public/js/system.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `Api.sensorLimits()`, `Api.putSensorLimit(field, {min, max})` (Task 2).

- [ ] **Step 1: Confirm the real GET/PUT round trip, then restore the original value**

```bash
BASE="http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1"
curl -s "$BASE/config/sensor-limits"
curl -s -X PUT "$BASE/config/sensor-limits/temperature_c" -H "Content-Type: application/json" -d '{"min":-40,"max":85}'
```
Expected: `PUT` response is `{"field":"temperature_c","min":-40,"max":85,"updated_at":"..."}` (this call intentionally writes back the same seed values, so it is a no-op change — safe to run against the shared dev database).

- [ ] **Step 2: Add the editor panel HTML**

Append to `TEMPLATE` in `system.js`, after the growth-chart panel:
```html
<div class="panel">
  <div class="panel-title">Sensor limits</div>
  <table>
    <thead><tr><th>Field</th><th>Min</th><th>Max</th><th>Updated</th><th></th></tr></thead>
    <tbody id="sensor-limits-editor-body"></tbody>
  </table>
</div>
```

- [ ] **Step 3: Add the editor logic**

Add to `system.js`:
```js
function loadSensorLimitEditor() {
  Api.sensorLimits().then((limits) => {
    document.getElementById('sensor-limits-editor-body').innerHTML = Object.entries(limits).map(([field, limit]) => `
      <tr data-field="${field}">
        <td>${field}</td>
        <td><input type="number" class="limit-min" value="${limit.min}" style="width:70px"></td>
        <td><input type="number" class="limit-max" value="${limit.max}" style="width:70px"></td>
        <td>${limit.updated_at}</td>
        <td><button class="save-limit">Save</button><span class="limit-status"></span></td>
      </tr>
    `).join('');
  }).catch((err) => showError(`Sensor limits unavailable: ${err.message || err.code}`));
}

function wireSensorLimitEditor() {
  document.getElementById('sensor-limits-editor-body').addEventListener('click', (evt) => {
    const btn = evt.target.closest('.save-limit');
    if (!btn) return;
    const row = btn.closest('tr');
    const field = row.dataset.field;
    const min = Number(row.querySelector('.limit-min').value);
    const max = Number(row.querySelector('.limit-max').value);
    const status = row.querySelector('.limit-status');
    status.textContent = 'saving…';
    Api.putSensorLimit(field, { min, max }).then((updated) => {
      status.textContent = `saved · ${updated.updated_at}`;
      row.children[3].textContent = updated.updated_at;
    }).catch((err) => {
      status.textContent = err.code === 'INVALID_PARAMETER' ? 'min must be less than max' : `error: ${err.message || err.code}`;
    });
  });
}
```

In `mount()`, add `wireSensorLimitEditor();`, and call `loadSensorLimitEditor();` once at the end of `mount()` (this table refreshes on tab entry, not every poll tick, since limits change rarely and mid-edit polling would clobber unsaved input).

- [ ] **Step 4: Add editor CSS**

```css
.limit-status { margin-left: 8px; font-size: 11px; color: var(--text-dim); }
```

- [ ] **Step 5: Verify in the browser**

Reload, SYSTEM tab, screenshot — expected: a table row per field (`temperature_c`, `humidity_pct`, `gas_ppm`, `distance_cm`) with editable min/max inputs matching `curl .../config/sensor-limits`. Change `distance_cm`'s max from 400 to 401 in the UI, click Save, screenshot — expected: status shows "saved · <new timestamp>". Then set it back to 400 and Save again, and confirm via `curl .../config/sensor-limits` that it reads back `{"min":2,"max":400}` (restoring the seed value so later tasks' assumptions about `distance_cm.max` stay valid).

- [ ] **Step 6: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/js/system.js rover-telemetry-frontend/public/css/style.css
git commit -m "feat(system): add sensor-limit editor"
```

---

### Task 16: Full responsive pass and end-to-end manual QA

**Files:**
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: nothing new — this task is verification and small CSS fixes across everything built in Tasks 1–15.

- [ ] **Step 1: Resize the browser window to a narrow viewport and screenshot each tab**

Use `mcp__claude-in-chrome__resize_window` to set the viewport to 375×800. Reload, screenshot LIVE, HISTORY, and SYSTEM. Expected per the 700px breakpoints already added in Tasks 1/5/9/13: single-column stacking on all three views, no horizontal scrollbar, no overlapping text. Fix any overflow found by adding `overflow-x: auto` to the specific offending table/chart wrapper (e.g., wrap each `<table>` in a `<div class="table-scroll">` and add `.table-scroll { overflow-x: auto; }` to `style.css`, applied only where actually needed).

- [ ] **Step 2: Restore the viewport and run a full-width pass**

Resize back to 1440×900. Reload and click through LIVE → HISTORY → SYSTEM → LIVE, screenshotting each. Expected: no console errors at any point (check with `mcp__claude-in-chrome__read_console_messages` after each navigation), all panels populated, tab switching stops the previous tab's polling (confirm by watching the Network tab is idle for inactive views — or simpler: add a temporary `console.log` in each view's `stop()`, watch it fire on tab-away, then remove the log before committing).

- [ ] **Step 3: Verify degraded/offline rover rendering**

In the browser console, temporarily monkey-patch to force a stale render: `Api.latest = () => Promise.reject({code:'NOT_FOUND', message:'test'});` then wait one poll tick and screenshot — expected: the Live view's stale banner reads "Rover has never reported." Reload the page afterward to restore the real `Api.latest`.

- [ ] **Step 4: Record what was checked**

Add a short section to the design doc noting the manual QA pass:

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
```

Append to `docs/superpowers/specs/2026-09-08-rover-telemetry-dashboard-design.md`:
```markdown

## 10. Manual QA record

Verified by browser walkthrough (Chrome automation) against the local backend at
`http://localhost/_worktrees/rover-telemetry-dashboard/rover-telemetry-backend/public/api/v1`:

- All three tabs render with real data from `rover-001` and switch without leaking timers.
- Responsive layout at 375px width: single column, no horizontal overflow, on all three views.
- Live view: fleet selection, five metric cards, both charts, incoming-readings table, sensor-limit bars, recent events.
- History view: range/resolution/sensor controls, query-cost panel, aggregated chart, statistics table, obstacle-events chart, gap list, CSV export URL.
- System view: metric cards, services/database/rejected panels, three history charts, sensor-limit editor round-trip (write-then-restore verified against `distance_cm`).
- Degraded/offline rendering confirmed via a forced `/latest` failure.
```

- [ ] **Step 5: Commit**

```bash
cd "C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard"
git add rover-telemetry-frontend/public/css/style.css docs/superpowers/specs/2026-09-08-rover-telemetry-dashboard-design.md
git commit -m "test: complete responsive pass and manual QA walkthrough"
```

---

## After this plan

The branch `feat/rover-telemetry-dashboard` (worktree at `C:/xampp/htdocs/_worktrees/rover-telemetry-dashboard`) is ready for the `finishing-a-development-branch` workflow (PR to `develop`) once all 16 tasks are checked off. Do not push or open a PR as part of this plan — that is a separate, explicit step.
