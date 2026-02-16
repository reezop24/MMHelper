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

  function updateGrowTargetHint(targetBalance, currentBalance, hintEl) {
    if (Number.isNaN(targetBalance) || targetBalance <= 0) {
      hintEl.textContent = (content.setNewGoalGrowTargetPrefix || "Grow Target kau adalah") + ": USD 0.00";
      return;
    }
    var growTarget = Math.max(targetBalance - currentBalance, 0);
    hintEl.textContent = (content.setNewGoalGrowTargetPrefix || "Grow Target kau adalah") + ": USD " + formatUsd(growTarget);
  }

  var name = params.get("name") || "-";
  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var capital = Number(params.get("capital_usd") || 0);
  var savedDate = params.get("saved_date") || "-";
  var tabungStartDate = params.get("tabung_start_date") || "-";
  var missionStatus = params.get("mission_status") || "-";
  var hasGoal = (params.get("has_goal") || "0") === "1";
  var currentTargetBalance = Number(params.get("target_balance_usd") || 0);
  var currentGrowTarget = Number(params.get("grow_target_usd") || 0);
  var currentTargetLabel = params.get("target_label") || "-";

  var minTarget = currentBalance + 100;

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryBalance").textContent = formatUsd(currentBalance);
  document.getElementById("summaryCapital").textContent = formatUsd(capital);
  document.getElementById("summaryDate").textContent = savedDate;
  document.getElementById("summaryTabungStartDate").textContent = tabungStartDate;
  document.getElementById("summaryMissionStatus").textContent = missionStatus;

  var form = document.getElementById("setGoalForm");
  var configuredLayer = document.getElementById("configuredLayer");

  var formStatusEl = document.getElementById("formStatus");
  var configuredStatusEl = document.getElementById("configuredStatus");

  var targetBalanceInput = document.getElementById("targetBalance");
  var targetSelect = document.getElementById("targetDays");
  var unlockAmountInput = document.getElementById("unlockAmount");
  var growTargetHint = document.getElementById("growTargetHint");

  var backToMenuBtn = document.getElementById("backToMenuBtn");
  var configuredBackBtn = document.getElementById("configuredBackBtn");
  var configuredResetBtn = document.getElementById("configuredResetBtn");

  document.getElementById("introText").textContent = content.setNewGoalIntro || "";
  document.getElementById("goalPrompt").textContent = content.setNewGoalPrompt || "";
  document.getElementById("balanceHint").textContent = (content.setNewGoalBalanceHintPrefix || "Baki semasa") + ": USD " + formatUsd(currentBalance);
  document.getElementById("minTargetHint").textContent = (content.setNewGoalMinTargetPrefix || "Minimum target") + ": USD " + formatUsd(minTarget);
  document.getElementById("targetPrompt").textContent = content.setNewGoalTargetPrompt || "";
  document.getElementById("unlockPrompt").textContent = content.setNewGoalUnlockPrompt || "";
  document.getElementById("finalPrompt").textContent = content.setNewGoalFinalPrompt || "";
  backToMenuBtn.textContent = content.setNewGoalBackToMenuBtn || "⬅️ Back to Project Grow";

  document.getElementById("configuredIntro").textContent = content.setNewGoalIntro || "";
  document.getElementById("configuredTitle").textContent = content.setNewGoalConfiguredTitle || "Target Capital dah diset ✅";
  document.getElementById("configuredTargetCapital").textContent = formatUsd(currentTargetBalance);
  document.getElementById("configuredGrowTarget").textContent = formatUsd(Math.max(currentGrowTarget, 0));
  document.getElementById("configuredTargetLabel").textContent = currentTargetLabel || "-";
  document.getElementById("resetInfoText").textContent = content.setNewGoalResetInfoText || "";
  configuredBackBtn.textContent = content.setNewGoalBackToMenuBtn || "⬅️ Back to Project Grow";
  configuredResetBtn.textContent = content.setNewGoalResetBtn || "Reset New Goal";

  function sendBackToProjectGrow() {
    var payload = { type: "project_grow_back_to_menu" };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    formStatusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Project Grow.";
    configuredStatusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Project Grow.";
  }

  function handleResetGoal(statusEl) {
    var confirmed = window.confirm(
      content.setNewGoalResetConfirmText || "Reset New Goal sekarang? Semua setting goal dan progress mission akan dipadam."
    );
    if (!confirmed) {
      statusEl.textContent = content.setNewGoalResetCancelledText || "Reset New Goal dibatalkan.";
      return;
    }

    var payload = {
      type: "project_grow_goal_reset",
      confirm_reset: 1
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = content.setNewGoalResetPreviewText || "Preview mode: reset hanya berfungsi bila buka dari Telegram.";
  }

  backToMenuBtn.addEventListener("click", sendBackToProjectGrow);
  configuredBackBtn.addEventListener("click", sendBackToProjectGrow);

  configuredResetBtn.addEventListener("click", function () {
    handleResetGoal(configuredStatusEl);
  });

  if (hasGoal) {
    configuredLayer.classList.remove("hidden");
    form.classList.add("hidden");
  } else {
    form.classList.remove("hidden");
    configuredLayer.classList.add("hidden");
  }

  updateGrowTargetHint(Number((targetBalanceInput.value || "").trim()), currentBalance, growTargetHint);
  targetBalanceInput.addEventListener("input", function () {
    var targetBalance = Number((targetBalanceInput.value || "").trim());
    updateGrowTargetHint(targetBalance, currentBalance, growTargetHint);
    formStatusEl.textContent = "";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var targetBalance = Number((targetBalanceInput.value || "").trim());
    var targetDays = (targetSelect.value || "").trim();
    var unlockAmount = Number((unlockAmountInput.value || "").trim());
    var targetLabel = "";

    if (Number.isNaN(targetBalance) || targetBalance <= 0) {
      formStatusEl.textContent = "Isi Target Capital yang valid dulu bro.";
      return;
    }

    if (targetBalance < minTarget) {
      formStatusEl.textContent = "Target minimum USD " + formatUsd(minTarget) + ".";
      return;
    }

    if (targetDays !== "30" && targetDays !== "90" && targetDays !== "180") {
      formStatusEl.textContent = "Pilih tempoh 30 hari, 3 bulan, atau 6 bulan.";
      return;
    }

    if (Number.isNaN(unlockAmount) || unlockAmount < 10) {
      formStatusEl.textContent = "Untuk unlock, nilai minimum ialah USD 10.";
      return;
    }

    if (targetDays === "30") {
      targetLabel = "30 hari";
    } else if (targetDays === "90") {
      targetLabel = "3 bulan";
    } else {
      targetLabel = "6 bulan";
    }

    var payload = {
      type: "set_new_goal",
      target_balance_usd: targetBalance,
      target_days: Number(targetDays),
      target_label: targetLabel,
      unlock_amount_usd: unlockAmount
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    formStatusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
