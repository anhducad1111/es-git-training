<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>Sensor Monitoring Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>

<body>
    <main class="container">
        <header class="header">
            <div>
                <p class="eyebrow">XAMPP / SENSOR LOGGER</p>
                <h1>Sensor Monitoring Dashboard</h1>
                <p class="subtitle">Live data from MySQL</p>
            </div>
            <div class="server-status"><span id="statusDot" class="status-dot"></span><span id="statusText">Connecting...</span></div>
        </header>
        <div id="staleWarning" class="stale-warning top-warning hidden" role="alert"></div>
        <section class="cards">
            <div class="card temperature">
                <div class="card-label">LATEST TEMPERATURE</div>
                <div class="value"><span id="temperature">--</span><small>°C</small></div>
                <div id="temperatureTime" class="card-footer">No data</div>
            </div>
            <div class="card humidity">
                <div class="card-label">LATEST HUMIDITY</div>
                <div class="value"><span id="humidity">--</span><small>%</small></div>
                <div id="humidityTime" class="card-footer">No data</div>
            </div>
            <div class="card device">
                <div class="card-label">LATEST DEVICE</div>
                <div id="device" class="device-name">--</div>
                <div id="lastUpdated" class="card-footer">No data</div>
            </div>
        </section>
        <section class="panel chart-panel" aria-labelledby="chartTitle">
            <div class="panel-header">
                <div>
                    <h2 id="chartTitle">Temperature and Humidity</h2>
                    <p>Recent readings. Temperature uses the left axis; humidity uses the right axis.</p>
                </div>
                <div class="chart-legend" aria-label="Chart legend"><span class="legend-temperature">Temperature</span><span class="legend-humidity">Humidity</span></div>
            </div>
            <div id="chartEmpty" class="chart-empty">Loading chart...</div>
            <div id="sensorChart" class="chart-wrap" role="img" aria-label="Temperature and humidity trend chart"></div>
        </section>
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h2>Recent Sensor Logs</h2>
                    <p>Latest 10 records from <strong>sensor_logs</strong></p>
                </div><button id="refreshButton" onclick="loadData()">Refresh Data</button>
            </div>
            <div id="errorBox" class="error-box hidden"></div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th aria-sort="none"><button type="button" class="sort-button" data-sort-key="id">ID <span class="sort-indicator" aria-hidden="true">↕</span></button></th>
                            <th>Device</th>
                            <th>Temperature</th>
                            <th>Humidity</th>
                            <th aria-sort="descending"><button type="button" class="sort-button" data-sort-key="created_at">Time <span class="sort-indicator" aria-hidden="true">↓</span></button></th>
                        </tr>
                    </thead>
                    <tbody id="sensorTable">
                        <tr>
                            <td colspan="5" class="loading">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>
        <footer>Auto refresh: every 5 seconds · Apache / PHP / MySQL</footer>
    </main>
    <script>
        const API_URL = "api/log.php";
        let records = [];
        let serverTime = null;
        let sortKey = "created_at";
        let sortDirection = "desc";
        async function loadData() {
            const button = document.getElementById("refreshButton"),
                table = document.getElementById("sensorTable"),
                errorBox = document.getElementById("errorBox");
            button.disabled = true;
            button.textContent = "Loading...";
            errorBox.classList.add("hidden");
            try {
                const response = await fetch(API_URL, {
                    method: "GET",
                    cache: "no-store"
                });
                if (!response.ok) throw new Error("HTTP " + response.status);
                const result = await response.json();
                if (!result.success) throw new Error(result.message || "API error");
                records = result.data || [];
                serverTime = result.server_time || null;
                updateDashboard();
                document.getElementById("statusText").textContent = "Server Online";
                document.getElementById("statusDot").classList.remove("offline")
            } catch (error) {
                console.error(error);
                document.getElementById("statusText").textContent = "Server Error";
                document.getElementById("statusDot").classList.add("offline");
                errorBox.textContent = "Could not load data: " + error.message;
                errorBox.classList.remove("hidden")
            } finally {
                button.disabled = false;
                button.textContent = "Refresh Data"
            }
        }

        function updateDashboard() {
            const table = document.getElementById("sensorTable");
            if (!records || records.length === 0) {
                table.innerHTML = '<tr><td colspan="5" class="empty">No sensor data yet.</td></tr>';
                ["temperature", "humidity", "device"].forEach(id => document.getElementById(id).textContent = "--");
                renderChart([]);
                updateStaleWarning(null);
                return
            }
            const latest = records.reduce((newest, record) => {
                const recordTime = String(record.created_at);
                const newestTime = String(newest.created_at);
                return recordTime > newestTime || (recordTime === newestTime && Number(record.id) > Number(newest.id)) ? record : newest;
            });
            renderChart(records);
            updateStaleWarning(latest);
            records = [...records].sort((a, b) => {
                const comparison = sortKey === "id"
                    ? Number(a.id) - Number(b.id)
                    : String(a.created_at).localeCompare(String(b.created_at));
                return sortDirection === "asc" ? comparison : -comparison;
            });
            document.getElementById("temperature").textContent = Number(latest.temperature).toFixed(1);
            document.getElementById("humidity").textContent = Number(latest.humidity).toFixed(1);
            document.getElementById("device").textContent = latest.device_name;
            document.getElementById("temperatureTime").textContent = "Updated: " + latest.created_at;
            document.getElementById("humidityTime").textContent = "Updated: " + latest.created_at;
            document.getElementById("lastUpdated").textContent = "Updated: " + latest.created_at;
            table.innerHTML = records.map(r => `<tr><td>${esc(r.id)}</td><td><span class="device-badge">${esc(r.device_name)}</span></td><td>${Number(r.temperature).toFixed(1)} °C</td><td>${Number(r.humidity).toFixed(1)} %</td><td class="time">${esc(r.created_at)}</td></tr>`).join("")
        }

        function updateStaleWarning(latest) {
            const warning = document.getElementById("staleWarning");
            if (!latest) {
                warning.classList.add("hidden");
                return;
            }
            const latestTime = new Date(String(latest.created_at).replace(" ", "T"));
            const referenceTime = serverTime ? new Date(String(serverTime).replace(" ", "T")) : new Date();
            const ageInMinutes = (referenceTime.getTime() - latestTime.getTime()) / 60000;
            if (Number.isFinite(ageInMinutes) && ageInMinutes >= 3) {
                warning.textContent = "No sensor update has been received for 3 minutes or more. Last update: " + latest.created_at;
                warning.classList.remove("hidden");
            } else {
                warning.classList.add("hidden");
            }
        }

        function renderChart(chartRecords) {
            const chart = document.getElementById("sensorChart");
            const empty = document.getElementById("chartEmpty");
            if (!chartRecords.length) {
                chart.innerHTML = "";
                chart.classList.add("hidden");
                empty.textContent = "No sensor data yet.";
                empty.classList.remove("hidden");
                return;
            }

            const data = [...chartRecords].sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
            const width = 760, height = 280, left = 58, right = 58, top = 24, bottom = 48;
            const plotWidth = width - left - right, plotHeight = height - top - bottom;
            const temperatures = data.map(record => Number(record.temperature));
            const humidities = data.map(record => Number(record.humidity));
            const range = values => {
                let min = Math.min(...values), max = Math.max(...values);
                const padding = Math.max((max - min) * 0.15, 1);
                min -= padding;
                max += padding;
                return { min, max };
            };
            const tempRange = range(temperatures), humidityRange = range(humidities);
            const x = index => left + (data.length === 1 ? plotWidth / 2 : index * plotWidth / (data.length - 1));
            const y = (value, scale) => top + (scale.max - value) * plotHeight / (scale.max - scale.min);
            const points = (values, scale) => values.map((value, index) => `${x(index).toFixed(1)},${y(value, scale).toFixed(1)}`).join(" ");
            const grid = [0, 0.5, 1].map(position => {
                const gridY = top + plotHeight * position;
                const tempValue = tempRange.max - (tempRange.max - tempRange.min) * position;
                const humidityValue = humidityRange.max - (humidityRange.max - humidityRange.min) * position;
                return `<line x1="${left}" y1="${gridY}" x2="${width - right}" y2="${gridY}" class="chart-grid"/><text x="${left - 10}" y="${gridY + 4}" text-anchor="end" class="chart-axis temp-axis">${tempValue.toFixed(1)}&#176;C</text><text x="${width - right + 10}" y="${gridY + 4}" class="chart-axis humidity-axis">${humidityValue.toFixed(1)}%</text>`;
            }).join("");
            const labels = data.map((record, index) => `<text x="${x(index)}" y="${height - 28}" text-anchor="middle" class="chart-label">${esc(String(record.created_at).slice(11, 16))}</text>`).join("");
            const dots = (values, scale, fill) => values.map((value, index) => `<circle cx="${x(index)}" cy="${y(value, scale)}" r="3.5" fill="${fill}" stroke="#ffffff" stroke-width="2"/>`).join("");
            chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><text x="16" y="${top + plotHeight / 2}" text-anchor="middle" transform="rotate(-90 16 ${top + plotHeight / 2})" class="chart-axis temp-axis">Temperature (&#176;C)</text><text x="${width - 16}" y="${top + plotHeight / 2}" text-anchor="middle" transform="rotate(90 ${width - 16} ${top + plotHeight / 2})" class="chart-axis humidity-axis">Humidity (%)</text><text x="${width / 2}" y="${height - 5}" text-anchor="middle" class="chart-label">Time</text>${grid}<polyline points="${points(temperatures, tempRange)}" fill="none" stroke="#e56a54" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>${dots(temperatures, tempRange, "#e56a54")}<polyline points="${points(humidities, humidityRange)}" fill="none" stroke="#3d7ee8" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>${dots(humidities, humidityRange, "#3d7ee8")}${labels}</svg>`;
            chart.classList.remove("hidden");
            empty.classList.add("hidden");
        }

        function updateSortButtons() {
            document.querySelectorAll(".sort-button").forEach(button => {
                const active = button.dataset.sortKey === sortKey;
                button.closest("th").setAttribute("aria-sort", active ? (sortDirection === "asc" ? "ascending" : "descending") : "none");
                button.querySelector(".sort-indicator").textContent = active ? (sortDirection === "asc" ? "↑" : "↓") : "↕";
            });
        }

        document.querySelectorAll(".sort-button").forEach(button => {
            button.addEventListener("click", () => {
                const selectedKey = button.dataset.sortKey;
                sortDirection = selectedKey === sortKey && sortDirection === "desc" ? "asc" : "desc";
                sortKey = selectedKey;
                updateDashboard();
                updateSortButtons();
            });
        });

        function esc(v) {
            return String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;")
        }
        loadData();
        setInterval(loadData, 5000);
    </script>
</body>

</html>
