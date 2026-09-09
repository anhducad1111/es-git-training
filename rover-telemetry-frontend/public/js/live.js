window.LiveView = (function () {
  let el;
  let pollTimer = null;
  let selectedUid = null;
  let cardsPollTimer = null;
  let lastGoodCardsAt = null;
  let cardsPollGeneration = 0;
  let fleetPollGeneration = 0;

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
        <div class="panel">
          <div class="panel-title" id="telemetry-panel-title">Telemetry</div>
          <div class="range-controls" id="telemetry-range-controls">
            <button data-range="10m">10 m</button><button data-range="1h">1 h</button>
            <button data-range="6h" class="active">6 h</button><button data-range="24h">24 h</button>
            <button data-range="7d">7 d</button><button data-range="30d">30 d</button>
          </div>
          <canvas id="telemetry-chart" height="90"></canvas>
        </div>
        <div class="panel">
          <div class="panel-title">Obstacle distance · live</div>
          <canvas id="obstacle-chart" height="70"></canvas>
        </div>
        <div class="panel">
          <div class="panel-title">Media Gallery</div>
          <div id="media-gallery" class="media-gallery"></div>
        </div>
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
      </div>
    </div>
  `;

  const incomingBuffers = {}; // uid -> array of {recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, state}
  const MAX_INCOMING_ROWS = 8;

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
      <div class="fleet-item ${r.device_uid === selectedUid ? 'selected' : ''}" data-uid="${Api.escapeHtml(r.device_uid)}">
        <span class="dot ${statusDotClass(r.status)}"></span>
        <span class="fleet-uid">${Api.escapeHtml(r.device_uid)}</span>
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
    const myGeneration = fleetPollGeneration;
    Promise.all([Api.rovers(), Api.validationErrorsSummary('24h')])
      .then(([rovers, rejects]) => {
        clearError();
        renderFleet(rovers);
        document.getElementById('rejected-total').textContent = rejects.total;
        document.getElementById('rejected-by-code').textContent = Object.entries(rejects.by_code)
          .map(([code, count]) => `${code} ${count}`).join(' · ');
      })
      .catch((err) => showError(`Fleet list unavailable: ${err.message || err.code}`))
      .finally(() => {
        if (myGeneration === fleetPollGeneration) {
          pollTimer = setTimeout(pollFleetAndRejects, window.APP_CONFIG.POLL_INTERVAL_LIVE_MS);
        }
      });
  }

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;
  }

  function start() {
    if (!pollTimer) {
      pollFleetAndRejects();
    }
    const uid = getSelectedUid();
    if (uid && !cardsPollTimer) {
      cardsPollGeneration += 1;
      pollCards(uid);
    }
  }

  function stop() {
    clearTimeout(pollTimer);
    clearTimeout(cardsPollTimer);
    pollTimer = null;
    cardsPollTimer = null;
    cardsPollGeneration += 1;
    fleetPollGeneration += 1;
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
    const myGeneration = cardsPollGeneration;
    const today = new Date().toISOString().slice(0, 10);
    Promise.all([Api.latest(uid), Api.summary(uid, { granularity: 'day', start: today, end: today })])
      .then(([latest, summary]) => {
        if (myGeneration !== cardsPollGeneration) return;
        lastGoodCardsAt = Date.now();
        showStale(null);
        renderCards(latest, summary.buckets);
        loadTelemetryChart(uid);
        loadObstacleChart(uid);
        pollEventsAndLimits(uid, latest);
      })
      .catch((err) => {
        if (myGeneration !== cardsPollGeneration) return;
        const staleFor = lastGoodCardsAt ? `stale since ${new Date(lastGoodCardsAt).toLocaleTimeString()}` : 'no data yet';
        showStale(`${err.code === 'NOT_FOUND' ? 'Rover has never reported.' : `Live data unavailable (${err.message || err.code}).`} ${staleFor}`);
      })
      .finally(() => {
        if (myGeneration === cardsPollGeneration && document.getElementById('metric-cards')) {
          cardsPollTimer = setTimeout(() => pollCards(uid), window.APP_CONFIG.POLL_INTERVAL_LIVE_MS);
        }
      });
  }

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

  function loadMediaGallery(uid) {
    Api.media(uid, { limit: 50 }).then((data) => {
      const gallery = document.getElementById('media-gallery');
      if (!data.media || data.media.length === 0) {
        gallery.innerHTML = '<p style="color: var(--text-dim);">No media files yet.</p>';
        return;
      }
      gallery.innerHTML = data.media.map((m) => {
        const icon = m.media_type === 'photo' ? '📷' : '🎥';
        return `
          <div class="media-item" data-id="${m.id}">
            <div class="media-preview" style="background: #eee; border-radius: 4px; padding: 8px; text-align: center; font-size: 28px;">
              ${icon}
            </div>
            <div class="media-info">
              <div class="media-type">${m.media_type}</div>
              <div class="media-time">${new Date(m.captured_at).toLocaleString()}</div>
              <div class="media-size">${(m.file_size_bytes / 1024).toFixed(0)} KB</div>
            </div>
            <button class="media-delete-btn" data-id="${m.id}" aria-label="Delete media">✕</button>
          </div>
        `;
      }).join('');

      // Add delete handlers
      gallery.querySelectorAll('.media-delete-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          if (confirm('Delete this media file?')) {
            Api.deleteMedia(uid, id).then(() => {
              loadMediaGallery(uid);
            }).catch((err) => {
              showError(`Failed to delete media: ${err.message || err.code}`);
            });
          }
        });
      });
    }).catch((err) => {
      showError(`Media gallery unavailable: ${err.message || err.code}`);
      document.getElementById('media-gallery').innerHTML = '<p style="color: var(--text-dim);">Media unavailable.</p>';
    });
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

  return {
    mount,
    start,
    stop,
    getSelectedUid,
    onRoverSelected(uid) {
      clearTimeout(cardsPollTimer);
      cardsPollGeneration += 1;
      lastGoodCardsAt = null;
      pollCards(uid);
      loadMediaGallery(uid);
    },
  };
})();
