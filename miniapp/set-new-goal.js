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

  var name = params.get("name") || "-";
  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var capital = Number(params.get("capital_usd") || 0);
  var savedDate = params.get("saved_date") || "-";
  var minTarget = currentBalance + 100;

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryBalance").textContent = formatUsd(currentBalance);
  document.getElementById("summaryCapital").textContent = formatUsd(capital);
  document.getElementById("summaryDate").textContent = savedDate;

  document.getElementById("introText").textContent = content.setNewGoalIntro || "";
  document.getElementById("goalPrompt").textContent = content.setNewGoalPrompt || "";
  document.getElementById("balanceHint").textContent = (content.setNewGoalBalanceHintPrefix || "Baki semasa") + ": USD " + formatUsd(currentBalance);
  document.getElementById("minTargetHint").textContent = (content.setNewGoalMinTargetPrefix || "Minimum target") + ": USD " + formatUsd(minTarget);
  document.getElementById("targetPrompt").textContent = content.setNewGoalTargetPrompt || "";
  document.getElementById("unlockPrompt").textContent = content.setNewGoalUnlockPrompt || "";
  document.getElementById("finalPrompt").textContent = content.setNewGoalFinalPrompt || "";

  var form = document.getElementById("setGoalForm");
  var statusEl = document.getElementById("formStatus");
  var targetBalanceInput = document.getElementById("targetBalance");
  var targetSelect = document.getElementById("targetDays");
  var unlockAmountInput = document.getElementById("unlockAmount");

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var targetBalance = Number((targetBalanceInput.value || "").trim());
    var targetDays = (targetSelect.value || "").trim();
    var unlockAmount = Number((unlockAmountInput.value || "").trim());
    var targetLabel = "";

    if (Number.isNaN(targetBalance) || targetBalance <= 0) {
      statusEl.textContent = "Isi target account yang valid dulu bro.";
      return;
    }

    if (targetBalance < minTarget) {
      statusEl.textContent = "Target kena minimum USD " + formatUsd(minTarget) + ".";
      return;
    }

    if (targetDays !== "30" && targetDays !== "90" && targetDays !== "180") {
      statusEl.textContent = "Pilih tempoh 30 hari, 3 bulan, atau 6 bulan.";
      return;
    }

    if (Number.isNaN(unlockAmount) || unlockAmount < 10) {
      statusEl.textContent = "Untuk unlock, nilai minimum ialah USD 10.";
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

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
