window.SystemView = (function () {
  let el;
  function mount(rootEl) { el = rootEl; el.textContent = 'System view (not yet implemented)'; }
  function start() {}
  function stop() {}
  return { mount, start, stop };
})();
