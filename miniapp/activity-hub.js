(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var content = window.MMHELPER_CONTENT || {};
  var params = new URLSearchParams(window.location.search);

  function asNum(name) {
    return Number(params.get(name) || 0);
  }

  function formatUsd(v) {
    return Number(v || 0).toFixed(2);
  }

  function formatPnl(v) {
    var n = Number(v || 0);
    return (n > 0 ? "+" : "") + "USD " + n.toFixed(2);
  }

  var model = {
    name: params.get("name") || "-",
    savedDate: params.get("saved_date") || "-",
    currentBalance: asNum("current_balance_usd"),
    tabungBalance: asNum("tabung_balance_usd"),
    targetBalance: asNum("target_balance_usd"),
    growTarget: asNum("grow_target_usd"),
    targetDays: asNum("target_days"),
    weeklyPerformance: asNum("weekly_performance_usd"),
    monthlyPerformance: asNum("monthly_performance_usd"),
    goalReached: (params.get("goal_reached") || "0") === "1",
    emergencyLeft: asNum("emergency_left"),

    activeTab: "trading",
    tradingMode: "",
    cashflowType: "deposit",
  };

  var statusEl = document.getElementById("formStatus");
  var tabButtons = Array.prototype.slice.call(document.querySelectorAll(".tab-btn"));
  var panels = {
    trading: document.getElementById("tab-trading"),
    cashflow: document.getElementById("tab-cashflow"),
    tabung: document.getElementById("tab-tabung"),
  };

  var modeProfitBtn = document.getElementById("modeProfit");
  var modeLossBtn = document.getElementById("modeLoss");
  var cashflowTypeEl = document.getElementById("cashflowType");
  var cashflowReasonEl = document.getElementById("cashflowReason");
  var tabungActionEl = document.getElementById("tabungAction");
  var tradingAmountEl = document.getElementById("tradingAmount");
  var cashflowAmountEl = document.getElementById("cashflowAmount");
  var tabungAmountEl = document.getElementById("tabungAmount");

  function readAmount(el) {
    var n = Number((el.value || "").trim());
    return Number.isFinite(n) && n > 0 ? n : 0;
  }

  function sanitizeNumericInput(el) {
    var raw = String(el.value || "");
    var cleaned = raw.replace(/[^0-9.]/g, "");
    var parts = cleaned.split(".");
    if (parts.length > 2) {
      cleaned = parts[0] + "." + parts.slice(1).join("");
    }
    if (cleaned !== raw) {
      el.value = cleaned;
    }
  }

  function setSignedTone(el, value) {
    el.classList.remove("value-positive", "value-negative");
    if (value > 0) {
      el.classList.add("value-positive");
    } else if (value < 0) {
      el.classList.add("value-negative");
    }
  }

  function syncSummary() {
    var capital = model.currentBalance + model.tabungBalance;
    var weeklyEl = document.getElementById("summaryWeekly");
    var monthlyEl = document.getElementById("summaryMonthly");
    document.getElementById("summaryName").textContent = model.name;
    document.getElementById("summaryDate").textContent = model.savedDate;
    document.getElementById("summaryBalance").textContent = formatUsd(model.currentBalance);
    document.getElementById("summaryTabung").textContent = formatUsd(model.tabungBalance);
    document.getElementById("summaryCapital").textContent = formatUsd(capital);
    weeklyEl.textContent = formatPnl(model.weeklyPerformance);
    monthlyEl.textContent = formatPnl(model.monthlyPerformance);
    setSignedTone(weeklyEl, model.weeklyPerformance);
    setSignedTone(monthlyEl, model.monthlyPerformance);
  }

  function syncMetrics() {
    var capital = model.currentBalance + model.tabungBalance;
    var tradingDaysMap = { 30: 22, 90: 66, 180: 132 };
    var tradingDays = tradingDaysMap[model.targetDays] || 0;
    var dailyTarget = tradingDays > 0 ? (model.growTarget / tradingDays) : 0;
    var progressPct = model.targetBalance > 0 ? Math.min((capital / model.targetBalance) * 100, 100) : 0;
    var leftToGoal = Math.max(model.targetBalance - capital, 0);
    var dailyTargetEl = document.getElementById("metricDailyTarget");
    var growProgressEl = document.getElementById("metricGrowProgress");
    var leftToGoalEl = document.getElementById("metricLeftToGoal");

    document.getElementById("metricTargetCapital").textContent = "USD " + formatUsd(model.targetBalance);
    document.getElementById("metricGrowTarget").textContent = "USD " + formatUsd(model.growTarget);
    document.getElementById("metricTargetDays").textContent = String(model.targetDays || 0);
    document.getElementById("metricTradingDays").textContent = String(tradingDays);
    dailyTargetEl.textContent = "USD " + formatUsd(dailyTarget);
    growProgressEl.textContent = Number(progressPct).toFixed(2) + "%";
    leftToGoalEl.textContent = "USD " + formatUsd(leftToGoal);
    document.getElementById("metricGoalStatus").textContent = model.goalReached ? "Reached" : "Not Reached";
    setSignedTone(dailyTargetEl, dailyTarget);
    setSignedTone(growProgressEl, progressPct);
    setSignedTone(leftToGoalEl, leftToGoal);
  }

  function syncLivePreview() {
    var currentAfter = model.currentBalance;
    var tabungAfter = model.tabungBalance;
    var amount = 0;

    if (model.activeTab === "trading") {
      amount = readAmount(tradingAmountEl);
      if (model.tradingMode === "profit") {
        currentAfter += amount;
      } else if (model.tradingMode === "loss") {
        currentAfter -= amount;
      }
    } else if (model.activeTab === "cashflow") {
      amount = readAmount(cashflowAmountEl);
      if (model.cashflowType === "withdrawal") {
        currentAfter -= amount;
      } else {
        currentAfter += amount;
      }
    } else {
      amount = readAmount(tabungAmountEl);
      var action = String(tabungActionEl.value || "save").trim();
      if (action === "save") {
        currentAfter -= amount;
        tabungAfter += amount;
      } else if (action === "emergency_withdrawal") {
        tabungAfter -= amount;
      } else if (action === "goal_to_current") {
        currentAfter += amount;
        tabungAfter -= amount;
      } else if (action === "goal_direct_withdrawal") {
        tabungAfter -= amount;
      }
    }

    var capitalAfter = currentAfter + tabungAfter;
    var growLeftAfter = Math.max(model.targetBalance - capitalAfter, 0);
    var previewCurrentEl = document.getElementById("previewCurrent");
    var previewTabungEl = document.getElementById("previewTabung");
    var previewCapitalEl = document.getElementById("previewCapital");
    var previewGrowLeftEl = document.getElementById("previewGrowLeft");
    previewCurrentEl.textContent = "USD " + formatUsd(currentAfter);
    previewTabungEl.textContent = "USD " + formatUsd(tabungAfter);
    previewCapitalEl.textContent = "USD " + formatUsd(capitalAfter);
    previewGrowLeftEl.textContent = "USD " + formatUsd(growLeftAfter);
    setSignedTone(previewCurrentEl, currentAfter);
    setSignedTone(previewTabungEl, tabungAfter);
    setSignedTone(previewCapitalEl, capitalAfter);
    setSignedTone(previewGrowLeftEl, growLeftAfter);
  }

  function switchTab(tabId) {
    model.activeTab = tabId;
    tabButtons.forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });
    Object.keys(panels).forEach(function (id) {
      panels[id].classList.toggle("active", id === tabId);
    });
    statusEl.textContent = "";
    syncLivePreview();
  }

  function setTradingMode(mode) {
    model.tradingMode = mode;
    modeProfitBtn.classList.toggle("active", mode === "profit");
    modeLossBtn.classList.toggle("active", mode === "loss");
    statusEl.textContent = "";
    syncLivePreview();
  }

  function fillCashflowReasons(kind) {
    var items = kind === "withdrawal" ? (content.withdrawalReasons || []) : (content.depositReasons || []);
    cashflowReasonEl.innerHTML = "";
    items.forEach(function (reason) {
      var opt = document.createElement("option");
      opt.value = reason;
      opt.textContent = reason;
      cashflowReasonEl.appendChild(opt);
    });
    if (items.length === 0) {
      var fallback = document.createElement("option");
      fallback.value = "Manual";
      fallback.textContent = "Manual";
      cashflowReasonEl.appendChild(fallback);
    }
  }

  function sendPayload(payload) {
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  }

  function backToMainMenu() {
    sendPayload({ type: "risk_calculator_back_to_menu" });
  }

  tabButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      switchTab(btn.getAttribute("data-tab") || "trading");
    });
  });

  modeProfitBtn.addEventListener("click", function () { setTradingMode("profit"); });
  modeLossBtn.addEventListener("click", function () { setTradingMode("loss"); });

  cashflowTypeEl.addEventListener("change", function () {
    model.cashflowType = cashflowTypeEl.value;
    fillCashflowReasons(model.cashflowType);
    syncLivePreview();
  });

  tabungActionEl.addEventListener("change", function () {
    statusEl.textContent = "";
    syncLivePreview();
  });
  tradingAmountEl.addEventListener("input", function () {
    sanitizeNumericInput(tradingAmountEl);
    syncLivePreview();
  });
  cashflowAmountEl.addEventListener("input", function () {
    sanitizeNumericInput(cashflowAmountEl);
    syncLivePreview();
  });
  tabungAmountEl.addEventListener("input", function () {
    sanitizeNumericInput(tabungAmountEl);
    syncLivePreview();
  });

  document.getElementById("topBackBtn").addEventListener("click", backToMainMenu);
  document.getElementById("backBtn").addEventListener("click", backToMainMenu);

  document.getElementById("hubForm").addEventListener("submit", function (event) {
    event.preventDefault();
    statusEl.textContent = "";

    if (model.activeTab === "trading") {
      var amountTrading = Number((document.getElementById("tradingAmount").value || "").trim());
      if (!model.tradingMode) {
        statusEl.textContent = "Pilih mode Profit/Loss dulu.";
        return;
      }
      if (!Number.isFinite(amountTrading) || amountTrading <= 0) {
        statusEl.textContent = "Isi amount trading yang valid.";
        return;
      }
      sendPayload({
        type: "trading_activity_update",
        mode: model.tradingMode,
        amount_usd: amountTrading,
      });
      return;
    }

    if (model.activeTab === "cashflow") {
      var amountCash = Number((document.getElementById("cashflowAmount").value || "").trim());
      var reason = String(cashflowReasonEl.value || "").trim();
      if (!reason) {
        statusEl.textContent = "Pilih reason dulu.";
        return;
      }
      if (!Number.isFinite(amountCash) || amountCash <= 0) {
        statusEl.textContent = "Isi amount yang valid.";
        return;
      }
      if (model.cashflowType === "withdrawal") {
        sendPayload({ type: "withdrawal_activity", reason: reason, amount_usd: amountCash });
      } else {
        sendPayload({ type: "deposit_activity", reason: reason, amount_usd: amountCash });
      }
      return;
    }

    var action = String(tabungActionEl.value || "save").trim();

    var amountTabung = Number((document.getElementById("tabungAmount").value || "").trim());
    if (!Number.isFinite(amountTabung) || amountTabung <= 0) {
      statusEl.textContent = "Isi amount tabung yang valid.";
      return;
    }
    sendPayload({
      type: "tabung_update_action",
      action: action,
      amount_usd: amountTabung,
    });
  });

  syncSummary();
  syncMetrics();
  fillCashflowReasons(model.cashflowType);
  syncLivePreview();
  switchTab("trading");
})();
