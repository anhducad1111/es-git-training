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
      <div>capacity ≈ ${db.projected_days_remaining == null ? 'n/a' : `${db.projected_days_remaining} days`}</div>
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
