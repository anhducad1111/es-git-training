window.Charts = (function () {
  // Fills the chart area from the last real data point to the right edge with a flat
  // gray rectangle, marking "no data yet" as a single solid block instead of many thin
  // per-category bars (which show grid lines through them as a striped pattern).
  const noDataBandPlugin = {
    id: 'noDataBand',
    beforeDatasetsDraw(chart) {
      const fromIndex = chart.$noDataFromIndex;
      if (fromIndex === undefined || fromIndex === null) return;
      const { ctx, chartArea, scales } = chart;
      if (!chartArea) return;
      const xPixel = fromIndex < 0 ? chartArea.left : scales.x.getPixelForValue(fromIndex);
      if (xPixel >= chartArea.right) return;
      ctx.save();
      ctx.fillStyle = 'rgba(140,140,140,0.25)';
      ctx.fillRect(xPixel, chartArea.top, chartArea.right - xPixel, chartArea.bottom - chartArea.top);
      ctx.restore();
    },
  };
  Chart.register(noDataBandPlugin);

  function axisTitle(text) {
    return { display: !!text, text: text || '' };
  }

  function lineWithBand({ canvasId, labels, avg, min, max, avgLabel, colorRgb, noDataFromIndex, xTitle, yTitle }) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: `${avgLabel} max`, data: max, borderWidth: 0, pointRadius: 0, fill: '+1', backgroundColor: `rgba(${colorRgb},0.15)`, spanGaps: false },
          { label: `${avgLabel} min`, data: min, borderWidth: 0, pointRadius: 0, fill: false, spanGaps: false },
          { label: avgLabel, data: avg, borderColor: `rgb(${colorRgb})`, backgroundColor: `rgb(${colorRgb})`, borderWidth: 2, pointRadius: 0, spanGaps: false },
        ],
      },
      options: {
        responsive: true,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { ticks: { maxTicksLimit: 8 }, title: axisTitle(xTitle === undefined ? 'Time (ICT)' : xTitle) },
          y: { beginAtZero: false, title: axisTitle(yTitle) },
        },
      },
    });
    chart.$noDataFromIndex = noDataFromIndex === undefined ? null : noDataFromIndex;
    return chart;
  }

  function thresholdDataset(label, value, count, colorRgb) {
    return { label, data: new Array(count).fill(value), borderColor: `rgb(${colorRgb})`, borderDash: [6, 4], borderWidth: 1, pointRadius: 0 };
  }

  function bandDataset(label, flags, yMax, colorRgba) {
    return {
      type: 'bar', label, data: flags.map((flag) => (flag ? yMax : 0)),
      backgroundColor: colorRgba, barPercentage: 1.0, categoryPercentage: 1.0, order: 5,
    };
  }

  function updateChart(chart, labels, datasetsData, noDataFromIndex) {
    chart.data.labels = labels;
    datasetsData.forEach((data, i) => { chart.data.datasets[i].data = data; });
    if (noDataFromIndex !== undefined) chart.$noDataFromIndex = noDataFromIndex;
    chart.update('none');
  }

  // Extends a chart's series with synthetic (null-valued) points from the last real
  // sample up to "now" so the x-axis right edge always reflects the current time, and
  // reports the index the real data ends at (for the noDataBand plugin above to shade).
  // The x-axis is a category scale (evenly spaced by index, not by real elapsed time),
  // so the number of synthetic points must roughly match the real data's own spacing -
  // otherwise a single trailing point would sit at nearly the same pixel as the last
  // real one regardless of how large the actual time gap is.
  function appendNowGapTail(labels, series, timestampsMs, gapThresholdMs, labelFn) {
    const toLabel = labelFn || ((iso) => TimeUtil.timeHM(iso));
    const nowMs = Date.now();
    const lastMs = timestampsMs.length ? timestampsMs[timestampsMs.length - 1] : null;
    const gapMs = lastMs === null ? gapThresholdMs + 1 : nowMs - lastMs;
    if (gapMs <= gapThresholdMs) {
      return { labels, series, noDataFromIndex: null };
    }
    const stepMs = timestampsMs.length >= 2
      ? (timestampsMs[timestampsMs.length - 1] - timestampsMs[0]) / (timestampsMs.length - 1)
      : gapMs;
    const pointCount = Math.min(300, Math.max(1, Math.round(gapMs / Math.max(stepMs, 1000))));
    const base = lastMs === null ? nowMs - gapMs : lastMs;
    const extraLabels = [];
    for (let i = 1; i <= pointCount; i += 1) {
      extraLabels.push(toLabel(new Date(base + (gapMs * i) / pointCount).toISOString()));
    }
    return {
      labels: labels.concat(extraLabels),
      series: series.map((arr) => arr.concat(new Array(extraLabels.length).fill(null))),
      noDataFromIndex: labels.length - 1,
    };
  }

  return { lineWithBand, thresholdDataset, bandDataset, updateChart, appendNowGapTail, axisTitle };
})();
