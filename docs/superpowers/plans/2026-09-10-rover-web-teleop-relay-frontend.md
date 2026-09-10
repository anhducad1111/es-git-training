# Rover Web Teleop Relay — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new "操作" (Control) tab to `rover-telemetry-frontend` that connects directly to `robot-desktop-app`'s (not-yet-built) WebSocket relay server and lets an operator drive the rover, adjust speed, and move the camera gimbal, with the UI correctly reflecting connect/allow state.

**Architecture:** A new `ControlView` module (same `mount(el)`/`start()`/`stop()` contract as `LiveView`/`HistoryView`/`GalleryView`/`SystemView`) owns a single browser-native `WebSocket` to `ws://<desktop_ip:port>/`. It sends `{"type":"command","command":"<string>"}` messages and reacts to `{"type":"status",...}` / `{"type":"rejected",...}` messages from the desktop app, per `docs/superpowers/specs/2026-09-10-rover-web-teleop-relay-design.md` §4–§6. `start()`/`stop()` open/close the socket so the connection only lives while the tab is active, matching how `app.js` already calls `stop()` on tab switch.

**Tech Stack:** Vanilla JS (no build step, no framework — matches every other view in this frontend), browser `WebSocket` API, `localStorage` for the remembered desktop address.

**Spec:** `docs/superpowers/specs/2026-09-10-rover-web-teleop-relay-design.md` (sections 4, 5, 6). Section 3 (desktop app server) and its toggle/auto-revert behavior are **out of scope for this plan** — the frontend is built strictly to the JSON protocol the spec already defines, with no server or mock included in this repo.

## Global Constraints

