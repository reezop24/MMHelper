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

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryBalance").textContent = formatUsd(currentBalance);
  document.getElementById("summaryCapital").textContent = formatUsd(capital);
  document.getElementById("summaryDate").textContent = savedDate;

  document.getElementById("introText").textContent = content.setNewGoalIntro || "";
  document.getElementById("goalPrompt").textContent = content.setNewGoalPrompt || "";
  document.getElementById("targetPrompt").textContent = content.setNewGoalTargetPrompt || "";
  document.getElementById("finalPrompt").textContent = content.setNewGoalFinalPrompt || "";

  var form = document.getElementById("setGoalForm");
  var statusEl = document.getElementById("formStatus");
  var goalInput = document.getElementById("newGoal");
  var targetSelect = document.getElementById("targetDays");

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var newGoal = (goalInput.value || "").trim();
    var targetDays = (targetSelect.value || "").trim();
    var targetLabel = "";

    if (!newGoal) {
      statusEl.textContent = "Isi sasaran dulu bro.";
      return;
    }

    if (newGoal.length < 8) {
      statusEl.textContent = "Bagi sasaran yang lebih jelas sikit (min 8 aksara).";
      return;
    }

    if (targetDays !== "14" && targetDays !== "30") {
      statusEl.textContent = "Pilih tempoh 14 hari atau 30 hari.";
      return;
    }

    targetLabel = targetDays + " hari";

    var payload = {
      type: "set_new_goal",
      new_goal: newGoal,
      target_days: Number(targetDays),
      target_label: targetLabel
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
