/* Risk calculators */
(function () {
  function row(label, value) {
    return `<div class="stat-row"><span>${label}</span><span>${value}</span></div>`;
  }

  async function loadSymbol(market) {
    const key = market.includes("XAU") ? "XAU/USD" : "BTC/USD";
    const res = await fetch("/api/symbols/" + encodeURIComponent(key), { credentials: "same-origin" });
    if (!res.ok) return;
    const data = await res.json();
    const tick = document.getElementById("ps_tick");
    const tickval = document.getElementById("ps_tickval");
    const contract = document.getElementById("ps_contract");
    if (tick) tick.value = data.tick_size;
    if (tickval) tickval.value = data.tick_value_per_lot;
    if (contract) contract.value = data.contract_size;
  }

  document.addEventListener("DOMContentLoaded", () => {
    const market = document.getElementById("ps_market");
    market?.addEventListener("change", () => loadSymbol(market.value));

    document.getElementById("posSizeForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        market: document.getElementById("ps_market").value,
        account_balance: document.getElementById("ps_balance").value,
        risk_percent: document.getElementById("ps_risk").value,
        entry_price: document.getElementById("ps_entry").value,
        stop_loss_price: document.getElementById("ps_sl").value,
        tick_size: document.getElementById("ps_tick").value,
        tick_value_per_lot: document.getElementById("ps_tickval").value,
        contract_size: document.getElementById("ps_contract").value,
      };
      const res = await fetch("/api/risk/position-size", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      const out = document.getElementById("posSizeResult");
      if (!out) return;
      if (data.error) {
        out.innerHTML = `<div class="error-summary">${data.error}</div>`;
        return;
      }
      out.innerHTML =
        row("Risk amount", "$" + Number(data.risk_amount).toFixed(2)) +
        row("Stop distance", data.stop_distance) +
        row("Ticks", data.number_of_ticks) +
        row("Suggested lots", data.suggested_lot_size) +
        row("Position value", data.position_value != null ? "$" + Number(data.position_value).toFixed(2) : "—") +
        (data.warning ? `<div class="warning-summary mt-1">${data.warning}</div>` : "");
    });

    document.getElementById("rrForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        direction: document.getElementById("rr_dir").value,
        entry: document.getElementById("rr_entry").value,
        stop_loss: document.getElementById("rr_sl").value,
        take_profit: document.getElementById("rr_tp").value,
      };
      const res = await fetch("/api/risk/risk-reward", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      const out = document.getElementById("rrResult");
      const bar = document.getElementById("rrBar");
      if (data.error) {
        out.innerHTML = `<div class="error-summary">${data.error}</div>`;
        bar.hidden = true;
        return;
      }
      const risk = Number(data.risk_distance);
      const reward = Number(data.reward_distance);
      const total = risk + reward || 1;
      document.getElementById("rrRiskSeg").style.width = (risk / total) * 100 + "%";
      document.getElementById("rrRewardSeg").style.width = (reward / total) * 100 + "%";
      bar.hidden = false;
      out.innerHTML =
        row("Risk distance", data.risk_distance) +
        row("Reward distance", data.reward_distance) +
        row("R:R ratio", data.risk_reward_ratio) +
        row("Min BE win rate", data.min_breakeven_win_rate != null ? data.min_breakeven_win_rate + "%" : "—");
    });
  });
})();