- No build tooling: plain `<script>` tags, ES5-compatible function style matching existing files (`window.XView = (function () { ... })();`).
- No new dependencies. Use the native `WebSocket` API only.
- This frontend has **no automated JS test suite** (`rover-telemetry-frontend` has no `package.json`/test runner). Every task's verification step is a concrete, manual browser check — open the page (`rover-telemetry-frontend/public/index.html` served through the existing local web server), use devtools/console, and confirm the described behavior. This matches how every other view in this codebase (`live.js`, `gallery.js`, `system.js`) is verified.
- Command vocabulary is fixed and reused verbatim, do not invent new commands: `forward`, `backward`, `left`, `right`, `stop`, `speed:<N>`, `servo:<pan>,<tilt>`.
- Protocol is fixed, do not add fields: outgoing `{"type":"command","command":"<string>"}`; incoming `{"type":"status","allowed":<bool>,"rover_connected":<bool>}` or `{"type":"rejected","reason":"not_allowed"}`.
- Follow existing CSS variable/class conventions in `rover-telemetry-frontend/public/css/style.css` (`--accent`, `--bad`, `--warn`, `--ok`, `.panel`, `.panel-title`, `.error-banner`, `.card` etc.) rather than introducing a new visual language.
- Reconnect backoff is a fixed 2s delay (matches `RoverWebSocket`'s own retry interval per the spec).

---

## File Layout

```
rover-telemetry-frontend/public/
├── index.html          # MODIFY: add "操作" tab button, #view-control section, control.js script tag
├── css/style.css        # MODIFY: append .control-* styles at end of file
└── js/
    └── control.js        # CREATE: ControlView module (mount/start/stop, WS lifecycle, UI rendering, command sending)
```

No other existing file needs to change. `control.js` does not depend on `Api`, `RoverSelection`, or `Charts` — it is fully self-contained, talking only to the desktop app's WebSocket.

---

### Task 1: Tab shell + address form (no WebSocket yet)

**Files:**
- Modify: `rover-telemetry-frontend/public/index.html:13-17` (nav), `:22-25` (main sections), `:35-39` (scripts)
- Create: `rover-telemetry-frontend/public/js/control.js`
- Modify: `rover-telemetry-frontend/public/css/style.css` (append at end, after line 183)

**Interfaces:**
- Produces: `window.ControlView` object with `{ mount(rootEl), start(), stop() }`, matching the shape `app.js` already expects for every entry in its `views` map (`rover-telemetry-frontend/public/js/app.js:2`).
- Produces (internal, used by later tasks in this same file): module-level `let ws = null;`, `let address = '';`, `const ADDRESS_STORAGE_KEY = 'roverControlAddress';`, `function renderStatusBanner(state)`, `function loadSavedAddress()`, `function saveAddress(value)`.

- [ ] **Step 1: Add the tab button and view section to `index.html`**

Edit `rover-telemetry-frontend/public/index.html`:

```html
  <nav class="tabs">
    <button class="tab-btn active" data-tab="live">LIVE</button>
    <button class="tab-btn" data-tab="history">HISTORY</button>
    <button class="tab-btn" data-tab="gallery">GALLERY</button>
    <button class="tab-btn" data-tab="control">操作</button>
    <button class="tab-btn" data-tab="system">SYSTEM</button>
  </nav>
```

```html
<main>
  <section id="view-live" class="view active"></section>
  <section id="view-history" class="view"></section>
  <section id="view-gallery" class="view"></section>
  <section id="view-control" class="view"></section>
  <section id="view-system" class="view"></section>
</main>
```

```html
<script src="js/gallery.js"></script>
<script src="js/control.js"></script>
<script src="js/system.js"></script>
```

- [ ] **Step 2: Register the view in `app.js`**

Edit `rover-telemetry-frontend/public/js/app.js:2`:

```javascript
  const views = { live: window.LiveView, history: window.HistoryView, gallery: window.GalleryView, control: window.ControlView, system: window.SystemView };
```

And add the mount call alongside the others (`rover-telemetry-frontend/public/js/app.js:38-41`):

```javascript
  views.live.mount(document.getElementById('view-live'));
  views.history.mount(document.getElementById('view-history'));
  views.gallery.mount(document.getElementById('view-gallery'));
  views.control.mount(document.getElementById('view-control'));
  views.system.mount(document.getElementById('view-system'));
```

- [ ] **Step 3: Create `control.js` with the address form and a stub status banner**

Create `rover-telemetry-frontend/public/js/control.js`:

```javascript
window.ControlView = (function () {
  const ADDRESS_STORAGE_KEY = 'roverControlAddress';

  let el;
  let address = '';
  let ws = null;

  const TEMPLATE = `
    <div class="panel">
      <div class="panel-title">Desktop App Connection</div>
      <div class="control-address-row">
        <label>Desktop app address
          <input type="text" id="control-address" placeholder="192.168.1.50:8765">
        </label>
        <button id="control-connect">接続</button>
        <button id="control-disconnect">切断</button>
      </div>
      <div id="control-status-banner" class="control-status-banner control-status-disconnected">未接続</div>
    </div>
    <div class="panel">
      <div class="panel-title">Drive</div>
      <div id="control-drive-pad" class="control-drive-pad"></div>
    </div>
  `;

  function loadSavedAddress() {
    try {
      return window.localStorage.getItem(ADDRESS_STORAGE_KEY) || '';
    } catch (e) {
      return '';
    }
  }

  function saveAddress(value) {
    try {
      window.localStorage.setItem(ADDRESS_STORAGE_KEY, value);
    } catch (e) {
      // localStorage unavailable (private mode, etc.) — connection still works this session.
    }
  }

  function renderStatusBanner(state) {
    const banner = document.getElementById('control-status-banner');
    if (!banner) return;
    banner.classList.remove('control-status-disconnected', 'control-status-not-allowed', 'control-status-allowed');
    if (state === 'allowed') {
      banner.classList.add('control-status-allowed');
      banner.textContent = '接続済み・操作可';
    } else if (state === 'not-allowed') {
      banner.classList.add('control-status-not-allowed');
      banner.textContent = '接続済み・操作不可（デスクトップ側で未許可）';
    } else {
      banner.classList.add('control-status-disconnected');
      banner.textContent = '未接続';
    }
  }

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;

    address = loadSavedAddress();
    document.getElementById('control-address').value = address;
    renderStatusBanner('disconnected');

    document.getElementById('control-connect').addEventListener('click', () => {
      const value = document.getElementById('control-address').value.trim();
      if (!value) return;
      address = value;
      saveAddress(address);
    });

    document.getElementById('control-disconnect').addEventListener('click', () => {
      renderStatusBanner('disconnected');
    });
  }

  function start() {}
  function stop() {}

  return { mount, start, stop };
})();
```

- [ ] **Step 4: Append base layout styles to `style.css`**

Append to `rover-telemetry-frontend/public/css/style.css` (after line 183):

```css

.control-address-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.control-address-row input { padding: 5px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: 13px; width: 200px; }
.control-address-row button { padding: 5px 12px; border: 1px solid var(--border); background: var(--panel); border-radius: 4px; cursor: pointer; font-size: 12px; }

.control-status-banner { margin-top: 10px; padding: 6px 10px; border-radius: 4px; font-size: 13px; font-weight: 600; }
.control-status-disconnected { background: #fdeceb; border: 1px solid var(--bad); color: var(--bad); }
.control-status-not-allowed { background: #fff6e5; border: 1px solid var(--warn); color: var(--warn); }
.control-status-allowed { background: #eaf6ec; border: 1px solid var(--ok); color: var(--ok); }
```

- [ ] **Step 5: Manual verification — tab wiring**

Open `rover-telemetry-frontend/public/index.html` through the existing local web server (e.g. `http://localhost/es-git-training/rover-telemetry-frontend/public/index.html`) in a browser.

Confirm:
- A "操作" tab button appears between GALLERY and SYSTEM.
- Clicking it shows the Desktop App Connection panel and a "未接続" red banner, with no errors in the devtools console.
- Typing an address (e.g. `192.168.1.50:8765`) and clicking 接続 does not throw; reloading the page shows the same address pre-filled in the input (proves `localStorage` round-trip).
- Switching to another tab and back does not duplicate the panel or throw.

- [ ] **Step 6: Commit**

```bash
git add rover-telemetry-frontend/public/index.html rover-telemetry-frontend/public/js/app.js rover-telemetry-frontend/public/js/control.js rover-telemetry-frontend/public/css/style.css
git commit -m "$(cat <<'EOF'
feat: add rover control tab shell with desktop address form

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012PwaDTKmN8jroC2Gqx6nDV
EOF
)"
```

---

### Task 2: WebSocket connection lifecycle (connect, disconnect, reconnect, status handling)

**Files:**
- Modify: `rover-telemetry-frontend/public/js/control.js`

**Interfaces:**
- Consumes: `renderStatusBanner(state)`, `ADDRESS_STORAGE_KEY`, `address`, `ws` from Task 1.
- Produces: `function connect()`, `function disconnect()`, `function scheduleReconnect()`, module-level `let reconnectTimer = null;`, `let allowState = 'disconnected';` (`'disconnected' | 'not-allowed' | 'allowed'`), `let roverConnected = false;`. `start()` now calls `connect()` if an address is set; `stop()` now calls `disconnect()` and clears any pending reconnect.

- [ ] **Step 1: Add connection state and the `connect`/`disconnect`/`scheduleReconnect` functions**

Edit `rover-telemetry-frontend/public/js/control.js` — add near the top, after `let ws = null;`:

```javascript
  let reconnectTimer = null;
  let allowState = 'disconnected';
  let roverConnected = false;
  const RECONNECT_DELAY_MS = 2000;
```

Add after `renderStatusBanner`:

```javascript
  function renderRoverWarning() {
    let warning = document.getElementById('control-rover-warning');
    if (allowState !== 'allowed' || roverConnected) {
      if (warning) warning.remove();
      return;
    }
    if (!warning) {
      warning = document.createElement('div');
      warning.id = 'control-rover-warning';
      warning.className = 'stale-banner';
      document.getElementById('control-status-banner').insertAdjacentElement('afterend', warning);
    }
    warning.textContent = 'デスクトップアプリには接続していますが、ローバーとの接続が切れています。';
  }

  function handleMessage(evt) {
    let data;
    try {
      data = JSON.parse(evt.data);
    } catch (e) {
      return;
    }
    if (data.type === 'status') {
      allowState = data.allowed ? 'allowed' : 'not-allowed';
      roverConnected = !!data.rover_connected;
      renderStatusBanner(allowState);
      renderRoverWarning();
    } else if (data.type === 'rejected') {
      renderStatusBanner('not-allowed');
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
      renderStatusBanner('disconnected');
      renderRoverWarning();
      scheduleReconnect();
    };
    ws.onerror = () => {
      // onclose fires right after onerror for a failed connection; let onclose drive reconnect.
    };
  }

  function disconnect() {
    clearReconnectTimer();
    allowState = 'disconnected';
    roverConnected = false;
    if (ws) {
      const socket = ws;
      ws = null;
      socket.onclose = null;
      socket.close();
    }
    renderStatusBanner('disconnected');
    renderRoverWarning();
  }
```

- [ ] **Step 2: Wire the connect/disconnect buttons and `start`/`stop` to the new functions**

Edit the `mount` function's button handlers:

```javascript
    document.getElementById('control-connect').addEventListener('click', () => {
      const value = document.getElementById('control-address').value.trim();
      if (!value) return;
      disconnect();
      address = value;
      saveAddress(address);
      connect();
    });

    document.getElementById('control-disconnect').addEventListener('click', () => {
      disconnect();
    });
```

Replace the stub `start`/`stop`:

```javascript
  function start() {
    if (address) connect();
  }

  function stop() {
    disconnect();
  }
```

- [ ] **Step 3: Manual verification — connect/disconnect/reconnect behavior**

With no relay server running yet (none exists — this is intentional, per plan scope):

- Open the Control tab, enter any `host:port` (e.g. `127.0.0.1:9`, a port nothing listens on), click 接続.
- Confirm the banner stays/returns to "未接続" within ~2s of the failed attempt and the devtools console shows no uncaught exceptions (a WebSocket connection error is expected and fine — just not an uncaught JS error).
- Confirm it keeps retrying roughly every 2s (watch the Network/WS tab in devtools for repeated connection attempts) without the retries stacking up (only one attempt in flight at a time).
- Click 切断: confirm retries stop (no new connection attempts appear in devtools after a few seconds).
- Switch to another tab and back: confirm no duplicate reconnect loops start (check devtools for connection attempt frequency staying at one per ~2s, not multiplying).

Full verification of the `status`/`rejected` message handling (banner text, rover-offline warning) requires a real WebSocket peer sending those messages, which this task does not yet have — it is covered in Task 5 Step 3 against a throwaway local server. For this task, confirm only the connect/disconnect/reconnect mechanics above.

- [ ] **Step 4: Commit**

```bash
git add rover-telemetry-frontend/public/js/control.js
git commit -m "$(cat <<'EOF'
feat: add WebSocket connect/disconnect/reconnect lifecycle to rover control tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012PwaDTKmN8jroC2Gqx6nDV
EOF
)"
```

---

### Task 3: Drive controls (forward/backward/left/right/stop, hold-to-drive + keyboard)

**Files:**
- Modify: `rover-telemetry-frontend/public/js/control.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `ws`, `allowState` from Task 2.
- Produces: `function sendCommand(command)` (guards on `allowState === 'allowed'` and `ws` open state before sending; used by Tasks 3 and 4), drive pad DOM built in `mount`.

- [ ] **Step 1: Add `sendCommand` and the drive pad markup**

Edit `rover-telemetry-frontend/public/js/control.js` — add after `disconnect()`:

```javascript
  function sendCommand(command) {
    if (allowState !== 'allowed') return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'command', command }));
  }
