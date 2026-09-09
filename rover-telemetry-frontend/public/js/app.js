(function () {
  const views = { live: window.LiveView, history: window.HistoryView, system: window.SystemView };
  let activeTab = 'live';

  function activateTabButton(tab, isActive) {
    document.getElementById(`view-${tab}`).classList.toggle('active', isActive);
    document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.toggle('active', isActive);
  }

  function switchTab(tab) {
    if (tab === activeTab) return;
    views[activeTab].stop();
    activateTabButton(activeTab, false);
    activeTab = tab;
    activateTabButton(activeTab, true);
    views[activeTab].start();
  }

  function pollHealth() {
    Api.health()
      .then((data) => {
        const badge = document.getElementById('health-badge');
        badge.textContent = `api ${data.api} · db ${data.database}`;
        badge.classList.toggle('down', data.status !== 'ok');
      })
      .catch(() => {
        const badge = document.getElementById('health-badge');
        badge.textContent = 'api down';
        badge.classList.add('down');
      })
      .finally(() => setTimeout(pollHealth, window.APP_CONFIG.POLL_INTERVAL_SYSTEM_MS));
  }

  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  views.live.mount(document.getElementById('view-live'));
  views.history.mount(document.getElementById('view-history'));
  views.system.mount(document.getElementById('view-system'));

  views[activeTab].start();
  pollHealth();
})();
