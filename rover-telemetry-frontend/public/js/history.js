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
        <span class="export-buttons">
          <button id="export-csv">Export CSV</button>
          <button id="export-json">Export JSON</button>
        </span>
      </div>
    </div>
    <div class="panel">
      <div class="panel-title">Query</div>
      <div id="history-query-cost">–</div>
    </div>
    <div class="panel">
      <canvas id="history-chart" height="90"></canvas>
    </div>
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
    document.getElementById('export-csv').addEventListener('click', () => triggerExport('csv'));
    document.getElementById('export-json').addEventListener('click', () => triggerExport('json'));
  }

  function start() {}
  function stop() {}

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

  window.HistoryView = window.HistoryView || {};
  const api = { mount, start, stop, getState: () => ({ uid, sensors, range, resolution, lastQuery }) };
  api._onData = (data) => { renderHistoryChart(data); renderGapsList(data.gaps); loadSummaryPanels(); };
  api._onSensorsChanged = () => { if (lastQuery) renderHistoryChart(lastQuery); };
  return api;
})();
