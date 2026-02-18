(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var statusEl = document.getElementById("status");

  function asNum(key) {
    return Number(params.get(key) || 0);
  }

  function usd(v) {
    return "USD " + Number(v || 0).toFixed(2);
  }

  function setSignedClass(el, value) {
    el.classList.remove("value-positive", "value-negative");
    var n = Number(value || 0);
    if (n > 0) {
      el.classList.add("value-positive");
    } else if (n < 0) {
      el.classList.add("value-negative");
    }
  }

  function backToReports() {
    var payload = { type: "records_reports_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Records & Reports.";
  }

  var weekly = asNum("weekly_pl_usd");
  var monthly = asNum("monthly_pl_usd");
  var profit = asNum("current_profit_usd");
  var targetCapital = asNum("target_capital_usd");
  var growTarget = asNum("grow_target_usd");

  document.getElementById("vName").textContent = params.get("name") || "-";
  document.getElementById("vSavedDate").textContent = params.get("saved_date") || "-";
  document.getElementById("vTabungStart").textContent = params.get("tabung_start_date") || "-";
  document.getElementById("vOpeningLabel").textContent = params.get("opening_balance_label") || "Opening Balance";
  document.getElementById("vInitial").textContent = usd(asNum("initial_balance_usd"));
  document.getElementById("vCurrent").textContent = usd(asNum("current_balance_usd"));
  document.getElementById("vProfit").textContent = usd(profit);
  document.getElementById("vCapital").textContent = usd(asNum("capital_usd"));
  document.getElementById("vTabung").textContent = usd(asNum("tabung_balance_usd"));
  document.getElementById("vWeekly").textContent = usd(weekly);
  document.getElementById("vMonthly").textContent = usd(monthly);
  document.getElementById("vTargetCapital").textContent = usd(targetCapital);
  document.getElementById("vGrowTarget").textContent = usd(growTarget);
  document.getElementById("vTargetLabel").textContent = params.get("target_label") || "-";
  document.getElementById("vMissionActive").textContent = (params.get("mission_active") || "0") === "1" ? "Yes" : "No";
  document.getElementById("vMissionMode").textContent = params.get("mission_mode_level") || "-";
  document.getElementById("vMissionStatus").textContent = params.get("mission_status_text") || "-";

  setSignedClass(document.getElementById("vProfit"), profit);
  setSignedClass(document.getElementById("vWeekly"), weekly);
  setSignedClass(document.getElementById("vMonthly"), monthly);
  setSignedClass(document.getElementById("vGrowTarget"), growTarget);

  document.getElementById("topBackBtn").addEventListener("click", backToReports);
  document.getElementById("backBtn").addEventListener("click", backToReports);
})();
