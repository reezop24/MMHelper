(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var statusEl = document.getElementById("formStatus");
  var form = document.getElementById("tabungForm");
  var amountInput = document.getElementById("amountInput");
  var amountField = document.getElementById("amountField");
  var goalOptionsWrap = document.getElementById("goalOptionsWrap");
  var panelTitle = document.getElementById("panelTitle");
  var panelDesc = document.getElementById("panelDesc");
  var modeNote = document.getElementById("modeNote");

  var modeSaveBtn = document.getElementById("modeSave");
  var modeEmergencyBtn = document.getElementById("modeEmergency");
  var modeGoalBtn = document.getElementById("modeGoal");

  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var tabungBalance = Number(params.get("tabung_balance_usd") || 0);
  var totalBalance = Number(params.get("total_balance_usd") || 0);
  var targetBalance = Number(params.get("target_balance_usd") || 0);
  var goalReached = (params.get("goal_reached") || "0") === "1";
  var emergencyLeft = Number(params.get("emergency_left") || 0);
  var setNewGoalUrl = params.get("set_new_goal_url") || "";

  var mode = "save";

  function formatUsd(value) {
    return Number(value || 0).toFixed(2);
  }

  function setSummary() {
    document.getElementById("summaryName").textContent = params.get("name") || "-";
    document.getElementById("summaryDate").textContent = params.get("saved_date") || "-";
    document.getElementById("summaryCurrentBalance").textContent = formatUsd(currentBalance);
    document.getElementById("summaryTabungBalance").textContent = formatUsd(tabungBalance);
    document.getElementById("summaryTotalBalance").textContent = formatUsd(totalBalance);
    document.getElementById("summaryGoalTarget").textContent = formatUsd(targetBalance);
  }

  function selectedGoalMode() {
    var picked = document.querySelector('input[name="goal_mode"]:checked');
    return picked ? picked.value : "goal_to_current";
  }

  function syncGoalAmountField() {
    if (mode !== "goal") {
      amountField.classList.remove("hide");
      amountInput.required = true;
      amountInput.disabled = false;
      return;
    }
    if (selectedGoalMode() === "goal_keep_and_new_goal") {
      amountField.classList.add("hide");
      amountInput.required = false;
      amountInput.disabled = true;
      amountInput.value = "";
      return;
    }
    amountField.classList.remove("hide");
    amountInput.required = true;
    amountInput.disabled = false;
  }

  function setActiveMode(nextMode) {
    mode = nextMode;
    modeSaveBtn.classList.toggle("active", mode === "save");
    modeEmergencyBtn.classList.toggle("active", mode === "emergency");
    modeGoalBtn.classList.toggle("active", mode === "goal");

    goalOptionsWrap.classList.toggle("hide", mode !== "goal");
    amountInput.value = "";
    statusEl.textContent = "";

    if (mode === "save") {
      panelTitle.textContent = "Simpan ke Tabung";
      panelDesc.textContent = "Masukkan jumlah yang nak disimpan. Duit ni akan ditolak terus dari Current Balance kau.";
      modeNote.textContent = "Simpan: transfer dalaman dari Current Balance ke Tabung.";
      amountInput.placeholder = "Contoh: 50";
      syncGoalAmountField();
      return;
    }

    if (mode === "emergency") {
      panelTitle.textContent = "Withdrawal Kecemasan";
      panelDesc.textContent = "Untuk kecemasan je. Withdrawal ni keluar terus dari tabung dan keluar dari ledger bot.";
      modeNote.textContent = "Limit emergency withdrawal: 2 kali setiap bulan. Baki bulan ni: " + emergencyLeft + " kali.";
      amountInput.placeholder = "Contoh: 30";
      syncGoalAmountField();
      return;
    }

    panelTitle.textContent = "Withdrawal Bila Goal Dah Capai";
    panelDesc.textContent = "Mode ni aktif bila Total Balance capai target Project Grow. Pilih cara pengeluaran ikut keperluan kau.";
    modeNote.textContent = goalReached
      ? "Goal dah capai. Kau boleh guna mode withdrawal goal."
      : "Mode ni masih lock sampai goal capai.";
    amountInput.placeholder = "Contoh: 100";
    syncGoalAmountField();
  }

  function sendPayload(payload) {
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  }

  function backToAccountActivity() {
    sendPayload({ type: "account_activity_back_to_menu" });
  }

  modeGoalBtn.disabled = !goalReached;

  modeSaveBtn.addEventListener("click", function () {
    setActiveMode("save");
  });

  modeEmergencyBtn.addEventListener("click", function () {
    setActiveMode("emergency");
  });

  modeGoalBtn.addEventListener("click", function () {
    if (!goalReached) {
      statusEl.textContent = "Mode withdrawal goal belum aktif. Selesaikan target dulu.";
      return;
    }
    setActiveMode("goal");
  });

  document.querySelectorAll('input[name="goal_mode"]').forEach(function (el) {
    el.addEventListener("change", syncGoalAmountField);
  });

  document.getElementById("topBackBtn").addEventListener("click", backToAccountActivity);
  document.getElementById("backToAccountBtn").addEventListener("click", backToAccountActivity);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    statusEl.textContent = "";

    if (mode === "save") {
      var saveAmount = Number((amountInput.value || "").trim());
      if (!isFinite(saveAmount) || saveAmount <= 0) {
        statusEl.textContent = "Isi jumlah yang valid dulu.";
        return;
      }
      sendPayload({ type: "tabung_update_action", action: "save", amount_usd: saveAmount });
      return;
    }

    if (mode === "emergency") {
      var emergencyAmount = Number((amountInput.value || "").trim());
      if (!isFinite(emergencyAmount) || emergencyAmount <= 0) {
        statusEl.textContent = "Isi jumlah yang valid dulu.";
        return;
      }
      if (emergencyLeft <= 0) {
        statusEl.textContent = "Limit emergency withdrawal bulan ni dah habis.";
        return;
      }
      sendPayload({ type: "tabung_update_action", action: "emergency_withdrawal", amount_usd: emergencyAmount });
      return;
    }

    var choice = selectedGoalMode();
    if (choice === "goal_keep_and_new_goal") {
      if (!setNewGoalUrl) {
        statusEl.textContent = "Link Set New Goal tak tersedia.";
        return;
      }
      window.location.href = setNewGoalUrl;
      return;
    }

    var goalAmount = Number((amountInput.value || "").trim());
    if (!isFinite(goalAmount) || goalAmount <= 0) {
      statusEl.textContent = "Isi jumlah yang valid dulu.";
      return;
    }
    sendPayload({ type: "tabung_update_action", action: choice, amount_usd: goalAmount });
  });

  setSummary();
  setActiveMode("save");
})();
