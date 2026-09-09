window.TimeUtil = (function () {
  const ZONE = 'Asia/Ho_Chi_Minh';

  function parts(iso) {
    const d = new Date(iso);
    const fmt = new Intl.DateTimeFormat('en-CA', {
      timeZone: ZONE,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false,
    });
    const map = {};
    fmt.formatToParts(d).forEach((p) => { map[p.type] = p.value; });
    return map;
  }

  function timeHM(iso) {
    const p = parts(iso);
    return `${p.hour}:${p.minute}`;
  }

  function timeHMS(iso) {
    const p = parts(iso);
    return `${p.hour}:${p.minute}:${p.second}`;
  }

  function dateTime(iso) {
    const p = parts(iso);
    return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}`;
  }

  function date(iso) {
    const p = parts(iso);
    return `${p.year}-${p.month}-${p.day}`;
  }

  return { timeHM, timeHMS, dateTime, date };
})();
