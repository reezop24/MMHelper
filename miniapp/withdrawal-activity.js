(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var content = window.MMHELPER_CONTENT || {};
  var params = new URLSearchParams(window.location.search);

  function formatUsd(value) {
    return Number(value || 0).toFixed(2);
  }

  function formatPnl(value) {
    var number = Number(value || 0);
    var sign = number > 0 ? "+" : "";
    return sign + "USD " + number.toFixed(2);
  }

  var name = params.get("name") || "-";
  var initialCapital = Number(params.get("initial_capital_usd") || 0);
  var savedDate = params.get("saved_date") || "-";
  var tabungStartDate = params.get("tabung_start_date") || "-";
  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var currentProfit = Number(params.get("current_profit_usd") || 0);
  var totalBalance = Number(params.get("total_balance_usd") || 0);
  var tabungBalance = Number(params.get("tabung_balance_usd") || 0);
  var capital = Number(params.get("capital_usd") || 0);
  var weeklyPerformance = Number(params.get("weekly_performance_usd") || 0);
  var monthlyPerformance = Number(params.get("monthly_performance_usd") || 0);

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryCapital").textContent = formatUsd(initialCapital);
  document.getElementById("summaryBalance").textContent = formatUsd(currentBalance);
  document.getElementById("summaryTotalBalance").textContent = formatUsd(totalBalance);
  document.getElementById("summaryTabungBalance").textContent = formatUsd(tabungBalance);
  document.getElementById("summaryCapitalTotal").textContent = formatUsd(capital);
  document.getElementById("summaryWeeklyPerformance").textContent = formatPnl(weeklyPerformance);
  document.getElementById("summaryMonthlyPerformance").textContent = formatPnl(monthlyPerformance);
  document.getElementById("summaryDate").textContent = savedDate;
  document.getElementById("summaryTabungStartDate").textContent = tabungStartDate;

  var introText = document.getElementById("introText");
  var reasonPrompt = document.getElementById("reasonPrompt");
  var amountPrompt = document.getElementById("amountPrompt");
  var finalPrompt = document.getElementById("finalPrompt");

  var weeklyAbs = Math.abs(weeklyPerformance).toFixed(2);
  var weeklyLabel = "(USD " + weeklyAbs + ")";

  if (weeklyPerformance >= 0) {
    introText.textContent = (content.getWithdrawalIntro || function () { return ""; })(weeklyLabel);
  } else {
    introText.textContent = (content.getWithdrawalIntroLoss || function () { return ""; })(weeklyLabel);
  }

  reasonPrompt.textContent = content.withdrawalReasonPrompt || "";
  amountPrompt.textContent = content.withdrawalAmountPrompt || "";
  finalPrompt.textContent = content.withdrawalFinalPrompt || "";

  var reasonSelect = document.getElementById("reasonSelect");
  (content.withdrawalReasons || []).forEach(function (reason) {
    var opt = document.createElement("option");
    opt.value = reason;
    opt.textContent = reason;
    reasonSelect.appendChild(opt);
  });

  var form = document.getElementById("withdrawalForm");
  var statusEl = document.getElementById("formStatus");
  var topBackBtn = document.getElementById("topBackBtn");
  var backToAccountBtn = document.getElementById("backToAccountBtn");

  topBackBtn.textContent = content.accountActivityBackBtn || "⬅️ Back to Account Activity";
  topBackBtn.addEventListener("click", function () {
    var payload = { type: "account_activity_back_to_menu" };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Account Activity.";
  });

  backToAccountBtn.textContent = content.accountActivityBackBtn || "⬅️ Back to Account Activity";
  backToAccountBtn.addEventListener("click", function () {
    var payload = { type: "account_activity_back_to_menu" };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Account Activity.";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var reason = (reasonSelect.value || "").trim();
    var amount = Number((document.getElementById("withdrawAmount").value || "").trim());

    if (!reason) {
      statusEl.textContent = "Pilih reason dulu.";
      return;
    }

    if (Number.isNaN(amount) || amount <= 0) {
      statusEl.textContent = "Isi jumlah withdraw yang valid.";
      return;
    }

    var payload = {
      type: "withdrawal_activity",
      reason: reason,
      amount_usd: amount
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
