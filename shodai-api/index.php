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
                            <th>ID</th>
                            <th>Device</th>
                            <th>Temperature</th>
                            <th>Humidity</th>
                            <th>Time</th>
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
                updateDashboard(result.data);
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

        function updateDashboard(records) {
            const table = document.getElementById("sensorTable");
            if (!records || records.length === 0) {
                table.innerHTML = '<tr><td colspan="5" class="empty">No sensor data yet.</td></tr>';
                ["temperature", "humidity", "device"].forEach(id => document.getElementById(id).textContent = "--");
                return
            }
            const latest = records[0];
            document.getElementById("temperature").textContent = Number(latest.temperature).toFixed(1);
            document.getElementById("humidity").textContent = Number(latest.humidity).toFixed(1);
            document.getElementById("device").textContent = latest.device_name;
            document.getElementById("temperatureTime").textContent = "Updated: " + latest.created_at;
            document.getElementById("humidityTime").textContent = "Updated: " + latest.created_at;
            document.getElementById("lastUpdated").textContent = "Updated: " + latest.created_at;
            table.innerHTML = records.map(r => `<tr><td>${esc(r.id)}</td><td><span class="device-badge">${esc(r.device_name)}</span></td><td>${Number(r.temperature).toFixed(1)} °C</td><td>${Number(r.humidity).toFixed(1)} %</td><td class="time">${esc(r.created_at)}</td></tr>`).join("")
        }

        function esc(v) {
            return String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;")
        }
        loadData();
        setInterval(loadData, 5000);
    </script>
</body>

</html>