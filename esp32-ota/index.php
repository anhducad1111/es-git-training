<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32 OTA Publisher</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #f2f6fb; color: #162033; margin: 0; }
    main { max-width: 760px; background: #fff; margin: 6vh auto; padding: 28px; border-radius: 16px; box-shadow: 0 8px 30px #b9c4d533; }
    label, input, button { display: block; width: 100%; box-sizing: border-box; }
    label { margin: 16px 0 6px; font-weight: 600; }
    input { padding: 11px; border: 1px solid #b9c4d5; border-radius: 8px; }
    button { margin-top: 22px; padding: 12px; border: 0; border-radius: 8px; background: #1769e0; color: #fff; font-weight: 700; cursor: pointer; }
    pre { white-space: pre-wrap; padding: 14px; min-height: 48px; background: #edf3fc; border-radius: 8px; }
    .hint { color: #596579; font-size: .9rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: .9rem; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #e3e9f2; }
    th { color: #596579; font-weight: 600; }
    h2 { margin-top: 40px; }
    code { background: #edf3fc; padding: 1px 5px; border-radius: 4px; }
  </style>
</head>
<body>
  <main>
    <h1>ESP32 OTA Publisher</h1>
    <p class="hint">
      Rename the firmware file to <code>filename-version-info-client.&lt;ext&gt;</code> before selecting it
      (e.g. <code>firmware-1_1_1-hotfix-taro.bin</code>). filename/info/client must be alphanumeric only;
      version may use underscores as separators (e.g. <code>1_1_1</code>).
      The server assigns an ID and a Da Nang timestamp automatically, and keeps only the latest 5 uploads.
    </p>
    <form id="uploadForm">
      <label for="firmware">Firmware file</label>
      <input id="firmware" name="firmware" type="file" required>
      <label for="ota_key">Administrator key</label>
      <input id="ota_key" name="ota_key" type="password" required>
      <button>Publish firmware</button>
    </form>
    <pre id="result">Select a firmware file to begin.</pre>

    <h2>Version history <span class="hint">(times shown in Da Nang / Asia-Ho_Chi_Minh, UTC+7)</span></h2>
    <table>
      <thead>
        <tr><th>ID</th><th>Filename</th><th>Version</th><th>Info</th><th>Client</th><th>Size</th><th>Published at</th></tr>
      </thead>
      <tbody id="historyBody">
        <tr><td colspan="7" class="hint">Enter the administrator key and publish, or click below, to load history.</td></tr>
      </tbody>
    </table>
    <button id="loadHistoryBtn" type="button">Refresh history</button>
  </main>
  <script>
    const resultEl = document.getElementById('result');
    const historyBody = document.getElementById('historyBody');

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    function formatSize(bytes) {
      if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return bytes + ' B';
    }

    async function loadHistory() {
      const key = document.getElementById('ota_key').value;
      if (!key) {
        historyBody.innerHTML = '<tr><td colspan="7" class="hint">Enter the administrator key first.</td></tr>';
        return;
      }
      historyBody.innerHTML = '<tr><td colspan="7" class="hint">Loading...</td></tr>';
      try {
        const response = await fetch('api/history.php', { headers: { 'X-OTA-Key': key } });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.message || `HTTP ${response.status}`);
        if (!data.data.length) {
          historyBody.innerHTML = '<tr><td colspan="7" class="hint">No firmware published yet.</td></tr>';
          return;
        }
        historyBody.innerHTML = data.data.map(row => `
          <tr>
            <td>${escapeHtml(row.id)}</td>
            <td>${escapeHtml(row.filename)}</td>
            <td>${escapeHtml(row.version)}</td>
            <td>${escapeHtml(row.info)}</td>
            <td>${escapeHtml(row.client)}</td>
            <td>${formatSize(row.size)}</td>
            <td>${escapeHtml(row.timestamp)}</td>
          </tr>
        `).join('');
      } catch (error) {
        historyBody.innerHTML = `<tr><td colspan="7">Error: ${error.message}</td></tr>`;
      }
    }

    document.getElementById('loadHistoryBtn').addEventListener('click', loadHistory);

    document.getElementById('uploadForm').addEventListener('submit', async event => {
      event.preventDefault();
      resultEl.textContent = 'Uploading...';
      try {
        const response = await fetch('api/upload.php', { method: 'POST', body: new FormData(event.currentTarget) });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.message || `HTTP ${response.status}`);
        resultEl.textContent = `Published id ${data.id}: ${data.filename} ${data.version} (${data.info}) by ${data.client}\nStored as: ${data.stored_as}\nSize: ${data.size} bytes\nRemoved old files: ${data.removed_old_files.join(', ') || 'none'}`;
        loadHistory();
      } catch (error) {
        resultEl.textContent = `Error: ${error.message}`;
      }
    });
  </script>
</body>
</html>