```

Replace the `#control-drive-pad` div's contents by changing the `TEMPLATE`'s drive panel:

```html
    <div class="panel">
      <div class="panel-title">Drive</div>
      <div class="control-drive-pad">
        <button class="control-drive-btn control-drive-forward" data-command="forward" data-stop-on-release="true">↑</button>
        <div class="control-drive-row">
          <button class="control-drive-btn control-drive-left" data-command="left" data-stop-on-release="true">←</button>
          <button class="control-drive-btn control-drive-stop" data-command="stop">STOP</button>
          <button class="control-drive-btn control-drive-right" data-command="right" data-stop-on-release="true">→</button>
        </div>
        <button class="control-drive-btn control-drive-backward" data-command="backward" data-stop-on-release="true">↓</button>
      </div>
      <p class="control-hint">矢印キーで走行、Spaceで緊急停止（このタブにフォーカスがある間）</p>
    </div>
```

- [ ] **Step 2: Wire hold-to-drive button behavior**

Add to `mount`, after the connect/disconnect handlers:

```javascript
    document.querySelectorAll('.control-drive-btn').forEach((btn) => {
      const command = btn.dataset.command;
      const stopOnRelease = btn.dataset.stopOnRelease === 'true';
      btn.addEventListener('mousedown', () => sendCommand(command));
      btn.addEventListener('touchstart', (e) => { e.preventDefault(); sendCommand(command); });
      if (stopOnRelease) {
        btn.addEventListener('mouseup', () => sendCommand('stop'));
        btn.addEventListener('mouseleave', () => sendCommand('stop'));
        btn.addEventListener('touchend', () => sendCommand('stop'));
      }
    });
```

