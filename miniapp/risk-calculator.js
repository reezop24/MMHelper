(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var form = document.getElementById("riskForm");
  var statusEl = document.getElementById("status");
  var backBtn = document.getElementById("topBackBtn");
  var riskUsdEl = document.getElementById("riskUsd");
  var lotSizeEl = document.getElementById("lotSize");
  var zoneUsdEl = document.getElementById("zoneUsd");
  var usedMarginEl = document.getElementById("usedMargin");
  var maxLossBeforeStopOutEl = document.getElementById("maxLossBeforeStopOut");
  var maxMoveBeforeStopOutEl = document.getElementById("maxMoveBeforeStopOut");
  var floatingFullEl = document.getElementById("floatingFull");
  var floatingHalfEl = document.getElementById("floatingHalf");

  function n(id) {
    return Number((document.getElementById(id).value || "").trim());
  }

  function f2(v) {
    return Number(v || 0).toFixed(2);
  }

  function f3(v) {
    return Number(v || 0).toFixed(3);
  }

  backBtn.addEventListener("click", function () {
    if (tg) {
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: back hanya aktif dalam Telegram.";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var balance = n("accountBalance");
    var riskPct = n("riskPercent");
    var zonePips = n("zonePips");
    var entryPrice = n("entryPrice");
    var leverage = n("leverage");
    var stopOutPct = n("stopOutPct");

    if (Number.isNaN(balance) || balance <= 0) {
      statusEl.textContent = "Modal semasa kena lebih dari 0.";
      return;
    }
    if (Number.isNaN(riskPct) || riskPct <= 0) {
      statusEl.textContent = "Risk % kena lebih dari 0.";
      return;
    }
    if (Number.isNaN(zonePips) || zonePips <= 0) {
      statusEl.textContent = "Saiz zon/SL (pips) kena lebih dari 0.";
      return;
    }
    if (Number.isNaN(entryPrice) || entryPrice <= 0) {
      statusEl.textContent = "Entry price XAUUSD kena lebih dari 0.";
      return;
    }
    if (Number.isNaN(leverage) || leverage <= 0) {
      statusEl.textContent = "Leverage tak sah.";
      return;
    }
    if (Number.isNaN(stopOutPct) || stopOutPct <= 0 || stopOutPct >= 100) {
      statusEl.textContent = "Stop-out % mesti antara 1 hingga 99.";
      return;
    }

    // XAUUSD assumptions: contract size=100, pip size=0.10 (1 lot ~= USD 10 per pip).
    var pipSize = 0.10;
    var zone = zonePips * pipSize;
    var riskUsd = balance * (riskPct / 100);
    var usdPerLotAtZone = zone * 100;
    var lot = usdPerLotAtZone > 0 ? riskUsd / usdPerLotAtZone : 0;

    // Margin model: used margin = (entry price * contract size * lot) / leverage.
    var contractSize = 100;
    var usedMargin = (entryPrice * contractSize * lot) / leverage;
    var stopOutEquity = usedMargin * (stopOutPct / 100);
    var maxLossBeforeStopOut = Math.max(balance - stopOutEquity, 0);
    var maxMoveBeforeStopOut = lot > 0 ? maxLossBeforeStopOut / (lot * contractSize) : 0;

    var floatingFull = lot * zone * 100;
    var floatingHalf = lot * (zone / 2) * 100;

    riskUsdEl.textContent = f2(riskUsd);
    lotSizeEl.textContent = f3(lot);
    zoneUsdEl.textContent = f2(zone);
    usedMarginEl.textContent = f2(usedMargin);
    maxLossBeforeStopOutEl.textContent = f2(maxLossBeforeStopOut);
    maxMoveBeforeStopOutEl.textContent = f2(maxMoveBeforeStopOut);
    floatingFullEl.textContent = f2(floatingFull);
    floatingHalfEl.textContent = f2(floatingHalf);

    if (floatingFull > maxLossBeforeStopOut && maxLossBeforeStopOut > 0) {
      statusEl.textContent = "Amaran: loss zon penuh melebihi kapasiti akaun sebelum stop-out. Kecilkan lot atau zon.";
      return;
    }
    statusEl.textContent = "Kiraan siap (per setup). Semak balik min lot/step lot dan stop-out broker.";
  });
})();
