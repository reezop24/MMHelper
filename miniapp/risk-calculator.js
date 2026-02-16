(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var CONTRACT_SIZE = 100; // XAUUSD standard contract
  var PIP_SIZE = 0.01; // Gold pip size

  var params = new URLSearchParams(window.location.search);
  var name = params.get("name") || "-";
  var savedDate = params.get("saved_date") || "-";

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryDate").textContent = savedDate;

  var topBackBtn = document.getElementById("topBackBtn");
  var backBtn = document.getElementById("backToMainBtn");
  var statusEl = document.getElementById("formStatus");
  var form = document.getElementById("riskForm");
  var submitBtn = document.getElementById("submitBtn");

  var balanceInput = document.getElementById("balanceInput");
  var leverageInput = document.getElementById("leverageInput");
  var priceInput = document.getElementById("priceInput");
  var slPipsInput = document.getElementById("slPipsInput");

  var maxLotEl = document.getElementById("maxLotValue");
  var marginUsedEl = document.getElementById("marginUsedValue");
  var priceMoveEl = document.getElementById("priceMoveValue");
  var lossIfSlEl = document.getElementById("lossIfSlValue");

  function toNum(value) {
    var num = Number((value || "").trim());
    return Number.isFinite(num) ? num : NaN;
  }

  function formatUsd(value) {
    return "USD " + Number(value || 0).toFixed(2);
  }

  function goBackMain() {
    var payload = { type: "risk_calculator_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Main Menu.";
  }

  function getCalc() {
    var balance = toNum(balanceInput.value);
    var leverage = toNum(leverageInput.value);
    var price = toNum(priceInput.value);
    var slPips = toNum(slPipsInput.value);

    var valid = balance > 0 && leverage > 0 && price > 0 && slPips > 0;
    if (!valid) {
      return {
        valid: false,
        balance: balance,
        leverage: leverage,
        price: price,
        slPips: slPips,
        maxLotMargin: 0,
        marginUsedUsd: 0,
        priceMoveUsd: 0,
        lossIfSlUsd: 0
      };
    }

    var maxLotMargin = (balance * leverage) / (CONTRACT_SIZE * price);
    var marginUsedUsd = (CONTRACT_SIZE * maxLotMargin * price) / leverage;
    var priceMoveUsd = slPips * PIP_SIZE;
    var lossIfSlUsd = CONTRACT_SIZE * maxLotMargin * priceMoveUsd;

    return {
      valid: true,
      balance: balance,
      leverage: leverage,
      price: price,
      slPips: slPips,
      maxLotMargin: maxLotMargin,
      marginUsedUsd: marginUsedUsd,
      priceMoveUsd: priceMoveUsd,
      lossIfSlUsd: lossIfSlUsd
    };
  }

  function render() {
    var calc = getCalc();
    maxLotEl.textContent = calc.maxLotMargin.toFixed(2) + " lot";
    marginUsedEl.textContent = formatUsd(calc.marginUsedUsd);
    priceMoveEl.textContent = formatUsd(calc.priceMoveUsd);
    lossIfSlEl.textContent = formatUsd(calc.lossIfSlUsd);
    submitBtn.disabled = !calc.valid;
  }

  [balanceInput, leverageInput, priceInput, slPipsInput].forEach(function (el) {
    el.addEventListener("input", function () {
      statusEl.textContent = "";
      render();
    });
  });

  topBackBtn.textContent = "⬅️ Back to Main Menu";
  backBtn.textContent = "⬅️ Back to Main Menu";
  topBackBtn.addEventListener("click", goBackMain);
  backBtn.addEventListener("click", goBackMain);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var calc = getCalc();

    if (!calc.valid) {
      statusEl.textContent = "Isi semua input dengan nilai valid dulu.";
      return;
    }

    var payload = {
      type: "risk_calculator_submit",
      balance_usd: calc.balance,
      leverage: calc.leverage,
      gold_price: calc.price,
      stop_loss_pips: calc.slPips,
      max_lot_margin: calc.maxLotMargin,
      margin_used_usd: calc.marginUsedUsd,
      loss_if_sl_usd: calc.lossIfSlUsd,
      price_move_usd: calc.priceMoveUsd
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });

  render();
})();