- [ ] **Step 3: Wire keyboard bindings (arrow keys hold-to-drive, Space = stop)**

Add to `mount`:

```javascript
    let activeDriveKey = null;

    document.addEventListener('keydown', (evt) => {
      if (evt.repeat) return;
      if (!el.closest('.view.active') || !el.classList.contains('active')) return;
      const keyToCommand = { ArrowUp: 'forward', ArrowDown: 'backward', ArrowLeft: 'left', ArrowRight: 'right' };
      if (keyToCommand[evt.key]) {
        activeDriveKey = evt.key;
        sendCommand(keyToCommand[evt.key]);
      } else if (evt.key === ' ') {
        sendCommand('stop');
      }
    });

    document.addEventListener('keyup', (evt) => {
      const keyToCommand = { ArrowUp: 'forward', ArrowDown: 'backward', ArrowLeft: 'left', ArrowRight: 'right' };
      if (keyToCommand[evt.key] && evt.key === activeDriveKey) {
        activeDriveKey = null;
        sendCommand('stop');
      }
    });
```

Note: `el.classList.contains('active')` checks the view's own class, which `app.js` toggles on tab switch (`rover-telemetry-frontend/public/js/app.js:6`) — this keeps arrow keys from driving the rover while the user is on a different tab (e.g. typing in a History date field).

