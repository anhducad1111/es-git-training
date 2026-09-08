window.LiveView = (function () {
  let el;
  let pollTimer = null;
  let selectedUid = null;
  let cardsPollTimer = null;
  let lastGoodCardsAt = null;

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
        <div id="live-stale-banner"></div>
        <div class="card-grid" id="metric-cards"></div>
        <!-- charts and tables from later tasks go below this line -->
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
    clearTimeout(cardsPollTimer);
    pollTimer = null;
  }

  function getSelectedUid() {
    return selectedUid;
  }

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
})();
