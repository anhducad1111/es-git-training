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
            <div class="server-status"><span id="statusDot" class="status-dot"></span><span id="statusText">Connecting...</span></div>
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

        function esc(v) {
            return String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
        }

        async function loadData() {
            console.log("loadData: not yet implemented");
        }

        loadData();
        setInterval(loadData, 5000);
    </script>
</body>

</html>