- [ ] **Step 4: Disable drive controls unless `allowState === 'allowed'`**

Add to `renderStatusBanner` (rename conceptually but keep the function name to avoid touching Task 1/2 call sites — just extend its body):

```javascript
  function renderStatusBanner(state) {
    const banner = document.getElementById('control-status-banner');
    if (!banner) return;
    banner.classList.remove('control-status-disconnected', 'control-status-not-allowed', 'control-status-allowed');
    if (state === 'allowed') {
      banner.classList.add('control-status-allowed');
      banner.textContent = '接続済み・操作可';
    } else if (state === 'not-allowed') {
      banner.classList.add('control-status-not-allowed');
      banner.textContent = '接続済み・操作不可（デスクトップ側で未許可）';
    } else {
      banner.classList.add('control-status-disconnected');
      banner.textContent = '未接続';
    }
    document.querySelectorAll('.control-drive-btn, .control-input').forEach((elm) => {
      elm.disabled = state !== 'allowed';
    });
  }
```

(`.control-input` is a class Task 4's speed slider and gimbal controls will use, so they're covered by this same guard once added.)

- [ ] **Step 5: Add drive pad styles**

Append to `rover-telemetry-frontend/public/css/style.css`:

```css

.control-hint { font-size: 12px; color: var(--text-dim); margin-top: 8px; }
.control-drive-pad { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.control-drive-row { display: flex; gap: 6px; }
.control-drive-btn {
  width: 64px; height: 48px; border: 1px solid var(--border); background: var(--panel); border-radius: 6px;
  font-size: 18px; cursor: pointer; user-select: none;
}
.control-drive-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.control-drive-stop { background: var(--bad); color: #fff; border-color: var(--bad); font-size: 12px; font-weight: 700; }
.control-drive-stop:disabled { background: var(--bad); opacity: 0.4; }
```

- [ ] **Step 6: Manual verification — drive controls gate correctly**

- Open the Control tab with no connection: confirm all drive buttons render visually disabled (grayed, `cursor: not-allowed`) and clicking/holding them does nothing (no exception, no attempted `ws.send`).
- Confirm arrow keys do nothing while a text input (e.g. the address field) has focus, and do nothing while another tab is active (switch to History, press ArrowLeft/Right, confirm no drive command is attempted).

