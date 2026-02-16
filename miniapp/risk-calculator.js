(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var CONTRACT_SIZE = 100;
  var PIP_SIZE = 0.01;

  var params = new URLSearchParams(window.location.search);
  var name = params.get("name") || "-";
  var savedDate = params.get("saved_date") || "-";
  var currentBalance = Number(params.get("current_balance_usd") || 0);

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryDate").textContent = savedDate;
  document.getElementById("summaryBalance").textContent = currentBalance.toFixed(2);

  var introText = document.getElementById("introText");
  introText.textContent = "Risk calculator ni bantu kau dapatkan jawapan berapa lot size kau boleh buka dengan modal tertentu dan risk size tertentu, contoh current balance kau sekarang ada USD " + currentBalance.toFixed(2) + " berapa lot kau boleh buka ikut risk yang kau tetapkan.. ko isi je semua box tu";

  var topBackBtn = document.getElementById("topBackBtn");
  var backBtn = document.getElementById("backToMainBtn");
  var statusEl = document.getElementById("formStatus");
  var form = document.getElementById("riskForm");
  var submitBtn = document.getElementById("submitBtn");

  var balanceInput = document.getElementById("balanceInput");
  var riskPctInput = document.getElementById("riskPctInput");
  var zonePipsInput = document.getElementById("zonePipsInput");
  var leverageInput = document.getElementById("leverageInput");
  var priceInput = document.getElementById("priceInput");

  var lineLeverage = document.getElementById("lineLeverage");
  var linePrice = document.getElementById("linePrice");
  var lineMargin = document.getElementById("lineMargin");
  var lineModal = document.getElementById("lineModal");
  var lineRisk = document.getElementById("lineRisk");
  var lineModal2 = document.getElementById("lineModal2");
  var lineRisk2 = document.getElementById("lineRisk2");
  var lineModalA = document.getElementById("lineModalA");
  var lineModalA2 = document.getElementById("lineModalA2");
  var lineMargin2 = document.getElementById("lineMargin2");
  var lineLotUnits = document.getElementById("lineLotUnits");
  var lineLotFinal = document.getElementById("lineLotFinal");
  var linePips = document.getElementById("linePips");
  var lineLoss = document.getElementById("lineLoss");

  function toNum(value) {
    var num = Number((value || "").trim());
    return Number.isFinite(num) ? num : NaN;
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
    var riskPct = toNum(riskPctInput.value);
    var zonePips = toNum(zonePipsInput.value);
    var leverage = toNum(leverageInput.value);
    var price = toNum(priceInput.value);

    var valid = balance > 0 && riskPct > 0 && zonePips > 0 && leverage > 0 && price > 0;
    if (!valid) {
      return {
        valid: false,
        balance: balance,
        riskPct: riskPct,
        zonePips: zonePips,
        leverage: leverage,
        price: price,
        marginPer001: 0,
        riskAmountUsd: 0,
        lotUnits001: 0,
        lotFinal: 0,
        lossIfSlUsd: 0
      };
    }

    var marginPer001 = price / leverage;
    var riskAmountUsd = balance * (riskPct / 100);
    var lotUnits001 = marginPer001 > 0 ? riskAmountUsd / marginPer001 : 0;
    var lotFinal = lotUnits001 * 0.01;
    var lossIfSlUsd = CONTRACT_SIZE * lotFinal * (zonePips * PIP_SIZE);

    return {
      valid: true,
      balance: balance,
      riskPct: riskPct,
      zonePips: zonePips,
      leverage: leverage,
      price: price,
      marginPer001: marginPer001,
      riskAmountUsd: riskAmountUsd,
      lotUnits001: lotUnits001,
      lotFinal: lotFinal,
      lossIfSlUsd: lossIfSlUsd
    };
  }

  function render() {
    var calc = getCalc();
    lineLeverage.textContent = Number.isFinite(calc.leverage) ? String(Math.round(calc.leverage)) : "0";
    linePrice.textContent = Number.isFinite(calc.price) ? calc.price.toFixed(2) : "0.00";
    lineMargin.textContent = calc.marginPer001.toFixed(4);

    lineModal.textContent = Number.isFinite(calc.balance) ? calc.balance.toFixed(2) : "0.00";
    lineRisk.textContent = Number.isFinite(calc.riskPct) ? calc.riskPct.toFixed(2) : "0.00";

    lineModal2.textContent = lineModal.textContent;
    lineRisk2.textContent = lineRisk.textContent;
    lineModalA.textContent = calc.riskAmountUsd.toFixed(2);
    lineModalA2.textContent = calc.riskAmountUsd.toFixed(2);

    lineMargin2.textContent = calc.marginPer001.toFixed(4);
    lineLotUnits.textContent = calc.lotUnits001.toFixed(2);
    lineLotFinal.textContent = calc.lotFinal.toFixed(2);

    linePips.textContent = Number.isFinite(calc.zonePips) ? calc.zonePips.toFixed(1) : "0.0";
    lineLoss.textContent = calc.lossIfSlUsd.toFixed(2);

    submitBtn.disabled = !calc.valid;
  }

  [balanceInput, riskPctInput, zonePipsInput, leverageInput, priceInput].forEach(function (el) {
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
      risk_pct: calc.riskPct,
      zone_pips: calc.zonePips,
      leverage: calc.leverage,
      gold_price: calc.price,
      margin_per_001: calc.marginPer001,
      modal_a_usd: calc.riskAmountUsd,
      lot_units_001: calc.lotUnits001,
      lot_size: calc.lotFinal,
      loss_if_sl_usd: calc.lossIfSlUsd
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });

  if (currentBalance > 0) {
    balanceInput.value = currentBalance.toFixed(2);
  }

  render();
})();
