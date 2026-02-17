(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var liveBalance = Number(params.get("current_balance_usd") || 0);
  var liveTargetDays = Number(params.get("target_days") || 0);
  var liveGrowTargetUsd = Number(params.get("grow_target_usd") || 0);

  var form = document.getElementById("riskForm");
  var statusEl = document.getElementById("status");
  var backBtn = document.getElementById("topBackBtn");
  var tabInputBtn = document.getElementById("tabInputBtn");
  var tabBalanceBtn = document.getElementById("tabBalanceBtn");
  var resultInputCard = document.getElementById("resultInputCard");
  var resultBalanceCard = document.getElementById("resultBalanceCard");
  var resultBalanceRecommendationCard = document.getElementById("resultBalanceRecommendationCard");

  function n(id) {
    return Number((document.getElementById(id).value || "").trim());
  }

  function f2(v) {
    return Number(v || 0).toFixed(2);
  }

  function floorToStep(value, step) {
    var base = Number(value || 0);
    if (!Number.isFinite(base) || base <= 0) return 0;
    var s = Number(step || 0);
    if (!Number.isFinite(s) || s <= 0) return 0;
    return Math.floor((base + 1e-12) / s) * s;
  }

  function setTab(tabName) {
    var showInput = tabName === "input";
    resultInputCard.classList.toggle("hidden", !showInput);
    resultBalanceCard.classList.toggle("hidden", showInput);
    resultBalanceRecommendationCard.classList.toggle("hidden", showInput);
    tabInputBtn.classList.toggle("active", showInput);
    tabBalanceBtn.classList.toggle("active", !showInput);
  }

  function tradingDaysByTargetDays(targetDays) {
    if (targetDays === 30) return 22;
    if (targetDays === 90) return 66;
    if (targetDays === 180) return 132;
    return 0;
  }

  function updateLiveRecommendation(balance, zonePips) {
    var dailyTargetUsdEl = document.getElementById("dailyTargetUsdLive");
    var dailyRiskPctEl = document.getElementById("dailyRiskPctLive");
    var dailyRiskUsdEl = document.getElementById("dailyRiskUsdLive");
    var perSetupRiskPctEl = document.getElementById("perSetupRiskPctLive");
    var perSetupRiskUsdEl = document.getElementById("perSetupRiskUsdLive");
    var recommendedLotDailyEl = document.getElementById("recommendedLotDailyLive");
    var recommendedLotPerSetupEl = document.getElementById("recommendedLotPerSetupLive");
    var noteEl = document.getElementById("liveRecommendationNote");

    var tradingDays = tradingDaysByTargetDays(liveTargetDays);
    if (balance <= 0 || tradingDays <= 0 || liveGrowTargetUsd <= 0 || zonePips <= 0) {
      dailyTargetUsdEl.textContent = "0.00";
      dailyRiskPctEl.textContent = "0.00";
      dailyRiskUsdEl.textContent = "0.00";
      perSetupRiskPctEl.textContent = "0.00";
      perSetupRiskUsdEl.textContent = "0.00";
      recommendedLotDailyEl.textContent = "0.00";
      recommendedLotPerSetupEl.textContent = "0.00";
      noteEl.textContent = "Recommendation perlukan data goal aktif (30/90/180 hari).";
      return;
    }

    var pipSize = 0.10;
    var contractSize = 100;
    var zoneUsd = zonePips * pipSize;
    var dailyTargetUsd = liveGrowTargetUsd / tradingDays;
    var dailyRiskUsd = dailyTargetUsd;
    var dailyRiskPct = (dailyRiskUsd / balance) * 100;
    var perSetupRiskUsd = dailyRiskUsd / 2;
    var perSetupRiskPct = dailyRiskPct / 2;
    var usdPerLotAtZone = zoneUsd * contractSize;
    var recommendedLotDaily = usdPerLotAtZone > 0 ? floorToStep(dailyTargetUsd / usdPerLotAtZone, 0.01) : 0;
    var recommendedLotPerSetup = floorToStep(recommendedLotDaily / 2, 0.01);

    dailyTargetUsdEl.textContent = f2(dailyTargetUsd);
    dailyRiskPctEl.textContent = f2(dailyRiskPct);
    dailyRiskUsdEl.textContent = f2(dailyRiskUsd);
    perSetupRiskPctEl.textContent = f2(perSetupRiskPct);
    perSetupRiskUsdEl.textContent = f2(perSetupRiskUsd);
    recommendedLotDailyEl.textContent = f2(recommendedLotDaily);
    recommendedLotPerSetupEl.textContent = f2(recommendedLotPerSetup);
    noteEl.textContent = "Cadangan ini berpandukan baki grow target semasa dan andaian 2 setup sehari.";
  }

  function calculate(balance, riskPct, zonePips, layerCount, entryPrice, leverage, stopOutPct) {
    var pipSize = 0.10;
    var contractSize = 100;
    var zone = zonePips * pipSize;
    var riskUsd = balance * (riskPct / 100);
    var usdPerLotAtZone = zone * contractSize;
    var rawLot = usdPerLotAtZone > 0 ? riskUsd / usdPerLotAtZone : 0;
    var lot = floorToStep(rawLot, 0.01);
    var lotPerSelectedLayer = floorToStep(lot / layerCount, 0.01);
    var lotPerTwoLayer = floorToStep(lot / 2, 0.01);
    var lotPerThreeLayer = floorToStep(lot / 3, 0.01);

    var usedMargin = (entryPrice * contractSize * lot) / leverage;
    var stopOutEquity = usedMargin * (stopOutPct / 100);
    var maxLossBeforeStopOut = Math.max(balance - stopOutEquity, 0);
    var maxMoveBeforeStopOut = lot > 0 ? maxLossBeforeStopOut / (lot * contractSize) : 0;
    var floatingFull = lot * zone * contractSize;
    var floatingHalf = lot * (zone / 2) * contractSize;

    return {
      lot: lot,
      riskUsd: riskUsd,
      lotPerSelectedLayer: lotPerSelectedLayer,
      lotPerTwoLayer: lotPerTwoLayer,
      lotPerThreeLayer: lotPerThreeLayer,
      zoneUsd: zone,
      usedMargin: usedMargin,
      maxLossBeforeStopOut: maxLossBeforeStopOut,
      maxMoveBeforeStopOut: maxMoveBeforeStopOut,
      floatingFull: floatingFull,
      floatingHalf: floatingHalf,
    };
  }

  function render(result, suffix, layerCount, balanceValue) {
    if (suffix === "Live") {
      document.getElementById("liveBalance").textContent = f2(balanceValue);
    }
    document.getElementById("riskUsd" + suffix).textContent = f2(result.riskUsd);
    document.getElementById("lotSize" + suffix).textContent = f2(result.lot);
    document.getElementById("selectedLayerLabel" + suffix).textContent = String(layerCount);
    document.getElementById("lotPerSelectedLayer" + suffix).textContent = f2(result.lotPerSelectedLayer);
    document.getElementById("lotPerTwoLayer" + suffix).textContent = f2(result.lotPerTwoLayer);
    document.getElementById("lotPerThreeLayer" + suffix).textContent = f2(result.lotPerThreeLayer);
    document.getElementById("zoneUsd" + suffix).textContent = f2(result.zoneUsd);
    document.getElementById("usedMargin" + suffix).textContent = f2(result.usedMargin);
    document.getElementById("maxLossBeforeStopOut" + suffix).textContent = f2(result.maxLossBeforeStopOut);
    document.getElementById("maxMoveBeforeStopOut" + suffix).textContent = f2(result.maxMoveBeforeStopOut);
    document.getElementById("floatingFull" + suffix).textContent = f2(result.floatingFull);
    document.getElementById("floatingHalf" + suffix).textContent = f2(result.floatingHalf);
  }

  backBtn.addEventListener("click", function () {
    if (tg) {
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: back hanya aktif dalam Telegram.";
  });

  tabInputBtn.addEventListener("click", function () {
    setTab("input");
  });

  tabBalanceBtn.addEventListener("click", function () {
    setTab("balance");
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
    if (Number.isNaN(layerCount) || layerCount <= 0 || layerCount > 10) {
      statusEl.textContent = "Layer tak sah. Pilih 1 hingga 10.";
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

    var inputResult = calculate(balance, riskPct, zonePips, layerCount, entryPrice, leverage, stopOutPct);
    render(inputResult, "", layerCount, balance);

    if (inputResult.lot <= 0) {
      statusEl.textContent = "Lot terlalu kecil selepas pembundaran 0.01. Naikkan risk% atau kecilkan zon.";
      return;
    }

    if (Number.isFinite(liveBalance) && liveBalance > 0) {
      var liveResult = calculate(liveBalance, riskPct, zonePips, layerCount, entryPrice, leverage, stopOutPct);
      render(liveResult, "Live", layerCount, liveBalance);
      updateLiveRecommendation(liveBalance, zonePips);
      if (inputResult.floatingFull > inputResult.maxLossBeforeStopOut && inputResult.maxLossBeforeStopOut > 0) {
        statusEl.textContent = "Amaran: loss zon penuh (tab input) melebihi kapasiti sebelum stop-out.";
        return;
      }
      statusEl.textContent = "Kiraan siap untuk dua tab. Lot dibundarkan ke bawah ikut step 0.01.";
      return;
    }

    updateLiveRecommendation(0, zonePips);
    statusEl.textContent = "Kiraan tab input siap. Tab current balance perlukan data balance user aktif.";
  });
})();
