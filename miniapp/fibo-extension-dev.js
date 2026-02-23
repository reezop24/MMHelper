(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var liveTickUrl = params.get("live_tick_url") || "/api/live-tick";
  var previewUrl = params.get("preview_url") || "/api/dbo-preview";
  var devMode = params.get("dev") === "1";
  var isNextMember = params.get("next_member") === "1";
  var serverProfilesStateRaw = params.get("profiles_state") || "";
  var devPreviewBase = params.get("dev_preview_base") || "./fibo-dev-preview";
  var devTickUrl = params.get("dev_tick_url") || "./fibo-dev-live-tick.json";
  var dataSource = "api";

  var trendEl = document.getElementById("trend");
  var tfEl = document.getElementById("tf");
  var profileTabsEl = document.getElementById("profileTabs");
  var profileResetBtn = document.getElementById("profileResetBtn");
  var profileSaveBtn = document.getElementById("profileSaveBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var profileSaveDefaultEl = document.getElementById("profileSaveDefault");
  var profileSaveLockEl = document.getElementById("profileSaveLock");
  var profileStatusEl = document.getElementById("profileStatus");
  var activeProfileLabelEl = document.getElementById("activeProfileLabel");
  var profileBadgeEl = document.getElementById("profileBadge");
  var aDateEl = document.getElementById("aDate");
  var bDateEl = document.getElementById("bDate");
  var cDateEl = document.getElementById("cDate");
  var aTimeEl = document.getElementById("aTime");
  var bTimeEl = document.getElementById("bTime");
  var cTimeEl = document.getElementById("cTime");
  var pickABtn = document.getElementById("pickABtn");
  var pickBBtn = document.getElementById("pickBBtn");
  var pickCBtn = document.getElementById("pickCBtn");
  var clearPointsBtn = document.getElementById("clearPointsBtn");
  var previewTextEl = document.getElementById("previewText");
  var backBtn = document.getElementById("topBackBtn");
  var chartInfoEl = document.getElementById("chartInfo");
  var liveInfoEl = document.getElementById("liveInfo");
  var crosshairInfoEl = document.getElementById("crosshairInfo");
  var chartWrapEl = document.getElementById("chartWrap");
  var chartBoxEl = document.getElementById("chartBox");

  var candles = [];
  var latestPrice = null;
  var latestTs = "";
  var stateKey = "fibofbo_fibo_extension_form_dev_v1";
  var activeProfile = 1;
  var profileCount = 7;

  var tfTimes = [];
  var chart = null;
  var candleSeries = null;
  var livePriceLine = null;
  var activePickTarget = "";
  var isTouchDevice = ("ontouchstart" in window) || (navigator.maxTouchPoints > 0);
  var pickTouchStartMs = 0;
  var pickTouchStartX = 0;
  var pickTouchMoved = false;
  var pickCandidateTime = 0;
  var builtinCandles = {
    h4: [
      { time: "2026-02-18 23:00:00", open: 4961.2, high: 4978.3, low: 4958.9, close: 4970.1 },
      { time: "2026-02-19 03:00:00", open: 4970.1, high: 4989.4, low: 4968.2, close: 4983.7 },
      { time: "2026-02-19 07:00:00", open: 4983.7, high: 5002.2, low: 4979.8, close: 4998.3 },
      { time: "2026-02-19 11:00:00", open: 4998.3, high: 5008.1, low: 4988.2, close: 4992.5 },
      { time: "2026-02-19 15:00:00", open: 4992.5, high: 5001.6, low: 4976.3, close: 4980.4 },
      { time: "2026-02-19 19:00:00", open: 4980.4, high: 4988.7, low: 4969.1, close: 4974.8 },
      { time: "2026-02-19 23:00:00", open: 4974.8, high: 4990.5, low: 4970.7, close: 4986.9 },
      { time: "2026-02-20 03:00:00", open: 4986.9, high: 5005.8, low: 4982.6, close: 5001.4 },
      { time: "2026-02-20 07:00:00", open: 5001.4, high: 5013.2, low: 4994, close: 5007.9 },
      { time: "2026-02-20 11:00:00", open: 5007.9, high: 5010.6, low: 4996.2, close: 5000.3 },
      { time: "2026-02-20 15:00:00", open: 5000.3, high: 5006.1, low: 4988.2, close: 4992.4 },
      { time: "2026-02-20 19:00:00", open: 4992.4, high: 5003.4, low: 4987.7, close: 4999.8 },
    ],
    d1: [
      { time: "2026-02-12 23:00:00", open: 4922.1, high: 4960.4, low: 4908.2, close: 4944.3 },
      { time: "2026-02-13 23:00:00", open: 4944.3, high: 4979.6, low: 4936.5, close: 4968.1 },
      { time: "2026-02-16 23:00:00", open: 4968.1, high: 5001.9, low: 4954.8, close: 4993.2 },
      { time: "2026-02-17 23:00:00", open: 4993.2, high: 5015.3, low: 4970.4, close: 4981.7 },
      { time: "2026-02-18 23:00:00", open: 4981.7, high: 5008.2, low: 4960.3, close: 4995.6 },
      { time: "2026-02-19 23:00:00", open: 4995.6, high: 5018.4, low: 4984.2, close: 5008.9 },
    ],
  };
  var INTRADAY_TF = { m15: true, m30: true, h1: true, h4: true };
  var TF_LIMITS = { m15: 500, m30: 400, h1: 350, h4: 260, d1: 220, w1: 180 };

  function f2(v) {
    return Number(v || 0).toFixed(2);
  }

  function getEmptyState() {
    return { activeProfile: 1, profiles: {} };
  }

  function parseServerState(raw) {
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return null;
      return parsed;
    } catch (_) {
      return null;
    }
  }

  function readState() {
    try {
      var raw = localStorage.getItem(stateKey);
      if (!raw) return getEmptyState();
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return getEmptyState();
      if (!parsed.profiles || typeof parsed.profiles !== "object") parsed.profiles = {};
      if (!Number.isFinite(Number(parsed.activeProfile))) parsed.activeProfile = 1;
      return parsed;
    } catch (_) {
      return getEmptyState();
    }
  }

  function writeState(state) {
    try {
      localStorage.setItem(stateKey, JSON.stringify(state));
    } catch (_) {
      // ignore storage failure
    }
  }

  function getCurrentStateForPayload() {
    var state = readState();
    state.activeProfile = activeProfile;
    state.profiles[String(activeProfile)] = collectFormData();
    return state;
  }

  function sendProfilePayloadToBot(kind, profileIdx, stateOverride) {
    if (!tg || typeof tg.sendData !== "function") return;
    var payload = {
      type: kind,
      profile: Number(profileIdx || activeProfile),
      state: stateOverride || readState(),
    };
    try {
      tg.sendData(JSON.stringify(payload));
    } catch (_) {
      // ignore sendData errors in preview/local mode
    }
  }

  function collectFormData() {
    return {
      trend: String(trendEl.value || ""),
      tf: String(tfEl.value || ""),
      aDate: String(aDateEl.value || ""),
      bDate: String(bDateEl.value || ""),
      cDate: String(cDateEl.value || ""),
      aTime: String(aTimeEl.value || ""),
      bTime: String(bTimeEl.value || ""),
      cTime: String(cTimeEl.value || ""),
    };
  }

  function hasProfileData(p) {
    if (!p || typeof p !== "object") return false;
    return Boolean(p.trend || p.tf || p.aDate || p.bDate || p.cDate || p.aTime || p.bTime || p.cTime);
  }

  function updateProfileTabsUI(state) {
    var tabButtons = profileTabsEl ? profileTabsEl.querySelectorAll(".profile-tab-btn") : [];
    tabButtons.forEach(function (btn) {
      var idx = Number(btn.getAttribute("data-profile") || "0");
      btn.classList.toggle("active", idx === activeProfile);
      var p = state.profiles[String(idx)];
      var filled = hasProfileData(p);
      btn.classList.toggle("filled", filled);
      btn.classList.toggle("empty", !filled);
    });
    if (activeProfileLabelEl) activeProfileLabelEl.textContent = "#" + String(activeProfile);
    if (profileBadgeEl) {
      profileBadgeEl.classList.toggle("show", activeProfile >= 3 && activeProfile <= 7);
    }
    var locked = activeProfile >= 3 && !isNextMember;
    if (profileSaveDefaultEl) {
      profileSaveDefaultEl.style.display = locked ? "none" : "inline-flex";
    }
    if (profileSaveLockEl) {
      profileSaveLockEl.classList.toggle("show", locked);
    }
    if (profileSaveBtn) {
      profileSaveBtn.setAttribute("aria-disabled", locked ? "true" : "false");
    }
  }

  function saveFormState(showMessage) {
    try {
      if (activeProfile >= 3 && !isNextMember) {
        if (showMessage && profileStatusEl) {
          profileStatusEl.textContent = "Profile 3-7 hanya untuk NEXTexclusive member.";
        }
        return;
      }
      var state = readState();
      state.activeProfile = activeProfile;
      state.profiles[String(activeProfile)] = collectFormData();
      writeState(state);
      updateProfileTabsUI(state);
      if (showMessage && profileStatusEl) {
        profileStatusEl.textContent = "Profile #" + String(activeProfile) + " disimpan.";
        sendProfilePayloadToBot("fibo_extension_profile_save", activeProfile, state);
      }
    } catch (_) {
      // ignore storage failure
    }
  }

  function applyProfileData(data) {
    var p = data || {};
    trendEl.value = p.trend || "";
    tfEl.value = p.tf || "h4";
    aDateEl.value = p.aDate || "";
    bDateEl.value = p.bDate || "";
    cDateEl.value = p.cDate || "";
    updateTimeInputs();
    [aTimeEl, bTimeEl, cTimeEl].forEach(setIntradayTimes);
    if (p.aTime) aTimeEl.value = p.aTime;
    if (p.bTime) bTimeEl.value = p.bTime;
    if (p.cTime) cTimeEl.value = p.cTime;
  }

  function resetCurrentProfile() {
    var state = readState();
    delete state.profiles[String(activeProfile)];
    state.activeProfile = activeProfile;
    writeState(state);
    applyProfileData({});
    updateProfileTabsUI(state);
    clearABCMarkers();
    renderPreview();
    if (profileStatusEl) {
      profileStatusEl.textContent = "Profile #" + String(activeProfile) + " direset.";
    }
    sendProfilePayloadToBot("fibo_extension_profile_reset", activeProfile, state);
  }

  function loadFormState() {
    try {
      var state = readState();
      activeProfile = Math.max(1, Math.min(profileCount, Number(state.activeProfile || 1)));
      applyProfileData(state.profiles[String(activeProfile)] || {});
      updateProfileTabsUI(state);
    } catch (_) {
      // ignore storage failure
    }
  }

  function switchProfile(profileIdx) {
    saveFormState(false);
    var prevTf = String(tfEl.value || "").toLowerCase();
    var state = readState();
    activeProfile = Math.max(1, Math.min(profileCount, Number(profileIdx || 1)));
    state.activeProfile = activeProfile;
    writeState(state);
    applyProfileData(state.profiles[String(activeProfile)] || {});
    var nextTf = String(tfEl.value || "").toLowerCase();
    updateProfileTabsUI(state);
    if (profileStatusEl) {
      if (activeProfile >= 3 && !isNextMember) {
        profileStatusEl.textContent = "Profile #" + String(activeProfile) + " dikunci (NEXTexclusive sahaja).";
      } else {
        profileStatusEl.textContent = "Profile #" + String(activeProfile) + " aktif.";
      }
    }
    if (prevTf !== nextTf || !candles.length) {
      reloadAll().then(initDefaultDates).then(function () {
        renderPreview();
        saveFormState(false);
      });
      return;
    }
    updateChart(false);
    renderPreview();
    saveFormState(false);
  }

  function normalizeTs(raw) {
    var s = String(raw || "").trim();
    if (!s) return "";
    s = s.replace("T", " ").replace("Z", "");
    if (s.length >= 19) return s.slice(0, 19);
    if (s.length === 16) return s + ":00";
    if (s.length === 10) return s + " 00:00:00";
    return s;
  }

  function toChartTime(rawTs) {
    var d = parseUtcDate(rawTs);
    if (Number.isNaN(d.getTime())) return 0;
    return Math.floor(d.getTime() / 1000);
  }

  function mytTextFromSec(ts) {
    if (!ts) return "-";
    var d = new Date(Number(ts) * 1000);
    var date = d.toLocaleDateString("en-GB", { timeZone: "Asia/Kuala_Lumpur" });
    var time = d.toLocaleTimeString("en-GB", {
      timeZone: "Asia/Kuala_Lumpur",
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
    });
    return date + " " + time + " MYT";
  }

  function shouldHideWeekendCandle(rawTs) {
    var d = parseUtcDate(rawTs);
    if (Number.isNaN(d.getTime())) return false;
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kuala_Lumpur",
      weekday: "short",
      hour: "2-digit",
      hour12: false,
    }).formatToParts(d);
    var weekday = "";
    var hour = -1;
    parts.forEach(function (p) {
      if (p.type === "weekday") weekday = String(p.value || "");
      if (p.type === "hour") {
        var h = Number(p.value);
        if (Number.isFinite(h)) hour = h;
      }
    });
    if (weekday === "Sun") return true;
    if (weekday === "Sat" && hour >= 6) return true;
    if (weekday === "Mon" && hour >= 0 && hour < 7) return true;
    return false;
  }

  function buildChartData() {
    var tf = String(tfEl.value || "").toLowerCase();
    var filterWeekend = Boolean(INTRADAY_TF[tf]);
    return candles
      .filter(function (c) {
        if (!filterWeekend) return true;
        return !shouldHideWeekendCandle(c.time || c.ts || "");
      })
      .map(function (c) {
        return {
          time: toChartTime(c.time || c.ts || ""),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
        };
      })
      .filter(function (c) {
        return c.time > 0 && Number.isFinite(c.open) && Number.isFinite(c.high) && Number.isFinite(c.low) && Number.isFinite(c.close);
      });
  }

  function initChart() {
    if (!window.LightweightCharts || chart) return;
    chart = window.LightweightCharts.createChart(chartBoxEl, {
      width: chartWrapEl.clientWidth,
      height: chartWrapEl.clientHeight,
      layout: {
        attributionLogo: false,
        background: { color: "#0b1220" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      rightPriceScale: {
        borderColor: "#1f2937",
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      localization: {
        locale: "en-GB",
        timeFormatter: function (time) {
          return mytTextFromSec(typeof time === "number" ? time : 0);
        },
      },
      timeScale: {
        borderColor: "#1f2937",
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: function (time) {
          var ts = typeof time === "number" ? time : 0;
          var d = new Date(ts * 1000);
          var date = d.toLocaleDateString("en-GB", { timeZone: "Asia/Kuala_Lumpur" });
          var hhmm = d.toLocaleTimeString("en-GB", {
            timeZone: "Asia/Kuala_Lumpur",
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
          });
          return date + " " + hhmm;
        },
      },
      crosshair: {
        mode: window.LightweightCharts.CrosshairMode.Normal,
      },
    });
    var candleOptions = {
      upColor: "#16a34a",
      downColor: "#dc2626",
      borderVisible: false,
      wickUpColor: "#16a34a",
      wickDownColor: "#dc2626",
      priceLineVisible: true,
      lastValueVisible: true,
    };
    if (typeof chart.addCandlestickSeries === "function") {
      candleSeries = chart.addCandlestickSeries(candleOptions);
    } else if (
      typeof chart.addSeries === "function" &&
      window.LightweightCharts &&
      window.LightweightCharts.CandlestickSeries
    ) {
      candleSeries = chart.addSeries(window.LightweightCharts.CandlestickSeries, candleOptions);
    } else {
      previewTextEl.textContent = "Chart library tak support candlestick series.";
      return;
    }

    chart.subscribeCrosshairMove(function (param) {
      if (!param || !param.time || !candleSeries) {
        crosshairInfoEl.textContent = "Crosshair: -";
        return;
      }
      if (activePickTarget) {
        var ct = Number(param.time);
        if (Number.isFinite(ct) && ct > 0) {
          pickCandidateTime = ct;
        }
      }
      var c = param.seriesData.get(candleSeries);
      if (!c) {
        crosshairInfoEl.textContent = "Crosshair: -";
        return;
      }
      crosshairInfoEl.textContent =
        "Crosshair: " +
        mytTextFromSec(param.time) +
        " | O:" + f2(c.open) +
        " H:" + f2(c.high) +
        " L:" + f2(c.low) +
        " C:" + f2(c.close);
    });

    chart.subscribeClick(function (param) {
      if (!activePickTarget) return;
      if (isTouchDevice) return;
      if (!param || !param.time) return;
      assignPickFromChartTime(param.time, "chart_click");
    });

    window.addEventListener("resize", function () {
      if (!chart) return;
      chart.applyOptions({
        width: chartWrapEl.clientWidth,
        height: chartWrapEl.clientHeight,
      });
    });
  }

  function findNearestCandleByChartTime(rawTime) {
    var clickedTs = Number(rawTime);
    if (!Number.isFinite(clickedTs) || clickedTs <= 0) return null;
    var nearest = null;
    var nearestDiff = Number.POSITIVE_INFINITY;
    for (var i = 0; i < candles.length; i++) {
      var row = candles[i];
      var rowTs = toChartTime(row.time || row.ts || "");
      if (!(rowTs > 0)) continue;
      var diff = Math.abs(rowTs - clickedTs);
      if (diff < nearestDiff) {
        nearestDiff = diff;
        nearest = row;
      }
    }
    return nearest;
  }

  function assignPickFromChartTime(rawTime, source) {
    if (!activePickTarget) return;
    var nearest = findNearestCandleByChartTime(rawTime);
    if (!nearest) return;
    var p = toMYTParts(nearest.time || nearest.ts || "");
    if (!p) return;
    var tf = String(tfEl.value || "").toLowerCase();
    var intraday = Boolean(INTRADAY_TF[tf]);
    if (activePickTarget === "A") {
      aDateEl.value = p.date;
      if (intraday) aTimeEl.value = p.time;
    } else if (activePickTarget === "B") {
      bDateEl.value = p.date;
      if (intraday) bTimeEl.value = p.time;
    } else if (activePickTarget === "C") {
      cDateEl.value = p.date;
      if (intraday) cTimeEl.value = p.time;
    }
    if (profileStatusEl) {
      profileStatusEl.textContent = "Point " + activePickTarget + " set dari chart (" + source + ").";
    }
    setPickTarget("");
    saveFormState(false);
    renderPreview();
  }

  function updateChart(resetView) {
    initChart();
    if (!chart || !candleSeries) return;
    var data = buildChartData();
    candleSeries.setData(data);
    if (resetView) {
      chart.timeScale().fitContent();
    }
    if (data.length) {
      chartInfoEl.textContent = "Chart " + String(tfEl.value || "").toUpperCase() + " | Candles: " + data.length + " | Source: " + dataSource;
    } else {
      chartInfoEl.textContent = "Chart " + String(tfEl.value || "").toUpperCase() + " | Candles: 0 | Source: " + dataSource;
    }
    updateLiveLine();
  }

  function updateLiveLine() {
    if (!candleSeries) return;
    var sourcePrice = Number.isFinite(latestPrice) ? latestPrice : null;
    var sourceTs = latestTs;
    if (!Number.isFinite(sourcePrice) && candles.length) {
      var last = candles[candles.length - 1];
      sourcePrice = Number(last.close);
      sourceTs = normalizeTs(last.time || last.ts || "");
    }
    if (!Number.isFinite(sourcePrice)) {
      liveInfoEl.textContent = "LIVE: -";
      return;
    }
    liveInfoEl.textContent = "LIVE: " + f2(sourcePrice) + " @ " + (sourceTs || "latest");
    if (!livePriceLine) {
      livePriceLine = candleSeries.createPriceLine({
        price: sourcePrice,
        color: "#ffffff",
        lineWidth: 1,
        lineStyle: window.LightweightCharts.LineStyle.Dotted,
        axisLabelVisible: true,
        title: "LIVE " + f2(sourcePrice),
      });
    } else {
      livePriceLine.applyOptions({
        price: sourcePrice,
        title: "LIVE " + f2(sourcePrice),
      });
    }
  }

  function clearABCMarkers() {
    if (!candleSeries || typeof candleSeries.setMarkers !== "function") return;
    candleSeries.setMarkers([]);
  }

  function updateABCMarkersAndFocus(side, aC, bC, cC) {
    if (!chart || !candleSeries || typeof candleSeries.setMarkers !== "function") return;
    var aTime = toChartTime(aC.time || aC.ts || "");
    var bTime = toChartTime(bC.time || bC.ts || "");
    var cTime = toChartTime(cC.time || cC.ts || "");
    if (!(aTime > 0 && bTime > 0 && cTime > 0)) {
      clearABCMarkers();
      return;
    }

    var isBuy = side === "BUY";
    var markers = [
      { time: aTime, position: isBuy ? "belowBar" : "aboveBar", color: "#60a5fa", shape: "circle", text: "A" },
      { time: bTime, position: isBuy ? "aboveBar" : "belowBar", color: "#f59e0b", shape: "circle", text: "B" },
      { time: cTime, position: isBuy ? "belowBar" : "aboveBar", color: "#c084fc", shape: "circle", text: "C" },
    ];
    candleSeries.setMarkers(markers);

    var minT = Math.min(aTime, bTime, cTime);
    var maxT = Math.max(aTime, bTime, cTime);
    var span = Math.max(maxT - minT, 1);
    var pad = Math.max(Math.floor(span * 0.4), 3600 * 4);
    chart.timeScale().setVisibleRange({
      from: minT - pad,
      to: maxT + pad,
    });
  }

  function parseUtcDate(raw) {
    var s = normalizeTs(raw).replace(" ", "T");
    if (!s) return new Date(NaN);
    if (!s.endsWith("Z")) s = s + "Z";
    return new Date(s);
  }

  function toMYTParts(raw) {
    var d = parseUtcDate(raw);
    if (Number.isNaN(d.getTime())) return null;
    var fmt = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Kuala_Lumpur",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    var parts = fmt.formatToParts(d);
    var out = {};
    parts.forEach(function (p) {
      out[p.type] = p.value;
    });
    return {
      date: (out.year || "") + "-" + (out.month || "") + "-" + (out.day || ""),
      time: (out.hour || "") + ":" + (out.minute || ""),
      full: (out.year || "") + "-" + (out.month || "") + "-" + (out.day || "") + " " + (out.hour || "") + ":" + (out.minute || "") + ":" + (out.second || ""),
    };
  }

  function defaultTimesForTf(tf) {
    if (tf === "m15") return ["00:00", "00:15", "00:30", "00:45"];
    if (tf === "m30") return ["00:00", "00:30"];
    if (tf === "h1") return ["00:00"];
    if (tf === "h4") return ["03:00", "07:00", "11:00", "15:00", "19:00", "23:00"];
    return ["00:00"];
  }

  function setIntradayTimes(selectEl) {
    selectEl.innerHTML = "";
    var tf = String(tfEl.value || "h4").toLowerCase();
    var rows = tfTimes.length ? tfTimes : defaultTimesForTf(tf);
    rows.forEach(function (t) {
      var opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      selectEl.appendChild(opt);
    });
  }

  function refreshTimeOptionsFromCandles() {
    var tf = String(tfEl.value || "h4").toLowerCase();
    if (!INTRADAY_TF[tf]) return;
    var uniq = {};
    candles.forEach(function (c) {
      var p = toMYTParts(c.time || c.ts || "");
      if (p && p.time) {
        uniq[p.time] = true;
      }
    });
    tfTimes = Object.keys(uniq).sort();
    [aTimeEl, bTimeEl, cTimeEl].forEach(setIntradayTimes);
    var state = readState();
    var p = state.profiles[String(activeProfile)] || {};
    if (p.aTime) aTimeEl.value = p.aTime;
    if (p.bTime) bTimeEl.value = p.bTime;
    if (p.cTime) cTimeEl.value = p.cTime;
  }

  function updateTimeInputs() {
    var tf = String(tfEl.value || "").toLowerCase();
    var isIntraday = Boolean(INTRADAY_TF[tf]);
    [aTimeEl, bTimeEl, cTimeEl].forEach(function (el) {
      el.disabled = !isIntraday;
      el.style.display = isIntraday ? "block" : "none";
    });
  }

  function fetchPointCandle(dateValue, timeValue) {
    if (!dateValue) return null;
    var tf = tfEl.value;
    var key = INTRADAY_TF[tf] ? (dateValue + " " + (timeValue || "00:00") + ":00") : dateValue;
    if (tf === "d1" || tf === "w1") {
      for (var i = candles.length - 1; i >= 0; i--) {
        var p = toMYTParts(candles[i].time || candles[i].ts || "");
        if (p && p.date === dateValue) return candles[i];
      }
      return null;
    }
    for (var j = candles.length - 1; j >= 0; j--) {
      var p2 = toMYTParts(candles[j].time || candles[j].ts || "");
      if (p2 && ((p2.date + " " + p2.time + ":00") === key)) return candles[j];
    }
    return null;
  }

  function computeLevels(side, a, b, c) {
    var ratios = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.382, 1.414, 1.618, 2.272, 2.618, 3.618, 4.236];
    var ab = Math.abs(b - a);
    var levels = {};
    ratios.forEach(function (r) {
      var key = String(r);
      levels[key] = side === "BUY" ? (c + (ab * r)) : (c - (ab * r));
    });
    return levels;
  }

  function getCurrentPriceFallback() {
    if (Number.isFinite(latestPrice)) return latestPrice;
    if (!candles.length) return null;
    var last = candles[candles.length - 1];
    var close = Number(last.close);
    if (Number.isFinite(close)) return close;
    return null;
  }

  function renderPreview() {
    var side = String(trendEl.value || "").toUpperCase();
    if (side !== "BUY" && side !== "SELL") {
      clearABCMarkers();
      previewTextEl.textContent = "Sila pilih trend dulu (Uptrend / Downtrend).";
      return;
    }

    var aC = fetchPointCandle(aDateEl.value, aTimeEl.value);
    var bC = fetchPointCandle(bDateEl.value, bTimeEl.value);
    var cC = fetchPointCandle(cDateEl.value, cTimeEl.value);

    if (!aC || !bC || !cC) {
      clearABCMarkers();
      previewTextEl.textContent = "Sila isi Point A/B/C dulu.\nPastikan tarikh/masa wujud dalam candle timeframe dipilih.";
      return;
    }

    updateABCMarkersAndFocus(side, aC, bC, cC);
    if (!window.FEEngine || typeof window.FEEngine.calculate !== "function") {
      previewTextEl.textContent = "FE engine belum tersedia.";
      return;
    }
    var result = window.FEEngine.calculate({
      side: side,
      tf: String(tfEl.value || ""),
      candles: candles,
      aC: aC,
      bC: bC,
      cC: cC,
      currentPrice: getCurrentPriceFallback(),
      latestTs: latestTs,
    });
    if (!result || !result.ok) {
      previewTextEl.textContent = (result && result.error) ? String(result.error) : "Gagal kira FE.";
      return;
    }
    previewTextEl.innerHTML = String(result.html || "");
    return;
  }

  async function fetchCandles() {
    var tf = String(tfEl.value || "h4").toLowerCase();
    var payload = null;
    if (devMode) {
      dataSource = "dev-json";
      try {
        var devUrl = devPreviewBase + "-" + tf + ".json?t=" + Date.now();
        var devRes = await fetch(devUrl, { cache: "no-store" });
        payload = await devRes.json();
        if (!devRes.ok) {
          throw new Error("dev_preview_http_" + devRes.status);
        }
      } catch (_devErr) {
        dataSource = "dev-builtin";
        payload = { ok: true, candles: builtinCandles[tf] || [] };
      }
    } else {
      dataSource = "api";
      var limit = Number(TF_LIMITS[tf] || 300);
      var url = previewUrl + "?tf=" + encodeURIComponent(tf) + "&limit=" + String(limit) + "&t=" + Date.now();
      var res = await fetch(url, { cache: "no-store" });
      payload = await res.json();
      if (!res.ok || (payload && payload.ok === false)) {
        throw new Error((payload && payload.error) || ("http_" + res.status));
      }
    }
    candles = Array.isArray(payload && payload.candles) ? payload.candles : [];
    refreshTimeOptionsFromCandles();
    updateChart(true);
  }

  async function fetchLiveTick() {
    try {
      var payload = null;
      if (devMode) {
        try {
          var devRes = await fetch(devTickUrl + "?t=" + Date.now(), { cache: "no-store" });
          if (!devRes.ok) return;
          payload = await devRes.json();
        } catch (_devTickErr) {
          var tf = String(tfEl.value || "h4").toLowerCase();
          var c = (builtinCandles[tf] || []).slice(-1)[0];
          if (!c) return;
          payload = { price: c.close, ts: c.time };
        }
      } else {
        var res = await fetch(liveTickUrl + "?t=" + Date.now(), { cache: "no-store" });
        if (!res.ok) return;
        payload = await res.json();
      }
      var p = Number(payload.price);
      if (Number.isFinite(p)) {
        latestPrice = p;
        latestTs = normalizeTs(payload.ts || payload.time || "");
        updateLiveLine();
      }
    } catch (_) {
      // ignore: fallback to latest candle close
    }
  }

  function backToMenu() {
    if (tg) {
      try {
        if (typeof tg.sendData === "function") {
          tg.sendData(JSON.stringify({ type: "fibo_extension_back_to_menu" }));
          return;
        }
      } catch (_) {
        // fallback close below
      }
      tg.close();
      return;
    }
    window.history.back();
  }

  function setPickTarget(target) {
    activePickTarget = String(target || "");
    if (pickABtn) pickABtn.classList.toggle("active", activePickTarget === "A");
    if (pickBBtn) pickBBtn.classList.toggle("active", activePickTarget === "B");
    if (pickCBtn) pickCBtn.classList.toggle("active", activePickTarget === "C");
  }

  function clearAllPoints() {
    aDateEl.value = "";
    bDateEl.value = "";
    cDateEl.value = "";
    aTimeEl.value = "";
    bTimeEl.value = "";
    cTimeEl.value = "";
    setPickTarget("");
    pickTouchStartMs = 0;
    pickTouchStartX = 0;
    pickTouchMoved = false;
    pickCandidateTime = 0;
    clearABCMarkers();
    saveFormState(false);
    if (profileStatusEl) {
      profileStatusEl.textContent = "Point A/B/C dikosongkan. Pilih Pick A/B/C untuk tandakan semula.";
    }
    renderPreview();
  }

  async function reloadAll() {
    previewTextEl.textContent = "Loading candle data...";
    try {
      await fetchCandles();
      await fetchLiveTick();
      updateChart(false);
      renderPreview();
    } catch (err) {
      previewTextEl.textContent = "Gagal load data: " + String(err.message || err);
    }
  }

  function initDefaultDates() {
    if (!candles.length) return;
    var last = candles[candles.length - 1];
    var ts = normalizeTs(last.time || last.ts || "");
    var d = ts.slice(0, 10);
    if (!aDateEl.value) aDateEl.value = d;
    if (!bDateEl.value) bDateEl.value = d;
    if (!cDateEl.value) cDateEl.value = d;
  }

  [aTimeEl, bTimeEl, cTimeEl].forEach(setIntradayTimes);
  updateTimeInputs();

  tfEl.addEventListener("change", function () {
    if (profileStatusEl) profileStatusEl.textContent = "";
    saveFormState(false);
    updateTimeInputs();
    reloadAll().then(initDefaultDates).then(renderPreview);
  });

  [trendEl, aDateEl, bDateEl, cDateEl, aTimeEl, bTimeEl, cTimeEl].forEach(function (el) {
    el.addEventListener("change", function () {
      if (profileStatusEl) profileStatusEl.textContent = "";
      saveFormState(false);
      renderPreview();
    });
  });

  if (profileSaveBtn) {
    profileSaveBtn.addEventListener("click", function () {
      saveFormState(true);
    });
  }

  if (profileResetBtn) {
    profileResetBtn.addEventListener("click", function () {
      resetCurrentProfile();
    });
  }

  if (pickABtn) {
    pickABtn.addEventListener("click", function () {
      setPickTarget(activePickTarget === "A" ? "" : "A");
      pickCandidateTime = 0;
    });
  }
  if (pickBBtn) {
    pickBBtn.addEventListener("click", function () {
      setPickTarget(activePickTarget === "B" ? "" : "B");
      pickCandidateTime = 0;
    });
  }
  if (pickCBtn) {
    pickCBtn.addEventListener("click", function () {
      setPickTarget(activePickTarget === "C" ? "" : "C");
      pickCandidateTime = 0;
    });
  }
  if (clearPointsBtn) {
    clearPointsBtn.addEventListener("click", function () {
      clearAllPoints();
    });
  }

  if (chartWrapEl) {
    chartWrapEl.addEventListener("click", function (ev) {
      if (!activePickTarget || !chart || isTouchDevice) return;
      var rect = chartWrapEl.getBoundingClientRect();
      var x = ev.clientX - rect.left;
      var time = chart.timeScale().coordinateToTime(x);
      if (!time) return;
      assignPickFromChartTime(time, "wrap_click");
    });
    chartWrapEl.addEventListener("touchstart", function (ev) {
      if (!activePickTarget || !chart) return;
      if (!ev.touches || !ev.touches.length) return;
      var t = ev.touches[0];
      var rect = chartWrapEl.getBoundingClientRect();
      var x = t.clientX - rect.left;
      pickTouchStartMs = Date.now();
      pickTouchStartX = x;
      pickTouchMoved = false;
      var time = chart.timeScale().coordinateToTime(x);
      if (time) {
        var ts = Number(time);
        if (Number.isFinite(ts) && ts > 0) pickCandidateTime = ts;
      }
    });
    chartWrapEl.addEventListener("touchmove", function (ev) {
      if (!activePickTarget || !chart) return;
      if (!ev.touches || !ev.touches.length) return;
      var t = ev.touches[0];
      var rect = chartWrapEl.getBoundingClientRect();
      var x = t.clientX - rect.left;
      if (Math.abs(x - pickTouchStartX) >= 8) {
        pickTouchMoved = true;
      }
      var time = chart.timeScale().coordinateToTime(x);
      if (time) {
        var ts = Number(time);
        if (Number.isFinite(ts) && ts > 0) pickCandidateTime = ts;
      }
    });
    chartWrapEl.addEventListener("touchend", function (ev) {
      if (!activePickTarget || !chart) return;
      if (!ev.changedTouches || !ev.changedTouches.length) return;
      var t = ev.changedTouches[0];
      var rect = chartWrapEl.getBoundingClientRect();
      var x = t.clientX - rect.left;
      var endTime = chart.timeScale().coordinateToTime(x);
      var heldMs = Date.now() - pickTouchStartMs;
      var longHold = heldMs >= 140;
      if (!pickTouchMoved && !longHold) {
        if (profileStatusEl) {
          profileStatusEl.textContent = "Hold & drag pada chart untuk pilih candle.";
        }
        return;
      }
      var finalTime = pickCandidateTime || Number(endTime || 0);
      if (!finalTime) {
        if (profileStatusEl) {
          profileStatusEl.textContent = "Tak dapat baca candle. Cuba hold lebih lama.";
        }
        return;
      }
      assignPickFromChartTime(finalTime, "hold_drag");
    });
  }

  if (profileTabsEl) {
    profileTabsEl.addEventListener("click", function (ev) {
      var target = ev.target;
      if (!target || !target.classList || !target.classList.contains("profile-tab-btn")) return;
      var idx = Number(target.getAttribute("data-profile") || "1");
      if (idx === activeProfile) return;
      switchProfile(idx);
    });
  }

  backBtn.addEventListener("click", backToMenu);
  if (bottomBackBtn) {
    bottomBackBtn.addEventListener("click", backToMenu);
  }

  loadFormState();
  updateTimeInputs();

  var serverState = parseServerState(serverProfilesStateRaw);
  if (serverState) {
    writeState(serverState);
    loadFormState();
  }

  reloadAll().then(function () {
    initDefaultDates();
    renderPreview();
    saveFormState(false);
  });
  setInterval(fetchLiveTick, 5000);
})();
