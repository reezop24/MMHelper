(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var statusEl = document.getElementById("formStatus");
  var submitBtn = document.getElementById("submitBtn");
  var disabledNote = document.getElementById("disabledNote");
  var addBtn = document.getElementById("addBtn");
  var subtractBtn = document.getElementById("subtractBtn");
  var amountInput = document.getElementById("adjustAmount");

  var mode = "add";
  var canAdjust = (params.get("can_adjust") || "0") === "1";
  var usedThisMonth = (params.get("used_this_month") || "0") === "1";
  var windowOpen = (params.get("window_open") || "0") === "1";
  var windowLabel = params.get("window_label") || "-";

  document.getElementById("summaryName").textContent = params.get("name") || "-";
  document.getElementById("summaryDate").textContent = params.get("saved_date") || "-";
  document.getElementById("summaryBalance").textContent = Number(params.get("current_balance") || 0).toFixed(2);
  document.getElementById("windowInfo").textContent = "Adjustment hanya dibenarkan pada 7 hari terakhir bulan.";

  var statusText = "Ready";
  if (!windowOpen) {
    statusText = "Window tutup";
  } else if (usedThisMonth) {
    statusText = "Dah guna bulan ini";
  }
  document.getElementById("summaryStatus").textContent = statusText;

  function setMode(nextMode) {
    mode = nextMode;
    addBtn.classList.toggle("active", mode === "add");
    subtractBtn.classList.toggle("active", mode === "subtract");
    statusEl.textContent = "";
  }

  addBtn.addEventListener("click", function () { setMode("add"); });
  subtractBtn.addEventListener("click", function () { setMode("subtract"); });

  function backToMMSetting() {
    var payload = { type: "mm_setting_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke MM Helper Setting.";
  }

  document.getElementById("topBackBtn").addEventListener("click", backToMMSetting);
  document.getElementById("backToMMBtn").addEventListener("click", backToMMSetting);

  if (!canAdjust) {
    submitBtn.disabled = true;
    addBtn.disabled = true;
    subtractBtn.disabled = true;
    amountInput.disabled = true;
    disabledNote.hidden = false;
    if (!windowOpen) {
      disabledNote.textContent = "Adjustment hanya dibenarkan pada 7 hari terakhir bulan (" + windowLabel + ").";
    } else if (usedThisMonth) {
      disabledNote.textContent = "Balance adjustment untuk bulan ini dah digunakan.";
    } else {
      disabledNote.textContent = "Balance adjustment tak dibenarkan sekarang.";
    }
  }

  document.getElementById("adjustmentForm").addEventListener("submit", function (event) {
    event.preventDefault();

    if (!canAdjust) {
      statusEl.textContent = "Adjustment tak dibenarkan sekarang.";
      return;
    }

    var amount = Number((amountInput.value || "").trim());
    if (Number.isNaN(amount) || amount <= 0) {
      statusEl.textContent = "Masukkan nilai adjustment yang valid.";
      return;
    }

    var payload = {
      type: "balance_adjustment",
      mode: mode,
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
