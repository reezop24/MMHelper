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
  var currentProfit = Number(params.get("current_profit_usd") || 0);

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryCapital").textContent = initialCapital.toFixed(2);
  document.getElementById("summaryBalance").textContent = currentBalance.toFixed(2);
  document.getElementById("summaryDate").textContent = savedDate;

  var introText = document.getElementById("introText");
  var reasonPrompt = document.getElementById("reasonPrompt");
  var amountPrompt = document.getElementById("amountPrompt");
  var finalPrompt = document.getElementById("finalPrompt");

  var profitAbs = Math.abs(currentProfit).toFixed(2);
  var profitLabel = "(USD " + profitAbs + ")";

  if (currentProfit >= 0) {
    introText.textContent = (content.getDepositIntro || function () { return ""; })(profitLabel);
  } else {
    introText.textContent = (content.getDepositIntroLoss || function () { return ""; })(profitLabel);
  }

  reasonPrompt.textContent = content.depositReasonPrompt || "";
  amountPrompt.textContent = content.depositAmountPrompt || "";
  finalPrompt.textContent = content.depositFinalPrompt || "";

  var reasonSelect = document.getElementById("reasonSelect");
  (content.depositReasons || []).forEach(function (reason) {
    var opt = document.createElement("option");
    opt.value = reason;
    opt.textContent = reason;
    reasonSelect.appendChild(opt);
  });

  var form = document.getElementById("depositForm");
  var statusEl = document.getElementById("formStatus");

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var reason = (reasonSelect.value || "").trim();
    var amount = Number((document.getElementById("depositAmount").value || "").trim());

    if (!reason) {
      statusEl.textContent = "Pilih reason dulu.";
      return;
    }

    if (Number.isNaN(amount) || amount <= 0) {
      statusEl.textContent = "Isi jumlah deposit yang valid.";
      return;
    }

    var payload = {
      type: "deposit_activity",
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
