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
        <div class="panel-title">Rejected ﾂｷ 24h</div>
        <div class="card-value" id="system-rejected-total">窶・/div>
        <div class="card-sub" id="system-rejected-by-code"></div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-title">Gateway resources</div>
      <span class="range-controls" id="system-range-controls">
        <button data-range="1h">1 h</button><button data-range="6h" class="active">6 h</button>
        <button data-range="24h">24 h</button><button data-range="7d">7 d</button>
      </span>
      <div class="chart-box"><canvas id="resources-chart"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-title">Ingest rate</div>
      <div class="chart-box"><canvas id="ingest-chart"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-title">Database growth</div>
      <div class="chart-box"><canvas id="growth-chart"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-title">Sensor limits</div>
      <table>
        <thead><tr><th>Field</th><th>Min</th><th>Max</th><th>Updated</th><th></th></tr></thead>
        <tbody id="sensor-limits-editor-body"></tbody>
      </table>
    </div>
  `;

  function fmt(value, digits) { return value === null || value === undefined ? '窶・ : Number(value).toFixed(digits === undefined ? 1 : digits); }

  function cardClass(value, warnAt) { return value >= warnAt ? 'warn' : ''; }

  function renderCards(system) {
    document.getElementById('system-cards').innerHTML = `
      <div class="card ${cardClass(system.cpu_load_percent, 80)}">
        <div class="card-label">CPU load</div><div class="card-value">${fmt(system.cpu_load_percent)}%</div>
      </div>
      <div class="card ${cardClass(system.cpu_temperature_c, 80)}">
        <div class="card-label">CPU temp</div><div class="card-value">${fmt(system.cpu_temperature_c)}ﾂｰC</div>
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
      const lastRun = typeof info === 'object' && info.last_run ? ` ﾂｷ last run ${Api.escapeHtml(info.last_run)}` : '';
      return `<tr><td>${Api.escapeHtml(name)}</td><td>${Api.escapeHtml(status)}${lastRun}</td></tr>`;
    }).join('');
  }

  function renderDatabase(db) {
    document.getElementById('database-panel').innerHTML = `
      <div>size ${fmt(db.size_mb)} MB</div>
      <div>rows ${db.row_count.toLocaleString()}</div>
      <div>growth ${fmt(db.growth_mb_per_day)} MB/day</div>
      <div>capacity 竕・${db.projected_days_remaining == null ? 'n/a' : `${db.projected_days_remaining} days`}</div>
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
      latestSystem = system;
      loadResourceCharts();
      document.getElementById('system-rejected-total').textContent = rejects.total;
      RejectChips.render(document.getElementById('system-rejected-by-code'), rejects.by_code);
    }).catch((err) => showError(`System data unavailable: ${err.message || err.code}`))
      .finally(() => { pollTimer = setTimeout(poll, window.APP_CONFIG.POLL_INTERVAL_SYSTEM_MS); });
  }

  let resourcesChart = null;
  let ingestChart = null;
  let growthChart = null;
  let historyRange = '6h';
  let latestSystem = null;

  const HIST_RANGE_TO_MS = { '1h': 36e5, '6h': 216e5, '24h': 864e5, '7d': 6048e5 };
  const GATEWAY_SAMPLE_GAP_THRESHOLD_MS = 120000; // gateway_metrics samples once/min; 2x that is "stale"

  function loadResourceCharts() {
    const start = new Date(Date.now() - HIST_RANGE_TO_MS[historyRange]).toISOString();
    const end = new Date().toISOString();
    Api.systemHistory({ start, end, resolution: 'auto' }).then((data) => {
      const rawLabels = data.points.map((p) => TimeUtil.timeHM(p.sampled_at));
      const rawCpuTemp = data.points.map((p) => p.cpu_temperature_c);
      const rawCpuLoad = data.points.map((p) => p.cpu_load_percent);
      const rawMemUsed = data.points.map((p) => p.memory_used_percent);
      const rawIngestRate = data.points.map((p) => p.ingest_rate_per_min);
      const rawDbSize = data.points.map((p) => p.database_size_mb);
      const timestampsMs = data.points.map((p) => new Date(p.sampled_at).getTime());

      const { labels, series, noDataFromIndex } = Charts.appendNowGapTail(
        rawLabels, [rawCpuTemp, rawCpuLoad, rawMemUsed, rawIngestRate, rawDbSize],
        timestampsMs, GATEWAY_SAMPLE_GAP_THRESHOLD_MS, TimeUtil.timeHM,
      );
      const [cpuTemp, cpuLoad, memUsed, ingestRate, dbSize] = series;

      if (!resourcesChart) {
        const ctx = document.getElementById('resources-chart').getContext('2d');
        resourcesChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets: [
              { label: 'CPU temp (ﾂｰC)', data: cpuTemp, borderColor: 'rgb(207,34,46)', pointRadius: 0, borderWidth: 2, spanGaps: false },
              { label: 'CPU load (%)', data: cpuLoad, borderColor: 'rgb(47,111,237)', pointRadius: 0, borderWidth: 2, spanGaps: false },
              { label: 'Memory used (%)', data: memUsed, borderColor: 'rgb(130,80,223)', pointRadius: 0, borderWidth: 2, spanGaps: false },
              Charts.thresholdDataset('Throttle limit 80ﾂｰC', 80, labels.length, '207,34,46'),
            ],
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
              x: { ticks: { color: Charts.TICK_COLOR }, title: Charts.axisTitle('Time (ICT)') },
              y: { ticks: { color: Charts.TICK_COLOR }, title: Charts.axisTitle('ﾂｰC / %') },
            },
          },
        });
        resourcesChart.$noDataFromIndex = noDataFromIndex;
      } else {
        resourcesChart.data.labels = labels;
        resourcesChart.data.datasets[0].data = cpuTemp;
        resourcesChart.data.datasets[1].data = cpuLoad;
        resourcesChart.data.datasets[2].data = memUsed;
        resourcesChart.data.datasets[3].data = new Array(labels.length).fill(80);
        resourcesChart.$noDataFromIndex = noDataFromIndex;
        resourcesChart.update('none');
      }

      if (!ingestChart) {
        const ctx2 = document.getElementById('ingest-chart').getContext('2d');
        ingestChart = new Chart(ctx2, {
          type: 'bar',
          data: { labels, datasets: [{ label: 'Accepted (rec/min)', data: ingestRate, backgroundColor: ingestRate.map((v) => (v === 0 ? 'rgba(207,34,46,0.4)' : 'rgba(26,127,55,0.6)')) }] },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
              x: { ticks: { color: Charts.TICK_COLOR }, title: Charts.axisTitle('Time (ICT)') },
              y: { ticks: { color: Charts.TICK_COLOR }, title: Charts.axisTitle('Readings / min') },
            },
          },
        });
        ingestChart.$noDataFromIndex = noDataFromIndex;
      } else {
        ingestChart.data.labels = labels;
        ingestChart.data.datasets[0].data = ingestRate;
        ingestChart.data.datasets[0].backgroundColor = ingestRate.map((v) => (v === 0 ? 'rgba(207,34,46,0.4)' : 'rgba(26,127,55,0.6)'));
        ingestChart.$noDataFromIndex = noDataFromIndex;
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
              { label: 'Size (MB)', data: dbSize, borderColor: 'rgb(184,120,20)', pointRadius: 0, borderWidth: 2, spanGaps: false },
              { label: 'Projected', data: projected, borderColor: 'rgb(184,120,20)', borderDash: [4, 4], pointRadius: 0, borderWidth: 1 },
            ],
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
              x: { ticks: { color: Charts.TICK_COLOR }, title: Charts.axisTitle('Time (ICT)') },
              y: { ticks: { color: Charts.TICK_COLOR }, title: Charts.axisTitle('Size (MB)', '184,120,20') },
            },
          },
        });
        growthChart.$noDataFromIndex = noDataFromIndex;
      } else {
        growthChart.data.labels = labels;
        growthChart.data.datasets[0].data = dbSize;
        growthChart.data.datasets[1].data = projected;
        growthChart.$noDataFromIndex = noDataFromIndex;
        growthChart.update('none');
      }
    }).catch((err) => showError(`Resource history unavailable: ${err.message || err.code}`));
  }

  function projectGrowth(dbSizeSeries, growthPerDay) {
    const last = dbSizeSeries.filter((v) => v !== null).slice(-1)[0] || 0;
    const perPoint = (growthPerDay || 0) / dbSizeSeries.length;
    return dbSizeSeries.map((_, i) => Number((last + perPoint * i).toFixed(2)));
  }

  function loadSensorLimitEditor() {
    Api.sensorLimits().then((limits) => {
      document.getElementById('sensor-limits-editor-body').innerHTML = Object.entries(limits).map(([field, limit]) => `
        <tr data-field="${Api.escapeHtml(field)}">
          <td>${Api.escapeHtml(field)}</td>
          <td><input type="number" class="limit-min" value="${limit.min}" style="width:70px"></td>
          <td><input type="number" class="limit-max" value="${limit.max}" style="width:70px"></td>
          <td>${Api.escapeHtml(limit.updated_at)}</td>
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
      status.textContent = 'saving窶ｦ';
      Api.putSensorLimit(field, { min, max }).then((updated) => {
        status.textContent = `saved ﾂｷ ${updated.updated_at}`;
        row.children[3].textContent = updated.updated_at;
      }).catch((err) => {
        status.textContent = err.code === 'INVALID_PARAMETER' ? 'min must be less than max' : `error: ${err.message || err.code}`;
      });
    });
  }

  function mount(rootEl) { el = rootEl; el.innerHTML = TEMPLATE; document.getElementById('system-range-controls').addEventListener('click', (evt) => {
    const btn = evt.target.closest('button');
    if (!btn) return;
    document.querySelectorAll('#system-range-controls button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    historyRange = btn.dataset.range;
    loadResourceCharts();
  }); wireSensorLimitEditor(); loadSensorLimitEditor(); }
  function start() { if (pollTimer) return; poll(); }
  function stop() { clearTimeout(pollTimer); pollTimer = null; }

  return { mount, start, stop };
})();
