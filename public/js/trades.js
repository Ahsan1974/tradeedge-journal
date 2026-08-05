/* Trade form live summary + import dropzone */
(function () {
  function num(id) {
    const el = document.getElementById(id);
    if (!el || el.value === "") return null;
    const v = Number(String(el.value).replace(/,/g, ""));
    return Number.isFinite(v) ? v : null;
  }

  function updateSummary() {
    const market = document.getElementById("market")?.value || "—";
    const dir = document.getElementById("direction")?.value || "—";
    const entry = num("entry_price");
    const sl = num("stop_loss");
    const tp = num("take_profit");
    const gross = num("profit_loss");
    const commission = num("commission") || 0;
    const swap = num("swap") || 0;
    const fees = num("fees") || 0;
    const netManual = document.getElementById("net_manual")?.checked;
    let net = num("net_profit_loss");
    if (!netManual && gross != null) {
      net = gross - commission - swap - fees;
      const netEl = document.getElementById("net_profit_loss");
      if (netEl && document.activeElement !== netEl) netEl.value = net.toFixed(2);
    }

    let riskDist = "—";
    let rewardDist = "—";
    let rr = "—";
    if (entry != null && sl != null) riskDist = Math.abs(entry - sl).toFixed(4);
    if (entry != null && tp != null) rewardDist = Math.abs(tp - entry).toFixed(4);
    if (entry != null && sl != null && tp != null && Math.abs(entry - sl) > 0) {
      rr = (Math.abs(tp - entry) / Math.abs(entry - sl)).toFixed(2);
      const rrEl = document.getElementById("risk_reward_ratio");
      if (rrEl && !document.querySelector('[name="rr_manual"]')?.checked && document.activeElement !== rrEl) {
        rrEl.value = rr;
      }
    }

    let status = "—";
    if (net != null) {
      status = net > 0 ? "WIN" : net < 0 ? "LOSS" : "BREAKEVEN";
      const statusEl = document.getElementById("status");
      const statusManual = document.getElementById("status_manual")?.checked;
      if (statusEl && !statusManual && statusEl.value !== "OPEN") statusEl.value = status;
    }

    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };
    set("sumMarket", market);
    set("sumDir", dir);
    set("sumRiskDist", riskDist);
    set("sumRewardDist", rewardDist);
    set("sumRR", rr);
    set("sumNet", net == null ? "—" : (net >= 0 ? "+" : "") + "$" + net.toFixed(2));
    set("sumStatus", status);
  }

  function initDropzone() {
    const zone = document.getElementById("dropzone");
    const input = document.getElementById("file");
    if (!zone || !input) return;
    ["dragenter", "dragover"].forEach((ev) =>
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((ev) =>
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
      })
    );
    zone.addEventListener("drop", (e) => {
      if (e.dataTransfer?.files?.length) input.files = e.dataTransfer.files;
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("tradeForm");
    if (form) {
      form.addEventListener("input", updateSummary);
      updateSummary();
    }
    initDropzone();
  });
})();
