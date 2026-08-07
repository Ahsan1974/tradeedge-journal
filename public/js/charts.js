/* Chart.js helpers for dark theme */
window.TradeEdgeCharts = (function () {
  const COLORS = {
    text: "#94a3b8",
    grid: "rgba(148,163,184,0.12)",
    green: "#22c55e",
    red: "#ef4444",
    blue: "#3b82f6",
    gold: "#d4a017",
    btc: "#f7931a",
  };

  Chart.defaults.color = COLORS.text;
  Chart.defaults.borderColor = COLORS.grid;
  Chart.defaults.font.family = "'DM Sans', sans-serif";
  Chart.defaults.plugins.legend.labels.color = COLORS.text;
  if (Chart.defaults.animation) {
    Chart.defaults.animation.duration = 750;
    Chart.defaults.animation.easing = "easeOutQuart";
  }

  function moneyTooltip(ctx) {
    const v = ctx.parsed.y ?? ctx.parsed;
    if (v == null) return "";
    return (v >= 0 ? "+" : "") + "$" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  function emptyMessage(canvasId, message) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    parent.innerHTML = `<div class="empty-state" style="padding:2rem"><p class="muted">${message || "No data for this period"}</p></div>`;
  }

  function barColors(values) {
    return values.map((v) => (v >= 0 ? COLORS.green : COLORS.red));
  }

  function lineChart(canvasId, labels, values, opts = {}) {
    const el = document.getElementById(canvasId);
    if (!el) return null;
    if (!labels.length) {
      emptyMessage(canvasId);
      return null;
    }
    return new Chart(el, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: opts.label || "Value",
            data: values,
            borderColor: opts.color || COLORS.blue,
            backgroundColor: (opts.color || COLORS.blue) + "33",
            fill: opts.fill !== false,
            tension: 0.25,
            pointRadius: labels.length > 40 ? 0 : 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: moneyTooltip } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8 }, grid: { color: COLORS.grid } },
          y: { grid: { color: COLORS.grid } },
        },
      },
    });
  }

  function doughnutChart(canvasId, labels, values, colors) {
    const el = document.getElementById(canvasId);
    if (!el) return null;
    if (!values.some((v) => v > 0)) {
      emptyMessage(canvasId);
      return null;
    }
    return new Chart(el, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data: values, backgroundColor: colors || [COLORS.green, COLORS.red, "#94a3b8"] }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  function barChart(canvasId, labels, values, opts = {}) {
    const el = document.getElementById(canvasId);
    if (!el) return null;
    if (!labels.length) {
      emptyMessage(canvasId);
      return null;
    }
    const colors = opts.colors || (opts.signed ? barColors(values) : Array(values.length).fill(opts.color || COLORS.blue));
    return new Chart(el, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label: opts.label || "", data: values, backgroundColor: colors, borderRadius: 4 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: opts.pct ? (c) => `${c.parsed.y?.toFixed(1)}%` : moneyTooltip } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 10 }, grid: { display: false } },
          y: { grid: { color: COLORS.grid } },
        },
      },
    });
  }

  function multiLineChart(canvasId, labels, datasets, opts = {}) {
    const el = document.getElementById(canvasId);
    if (!el) return null;
    if (!labels.length) {
      emptyMessage(canvasId);
      return null;
    }
    return new Chart(el, {
      type: "line",
      data: {
        labels,
        datasets: datasets.map((ds) => ({
          label: ds.label || "Value",
          data: ds.values || [],
          borderColor: ds.color || COLORS.blue,
          backgroundColor: "transparent",
          fill: false,
          tension: 0.25,
          pointRadius: labels.length > 40 ? 0 : 2,
          borderWidth: 2,
          borderDash: ds.dashed ? [6, 4] : [],
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: "bottom" },
          tooltip: { callbacks: { label: moneyTooltip } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8 }, grid: { color: COLORS.grid } },
          y: { grid: { color: COLORS.grid } },
        },
      },
    });
  }

  return { COLORS, fetchJSON, lineChart, multiLineChart, doughnutChart, barChart, emptyMessage, moneyTooltip };
})();