`allowState` is only ever set to `'allowed'` by a real `status` message (Task 2), so the enabled-controls path (buttons active, keypresses actually calling `sendCommand`, and the exact JSON payload sent) is verified end-to-end in Task 5 Step 3 against a throwaway local server, once the drive/speed/gimbal wiring from Tasks 3–4 is complete.

- [ ] **Step 7: Commit**

```bash
git add rover-telemetry-frontend/public/js/control.js rover-telemetry-frontend/public/css/style.css
git commit -m "$(cat <<'EOF'
feat: add hold-to-drive controls and keyboard bindings to rover control tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012PwaDTKmN8jroC2Gqx6nDV
EOF
)"
```

---

### Task 4: Speed slider and gimbal controls

**Files:**
- Modify: `rover-telemetry-frontend/public/js/control.js`
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- Consumes: `sendCommand(command)` from Task 3.
- Produces: module-level `let gimbalPan = 90;`, `let gimbalTilt = 90;` (matching `robot-desktop-app/app.py`'s centered defaults, `_gimbal_pan = 90` / `_gimbal_tilt = 90`), `function updateGimbal()`.

- [ ] **Step 1: Add speed and gimbal markup to `TEMPLATE`**

Append a new panel to `TEMPLATE` in `control.js`, after the Drive panel:

```html
    <div class="panel">
      <div class="panel-title">Speed</div>
      <input type="range" id="control-speed" class="control-input" min="180" max="255" value="220">
      <span id="control-speed-value">220</span>
    </div>
    <div class="panel">
      <div class="panel-title">Camera Gimbal</div>
      <div class="control-gimbal-grid">
        <button class="control-drive-btn control-input" id="control-gimbal-up" data-pan-delta="0" data-tilt-delta="5">↑</button>
        <button class="control-drive-btn control-input" id="control-gimbal-left" data-pan-delta="-5" data-tilt-delta="0">←</button>
        <button class="control-drive-btn control-input" id="control-gimbal-center">C</button>
        <button class="control-drive-btn control-input" id="control-gimbal-right" data-pan-delta="5" data-tilt-delta="0">→</button>
        <button class="control-drive-btn control-input" id="control-gimbal-down" data-pan-delta="0" data-tilt-delta="-5">↓</button>
      </div>
    </div>
```

- [ ] **Step 2: Add gimbal state and `updateGimbal`**

Add near the other module-level state in `control.js`:

```javascript
  let gimbalPan = 90;
  let gimbalTilt = 90;

  function updateGimbal() {
    sendCommand(`servo:${gimbalPan},${gimbalTilt}`);
  }
```

- [ ] **Step 3: Wire the speed slider and gimbal buttons in `mount`**

Add to `mount`:

```javascript
    document.getElementById('control-speed').addEventListener('input', (evt) => {
      document.getElementById('control-speed-value').textContent = evt.target.value;
    });
    document.getElementById('control-speed').addEventListener('change', (evt) => {
      sendCommand(`speed:${evt.target.value}`);
    });

    ['control-gimbal-up', 'control-gimbal-left', 'control-gimbal-right', 'control-gimbal-down'].forEach((id) => {
      document.getElementById(id).addEventListener('click', () => {
        const btn = document.getElementById(id);
        gimbalPan = Math.max(0, Math.min(180, gimbalPan + Number(btn.dataset.panDelta)));
        gimbalTilt = Math.max(0, Math.min(180, gimbalTilt + Number(btn.dataset.tiltDelta)));
        updateGimbal();
      });
    });

    document.getElementById('control-gimbal-center').addEventListener('click', () => {
      gimbalPan = 90;
      gimbalTilt = 90;
      updateGimbal();
    });
```

- [ ] **Step 4: Add gimbal grid styles**

Append to `style.css`:

```css

.control-gimbal-grid { display: grid; grid-template-columns: repeat(3, 64px); grid-template-rows: repeat(3, 48px); gap: 6px; justify-content: start; }
#control-gimbal-up { grid-column: 2; grid-row: 1; }
#control-gimbal-left { grid-column: 1; grid-row: 2; }
#control-gimbal-center { grid-column: 2; grid-row: 2; }
#control-gimbal-right { grid-column: 3; grid-row: 2; }
#control-gimbal-down { grid-column: 2; grid-row: 3; }
```

- [ ] **Step 5: Manual verification — speed and gimbal UI**

- Open the Control tab: confirm the speed slider shows `220` initially and dragging it live-updates the adjacent number without sending anything yet (only `change`, i.e. on release, triggers a send attempt — check devtools shows no `ws.send` call attempted while disconnected, consistent with the `allowState !== 'allowed'` guard in `sendCommand`).
- Confirm the gimbal buttons are laid out in a proper 3x3-ish D-pad (up/left/center/right/down, no overlapping cells) and clicking each updates internal `gimbalPan`/`gimbalTilt` conceptually — verify by temporarily adding a `console.log` in `updateGimbal` during this manual check only, then remove it before committing.
- Confirm the center button resets visually-inferred position (no crash) even with no connection.

- [ ] **Step 6: Commit**

```bash
git add rover-telemetry-frontend/public/js/control.js rover-telemetry-frontend/public/css/style.css
git commit -m "$(cat <<'EOF'
feat: add speed slider and gimbal controls to rover control tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012PwaDTKmN8jroC2Gqx6nDV
EOF
)"
```

---

### Task 5: Responsive layout pass + end-to-end check against a throwaway local server

**Files:**
- Modify: `rover-telemetry-frontend/public/css/style.css`

**Interfaces:**
- None new — this task only adds a responsive breakpoint and performs verification of everything built in Tasks 1–4 together.

- [ ] **Step 1: Add a narrow-viewport rule for the control tab**

Append to `style.css`, inside (or alongside) the existing `@media (max-width: 700px)` block pattern used elsewhere in the file:

```css

@media (max-width: 700px) {
  .control-address-row input { width: 100%; }
  .control-drive-btn { width: 56px; height: 44px; }
}
```

- [ ] **Step 2: Write a throwaway local verification server (not committed)**

This step exists only to exercise the full protocol end-to-end before considering the frontend done; the script is never added to the repo (per plan scope — "no mock server included in the repo").

In the scratchpad directory, create a short-lived Python script using the `websockets` package (`pip install websockets` if not already present) that:
- Accepts one connection.
- Immediately sends `{"type":"status","allowed":true,"rover_connected":true}`.
- On receiving any `{"type":"command",...}` message, prints it to stdout.
- On receiving the text `"toggle"` (typed manually is not applicable over this protocol — instead, just restart the script with `allowed: false` for the second half of this check, see Step 3).

Run it on `127.0.0.1:8765`.

- [ ] **Step 3: Run the end-to-end manual check**

With the throwaway server from Step 2 running and reporting `allowed: true`:
- Open the Control tab, enter `127.0.0.1:8765`, click 接続.
- Confirm the banner turns green "接続済み・操作可" and all drive/speed/gimbal controls become enabled (not grayed out).
- Hold the ↑ button; confirm the server's stdout prints `{"type": "command", "command": "forward"}`; release; confirm it prints `{"type": "command", "command": "stop"}`.
- Press the ArrowLeft key while the tab is focused; confirm `left` then `stop` (on keyup) print.
- Drag the speed slider and release; confirm `speed:<N>` prints with the exact value shown next to the slider.
- Click each gimbal direction button and confirm `servo:<pan>,<tilt>` prints with values changing by exactly 5 and clamped to `[0, 180]` (click the up-arrow gimbal button 40+ times and confirm tilt stops increasing past 180, never exceeds it).
- Click 中央 (center): confirm `servo:90,90` prints.
- Stop the throwaway server (simulating desktop app closing): confirm within ~2s the tab shows "未接続" and controls gray out again; confirm it starts reconnecting (visible in devtools' WS attempts).
- Restart the throwaway server but change its first message to `{"type":"status","allowed":false,"rover_connected":true}`: confirm the tab shows "接続済み・操作不可" (yellow/warn styling) and every drive/speed/gimbal control is disabled again, and clicking them does not print anything server-side (proving the client-side `sendCommand` guard works even though the server would have accepted the socket).
- Delete the throwaway script from the scratchpad directory once done (it was never part of the repo).

- [ ] **Step 4: Commit the CSS-only change**

```bash
git add rover-telemetry-frontend/public/css/style.css
git commit -m "$(cat <<'EOF'
style: add narrow-viewport layout rules for rover control tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012PwaDTKmN8jroC2Gqx6nDV
EOF
)"
```
