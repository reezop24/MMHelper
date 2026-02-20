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
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var tabInputBtn = document.getElementById("tabInputBtn");
  var tabBalanceBtn = document.getElementById("tabBalanceBtn");
  var tabRecommendationBtn = document.getElementById("tabRecommendationBtn");
  var resultInputCard = document.getElementById("resultInputCard");
  var resultBalanceCard = document.getElementById("resultBalanceCard");
  var resultBalanceRecommendationCard = document.getElementById("resultBalanceRecommendationCard");
  var entryPriceInput = document.getElementById("entryPrice");
  var liveFeedStatusEl = document.getElementById("liveFeedStatus");
  var liveFeedPriceEl = document.getElementById("liveFeedPrice");
  var liveFeedSymbolEl = document.getElementById("liveFeedSymbol");
  var liveFeedTsEl = document.getElementById("liveFeedTs");
  var liveTickEndpoint = params.get("live_tick_url") || "live-tick.json";

  function n(id) {
    return Number((document.getElementById(id).value || "").trim());
  }

  function f2(v) {
    return Number(v || 0).toFixed(2);
  }

  function updateLiveFeedUi(payload) {
    var symbol = String(payload.symbol || "XAU/USD");
    var price = Number(payload.price);
    var ts = String(payload.ts || "");
    var dt = ts ? new Date(ts) : null;
    var hasValidTime = dt && !Number.isNaN(dt.getTime());
    var agoSec = hasValidTime ? Math.max(0, Math.round((Date.now() - dt.getTime()) / 1000)) : null;
    var isFresh = agoSec !== null && agoSec <= 90;

    liveFeedSymbolEl.textContent = symbol;
    liveFeedPriceEl.textContent = Number.isFinite(price) ? f2(price) : "--";
    if (Number.isFinite(price)) {
      entryPriceInput.value = f2(price);
    }
    liveFeedTsEl.textContent = hasValidTime ? dt.toLocaleString() : "--";
    liveFeedStatusEl.textContent = isFresh ? "🔴 LIVE" : "🟠 STALE";
    liveFeedStatusEl.style.color = isFresh ? "#ff6b6b" : "#ffd37a";
  }

  function setLiveFeedError(statusText) {
    liveFeedStatusEl.textContent = "⚫ " + statusText;
    liveFeedStatusEl.style.color = "#ff8f8f";
  }

  async function pollLiveFeed() {
    try {
      var response = await fetch(liveTickEndpoint + "?t=" + Date.now(), { cache: "no-store" });
      if (!response.ok) {
        throw new Error("http_" + response.status);
      }
      var payload = await response.json();
      if (!payload || typeof payload !== "object") {
        throw new Error("invalid_payload");
      }
      updateLiveFeedUi(payload);
    } catch (err) {
      setLiveFeedError("OFFLINE");
    }
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
    var showBalance = tabName === "balance";
    var showRecommendation = tabName === "recommendation";
    resultInputCard.classList.toggle("hidden", !showInput);
    resultBalanceCard.classList.toggle("hidden", !showBalance);
    resultBalanceRecommendationCard.classList.toggle("hidden", !showRecommendation);
    tabInputBtn.classList.toggle("active", showInput);
    tabBalanceBtn.classList.toggle("active", showBalance);
    tabRecommendationBtn.classList.toggle("active", showRecommendation);
  }

  function tradingDaysByTargetDays(targetDays) {
    if (targetDays === 30) return 22;
    if (targetDays === 90) return 66;
    if (targetDays === 180) return 132;
    return 0;
  }

  function updateLiveRecommendation(balance, riskPct) {
    var dailyTargetUsdEl = document.getElementById("dailyTargetUsdLive");
    var perSetupTargetUsdEl = document.getElementById("perSetupTargetUsdLive");
    var recommendedLotEl = document.getElementById("recommendedLotLive");
    var fixedTpPipsEl = document.getElementById("fixedTpPipsLive");
    var fixedSlPipsEl = document.getElementById("fixedSlPipsLive");
    var expectedTpUsdEl = document.getElementById("expectedTpUsdLive");
    var expectedSlUsdEl = document.getElementById("expectedSlUsdLive");
    var riskBudgetUsdEl = document.getElementById("riskBudgetUsdLive");
    var noteEl = document.getElementById("liveRecommendationNote");

    var tradingDays = tradingDaysByTargetDays(liveTargetDays);
    if (balance <= 0 || tradingDays <= 0 || liveGrowTargetUsd <= 0 || riskPct <= 0) {
      dailyTargetUsdEl.textContent = "0.00";
      perSetupTargetUsdEl.textContent = "0.00";
      recommendedLotEl.textContent = "0.00";
      fixedTpPipsEl.textContent = "40";
      fixedSlPipsEl.textContent = "40";
      expectedTpUsdEl.textContent = "0.00";
      expectedSlUsdEl.textContent = "0.00";
      riskBudgetUsdEl.textContent = "0.00";
      noteEl.textContent = "Recommendation perlukan goal aktif dan risk% yang sah.";
      return;
    }

    var pipValuePerLot = 10; // XAUUSD, 1.00 lot ~ USD10/pip
    var fixedTpPips = 40;
    var fixedSlPips = 40;
    var dailyTargetUsd = liveGrowTargetUsd / tradingDays;
    var perSetupTargetUsd = dailyTargetUsd / 2;
    var rawLot = perSetupTargetUsd / (fixedTpPips * pipValuePerLot);
    var recommendedLot = floorToStep(rawLot, 0.01);
    var expectedTpUsd = recommendedLot * fixedTpPips * pipValuePerLot;
    var expectedSlUsd = recommendedLot * fixedSlPips * pipValuePerLot;
    var riskBudgetUsd = balance * (riskPct / 100);

    dailyTargetUsdEl.textContent = f2(dailyTargetUsd);
    perSetupTargetUsdEl.textContent = f2(perSetupTargetUsd);
    recommendedLotEl.textContent = f2(recommendedLot);
    fixedTpPipsEl.textContent = String(fixedTpPips);
    fixedSlPipsEl.textContent = String(fixedSlPips);
    expectedTpUsdEl.textContent = f2(expectedTpUsd);
    expectedSlUsdEl.textContent = f2(expectedSlUsd);
    riskBudgetUsdEl.textContent = f2(riskBudgetUsd);

    if (recommendedLot <= 0) {
      noteEl.textContent = "Lot jadi 0.00 selepas step 0.01. Daily target terlalu kecil untuk setup TP/SL 40 pips.";
      return;
    }
    if (expectedSlUsd > riskBudgetUsd && riskBudgetUsd > 0) {
      noteEl.textContent = "Amaran: risiko SL40 melebihi risk USD dari tetapan risk% anda.";
      return;
    }
    noteEl.textContent = "Formula recommendation: lot dikira terus dari daily target (2 setup/hari) dengan TP40/SL40 tetap.";
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
      zonePriceMove: zone,
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
    document.getElementById("zonePriceMove" + suffix).textContent = f2(result.zonePriceMove);
    document.getElementById("usedMargin" + suffix).textContent = f2(result.usedMargin);
    document.getElementById("maxLossBeforeStopOut" + suffix).textContent = f2(result.maxLossBeforeStopOut);
    document.getElementById("maxMoveBeforeStopOut" + suffix).textContent = f2(result.maxMoveBeforeStopOut);
    document.getElementById("floatingFull" + suffix).textContent = f2(result.floatingFull);
    document.getElementById("floatingHalf" + suffix).textContent = f2(result.floatingHalf);
  }

  function backToMainMenu() {
    var payload = { type: "risk_calculator_back_to_menu" };
    if (tg) {
      try {
        tg.sendData(JSON.stringify(payload));
      } catch (err) {
        // no-op
      }
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Main Menu.";
  }

  backBtn.addEventListener("click", backToMainMenu);
  bottomBackBtn.addEventListener("click", backToMainMenu);

  tabInputBtn.addEventListener("click", function () {
    setTab("input");
  });

  tabBalanceBtn.addEventListener("click", function () {
    setTab("balance");
  });

  tabRecommendationBtn.addEventListener("click", function () {
    setTab("recommendation");
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
      updateLiveRecommendation(liveBalance, riskPct);
      if (inputResult.floatingFull > inputResult.maxLossBeforeStopOut && inputResult.maxLossBeforeStopOut > 0) {
        statusEl.textContent = "Amaran: loss zon penuh (tab input) melebihi kapasiti sebelum stop-out.";
        return;
      }
      statusEl.textContent = "Kiraan siap. Semak semua tab preview. Lot dibundarkan ke bawah ikut step 0.01.";
      return;
    }

    updateLiveRecommendation(0, riskPct);
    statusEl.textContent = "Kiraan tab input siap. Tab current balance perlukan data balance user aktif.";
  });

  pollLiveFeed();
  window.setInterval(pollLiveFeed, 3000);
})();
