window.Charts = (function () {
  function lineWithBand({ canvasId, labels, avg, min, max, avgLabel, colorRgb }) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
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
        scales: { x: { ticks: { maxTicksLimit: 8 } }, y: { beginAtZero: false } },
      },
    });
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

  function updateChart(chart, labels, datasetsData) {
    chart.data.labels = labels;
    datasetsData.forEach((data, i) => { chart.data.datasets[i].data = data; });
    chart.update('none');
  }

  return { lineWithBand, thresholdDataset, bandDataset, updateChart };
})();
