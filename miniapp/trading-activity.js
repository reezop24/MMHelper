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

  function formatPct(value) {
    return Number(value || 0).toFixed(2);
  }

  function tradingDaysByTargetDays(targetDays) {
    if (targetDays === 30) return 22;
    if (targetDays === 90) return 66;
    if (targetDays === 180) return 132;
    return 0;
  }

  function getNumericInputValue(inputEl) {
    var raw = (inputEl.value || "").trim();
    if (!raw) return NaN;
    return Number(raw);
  }

  function isValidAmount(amount) {
    return !Number.isNaN(amount) && amount > 0;
  }

  function setValueTone(el, value) {
    el.classList.remove("positive", "negative");
    if (value > 0) el.classList.add("positive");
    if (value < 0) el.classList.add("negative");
  }

  var name = params.get("name") || "-";
  var initialCapital = Number(params.get("initial_capital_usd") || 0);
  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var savedDate = params.get("saved_date") || "-";
  var tabungStartDate = params.get("tabung_start_date") || "-";
  var totalBalance = Number(params.get("total_balance_usd") || 0);
  var tabungBalance = Number(params.get("tabung_balance_usd") || 0);
  var weeklyPerformance = Number(params.get("weekly_performance_usd") || 0);
  var monthlyPerformance = Number(params.get("monthly_performance_usd") || 0);
  var targetBalance = Number(params.get("target_balance_usd") || 0);
  var growTarget = Number(params.get("grow_target_usd") || 0);
  var targetDays = Number(params.get("target_days") || 0);
  var goalReached = (params.get("goal_reached") || "0") === "1";
  var goalBaselineBalance = Number(params.get("goal_baseline_balance_usd") || 0);
  var tabungUpdateUrl = params.get("tabung_update_url") || "";
  var dailyTargetReachedToday = (params.get("daily_target_reached_today") || "0") === "1";

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryCapital").textContent = formatUsd(initialCapital);
  document.getElementById("summaryBalance").textContent = formatUsd(currentBalance);
  document.getElementById("summaryTotalBalance").textContent = formatUsd(totalBalance);
  document.getElementById("summaryTabungBalance").textContent = formatUsd(tabungBalance);
  document.getElementById("summaryWeeklyPerformance").textContent = formatPnl(weeklyPerformance);
  document.getElementById("summaryMonthlyPerformance").textContent = formatPnl(monthlyPerformance);
  document.getElementById("summaryDate").textContent = savedDate;
  document.getElementById("summaryTabungStartDate").textContent = tabungStartDate;

  var dailyTargetValueEl = document.getElementById("dailyTargetValue");
  var dailyTargetNoteEl = document.getElementById("dailyTargetNote");
  var dailyTargetActionBtn = document.getElementById("dailyTargetActionBtn");
  var dailyHitAlertEl = document.getElementById("dailyHitAlert");
  var floatingProgressUsd = currentBalance - goalBaselineBalance;
  dailyTargetActionBtn.classList.add("hidden");
  dailyTargetActionBtn.addEventListener("click", function () {
    if (!tabungUpdateUrl) return;
    window.location.href = tabungUpdateUrl;
  });

  if (targetBalance <= 0) {
    dailyTargetValueEl.textContent = "USD 0.00 (0.00%)";
    dailyTargetNoteEl.textContent = "Set New Goal dulu untuk aktifkan tracker target harian.";
  } else if (goalReached || growTarget <= 0) {
    dailyTargetValueEl.textContent = "USD 0.00 (0.00%)";
    dailyTargetNoteEl.textContent = "Target dah capai. Masukkan keuntungan ke tabung supaya grow target berubah.";
    if (tabungUpdateUrl) {
      dailyTargetActionBtn.classList.remove("hidden");
    }
  } else {
    var tradingDays = tradingDaysByTargetDays(targetDays);
    var dailyTargetUsd = tradingDays > 0 ? growTarget / tradingDays : growTarget / 22;
    var baseBalance = currentBalance > 0 ? currentBalance : initialCapital;
    var dailyTargetPct = baseBalance > 0 ? (dailyTargetUsd / baseBalance) * 100 : 0;
    if (floatingProgressUsd >= dailyTargetUsd && dailyTargetUsd > 0) {
      dailyTargetValueEl.textContent = "Daily Target Reached ✅";
      dailyTargetNoteEl.textContent = "Target harian dah capai, tapi grow target takkan berubah selagi duit belum masuk tabung.";
      if (tabungUpdateUrl) {
        dailyTargetActionBtn.classList.remove("hidden");
      }
      dailyTargetReachedToday = true;
    } else {
      dailyTargetValueEl.textContent = "USD " + formatUsd(dailyTargetUsd) + " (" + formatPct(dailyTargetPct) + "%)";
      dailyTargetNoteEl.innerHTML = "Baki grow target tabung: USD " + formatUsd(growTarget) + ".<br>Daily P/L semasa: USD " + formatUsd(floatingProgressUsd) + ".";
    }
  }

  if (dailyTargetReachedToday) {
    dailyHitAlertEl.classList.remove("hidden");
  } else {
    dailyHitAlertEl.classList.add("hidden");
  }

  var introText = document.getElementById("introText");
  var modePrompt = document.getElementById("modePrompt");
  var amountPrompt = document.getElementById("amountPrompt");
  var finalPrompt = document.getElementById("finalPrompt");

  introText.textContent = content.tradingIntro || "";
  finalPrompt.textContent = (content.getTradingFinalPrompt || function () { return ""; })("");

  var stepMode = document.getElementById("stepMode");
  var stepAmount = document.getElementById("stepAmount");
  var stepReview = document.getElementById("stepReview");

  var lossBtn = document.getElementById("lossBtn");
  var profitBtn = document.getElementById("profitBtn");
  var dynamicFields = document.getElementById("dynamicFields");
  var amountInput = document.getElementById("tradeAmount");

  var impactCard = document.getElementById("impactCard");
  var impactMode = document.getElementById("impactMode");
  var impactAmount = document.getElementById("impactAmount");
  var impactWeekly = document.getElementById("impactWeekly");
  var impactBalance = document.getElementById("impactBalance");

  var form = document.getElementById("tradingForm");
  var submitBtn = document.getElementById("submitBtn");
  var statusEl = document.getElementById("formStatus");
  var topBackBtn = document.getElementById("topBackBtn");
  var backToAccountBtn = document.getElementById("backToAccountBtn");

  var selectedMode = "";

  function goBackAccountActivity() {
    var payload = { type: "account_activity_back_to_menu" };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Account Activity.";
  }

  topBackBtn.textContent = content.accountActivityBackBtn || "⬅️ Back to Account Activity";
  topBackBtn.addEventListener("click", goBackAccountActivity);

  backToAccountBtn.textContent = content.accountActivityBackBtn || "⬅️ Back to Account Activity";
  backToAccountBtn.addEventListener("click", function () {
    goBackAccountActivity();
  });

  function updateStepState(amount) {
    stepMode.classList.add("active");
    stepAmount.classList.toggle("active", Boolean(selectedMode));
    stepReview.classList.toggle("active", Boolean(selectedMode) && isValidAmount(amount));
  }

  function updatePreview() {
    var amount = getNumericInputValue(amountInput);
    var hasAmount = isValidAmount(amount);

    updateStepState(amount);
    submitBtn.disabled = !(selectedMode && hasAmount);

    if (!selectedMode || !hasAmount) {
      impactCard.classList.add("hidden");
      return;
    }

    var net = selectedMode === "profit" ? amount : -amount;
    var projectedWeekly = weeklyPerformance + net;
    var projectedBalance = currentBalance + net;

    impactMode.textContent = selectedMode === "profit" ? "PROFIT" : "LOSS";
    impactAmount.textContent = "USD " + amount.toFixed(2);
    impactWeekly.textContent = formatPnl(projectedWeekly);
    impactBalance.textContent = "USD " + projectedBalance.toFixed(2);

    setValueTone(impactAmount, net);
    setValueTone(impactWeekly, projectedWeekly);
    setValueTone(impactBalance, projectedBalance - currentBalance);

    impactCard.classList.remove("hidden");
  }

  function setMode(mode) {
    selectedMode = mode;

    lossBtn.classList.toggle("active", mode === "loss");
    profitBtn.classList.toggle("active", mode === "profit");

    dynamicFields.classList.remove("hidden");

    modePrompt.textContent = (content.getTradingModePrompt || function () { return ""; })(mode);
    amountPrompt.textContent = (content.getTradingAmountPrompt || function () { return ""; })(mode);
    finalPrompt.textContent = (content.getTradingFinalPrompt || function () { return ""; })(mode);

    statusEl.textContent = "";
    amountInput.focus();
    updatePreview();
  }

  lossBtn.addEventListener("click", function () {
    setMode("loss");
  });

  profitBtn.addEventListener("click", function () {
    setMode("profit");
  });

  amountInput.addEventListener("input", function () {
    updatePreview();
    statusEl.textContent = "";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var amount = getNumericInputValue(amountInput);

    if (!selectedMode) {
      statusEl.textContent = "Pilih loss atau profit dulu.";
      return;
    }

    if (!isValidAmount(amount)) {
      statusEl.textContent = "Isi jumlah yang valid dulu.";
      return;
    }

    var payload = {
      type: "trading_activity_update",
      mode: selectedMode,
      amount_usd: amount
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });

  updateStepState(NaN);
})();
