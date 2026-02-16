(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var content = window.MMHELPER_CONTENT || {};
  var params = new URLSearchParams(window.location.search);

  var name = params.get("name") || "-";
  var initialCapital = Number(params.get("initial_capital_usd") || 0);
  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var savedDate = params.get("saved_date") || "-";

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryCapital").textContent = initialCapital.toFixed(2);
  document.getElementById("summaryBalance").textContent = currentBalance.toFixed(2);
  document.getElementById("summaryDate").textContent = savedDate;

  var introText = document.getElementById("introText");
  var modePrompt = document.getElementById("modePrompt");
  var amountPrompt = document.getElementById("amountPrompt");
  var finalPrompt = document.getElementById("finalPrompt");

  introText.textContent = content.tradingIntro || "";
  finalPrompt.textContent = content.tradingFinalPrompt || "";

  var lossBtn = document.getElementById("lossBtn");
  var profitBtn = document.getElementById("profitBtn");
  var dynamicFields = document.getElementById("dynamicFields");
  var amountInput = document.getElementById("tradeAmount");
  var form = document.getElementById("tradingForm");
  var statusEl = document.getElementById("formStatus");

  var selectedMode = "";

  function setMode(mode) {
    selectedMode = mode;

    lossBtn.classList.toggle("active", mode === "loss");
    profitBtn.classList.toggle("active", mode === "profit");

    dynamicFields.classList.remove("hidden");

    modePrompt.textContent = (content.getTradingModePrompt || function () { return ""; })(mode);
    amountPrompt.textContent = (content.getTradingAmountPrompt || function () { return ""; })(mode);

    amountInput.focus();
    statusEl.textContent = "";
  }

  lossBtn.addEventListener("click", function () {
    setMode("loss");
  });

  profitBtn.addEventListener("click", function () {
    setMode("profit");
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var amount = Number((amountInput.value || "").trim());

    if (!selectedMode) {
      statusEl.textContent = "Pilih loss atau profit dulu.";
      return;
    }

    if (Number.isNaN(amount) || amount <= 0) {
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
})();
