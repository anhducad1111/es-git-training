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
            <div class="chart-canvas">
                <div id="chartEmpty" class="chart-empty">Loading chart...</div>
                <div id="sensorChart" class="chart-wrap hidden" role="img" aria-label="Sensor history trend chart"></div>
                <div id="chartTooltip" class="chart-tooltip hidden"></div>
            </div>
        </section>
        <section class="panel analysis-panel" aria-labelledby="analysisTitle">
            <div class="panel-header">
                <div>
                    <h2 id="analysisTitle">AI Analysis</h2>
                    <p>Gemini analysis results received in the last 30 minutes.</p>
                </div>
            </div>
            <div id="analysisList" class="analysis-list">
                <div class="loading">Loading...</div>
            </div>
        </section>
        <footer>Auto refresh: every 5 seconds &middot; Apache / PHP / MySQL</footer>
    </main>
    <script>
        const API_URL = "api/get-data.php";
        const ANALYSIS_API_URL = "api/get-analysis.php";

        const CARD_GROUPS = [
            { title: "CO2 & Gas", labels: ["co2", "gas"] },
            { title: "Temperature, Humidity & Pressure", labels: ["temperature", "humidity", "pressure"] },
            { title: "Particulate Matter", labels: ["pm1.0", "pm2.5", "pm10"] },
            { title: "Battery", labels: ["battery"] },
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

        const COLOR_PALETTE = ["#e56a54", "#3d7ee8", "#20b26b", "#a35de0", "#e0a72a", "#2ac1c1", "#e05299", "#7d889b", "#4560c9"];

        let lastHistory = {};
        let visibleLabels = new Set();
        let seenLabels = new Set();
        let labelColors = {};

        function colorForLabel(label) {
            if (!(label in labelColors)) {
                labelColors[label] = COLOR_PALETTE[Object.keys(labelColors).length % COLOR_PALETTE.length];
            }
            return labelColors[label];
        }

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
            labels.filter(l => !grouped.has(l)).forEach(l => {
                cards.push(`<div class="card"><div class="card-label">${esc(l.toUpperCase())}</div>${rowHtml(l, latest[l])}<div class="card-footer">Updated: ${esc(latest[l].reading_time)}</div></div>`);
            });
            container.innerHTML = cards.join("");
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

        function renderCheckboxes(labels) {
            labels.forEach(l => {
                if (!seenLabels.has(l)) {
                    seenLabels.add(l);
                    visibleLabels.add(l);
                }
                colorForLabel(l);
            });
            const box = document.getElementById("chartCheckboxes");
            box.innerHTML = labels.map(l => `<label class="chart-checkbox"><input type="checkbox" data-label="${esc(l)}" ${visibleLabels.has(l) ? "checked" : ""}><span class="color-dot" style="background:${colorForLabel(l)}"></span>${esc(l)}</label>`).join("");
            box.querySelectorAll("input[type=checkbox]").forEach(input => {
                input.addEventListener("change", () => {
                    const label = input.dataset.label;
                    if (input.checked) visibleLabels.add(label); else visibleLabels.delete(label);
                    renderChart(lastHistory);
                });
            });
        }

        function renderChart(history) {
            const labels = Object.keys(history);
            renderCheckboxes(labels);
            const chart = document.getElementById("sensorChart");
            const empty = document.getElementById("chartEmpty");
            const activeLabels = labels.filter(l => visibleLabels.has(l) && history[l].length > 0);
            if (activeLabels.length === 0) {
                chart.innerHTML = "";
                chart.classList.add("hidden");
                empty.textContent = labels.length === 0 ? "No sensor data yet." : "No labels selected.";
                empty.classList.remove("hidden");
                return;
            }
            const width = 900, height = 360, left = 20, right = 20, top = 20, bottom = 20;
            const plotWidth = width - left - right, plotHeight = height - top - bottom;
            const allTimes = [...new Set(activeLabels.flatMap(l => history[l].map(p => p.reading_time)))].sort();
            const x = time => {
                const idx = allTimes.indexOf(time);
                return left + (allTimes.length <= 1 ? plotWidth / 2 : idx * plotWidth / (allTimes.length - 1));
            };
            const normalize = values => {
                const min = Math.min(...values), max = Math.max(...values);
                const range = max - min || 1;
                return values.map(v => (v - min) / range * 100);
            };
            let seriesSvg = "", dotsSvg = "";
            activeLabels.forEach(label => {
                const points = history[label];
                const values = points.map(p => p.data);
                const normalized = normalize(values);
                const color = colorForLabel(label);
                const unit = UNIT_MAP[label] || "";
                const coords = points.map((p, idx) => `${x(p.reading_time).toFixed(1)},${(top + plotHeight - normalized[idx] * plotHeight / 100).toFixed(1)}`).join(" ");
                seriesSvg += `<polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
                points.forEach((p, idx) => {
                    const cx = x(p.reading_time).toFixed(1);
                    const cy = (top + plotHeight - normalized[idx] * plotHeight / 100).toFixed(1);
                    const tooltip = `${label}: ${p.data}${unit ? " " + unit : ""}`;
                    dotsSvg += `<circle cx="${cx}" cy="${cy}" r="8" fill="transparent" data-tooltip="${esc(tooltip)}"/><circle cx="${cx}" cy="${cy}" r="3" fill="${color}" stroke="#fff" stroke-width="1.5" style="pointer-events:none"/>`;
                });
            });
            const gridLines = [0, 25, 50, 75, 100].map(pct => {
                const gy = top + plotHeight - pct * plotHeight / 100;
                return `<line x1="${left}" y1="${gy}" x2="${width - right}" y2="${gy}" class="chart-grid"/><text x="${left}" y="${gy - 4}" class="chart-axis">${pct}%</text>`;
            }).join("");
            chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">${gridLines}${seriesSvg}${dotsSvg}</svg>`;
            chart.classList.remove("hidden");
            empty.classList.add("hidden");
        }

        function mdInline(raw) {
            let s = esc(raw);
            s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
            s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
            s = s.replace(/`([^`]+?)`/g, "<code>$1</code>");
            s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, label, url) => {
                const safeUrl = /^https?:\/\//.test(url) ? esc(url) : "#";
                return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
            });
            return s;
        }

        function mdBlock(text) {
            const lines = text.split("\n");
            let html = "", listType = null, paragraph = [];
            const flushParagraph = () => {
                if (paragraph.length) {
                    html += `<p>${paragraph.join(" ")}</p>`;
                    paragraph = [];
                }
            };
            const closeList = () => {
                if (listType) {
                    html += `</${listType}>`;
                    listType = null;
                }
            };
            lines.forEach(rawLine => {
                const line = rawLine.trim();
                if (line === "") {
                    flushParagraph();
                    closeList();
                    return;
                }
                const heading = line.match(/^(#{1,6})\s+(.*)$/);
                if (heading) {
                    flushParagraph();
                    closeList();
                    const level = Math.min(heading[1].length + 3, 6);
                    html += `<h${level}>${mdInline(heading[2])}</h${level}>`;
                    return;
                }
                const ul = line.match(/^[-*]\s+(.*)$/);
                if (ul) {
                    flushParagraph();
                    if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
                    html += `<li>${mdInline(ul[1])}</li>`;
                    return;
                }
                const ol = line.match(/^\d+\.\s+(.*)$/);
                if (ol) {
                    flushParagraph();
                    if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
                    html += `<li>${mdInline(ol[1])}</li>`;
                    return;
                }
                closeList();
                paragraph.push(mdInline(line));
            });
            flushParagraph();
            closeList();
            return html;
        }

        function renderMarkdown(text) {
            const parts = String(text).split(/```/);
            return parts.map((part, i) => {
                if (i % 2 === 1) {
                    const lines = part.replace(/^\n/, "").split("\n");
                    if (lines[0] && !lines[0].includes(" ") && lines[0].trim() !== "") lines.shift();
                    return `<pre><code>${esc(lines.join("\n"))}</code></pre>`;
                }
                return mdBlock(part);
            }).join("");
        }

        function renderAnalysis(logs) {
            const container = document.getElementById("analysisList");
            if (!logs || logs.length === 0) {
                container.innerHTML = '<div class="empty">No analysis received in the last 30 minutes.</div>';
                return;
            }
            const log = logs[0];
            container.innerHTML = `<article class="analysis-entry"><div class="analysis-time">${esc(log.created_at)}</div><div class="analysis-content">${renderMarkdown(log.content)}</div></article>`;
        }

        async function loadAnalysis() {
            try {
                const response = await fetch(ANALYSIS_API_URL, { method: "GET", cache: "no-store" });
                if (!response.ok) throw new Error("HTTP " + response.status);
                const result = await response.json();
                if (!result.success) throw new Error(result.message || "API error");
                renderAnalysis(result.logs);
            } catch (error) {
                console.error(error);
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
                updateStaleWarning(result.latest, result.server_time);
                lastHistory = result.history;
                renderChart(result.history);
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

        const chartCanvas = document.querySelector(".chart-canvas");
        const chartTooltip = document.getElementById("chartTooltip");
        chartCanvas.addEventListener("pointermove", e => {
            const target = e.target.closest("circle[data-tooltip]");
            if (!target) {
                chartTooltip.classList.add("hidden");
                return;
            }
            const rect = chartCanvas.getBoundingClientRect();
            chartTooltip.textContent = target.dataset.tooltip;
            chartTooltip.style.left = (e.clientX - rect.left) + "px";
            chartTooltip.style.top = (e.clientY - rect.top) + "px";
            chartTooltip.classList.remove("hidden");
        });
        chartCanvas.addEventListener("pointerleave", () => chartTooltip.classList.add("hidden"));

        loadData();
        loadAnalysis();
        setInterval(() => {
            loadData();
            loadAnalysis();
        }, 5000);
    </script>
</body>

</html>
