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
  var selectedLayerLabelEl = document.getElementById("selectedLayerLabel");
  var lotPerSelectedLayerEl = document.getElementById("lotPerSelectedLayer");
  var lotPerTwoLayerEl = document.getElementById("lotPerTwoLayer");
  var lotPerThreeLayerEl = document.getElementById("lotPerThreeLayer");
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

  function floorToStep(value, step) {
    var n = Number(value || 0);
    if (!Number.isFinite(n) || n <= 0) return 0;
    var s = Number(step || 0);
    if (!Number.isFinite(s) || s <= 0) return 0;
    return Math.floor((n + 1e-12) / s) * s;
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
    var layerCount = n("layerCount");
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
    if (Number.isNaN(layerCount) || layerCount <= 0) {
      statusEl.textContent = "Layer tak sah.";
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
    if (Number.isNaN(stopOutPct) || stopOutPct < 0 || stopOutPct > 50) {
      statusEl.textContent = "Stop-out % mesti antara 0 hingga 50.";
      return;
    }

    // XAUUSD assumptions: contract size=100, pip size=0.10 (1 lot ~= USD 10 per pip).
    var pipSize = 0.10;
    var zone = zonePips * pipSize;
    var riskUsd = balance * (riskPct / 100);
    var usdPerLotAtZone = zone * 100;
    var rawLot = usdPerLotAtZone > 0 ? riskUsd / usdPerLotAtZone : 0;
    var lot = floorToStep(rawLot, 0.01);
    var lotPerSelectedLayer = floorToStep(lot / layerCount, 0.01);
    var lotPerTwoLayer = floorToStep(lot / 2, 0.01);
    var lotPerThreeLayer = floorToStep(lot / 3, 0.01);

    // Margin model: used margin = (entry price * contract size * lot) / leverage.
    var contractSize = 100;
    var usedMargin = (entryPrice * contractSize * lot) / leverage;
    var stopOutEquity = usedMargin * (stopOutPct / 100);
    var maxLossBeforeStopOut = Math.max(balance - stopOutEquity, 0);
    var maxMoveBeforeStopOut = lot > 0 ? maxLossBeforeStopOut / (lot * contractSize) : 0;

    var floatingFull = lot * zone * 100;
    var floatingHalf = lot * (zone / 2) * 100;

    riskUsdEl.textContent = f2(riskUsd);
    lotSizeEl.textContent = f2(lot);
    selectedLayerLabelEl.textContent = String(layerCount);
    lotPerSelectedLayerEl.textContent = f2(lotPerSelectedLayer);
    lotPerTwoLayerEl.textContent = f2(lotPerTwoLayer);
    lotPerThreeLayerEl.textContent = f2(lotPerThreeLayer);
    zoneUsdEl.textContent = f2(zone);
    usedMarginEl.textContent = f2(usedMargin);
    maxLossBeforeStopOutEl.textContent = f2(maxLossBeforeStopOut);
    maxMoveBeforeStopOutEl.textContent = f2(maxMoveBeforeStopOut);
    floatingFullEl.textContent = f2(floatingFull);
    floatingHalfEl.textContent = f2(floatingHalf);

    if (lot <= 0) {
      statusEl.textContent = "Lot terlalu kecil selepas pembundaran 0.01. Naikkan risk% atau kecilkan zon.";
      return;
    }

    if (floatingFull > maxLossBeforeStopOut && maxLossBeforeStopOut > 0) {
      statusEl.textContent = "Amaran: loss zon penuh melebihi kapasiti akaun sebelum stop-out. Kecilkan lot atau zon.";
      return;
    }
    statusEl.textContent = "Kiraan siap (per setup). Lot dibundarkan ke bawah ikut step 0.01.";
  });
})();
