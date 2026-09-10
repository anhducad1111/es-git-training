window.ControlView = (function () {
  const ADDRESS_STORAGE_KEY = 'roverControlAddress';

  let el;
  let address = '';
  let ws = null;
  let reconnectTimer = null;
  let allowState = 'disconnected';
  let roverConnected = false;
  const RECONNECT_DELAY_MS = 2000;

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

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;

    address = loadSavedAddress();
    document.getElementById('control-address').value = address;
    renderStatusBanner('disconnected');

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
  }

  function start() {
    if (address) connect();
  }

  function stop() {
    disconnect();
  }

  return { mount, start, stop };
})();
