window.RejectChips = (function () {
  const signatures = new WeakMap();
  const bound = new WeakSet();

  function renderDetailRows(errors) {
    if (errors.length === 0) return '<div class="chip-detail-empty">No records.</div>';
    return `
      <table>
        <thead><tr><th>Time (ICT)</th><th>Rover</th><th>Detail</th></tr></thead>
        <tbody>${errors.map((e) => `
          <tr>
            <td>${TimeUtil.dateTime(e.received_at)}</td>
            <td>${Api.escapeHtml(e.device_uid || '–')}</td>
            <td>${Api.escapeHtml(e.detail)}</td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  function bind(container) {
    if (bound.has(container)) return;
    bound.add(container);
    container.addEventListener('click', (evt) => {
      const chip = evt.target.closest('.chip');
      if (!chip) return;
      const code = chip.dataset.code;
      const detail = container.querySelector('.chip-detail');
      const wasActive = chip.classList.contains('expanded');
      container.querySelectorAll('.chip').forEach((c) => c.classList.remove('expanded'));
      if (wasActive) {
        detail.hidden = true;
        detail.innerHTML = '';
        return;
      }
      chip.classList.add('expanded');
      detail.hidden = false;
      detail.innerHTML = '<div class="chip-detail-loading">Loading…</div>';
      Api.validationErrors({ window: '24h', error_code: code, limit: 20 }).then((data) => {
        detail.innerHTML = renderDetailRows(data.errors);
      }).catch((err) => {
        detail.innerHTML = `<div class="chip-detail-empty">Failed: ${err.message || err.code}</div>`;
      });
    });
  }

  function render(container, byCode) {
    if (!container) return;
    bind(container);
    const signature = JSON.stringify(byCode);
    if (signatures.get(container) === signature) return;
    signatures.set(container, signature);
    const entries = Object.entries(byCode);
    container.innerHTML = entries.length === 0
      ? '<span>No rejects.</span>'
      : `<div class="chip-list">${entries.map(([code, count]) => `
          <span class="chip" data-code="${Api.escapeHtml(code)}">${Api.escapeHtml(code)} ${count} <span class="chip-chevron">▾</span></span>
        `).join('')}</div><div class="chip-detail" hidden></div>`;
  }

  return { render };
})();
