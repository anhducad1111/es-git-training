<!DOCTYPE html>
<html lang="ja">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>Sensor Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>

<body>
    <main class="container">
        <header class="header">
            <div>
                <p class="eyebrow">ESP32 / SENSOR DASHBOARD</p>
                <h1>Sensor Dashboard</h1>
                <p class="subtitle">Live data from MySQL</p>
            </div>
            <div class="header-right">
                <div class="battery-status"><span id="batteryValue">--</span><small>%</small></div>
                <div class="server-status"><span id="statusDot" class="status-dot"></span><span id="statusText">Connecting...</span></div>
            </div>
        </header>
        <div id="staleWarning" class="stale-warning top-warning hidden" role="alert"></div>
        <div id="errorBox" class="error-box hidden"></div>
        <section class="cards" id="cardsContainer">
            <div class="loading">Loading...</div>
        </section>
        <section class="panel chart-panel" aria-labelledby="chartTitle">
            <div class="panel-header">
                <div>
                    <h2 id="chartTitle">Sensor History</h2>
                    <p>Each series normalized to 0-100%. Hover a point for the real value.</p>
                </div>
            </div>
            <div id="chartCheckboxes" class="chart-checkboxes"></div>
            <div id="chartEmpty" class="chart-empty">Loading chart...</div>
            <div id="sensorChart" class="chart-wrap hidden" role="img" aria-label="Sensor history trend chart"></div>
        </section>
        <footer>Auto refresh: every 5 seconds &middot; Apache / PHP / MySQL</footer>
    </main>
    <script>
        const API_URL = "api/get-data.php";

        const CARD_GROUPS = [
            { title: "CO2 & Gas", labels: ["co2", "gas"] },
            { title: "Temperature, Humidity & Pressure", labels: ["temperature", "humidity", "pressure"] },
            { title: "Particulate Matter", labels: ["pm1.0", "pm2.5", "pm10"] },
        ];

        const UNIT_MAP = {
            "co2": "ppm",
            "pm1.0": "µg/m³",
            "pm2.5": "µg/m³",
            "pm10": "µg/m³",
            "temperature": "°C",
            "humidity": "%",
            "pressure": "hPa",
            "battery": "%",
        };

        let lastHistory = {};

        function esc(v) {
            return String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
        }

        function rowHtml(label, entry) {
            const unit = UNIT_MAP[label] || "";
            return `<div class="metric-row"><span class="metric-name">${esc(label)}</span><span class="metric-value">${Number(entry.data).toFixed(2)}${unit ? " <small>" + esc(unit) + "</small>" : ""}</span></div>`;
        }

        function renderCards(latest) {
            const container = document.getElementById("cardsContainer");
            const labels = Object.keys(latest);
            if (labels.length === 0) {
                container.innerHTML = '<div class="empty">No data yet.</div>';
                return;
            }
            const grouped = new Set();
            const cards = [];
            CARD_GROUPS.forEach(group => {
                const present = group.labels.filter(l => labels.includes(l));
                if (present.length === 0) return;
                present.forEach(l => grouped.add(l));
                const rows = present.map(l => rowHtml(l, latest[l])).join("");
                const footerTime = present.reduce((max, l) => latest[l].reading_time > max ? latest[l].reading_time : max, latest[present[0]].reading_time);
                cards.push(`<div class="card"><div class="card-label">${esc(group.title.toUpperCase())}</div>${rows}<div class="card-footer">Updated: ${esc(footerTime)}</div></div>`);
            });
            labels.filter(l => !grouped.has(l) && l !== "battery").forEach(l => {
                cards.push(`<div class="card"><div class="card-label">${esc(l.toUpperCase())}</div>${rowHtml(l, latest[l])}<div class="card-footer">Updated: ${esc(latest[l].reading_time)}</div></div>`);
            });
            container.innerHTML = cards.join("");
        }

        function renderBattery(latest) {
            const valueEl = document.getElementById("batteryValue");
            valueEl.textContent = latest.battery ? Number(latest.battery.data).toFixed(0) : "--";
        }

        function updateStaleWarning(latest, serverTime) {
            const warning = document.getElementById("staleWarning");
            const labels = Object.keys(latest);
            if (labels.length === 0) {
                warning.classList.add("hidden");
                return;
            }
            const latestTime = labels.reduce((max, l) => latest[l].reading_time > max ? latest[l].reading_time : max, latest[labels[0]].reading_time);
            const latestDate = new Date(latestTime.replace(" ", "T"));
            const referenceDate = serverTime ? new Date(serverTime.replace(" ", "T")) : new Date();
            const ageMinutes = (referenceDate.getTime() - latestDate.getTime()) / 60000;
            if (Number.isFinite(ageMinutes) && ageMinutes >= 3) {
                warning.textContent = "No sensor update has been received for 3 minutes or more. Last update: " + latestTime;
                warning.classList.remove("hidden");
            } else {
                warning.classList.add("hidden");
            }
        }

        async function loadData() {
            const statusDot = document.getElementById("statusDot");
            const statusText = document.getElementById("statusText");
            const errorBox = document.getElementById("errorBox");
            try {
                const response = await fetch(API_URL, { method: "GET", cache: "no-store" });
                if (!response.ok) throw new Error("HTTP " + response.status);
                const result = await response.json();
                if (!result.success) throw new Error(result.message || "API error");
                renderCards(result.latest);
                renderBattery(result.latest);
                updateStaleWarning(result.latest, result.server_time);
                lastHistory = result.history;
                statusText.textContent = "Server Online";
                statusDot.classList.remove("offline");
                errorBox.classList.add("hidden");
            } catch (error) {
                console.error(error);
                statusText.textContent = "Server Error";
                statusDot.classList.add("offline");
                errorBox.textContent = "Could not load data: " + error.message;
                errorBox.classList.remove("hidden");
            }
        }

        loadData();
        setInterval(loadData, 5000);
    </script>
</body>

</html>
