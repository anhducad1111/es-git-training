window.ControlView = (function () {
  const ADDRESS_STORAGE_KEY = 'roverControlAddress';
  const CAMERA_ADDRESS_STORAGE_KEY = 'roverControlCameraAddress';
  const RECONNECT_DELAY_MS = 2000;
  const DEFAULT_CAMERA_ADDRESS = '192.168.1.117';

  let el;
  let address = '';
  let cameraAddress = '';
  let ws = null;
  let reconnectTimer = null;
  let allowState = 'disconnected';
  let roverConnected = false;
  let gimbalPan = 90;
  let gimbalTilt = 90;

  let telemetryUid = null;
  let telemetryTimer = null;

  // A single semicircular dial reused for both the pan (N/S/W/E) and tilt (UP/DN/LVL)
  // gimbal-position gauges, mirroring robot-desktop-app's GimbalHUD widget (widgets/gimbal_hud.py).
  // The needle is a plain SVG <line>, rotated with a native SVG `rotate(angle cx cy)` transform
  // set from JS — value 90 (centered) points straight up, 0 points left, 180 points right.
  function gimbalDialSvg(idPrefix, topLabel, bottomLabel, leftLabel, rightLabel) {
    return `
      <svg class="control-gimbal-dial" viewBox="0 0 100 60" aria-hidden="true">
        <path d="M 10 52 A 40 40 0 0 1 90 52" fill="none" stroke="#ff2a85" stroke-opacity="0.35" stroke-width="1.5"></path>
        <line x1="50" y1="52" x2="50" y2="14" stroke="#3b82f6" stroke-opacity="0.3" stroke-dasharray="2,2"></line>
        <line id="${idPrefix}-needle" x1="50" y1="52" x2="50" y2="16" stroke="#ff2a85" stroke-width="2.4"></line>
        <circle cx="50" cy="52" r="2.4" fill="#ff2a85"></circle>
        <text x="50" y="9" text-anchor="middle" class="control-gimbal-dial-label">${topLabel}</text>
        <text x="50" y="59" text-anchor="middle" class="control-gimbal-dial-label control-gimbal-dial-label-dim">${bottomLabel}</text>
        <text x="4" y="55" text-anchor="start" class="control-gimbal-dial-label control-gimbal-dial-label-dim">${leftLabel}</text>
        <text x="96" y="55" text-anchor="end" class="control-gimbal-dial-label control-gimbal-dial-label-dim">${rightLabel}</text>
      </svg>
    `;
  }

  const TEMPLATE = `
    <div class="control-layout">
      <aside class="control-sidebar">
        <div class="control-sidebar-section">
          <div class="control-sidebar-title">TELEOPERATION</div>
          <div class="control-sidebar-sub">Drive the rover through the desktop app relay.<br>Keyboard control is active while this tab has focus.</div>
        </div>

        <div class="control-sidebar-section">
          <div class="control-sidebar-title">CONNECTION</div>
          <label class="control-field-label">Desktop app address</label>
          <input type="text" id="control-address" class="control-field-input" placeholder="192.168.1.50:8765">
          <div class="control-address-row">
            <button id="control-connect">Connect</button>
            <button id="control-disconnect">Disconnect</button>
          </div>
          <div id="control-status-banner" class="control-status-banner control-status-disconnected">Not connected</div>
          <label class="control-field-label">Camera address</label>
          <input type="text" id="control-camera-address" class="control-field-input" placeholder="192.168.1.117">
          <div class="control-address-row">
            <button id="control-camera-connect">Connect</button>
            <button id="control-camera-disconnect">Disconnect</button>
          </div>
        </div>

        <div class="control-sidebar-section">
          <div class="control-sidebar-title">CAMERA</div>
          <button class="control-disabled-btn control-disabled-block" disabled title="Not implemented in this iteration">OTA UPDATE</button>
        </div>
      </aside>

      <div class="control-main">
        <div class="control-video-row">
          <div class="control-video-panel">
            <div class="control-video-overlay-bar">
              <span id="control-tele-dist" class="control-tele-chip">DIST –</span>
              <span id="control-tele-temp" class="control-tele-chip">TEMP –</span>
              <span id="control-tele-hum" class="control-tele-chip">HUM –</span>
              <span id="control-tele-gas" class="control-tele-chip">GAS –</span>
              <span class="control-video-label">MJPEG</span>
            </div>
            <div class="control-video-body">
              <img id="control-camera-feed" class="control-camera-feed" alt="camera feed" hidden>
              <div id="control-video-placeholder" class="control-video-placeholder">No video</div>
              <div class="control-crosshair-h"></div>
              <div class="control-crosshair-v"></div>
              <div class="control-gimbal-hud">
                <div class="control-gimbal-hud-title">CAM <span>GIMBAL</span></div>
                ${gimbalDialSvg('control-tilt-dial', 'UP', 'DN', '', 'LVL')}
                <div class="control-gimbal-hud-value" id="control-tilt-offset">+0°</div>
                ${gimbalDialSvg('control-pan-dial', 'N', 'S', 'W', 'E')}
                <div class="control-gimbal-hud-value" id="control-pan-offset">+0°</div>
              </div>
            </div>
          </div>

          <div class="control-side-stats">
            <div class="card control-card">
              <div class="card-label">SPEED · PWM</div>
              <div class="card-value" id="control-speed-value">220</div>
              <input type="range" id="control-speed" class="control-input control-card-slider" min="180" max="255" value="220">
              <div class="control-card-sub-row"><span>180</span><span>255</span></div>
            </div>
            <div class="card control-card">
              <div class="card-label">AUTO-BRAKE</div>
              <div class="card-value" id="control-autobrake-state">–</div>
              <div class="limit-track"><div class="limit-fill" id="control-autobrake-fill" style="width:0%"></div></div>
              <div class="control-card-sub-row"><span id="control-autobrake-dist">dist –</span></div>
            </div>
            <div class="card control-card">
              <div class="card-label">CAMERA</div>
              <button id="control-snapshot" class="control-input control-side-btn">SNAPSHOT · SAVE JPEG</button>
              <label class="control-field-label">Resolution</label>
              <select id="control-resolution" class="control-input control-field-input">
                <option value="640,480">640x480 (30 FPS)</option>
                <option value="1280,720">1280x720 (15 FPS)</option>
                <option value="320,240">320x240 (60 FPS)</option>
                <option value="160,120">160x120 (90 FPS)</option>
              </select>
              <div class="control-address-row">
                <button id="control-flip-h" class="control-flip-btn">FLIP H</button>
                <button id="control-flip-v" class="control-flip-btn">FLIP V</button>
              </div>
            </div>
            <div class="card control-card">
              <div class="card-label">GIMBAL</div>
              <div class="control-gimbal-grid">
                <button class="control-drive-btn control-input" id="control-gimbal-up" data-pan-delta="0" data-tilt-delta="5">↑</button>
                <button class="control-drive-btn control-input" id="control-gimbal-left" data-pan-delta="-5" data-tilt-delta="0">←</button>
                <button class="control-drive-btn control-input" id="control-gimbal-center">C</button>
                <button class="control-drive-btn control-input" id="control-gimbal-right" data-pan-delta="5" data-tilt-delta="0">→</button>
                <button class="control-drive-btn control-input" id="control-gimbal-down" data-pan-delta="0" data-tilt-delta="-5">↓</button>
              </div>
            </div>
            <div class="card control-card">
              <div class="card-label">DRIVE</div>
              <div class="control-drive-pad">
                <button class="control-drive-btn control-drive-forward" data-command="forward" data-stop-on-release="true">↑</button>
                <div class="control-drive-row">
                  <button class="control-drive-btn control-drive-left" data-command="left" data-stop-on-release="true">←</button>
                  <button class="control-drive-btn control-drive-stop" data-command="stop">STOP</button>
                  <button class="control-drive-btn control-drive-right" data-command="right" data-stop-on-release="true">→</button>
                </div>
                <button class="control-drive-btn control-drive-backward" data-command="backward" data-stop-on-release="true">↓</button>
              </div>
            </div>
          </div>
        </div>

        <div id="control-rover-warning-slot"></div>

        <div class="control-keys-bar">
          <span class="control-keys-label">KEYS</span>
          <span class="control-key-chip">W/S drive</span>
          <span class="control-key-chip">A/D spin</span>
          <span class="control-key-chip">IJKL gimbal</span>
          <span class="control-key-chip">C center</span>
          <span class="control-key-chip control-key-chip-danger">SPACE stop</span>
        </div>
      </div>
    </div>
  `;

  function loadSaved(key) {
    try {
      return window.localStorage.getItem(key) || '';
    } catch (e) {
      return '';
    }
  }

  function saveValue(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      // localStorage unavailable (private mode, etc.) — connection still works this session.
    }
  }

  function showCameraFeed() {
    const img = document.getElementById('control-camera-feed');
    const placeholder = document.getElementById('control-video-placeholder');
    if (!img || !cameraAddress) return;
    img.src = `http://${cameraAddress}/640x480.mjpeg`;
    img.hidden = false;
    if (placeholder) placeholder.hidden = true;
  }

  function hideCameraFeed() {
    const img = document.getElementById('control-camera-feed');
    const placeholder = document.getElementById('control-video-placeholder');
    if (!img) return;
    img.removeAttribute('src');
    img.hidden = true;
    if (placeholder) placeholder.hidden = false;
  }

  function syncCameraToAllowState() {
    if (allowState === 'allowed') {
      showCameraFeed();
    } else {
      hideCameraFeed();
    }
  }

  function renderConnectionState(state) {
    const banner = document.getElementById('control-status-banner');
    if (!banner) return;
    banner.classList.remove('control-status-disconnected', 'control-status-not-allowed', 'control-status-allowed');
    if (state === 'allowed') {
      banner.classList.add('control-status-allowed');
      banner.textContent = 'Connected · control allowed';
    } else if (state === 'not-allowed') {
      banner.classList.add('control-status-not-allowed');
      banner.textContent = "Connected · control not allowed (desktop app hasn't granted access)";
    } else {
      banner.classList.add('control-status-disconnected');
      banner.textContent = 'Not connected';
    }
    el.querySelectorAll('.control-drive-btn, .control-input').forEach((elm) => {
      elm.disabled = state !== 'allowed';
    });
  }

  function renderRoverWarning() {
    const slot = document.getElementById('control-rover-warning-slot');
    if (!slot) return;
    if (allowState !== 'allowed' || roverConnected) {
      slot.innerHTML = '';
      return;
    }
    slot.innerHTML = '<div class="stale-banner">Connected to the desktop app, but the rover link is down.</div>';
  }

  function handleMessage(evt) {
    let data;
    try {
      data = JSON.parse(evt.data);
    } catch (e) {
      return;
    }
    if (!data || typeof data !== 'object') return;
    if (data.type === 'status') {
      allowState = data.allowed ? 'allowed' : 'not-allowed';
      roverConnected = !!data.rover_connected;
      renderConnectionState(allowState);
      renderRoverWarning();
      syncCameraToAllowState();
    } else if (data.type === 'rejected') {
      allowState = 'not-allowed';
      renderConnectionState(allowState);
      renderRoverWarning();
      syncCameraToAllowState();
    }
  }

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function scheduleReconnect() {
    clearReconnectTimer();
    reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
  }

  function connect() {
    if (!address) return;
    if (ws) return;
    let socket;
    try {
      socket = new WebSocket(`ws://${address}/`);
    } catch (e) {
      scheduleReconnect();
      return;
    }
    ws = socket;
    ws.onmessage = handleMessage;
    ws.onclose = () => {
      ws = null;
      allowState = 'disconnected';
      roverConnected = false;
      renderConnectionState('disconnected');
      renderRoverWarning();
      syncCameraToAllowState();
      scheduleReconnect();
    };
    ws.onerror = () => {
      // onclose fires right after onerror for a failed connection; let onclose drive reconnect.
    };
  }

  function disconnect() {
    clearReconnectTimer();
    if (ws && ws.readyState === WebSocket.OPEN && allowState === 'allowed') {
      ws.send(JSON.stringify({ type: 'command', command: 'stop' }));
    }
    allowState = 'disconnected';
    roverConnected = false;
    if (ws) {
      const socket = ws;
      ws = null;
      socket.onclose = null;
      socket.close();
    }
    renderConnectionState('disconnected');
    renderRoverWarning();
    syncCameraToAllowState();
  }

  function sendCommand(command) {
    if (allowState !== 'allowed') return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'command', command }));
  }

  // Distinct from sendCommand(): "action" messages (currently only "snapshot") tell the
  // desktop app to run a local action of its own, not to forward a string to the rover.
  // See design spec §3.5 — the desktop-app side of this is not built yet.
  function sendAction(action) {
    if (allowState !== 'allowed') return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'action', action }));
  }

  // Flip H/V never touch the relay (spec §3.7/§4.7) — purely how this browser renders the
  // camera <img> it already has open, so these are not gated by allowState.
  let flipH = false;
  let flipV = false;

  function updateFlipTransform() {
    const img = document.getElementById('control-camera-feed');
    if (img) img.style.transform = `scaleX(${flipH ? -1 : 1}) scaleY(${flipV ? -1 : 1})`;
  }

  // Needle at rest (0deg) is drawn pointing straight up; rotating by (value-90) degrees
  // clockwise about the dial's pivot (50,52 in the dial's own viewBox) sweeps it from
  // fully left (value=0) through straight up (value=90) to fully right (value=180).
  function setDialNeedle(idPrefix, value) {
    const needle = document.getElementById(`${idPrefix}-needle`);
    if (!needle) return;
    needle.setAttribute('transform', `rotate(${value - 90} 50 52)`);
  }

  function fmtOffset(value) {
    const offset = value - 90;
    return `${offset >= 0 ? '+' : ''}${offset}°`;
  }

  function updateGimbal() {
    document.getElementById('control-tilt-offset').textContent = fmtOffset(gimbalTilt);
    document.getElementById('control-pan-offset').textContent = fmtOffset(gimbalPan);
    setDialNeedle('control-tilt-dial', gimbalTilt);
    setDialNeedle('control-pan-dial', gimbalPan);
    sendCommand(`servo:${gimbalPan},${gimbalTilt}`);
  }

  function adjustGimbal(panDelta, tiltDelta) {
    gimbalPan = Math.max(0, Math.min(180, gimbalPan + panDelta));
    gimbalTilt = Math.max(0, Math.min(180, gimbalTilt + tiltDelta));
    updateGimbal();
  }

  function centerGimbal() {
    gimbalPan = 90;
    gimbalTilt = 90;
    updateGimbal();
  }

  // --- Telemetry overlay (read-only, from the existing HTTP telemetry API — independent of the WS relay) ---

  function fmtTele(value, digits, unit) {
    return value === null || value === undefined ? '–' : `${Number(value).toFixed(digits)}${unit}`;
  }

  function renderTelemetry(latest) {
    document.getElementById('control-tele-dist').textContent = `DIST ${fmtTele(latest.distance_cm, 0, ' cm')}`;
    document.getElementById('control-tele-temp').textContent = `TEMP ${fmtTele(latest.temperature_c, 1, ' °C')}`;
    document.getElementById('control-tele-hum').textContent = `HUM ${fmtTele(latest.humidity_pct, 0, ' %')}`;
    document.getElementById('control-tele-gas').textContent = `GAS ${fmtTele(latest.gas_ppm, 0, ' ppm')}`;

    const state = document.getElementById('control-autobrake-state');
    const fill = document.getElementById('control-autobrake-fill');
    const dist = document.getElementById('control-autobrake-dist');
    if (latest.auto_brake) {
      state.textContent = 'BRAKING';
      fill.style.background = 'var(--bad)';
    } else {
      state.textContent = 'CLEAR';
      fill.style.background = 'var(--ok)';
    }
    const distCm = latest.distance_cm;
    fill.style.width = distCm === null || distCm === undefined ? '0%' : `${Math.max(0, Math.min(100, (distCm / 100) * 100))}%`;
    dist.textContent = distCm === null || distCm === undefined ? 'dist –' : `dist ${Number(distCm).toFixed(0)} cm`;
  }

  function pollTelemetry() {
    if (!telemetryUid) {
      telemetryTimer = setTimeout(pollTelemetry, window.APP_CONFIG.POLL_INTERVAL_LIVE_MS);
      return;
    }
    Api.latest(telemetryUid)
      .then((latest) => renderTelemetry(latest))
      .catch(() => {})
      .finally(() => { telemetryTimer = setTimeout(pollTelemetry, window.APP_CONFIG.POLL_INTERVAL_LIVE_MS); });
  }

  function startTelemetry() {
    if (telemetryTimer) return;
    telemetryUid = RoverSelection.get();
    if (!telemetryUid) {
      Api.rovers().then((rovers) => {
        if (rovers.length > 0 && !telemetryUid) telemetryUid = rovers[0].device_uid;
      }).catch(() => {});
    }
    pollTelemetry();
  }

  function stopTelemetry() {
    if (telemetryTimer) {
      clearTimeout(telemetryTimer);
      telemetryTimer = null;
    }
  }

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;

    address = loadSaved(ADDRESS_STORAGE_KEY);
    document.getElementById('control-address').value = address;
    renderConnectionState('disconnected');
    // Paint the dials at their 90/90 default without going through updateGimbal(), which
    // would also (harmlessly, but needlessly) attempt to sendCommand() before any connection exists.
    setDialNeedle('control-tilt-dial', gimbalTilt);
    setDialNeedle('control-pan-dial', gimbalPan);
    document.getElementById('control-tilt-offset').textContent = fmtOffset(gimbalTilt);
    document.getElementById('control-pan-offset').textContent = fmtOffset(gimbalPan);

    document.getElementById('control-connect').addEventListener('click', () => {
      const value = document.getElementById('control-address').value.trim();
      if (!value) return;
      disconnect();
      address = value;
      saveValue(ADDRESS_STORAGE_KEY, address);
      connect();
    });

    document.getElementById('control-disconnect').addEventListener('click', () => {
      disconnect();
    });

    cameraAddress = loadSaved(CAMERA_ADDRESS_STORAGE_KEY) || DEFAULT_CAMERA_ADDRESS;
    document.getElementById('control-camera-address').value = cameraAddress;

    document.getElementById('control-camera-connect').addEventListener('click', () => {
      const value = document.getElementById('control-camera-address').value.trim();
      if (!value) return;
      cameraAddress = value;
      saveValue(CAMERA_ADDRESS_STORAGE_KEY, cameraAddress);
      showCameraFeed();
    });

    document.getElementById('control-camera-disconnect').addEventListener('click', () => {
      hideCameraFeed();
    });

    document.querySelectorAll('.control-drive-btn[data-command]').forEach((btn) => {
      const command = btn.dataset.command;
      const stopOnRelease = btn.dataset.stopOnRelease === 'true';
      btn.addEventListener('mousedown', () => sendCommand(command));
      btn.addEventListener('touchstart', (e) => { e.preventDefault(); sendCommand(command); });
      if (stopOnRelease) {
        btn.addEventListener('mouseup', () => sendCommand('stop'));
        btn.addEventListener('mouseleave', () => sendCommand('stop'));
        btn.addEventListener('touchend', () => sendCommand('stop'));
        btn.addEventListener('touchcancel', () => sendCommand('stop'));
      }
    });

    let activeDriveKey = null;

    window.addEventListener('blur', () => {
      if (activeDriveKey) {
        activeDriveKey = null;
        sendCommand('stop');
      }
    });

    // Keybinds mirror robot-desktop-app exactly: W/S/A/D drive, IJKL gimbal (±5° per press,
    // no auto-repeat), C center, Space stop.
    document.addEventListener('keydown', (evt) => {
      if (evt.repeat) return;
      if (!el.classList.contains('active')) return;
      const activeTag = document.activeElement && document.activeElement.tagName;
      if (activeTag === 'INPUT' || activeTag === 'TEXTAREA') return;

      const key = evt.key.toLowerCase();
      const driveKeyToCommand = { w: 'forward', s: 'backward', a: 'left', d: 'right' };
      if (driveKeyToCommand[key]) {
        evt.preventDefault();
        activeDriveKey = key;
        sendCommand(driveKeyToCommand[key]);
      } else if (key === ' ') {
        evt.preventDefault();
        sendCommand('stop');
      } else if (key === 'i') {
        evt.preventDefault();
        adjustGimbal(0, 5);
      } else if (key === 'k') {
        evt.preventDefault();
        adjustGimbal(0, -5);
      } else if (key === 'j') {
        evt.preventDefault();
        adjustGimbal(-5, 0);
      } else if (key === 'l') {
        evt.preventDefault();
        adjustGimbal(5, 0);
      } else if (key === 'c') {
        evt.preventDefault();
        centerGimbal();
      }
    });

    document.addEventListener('keyup', (evt) => {
      const key = evt.key.toLowerCase();
      const driveKeyToCommand = { w: 'forward', s: 'backward', a: 'left', d: 'right' };
      if (driveKeyToCommand[key] && key === activeDriveKey) {
        activeDriveKey = null;
        sendCommand('stop');
      }
    });

    document.getElementById('control-speed').addEventListener('input', (evt) => {
      document.getElementById('control-speed-value').textContent = evt.target.value;
    });
    document.getElementById('control-speed').addEventListener('change', (evt) => {
      sendCommand(`speed:${evt.target.value}`);
    });

    ['control-gimbal-up', 'control-gimbal-left', 'control-gimbal-right', 'control-gimbal-down'].forEach((id) => {
      document.getElementById(id).addEventListener('click', () => {
        const btn = document.getElementById(id);
        adjustGimbal(Number(btn.dataset.panDelta), Number(btn.dataset.tiltDelta));
      });
    });

    document.getElementById('control-gimbal-center').addEventListener('click', () => {
      centerGimbal();
    });

    document.getElementById('control-snapshot').addEventListener('click', () => {
      sendAction('snapshot');
    });

    document.getElementById('control-resolution').addEventListener('change', (evt) => {
      sendCommand(`resolution:${evt.target.value}`);
    });

    document.getElementById('control-flip-h').addEventListener('click', () => {
      flipH = !flipH;
      document.getElementById('control-flip-h').classList.toggle('active', flipH);
      updateFlipTransform();
    });

    document.getElementById('control-flip-v').addEventListener('click', () => {
      flipV = !flipV;
      document.getElementById('control-flip-v').classList.toggle('active', flipV);
      updateFlipTransform();
    });

    RoverSelection.subscribe((newUid) => {
      telemetryUid = newUid;
    });
  }

  function start() {
    if (address) connect();
    startTelemetry();
  }

  function stop() {
    disconnect();
    stopTelemetry();
  }

  return { mount, start, stop };
})();
