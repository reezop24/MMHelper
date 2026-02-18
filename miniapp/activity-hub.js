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
  var tabungAmountWrapEl = document.getElementById("tabungAmountWrap");
  var tabungHintEl = document.getElementById("tabungHint");

  function syncSummary() {
    document.getElementById("summaryName").textContent = model.name;
    document.getElementById("summaryDate").textContent = model.savedDate;
    document.getElementById("summaryBalance").textContent = formatUsd(model.currentBalance);
    document.getElementById("summaryTabung").textContent = formatUsd(model.tabungBalance);
    document.getElementById("summaryWeekly").textContent = formatPnl(model.weeklyPerformance);
    document.getElementById("summaryMonthly").textContent = formatPnl(model.monthlyPerformance);
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
  }

  function setTradingMode(mode) {
    model.tradingMode = mode;
    modeProfitBtn.classList.toggle("active", mode === "profit");
    modeLossBtn.classList.toggle("active", mode === "loss");
    statusEl.textContent = "";
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

  function syncTabungModeView() {
    var action = (tabungActionEl.value || "save").trim();
    tabungAmountWrapEl.classList.toggle("hidden", false);
    if (action === "emergency_withdrawal") {
      tabungHintEl.textContent = "Emergency left bulan ini: " + model.emergencyLeft + " kali.";
      return;
    }
    if (action === "goal_to_current" || action === "goal_direct_withdrawal") {
      tabungHintEl.textContent = model.goalReached
        ? "Goal reached: action ini dibenarkan."
        : "Goal belum capai: action ini akan ditolak oleh backend.";
      return;
    }
    tabungHintEl.textContent = "Submit akan hantar payload tabung_update_action.";
  }

  function sendPayload(payload) {
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  }

  function backToAccount() {
    sendPayload({ type: "account_activity_back_to_menu" });
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
  });

  tabungActionEl.addEventListener("change", function () {
    syncTabungModeView();
    statusEl.textContent = "";
  });

  document.getElementById("topBackBtn").addEventListener("click", backToAccount);
  document.getElementById("backBtn").addEventListener("click", backToAccount);

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
  fillCashflowReasons(model.cashflowType);
  syncTabungModeView();
  switchTab("trading");
})();
