window.LiveView = (function () {
  let el;
  function mount(rootEl) { el = rootEl; el.textContent = 'Live view (not yet implemented)'; }
  function start() {}
  function stop() {}
  return { mount, start, stop };
})();
