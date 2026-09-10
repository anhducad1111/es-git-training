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
