window.Charts = (function () {
  // Fills every "no data" span - the trailing one up to now, and any gap in the middle
  // of the range where the rover was offline and later reconnected - with a flat gray
  // rectangle, so a gap stays visibly marked even after data resumes on either side of
  // it. One solid block per span instead of many thin per-category bars (which show
  // grid lines through them as a striped pattern).
  const noDataBandPlugin = {
    id: 'noDataBand',
    beforeDatasetsDraw(chart) {
      const ranges = chart.$noDataRanges;
      if (!ranges || !ranges.length) return;
      const { ctx, chartArea, scales } = chart;
      if (!chartArea) return;
      ctx.save();
      ctx.fillStyle = 'rgba(140,140,140,0.25)';
      ranges.forEach(([fromIndex, toIndex]) => {
        const xFrom = fromIndex < 0 ? chartArea.left : scales.x.getPixelForValue(fromIndex);
        const xTo = toIndex === null ? chartArea.right : scales.x.getPixelForValue(toIndex);
        if (xTo <= xFrom) return;
        ctx.fillRect(xFrom, chartArea.top, xTo - xFrom, chartArea.bottom - chartArea.top);
      });
      ctx.restore();
    },
  };
  Chart.register(noDataBandPlugin);

  const AXIS_LABEL_COLOR = '#5b6270'; // matches --text-dim, used when a color can't be attributed to one series
  const TICK_COLOR = '#8a909c'; // slightly muted so tick labels don't compete with the plotted lines

  function axisTitle(text, colorRgb) {
    return {
      display: !!text,
      text: text || '',
      color: colorRgb ? `rgb(${colorRgb})` : AXIS_LABEL_COLOR,
      font: { weight: '600', size: 12 },
    };
  }

  function lineWithBand({ canvasId, labels, avg, min, max, avgLabel, colorRgb, noDataRanges, xTitle, yTitle }) {
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
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            ticks: { maxTicksLimit: 8, color: TICK_COLOR },
            title: axisTitle(xTitle === undefined ? 'Time (ICT)' : xTitle),
          },
          y: {
            beginAtZero: false,
            ticks: { color: TICK_COLOR },
            title: axisTitle(yTitle, yTitle ? colorRgb : null),
          },
        },
      },
    });
    chart.$noDataRanges = noDataRanges || [];
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

  function updateChart(chart, labels, datasetsData, noDataRanges) {
    chart.data.labels = labels;
    datasetsData.forEach((data, i) => { chart.data.datasets[i].data = data; });
    if (noDataRanges !== undefined) chart.$noDataRanges = noDataRanges;
    chart.update('none');
  }

  // Extends a chart's series with synthetic (null-valued) points across every "no data"
  // span - internal gaps where the rover reconnected after being offline, and the
  // trailing span up to "now" if the last real sample is stale - so those spans stay a
  // consistent width on screen and the noDataBand plugin above has something to shade.
  // The x-axis is a category scale (evenly spaced by index, not by real elapsed time),
  // so without synthetic points a gap's width on screen would reflect nothing about its
  // real duration - two adjacent real readings would sit at the same one-category
  // distance whether they were 1 second or 1 day apart.
  function appendGapFills(labels, series, timestampsMs, gapThresholdMs, labelFn) {
    const toLabel = labelFn || ((iso) => TimeUtil.timeHM(iso));
    const nowMs = Date.now();
    const avgStepMs = timestampsMs.length >= 2
      ? (timestampsMs[timestampsMs.length - 1] - timestampsMs[0]) / (timestampsMs.length - 1)
      : gapThresholdMs;

    function spanLabels(fromMs, toMs) {
      const spanMs = toMs - fromMs;
      const pointCount = Math.min(60, Math.max(1, Math.round(spanMs / Math.max(avgStepMs, 1000))));
      const extra = [];
      for (let i = 1; i <= pointCount; i += 1) {
        extra.push(toLabel(new Date(fromMs + (spanMs * i) / pointCount).toISOString()));
      }
      return extra;
    }

    const outLabels = [];
    const outSeries = series.map(() => []);
    const noDataRanges = [];
    const pushNulls = (extraLabels) => {
      extraLabels.forEach((lbl) => {
        outLabels.push(lbl);
        outSeries.forEach((arr) => arr.push(null));
      });
    };

    for (let i = 0; i < timestampsMs.length; i += 1) {
      if (i > 0 && (timestampsMs[i] - timestampsMs[i - 1]) > gapThresholdMs) {
        const fromIndex = outLabels.length - 1;
        pushNulls(spanLabels(timestampsMs[i - 1], timestampsMs[i]));
        noDataRanges.push([fromIndex, outLabels.length]);
      }
      outLabels.push(labels[i]);
      series.forEach((arr, si) => outSeries[si].push(arr[i]));
    }

    const lastMs = timestampsMs.length ? timestampsMs[timestampsMs.length - 1] : null;
    const trailingGapMs = lastMs === null ? gapThresholdMs + 1 : nowMs - lastMs;
    if (trailingGapMs > gapThresholdMs) {
      const fromIndex = outLabels.length - 1;
      const base = lastMs === null ? nowMs - trailingGapMs : lastMs;
      pushNulls(spanLabels(base, nowMs));
      noDataRanges.push([fromIndex, null]);
    }

    return { labels: outLabels, series: outSeries, noDataRanges };
  }

  return { lineWithBand, thresholdDataset, bandDataset, updateChart, appendGapFills, axisTitle, TICK_COLOR };
})();
