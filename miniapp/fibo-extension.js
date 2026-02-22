(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var liveTickUrl = params.get("live_tick_url") || "/api/live-tick";
  var previewUrl = params.get("preview_url") || "/api/dbo-preview";

  var tfEl = document.getElementById("tf");
  var aDateEl = document.getElementById("aDate");
  var bDateEl = document.getElementById("bDate");
  var cDateEl = document.getElementById("cDate");
  var aTimeEl = document.getElementById("aTime");
  var bTimeEl = document.getElementById("bTime");
  var cTimeEl = document.getElementById("cTime");
  var previewTextEl = document.getElementById("previewText");
  var backBtn = document.getElementById("topBackBtn");

  var candles = [];
  var latestPrice = null;
  var latestTs = "";

  var h4Times = [];

  function f2(v) {
    return Number(v || 0).toFixed(2);
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

  function setH4Times(selectEl) {
    selectEl.innerHTML = "";
    var rows = h4Times.length ? h4Times : ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"];
    rows.forEach(function (t) {
      var opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      selectEl.appendChild(opt);
    });
  }

  function refreshH4TimeOptionsFromCandles() {
    if (tfEl.value !== "h4") return;
    var uniq = {};
    candles.forEach(function (c) {
      var ts = normalizeTs(c.time || c.ts || "");
      if (ts.length >= 16) {
        uniq[ts.slice(11, 16)] = true;
      }
    });
    h4Times = Object.keys(uniq).sort();
    [aTimeEl, bTimeEl, cTimeEl].forEach(setH4Times);
  }

  function updateTimeInputs() {
    var isH4 = tfEl.value === "h4";
    [aTimeEl, bTimeEl, cTimeEl].forEach(function (el) {
      el.disabled = !isH4;
      el.style.display = isH4 ? "block" : "none";
    });
  }

  function fetchPointCandle(dateValue, timeValue) {
    if (!dateValue) return null;
    var tf = tfEl.value;
    var key = tf === "h4" ? (dateValue + " " + (timeValue || "00:00") + ":00") : dateValue;
    if (tf === "d1") {
      for (var i = candles.length - 1; i >= 0; i--) {
        var ts = normalizeTs(candles[i].time || candles[i].ts || "");
        if (ts.startsWith(dateValue)) return candles[i];
      }
      return null;
    }
    for (var j = candles.length - 1; j >= 0; j--) {
      var ts2 = normalizeTs(candles[j].time || candles[j].ts || "");
      if (ts2 === key) return candles[j];
    }
    return null;
  }

  function computeLevels(side, a, b, c) {
    var ratios = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.414, 1.618, 2.272, 2.618, 3.618, 4.236];
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
    var aC = fetchPointCandle(aDateEl.value, aTimeEl.value);
    var bC = fetchPointCandle(bDateEl.value, bTimeEl.value);
    var cC = fetchPointCandle(cDateEl.value, cTimeEl.value);

    if (!aC || !bC || !cC) {
      previewTextEl.textContent = "Sila isi Point A/B/C dulu.\nPastikan tarikh/masa wujud dalam candle timeframe dipilih.";
      return;
    }

    var aClose = Number(aC.close);
    var bClose = Number(bC.close);
    var side = bClose >= aClose ? "BUY" : "SELL";

    var aPrice = side === "BUY" ? Number(aC.low) : Number(aC.high);
    var bPrice = side === "BUY" ? Number(bC.high) : Number(bC.low);
    var cPrice = side === "BUY" ? Number(cC.low) : Number(cC.high);
    if (!Number.isFinite(aPrice) || !Number.isFinite(bPrice) || !Number.isFinite(cPrice)) {
      previewTextEl.textContent = "Data candle point tak lengkap untuk kira FE.";
      return;
    }

    var levels = computeLevels(side, aPrice, bPrice, cPrice);
    var currentPrice = getCurrentPriceFallback();
    var level1 = Number(levels["1"]);
    var broken1 = false;
    if (Number.isFinite(currentPrice)) {
      broken1 = side === "BUY" ? currentPrice >= level1 : currentPrice <= level1;
    }

    var lines = [];
    lines.push("Fibo Extension Preview");
    lines.push("TF: " + String(tfEl.value).toUpperCase() + " | Side: " + side);
    if (Number.isFinite(currentPrice)) {
      lines.push("Current price: " + f2(currentPrice) + " (" + (latestTs || "latest") + ")");
      lines.push("Break level 1: " + (broken1 ? "YES" : "NO"));
    } else {
      lines.push("Current price: -");
      lines.push("Break level 1: unknown");
    }
    lines.push("");
    lines.push("Point A: " + normalizeTs(aC.time || aC.ts || "") + " @ " + f2(aPrice));
    lines.push("Point B: " + normalizeTs(bC.time || bC.ts || "") + " @ " + f2(bPrice));
    lines.push("Point C: " + normalizeTs(cC.time || cC.ts || "") + " @ " + f2(cPrice));
    lines.push("");

    if (!broken1) {
      lines.push("Belum pecah level 1.");
      lines.push("Fokus awal:");
      lines.push("- Level 0.5 : " + f2(levels["0.5"]) + " (kawasan pullback awal)");
      lines.push("- Level 0   : " + f2(levels["0"]) + " (anchor C, invalidasi idea jika reject kuat)");
    } else {
      lines.push("Level 1 sudah pecah.");
      lines.push("Zon entry (risk berbeza):");
      lines.push("- 0.5   : " + f2(levels["0.5"]) + "  [Low Risk]");
      lines.push("- 0.618 : " + f2(levels["0.618"]) + "  [Medium Risk]");
      lines.push("- 0.786 : " + f2(levels["0.786"]) + "  [High Risk]");
      lines.push("- 1.0   : " + f2(levels["1"]) + "  [Breakout Risk]");
      lines.push("");
      lines.push("Checkpoint seterusnya:");
      lines.push("- 1.618 : " + f2(levels["1.618"]));
      lines.push("- 2.618 : " + f2(levels["2.618"]));
      lines.push("");
      lines.push("Possible reverse / trend continue / new structure:");
      lines.push("- 3.618 : " + f2(levels["3.618"]));
      lines.push("- 4.236 : " + f2(levels["4.236"]));
    }

    previewTextEl.textContent = lines.join("\n");
  }

  async function fetchCandles() {
    var tf = String(tfEl.value || "h4").toLowerCase();
    var url = previewUrl + "?tf=" + encodeURIComponent(tf) + "&limit=1200&t=" + Date.now();
    var res = await fetch(url, { cache: "no-store" });
    var payload = await res.json();
    if (!res.ok || (payload && payload.ok === false)) {
      throw new Error((payload && payload.error) || ("http_" + res.status));
    }
    candles = Array.isArray(payload.candles) ? payload.candles : [];
    refreshH4TimeOptionsFromCandles();
  }

  async function fetchLiveTick() {
    try {
      var res = await fetch(liveTickUrl + "?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) return;
      var payload = await res.json();
      var p = Number(payload.price);
      if (Number.isFinite(p)) {
        latestPrice = p;
        latestTs = normalizeTs(payload.ts || payload.time || "");
      }
    } catch (_) {
      // ignore: fallback to latest candle close
    }
  }

  function backToMenu() {
    if (tg) {
      tg.close();
      return;
    }
    window.history.back();
  }

  async function reloadAll() {
    previewTextEl.textContent = "Loading candle data...";
    try {
      await fetchCandles();
      await fetchLiveTick();
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

  [aTimeEl, bTimeEl, cTimeEl].forEach(setH4Times);
  updateTimeInputs();

  tfEl.addEventListener("change", function () {
    updateTimeInputs();
    reloadAll().then(initDefaultDates).then(renderPreview);
  });

  [aDateEl, bDateEl, cDateEl, aTimeEl, bTimeEl, cTimeEl].forEach(function (el) {
    el.addEventListener("change", renderPreview);
  });

  backBtn.addEventListener("click", backToMenu);

  reloadAll().then(function () {
    initDefaultDates();
    renderPreview();
  });
  setInterval(fetchLiveTick, 15000);
})();
