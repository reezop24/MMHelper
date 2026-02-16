(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var name = params.get("name") || "-";
  var savedDate = params.get("saved_date") || "-";
  var currentBalance = Number(params.get("current_balance_usd") || 0);

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryDate").textContent = savedDate;
  document.getElementById("summaryBalance").textContent = currentBalance.toFixed(2);

  var introText = document.getElementById("introText");
  introText.textContent = "Risk calculator ni bantu kau dapatkan jawapan berapa lot size kau boleh buka dengan modal tertentu dan risk size tertentu , contoh current balance kau sekarang ada USD " + currentBalance.toFixed(2) + " berapa lot kau boleh buka ikut risk yang kau tetapkan.. ko isi je semua box tu";

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

  var lineCurrentPriceLabel = document.getElementById("lineCurrentPriceLabel");
  var lineLeverageLabel = document.getElementById("lineLeverageLabel");
  var lineMargin = document.getElementById("lineMargin");
  var lineRiskXModal = document.getElementById("lineRiskXModal");
  var lineModalA = document.getElementById("lineModalA");
  var lineMargin2 = document.getElementById("lineMargin2");
  var lineLotA = document.getElementById("lineLotA");
  var lineLotB = document.getElementById("lineLotB");
  var lineZonePips = document.getElementById("lineZonePips");
  var lineZoneDivLotB = document.getElementById("lineZoneDivLotB");
  var lineModalAFinal = document.getElementById("lineModalAFinal");
  var lineLotC = document.getElementById("lineLotC");

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
        lotA: 0,
        lotB: 0,
        lotC: 0
      };
    }

    var marginPer001 = price / leverage;
    var riskAmountUsd = balance * (riskPct / 100);
    var lotA = marginPer001 > 0 ? riskAmountUsd / marginPer001 : 0;
    var lotB = lotA * 100;
    var lotC = lotB > 0 ? zonePips / lotB : 0;

    return {
      valid: true,
      balance: balance,
      riskPct: riskPct,
      zonePips: zonePips,
      leverage: leverage,
      price: price,
      marginPer001: marginPer001,
      riskAmountUsd: riskAmountUsd,
      lotA: lotA,
      lotB: lotB,
      lotC: lotC
    };
  }

  function render() {
    var calc = getCalc();
    lineCurrentPriceLabel.textContent = Number.isFinite(calc.price) ? "$" + calc.price.toFixed(2) : "current price";
    lineLeverageLabel.textContent = Number.isFinite(calc.leverage) ? String(Math.round(calc.leverage)) : "leverage";
    lineMargin.textContent = calc.marginPer001.toFixed(4);
    lineRiskXModal.textContent = Number.isFinite(calc.riskPct) && Number.isFinite(calc.balance)
      ? calc.riskPct.toFixed(2) + "% x USD " + calc.balance.toFixed(2) + " = USD " + calc.riskAmountUsd.toFixed(2)
      : "RIsk X modal = Modal A";
    lineModalA.textContent = calc.riskAmountUsd.toFixed(2);
    lineMargin2.textContent = calc.marginPer001.toFixed(4);
    lineLotA.textContent = "USD " + calc.riskAmountUsd.toFixed(2) + " ÷ " + calc.marginPer001.toFixed(4) + " = " + calc.lotA.toFixed(2);
    lineLotB.textContent = calc.lotA.toFixed(2) + " x 100 = " + calc.lotB.toFixed(2);
    lineZonePips.textContent = Number.isFinite(calc.zonePips) ? calc.zonePips.toFixed(1) : "zon yang user pilih";
    lineZoneDivLotB.textContent = Number.isFinite(calc.zonePips)
      ? calc.zonePips.toFixed(1) + " ÷ " + calc.lotB.toFixed(2) + " = " + calc.lotC.toFixed(4)
      : "zon yang user pilih ÷ Lot B = lot C";
    lineModalAFinal.textContent = "USD " + calc.riskAmountUsd.toFixed(2);
    lineLotC.textContent = calc.lotC.toFixed(4);

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
      lot_a: calc.lotA,
      lot_b: calc.lotB,
      lot_c: calc.lotC
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
