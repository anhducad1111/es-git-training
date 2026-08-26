<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>OTA Firmware Publisher</title>
    <link rel="stylesheet" href="style.css">
</head>

<body>
    <main class="container">
        <section class="session-bar">
            <div class="session-info">
                <p class="eyebrow">SESSION</p>
                <p id="sessionStatus" class="session-status">Not signed in</p>
            </div>
            <form id="signInForm" class="session-form">
                <input id="sessionKey" type="password" placeholder="Administrator key" autocomplete="current-password" required>
                <button type="submit">Sign in</button>
                <button id="signOutButton" class="secondary-button hidden" type="button">Sign out</button>
            </form>
        </section>

        <header class="header">
            <div>
                <p class="eyebrow">ESP32 / OTA UPDATES</p>
                <h1>Firmware Publisher</h1>
                <p class="subtitle">Push builds to devices and keep a rolling history</p>
            </div>
            <div class="server-status"><span id="statusDot" class="status-dot"></span><span id="statusText">Not authenticated</span></div>
        </header>

        <div id="capacityWarning" class="capacity-warning hidden" role="status"></div>

        <section class="cards">
            <div class="card">
                <div class="card-label">LATEST VERSION</div>
                <div class="value version-value mono"><span id="latestVersion">--</span></div>
                <div id="latestVersionFooter" class="card-footer">No builds yet</div>
            </div>
            <div class="card">
                <div class="card-label">FILES STORED</div>
                <div class="value"><span id="filesStored">--</span><small>/ 5 slots</small></div>
                <div id="capacityDots" class="capacity-dots"></div>
            </div>
            <div class="card">
                <div class="card-label">LATEST PUBLISHER</div>
                <div class="value" id="latestClient" style="font-size:26px">--</div>
                <div id="latestClientFooter" class="card-footer">No builds yet</div>
            </div>
        </section>

        <section class="panel" aria-labelledby="publishTitle">
            <div class="panel-header">
                <div>
                    <h2 id="publishTitle">Publish Firmware</h2>
                    <p>Any file name works &mdash; the server assigns an ID and a Da Nang timestamp automatically</p>
                </div>
            </div>
            <div class="panel-body">
                <form id="uploadForm">
                    <div class="form-grid">
                        <div class="field wide">
                            <label for="firmware">Firmware file</label>
                            <input id="firmware" name="firmware" type="file" required>
                        </div>
                        <div class="field">
                            <label for="version">Version</label>
                            <input id="version" name="version" class="mono" placeholder="1_1_1" required pattern="[A-Za-z0-9_]+">
                            <p class="field-hint">Letters, numbers, underscores</p>
                        </div>
                        <div class="field">
                            <label for="info">Info</label>
                            <input id="info" name="info" placeholder="hotfix" required pattern="[A-Za-z0-9]+">
                            <p class="field-hint">Alphanumeric only</p>
                        </div>
                        <div class="field">
                            <label for="client">Client</label>
                            <input id="client" name="client" placeholder="taro" required pattern="[A-Za-z0-9]+">
                            <p class="field-hint">Alphanumeric only</p>
                        </div>
                        <div class="form-actions">
                            <button id="publishButton" type="submit">Publish firmware</button>
                        </div>
                    </div>
                </form>
            </div>
            <div id="resultBanner" class="banner banner-idle">
                <p class="banner-title">Ready to publish</p>
                <p>Select a firmware file and fill in the details above.</p>
            </div>
        </section>

        <section class="panel" aria-labelledby="historyTitle">
            <div class="panel-header">
                <div>
                    <h2 id="historyTitle">Version History</h2>
                    <p>Latest 5 builds &middot; times shown in Da Nang (Asia/Ho_Chi_Minh, UTC+7)</p>
                </div>
                <button id="refreshButton" class="secondary-button" type="button">Refresh history</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th aria-sort="descending"><button type="button" class="sort-button" data-sort-key="id">ID <span class="sort-indicator" aria-hidden="true">&darr;</span></button></th>
                            <th>Filename</th>
                            <th>Version</th>
                            <th>Info</th>
                            <th>Client</th>
                            <th>Size</th>
                            <th aria-sort="none"><button type="button" class="sort-button" data-sort-key="timestamp">Published <span class="sort-indicator" aria-hidden="true">&hArr;</span></button></th>
                        </tr>
                    </thead>
                    <tbody id="historyBody">
                        <tr>
                            <td colspan="7" class="empty">Sign in with the administrator key above to load past builds.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <footer>Auto-prune keeps the latest 5 builds &middot; Apache / PHP / filesystem storage</footer>
    </main>

    <script>
        const KEEP_LATEST = 5;
        const SESSION_STORAGE_KEY = 'esp32_ota_session';
        const SESSION_DURATION_MS = 12 * 60 * 60 * 1000; // stay signed in for 12 hours on this device
        let entries = [];
        let sortKey = 'id';
        let sortDirection = 'desc';
        let adminKey = '';

        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const historyBody = document.getElementById('historyBody');
        const resultBanner = document.getElementById('resultBanner');
        const sessionStatus = document.getElementById('sessionStatus');
        const sessionKeyInput = document.getElementById('sessionKey');
        const signOutButton = document.getElementById('signOutButton');

        function readSession() {
            try {
                const raw = localStorage.getItem(SESSION_STORAGE_KEY);
                if (!raw) return null;
                const parsed = JSON.parse(raw);
                if (!parsed.key || !parsed.expiresAt || Date.now() > parsed.expiresAt) {
                    localStorage.removeItem(SESSION_STORAGE_KEY);
                    return null;
                }
                return parsed;
            } catch {
                return null;
            }
        }

        function writeSession(key) {
            try {
                localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ key, expiresAt: Date.now() + SESSION_DURATION_MS }));
            } catch {}
        }

        function clearSession() {
            try { localStorage.removeItem(SESSION_STORAGE_KEY); } catch {}
        }

        function formatExpiry(expiresAt) {
            return new Date(expiresAt).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        }

        function setSignedOutUI(message) {
            statusDot.classList.remove('online', 'offline');
            statusText.textContent = 'Not authenticated';
            sessionStatus.className = 'session-status';
            sessionStatus.textContent = message || 'Not signed in';
            signOutButton.classList.add('hidden');
        }

        function setSignedInUI(expiresAt) {
            statusDot.classList.remove('offline');
            statusDot.classList.add('online');
            statusText.textContent = 'Authenticated';
            sessionStatus.className = 'session-status signed-in';
            sessionStatus.textContent = `Signed in · expires ${formatExpiry(expiresAt)}`;
            signOutButton.classList.remove('hidden');
        }

        function esc(value) {
            return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
        }

        function formatSize(bytes) {
            const n = Number(bytes);
            if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(2) + ' MB';
            if (n >= 1024) return (n / 1024).toFixed(1) + ' KB';
            return n + ' B';
        }

        function setBanner(kind, title, lines, receipt) {
            resultBanner.className = 'banner banner-' + kind;
            const receiptHtml = receipt ? `<div class="receipt">${receipt}</div>` : '';
            resultBanner.innerHTML = `<p class="banner-title">${esc(title)}</p>${lines.map(l => `<p>${l}</p>`).join('')}${receiptHtml}`;
        }

        function renderSummary() {
            const latestVersionEl = document.getElementById('latestVersion');
            const latestVersionFooter = document.getElementById('latestVersionFooter');
            const filesStoredEl = document.getElementById('filesStored');
            const latestClientEl = document.getElementById('latestClient');
            const latestClientFooter = document.getElementById('latestClientFooter');
            const capacityDots = document.getElementById('capacityDots');
            const capacityWarning = document.getElementById('capacityWarning');

            filesStoredEl.textContent = entries.length;
            capacityDots.innerHTML = Array.from({ length: KEEP_LATEST }, (_, i) => {
                const filled = i < entries.length;
                const isNewest = filled && i === 0;
                return `<span class="capacity-dot ${filled ? 'filled' : ''} ${isNewest ? 'newest' : ''}"></span>`;
            }).join('');

            if (entries.length >= KEEP_LATEST) {
                capacityWarning.textContent = 'Storage is full — publishing again will remove the oldest build.';
                capacityWarning.classList.remove('hidden');
            } else {
                capacityWarning.classList.add('hidden');
            }

            if (!entries.length) {
                latestVersionEl.textContent = '--';
                latestVersionFooter.textContent = 'No builds yet';
                latestClientEl.textContent = '--';
                latestClientFooter.textContent = 'No builds yet';
                return;
            }

            const latest = entries.reduce((newest, e) => Number(e.id) > Number(newest.id) ? e : newest);
            latestVersionEl.textContent = latest.version;
            latestVersionFooter.textContent = `Published ${latest.timestamp}`;
            latestClientEl.textContent = latest.client;
            latestClientFooter.textContent = `File: ${latest.filename}`;
        }

        function renderTable() {
            if (!entries.length) return;
            const sorted = [...entries].sort((a, b) => {
                const comparison = sortKey === 'id'
                    ? Number(a.id) - Number(b.id)
                    : String(a.timestamp).localeCompare(String(b.timestamp));
                return sortDirection === 'asc' ? comparison : -comparison;
            });
            const newestId = Math.max(...entries.map(e => Number(e.id)));
            historyBody.innerHTML = sorted.map(row => `
                <tr>
                    <td class="mono">${esc(row.id)}${Number(row.id) === newestId ? '<span class="newest-badge">Newest</span>' : ''}</td>
                    <td>${esc(row.filename)}</td>
                    <td><span class="build-tag mono">${esc(row.version)}</span></td>
                    <td>${esc(row.info)}</td>
                    <td><span class="client-badge">${esc(row.client)}</span></td>
                    <td>${formatSize(row.size)}</td>
                    <td class="time">${esc(row.timestamp)}</td>
                </tr>
            `).join('');
        }

        function updateSortButtons() {
            document.querySelectorAll('.sort-button').forEach(button => {
                const active = button.dataset.sortKey === sortKey;
                button.closest('th').setAttribute('aria-sort', active ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none');
                button.querySelector('.sort-indicator').innerHTML = active ? (sortDirection === 'asc' ? '&uarr;' : '&darr;') : '&hArr;';
            });
        }

        document.querySelectorAll('.sort-button').forEach(button => {
            button.addEventListener('click', () => {
                const selectedKey = button.dataset.sortKey;
                sortDirection = selectedKey === sortKey && sortDirection === 'desc' ? 'asc' : 'desc';
                sortKey = selectedKey;
                renderTable();
                updateSortButtons();
            });
        });

        async function loadHistory({ silent = false } = {}) {
            if (!adminKey) {
                setSignedOutUI();
                if (!silent) {
                    historyBody.innerHTML = '<tr><td colspan="7" class="empty">Sign in with the administrator key first.</td></tr>';
                }
                return;
            }
            if (!silent) {
                historyBody.innerHTML = '<tr><td colspan="7" class="loading">Loading...</td></tr>';
            }
            try {
                const response = await fetch('api/history.php', { headers: { 'X-OTA-Key': adminKey }, cache: 'no-store' });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || `HTTP ${response.status}`);
                entries = data.data || [];
                renderSummary();
                if (!entries.length) {
                    historyBody.innerHTML = '<tr><td colspan="7" class="empty">No firmware published yet.</td></tr>';
                } else {
                    renderTable();
                    updateSortButtons();
                }
                return true;
            } catch (error) {
                adminKey = '';
                clearSession();
                setSignedOutUI('Invalid administrator key');
                historyBody.innerHTML = `<tr><td colspan="7" class="empty">Could not load history: ${esc(error.message)}</td></tr>`;
                return false;
            }
        }

        document.getElementById('refreshButton').addEventListener('click', () => loadHistory());

        document.getElementById('signInForm').addEventListener('submit', async event => {
            event.preventDefault();
            const candidate = sessionKeyInput.value.trim();
            if (!candidate) return;
            sessionStatus.className = 'session-status';
            sessionStatus.textContent = 'Signing in...';
            adminKey = candidate;
            const ok = await loadHistory();
            if (ok) {
                writeSession(candidate);
                const session = readSession();
                setSignedInUI(session ? session.expiresAt : Date.now() + SESSION_DURATION_MS);
                sessionKeyInput.value = '';
            }
        });

        signOutButton.addEventListener('click', () => {
            adminKey = '';
            clearSession();
            entries = [];
            renderSummary();
            historyBody.innerHTML = '<tr><td colspan="7" class="empty">Sign in with the administrator key first.</td></tr>';
            setSignedOutUI('Signed out');
        });

        document.getElementById('uploadForm').addEventListener('submit', async event => {
            event.preventDefault();
            const form = event.currentTarget;
            const button = document.getElementById('publishButton');
            if (!adminKey) {
                setBanner('error', 'Publish failed', ['Sign in with the administrator key first.']);
                return;
            }
            button.disabled = true;
            button.textContent = 'Publishing...';
            setBanner('pending', 'Publishing…', ['Uploading the firmware file.']);
            try {
                const response = await fetch('api/upload.php', {
                    method: 'POST',
                    headers: { 'X-OTA-Key': adminKey },
                    body: new FormData(form),
                });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || `HTTP ${response.status}`);
                const removed = (data.removed_old_files || []).length
                    ? `<span>Removed:</span> <strong>${esc(data.removed_old_files.join(', '))}</strong>`
                    : '<span>Removed:</span> <strong>none</strong>';
                setBanner('success', `Published build #${data.id}`,
                    [`<span class="build-tag mono">${esc(data.version)}</span> by <strong>${esc(data.client)}</strong> &mdash; ${esc(data.info)}`],
                    `<span>Stored as:</span> <strong class="mono">${esc(data.stored_as)}</strong><span>Size:</span> <strong>${formatSize(data.size)}</strong>${removed}`
                );
                form.reset();
                loadHistory();
            } catch (error) {
                setBanner('error', 'Publish failed', [esc(error.message)]);
            } finally {
                button.disabled = false;
                button.textContent = 'Publish firmware';
            }
        });

        (function bootstrapSession() {
            const session = readSession();
            if (!session) {
                setSignedOutUI();
                return;
            }
            adminKey = session.key;
            setSignedInUI(session.expiresAt);
            loadHistory({ silent: true });
        })();
    </script>
</body>

</html>
