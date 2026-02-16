(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var statusEl = document.getElementById("formStatus");

  function formatUsd(value) {
    return "USD " + Number(value || 0).toFixed(2);
  }

  function formatPnl(value) {
    var n = Number(value || 0);
    if (n > 0) return "+USD " + n.toFixed(2);
    if (n < 0) return "-USD " + Math.abs(n).toFixed(2);
    return "USD 0.00";
  }

  function applyTone(el, value) {
    el.classList.remove("positive", "negative");
    if (value > 0) el.classList.add("positive");
    if (value < 0) el.classList.add("negative");
  }

  var tabungBalance = Number(params.get("tabung_balance_usd") || 0);
  var growTarget = Number(params.get("grow_target_usd") || 0);
  var daysLeftLabel = params.get("days_left_label") || "-";
  var growProgressPct = Number(params.get("grow_progress_pct") || 0);
  var weeklyGrow = Number(params.get("weekly_grow_usd") || 0);
  var monthlyGrow = Number(params.get("monthly_grow_usd") || 0);

  document.getElementById("summaryName").textContent = params.get("name") || "-";
  document.getElementById("summaryDate").textContent = params.get("saved_date") || "-";
  document.getElementById("summaryTabungStartDate").textContent = params.get("tabung_start_date") || "-";

  document.getElementById("tabungBalance").textContent = formatUsd(tabungBalance);
  document.getElementById("growTarget").textContent = formatUsd(growTarget);
  document.getElementById("daysLeftLabel").textContent = daysLeftLabel;
  document.getElementById("growProgress").textContent = growProgressPct.toFixed(0) + "%";
  document.getElementById("weeklyGrow").textContent = formatPnl(weeklyGrow);
  document.getElementById("monthlyGrow").textContent = formatPnl(monthlyGrow);

  applyTone(document.getElementById("weeklyGrow"), weeklyGrow);
  applyTone(document.getElementById("monthlyGrow"), monthlyGrow);
  document.getElementById("growProgressBar").style.width = Math.max(0, Math.min(growProgressPct, 100)).toFixed(2) + "%";

  function backToProjectGrow() {
    var payload = { type: "project_grow_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Project Grow.";
  }

  document.getElementById("topBackBtn").addEventListener("click", backToProjectGrow);
  document.getElementById("backToProjectBtn").addEventListener("click", backToProjectGrow);
})();
