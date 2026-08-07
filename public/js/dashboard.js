/* Dashboard chart bootstrap */
(function () {
  document.addEventListener("DOMContentLoaded", async () => {
    const root = document.getElementById("dashboardCharts");
    if (!root || !window.TradeEdgeCharts) return;

    const params = new URLSearchParams({
      period: root.dataset.period || "30d",
      market: root.dataset.market || "ALL",
      setup: root.dataset.setup || "ALL",
      session: root.dataset.session || "ALL",
    });
    if (root.dataset.start) params.set("start", root.dataset.start);
    if (root.dataset.end) params.set("end", root.dataset.end);
    const q = params.toString();
    const C = TradeEdgeCharts;

    const [
      equityBalance,
      distribution,
      frequency,
      daily,
      monthly,
      market,
      setup,
      session,
      timeframe,
      drawdown,
    ] = await Promise.all([
      C.fetchJSON("/api/analytics/equity-vs-balance?" + q),
      C.fetchJSON("/api/analytics/distribution?" + q),
      C.fetchJSON("/api/analytics/frequency?" + q),
      C.fetchJSON("/api/analytics/daily-pnl?" + q),
      C.fetchJSON("/api/analytics/monthly-pnl?" + q),
      C.fetchJSON("/api/analytics/market-comparison?" + q),
      C.fetchJSON("/api/analytics/profit-by-setup?" + q),
      C.fetchJSON("/api/analytics/profit-by-session?" + q),
      C.fetchJSON("/api/analytics/winrate-by-timeframe?" + q),
      C.fetchJSON("/api/analytics/drawdown?" + q),
    ]);

    if (equityBalance && C.multiLineChart) {
      C.multiLineChart("chartCumulative", equityBalance.labels || [], [
        { label: "Trading equity", values: equityBalance.trading_equity || [], color: C.COLORS.blue },
        { label: "Account balance", values: equityBalance.account_balance || [], color: C.COLORS.gold, dashed: true },
      ]);
      const note = document.getElementById("equityBalanceNote");
      if (note && equityBalance.cash_adjustment != null) {
        const adj = Number(equityBalance.cash_adjustment);
        note.textContent =
          adj === 0
            ? "Trading equity matches account balance (no extra deposits/withdrawals detected)."
            : `Implied cash adjustment (deposits − withdrawals − non-trade items): ${adj >= 0 ? "+" : ""}$${adj.toFixed(2)}.`;
      }
    } else if (equityBalance) {
      C.lineChart("chartCumulative", equityBalance.labels || [], equityBalance.trading_equity || [], {
        label: "Equity",
        color: C.COLORS.blue,
      });
    }
    if (distribution) C.doughnutChart("chartDistribution", distribution.labels || [], distribution.values || [], distribution.colors);
    if (frequency) C.barChart("chartFrequency", frequency.labels || [], frequency.values || [], { color: C.COLORS.blue });
    if (daily) C.barChart("chartDaily", daily.labels || [], daily.values || [], { signed: true });
    if (monthly) C.barChart("chartMonthly", monthly.labels || [], monthly.values || [], { signed: true });
    if (market) C.barChart("chartMarket", market.labels || [], market.net_pnl || [], { colors: market.colors });
    if (setup) C.barChart("chartSetup", setup.labels || [], setup.values || [], { signed: true });
    if (session) C.barChart("chartSession", session.labels || [], session.values || [], { signed: true });
    if (timeframe) C.barChart("chartTimeframe", timeframe.labels || [], timeframe.values || [], { color: C.COLORS.gold, pct: true });
    if (drawdown) C.lineChart("chartDrawdown", drawdown.labels || [], drawdown.values || [], { label: "Drawdown", color: C.COLORS.red, fill: true });
  });
})();
