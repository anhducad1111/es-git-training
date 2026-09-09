window.RoverSelection = (function () {
  let current = null;
  const listeners = [];

  return {
    get: () => current,
    set(uid) {
      if (!uid || uid === current) return;
      current = uid;
      listeners.forEach((fn) => fn(uid));
    },
    subscribe(fn) {
      listeners.push(fn);
    },
  };
})();
