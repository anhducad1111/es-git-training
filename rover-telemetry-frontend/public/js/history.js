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
