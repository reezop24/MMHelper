(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var previewUrl = params.get("preview_url") || "/api/dbo-preview";
  var liveTickUrl = params.get("live_tick_url") || "/api/live-tick";
  var profilesStateRaw = params.get("profiles_state") || "";

  var biasPillEl = document.getElementById("biasPill");
  var metaEl = document.getElementById("meta");
  var summaryListEl = document.getElementById("summaryList");
  var profilesEl = document.getElementById("profiles");
  var emptyEl = document.getElementById("empty");
  var backBtn = document.getElementById("backBtn");

  var TF_WEIGHT = { w1: 60, d1: 50, h4: 40, h1: 30, m30: 20, m15: 10 };
  var KEY_LEVELS = ["0.5", "1", "1.382", "1.618"];
  var PIP_SIZE = 0.10;

  function f2(v) { return Number(v || 0).toFixed(2); }
  function pipDiff(a, b) { return Math.abs(Number(a) - Number(b)) / PIP_SIZE; }

  function normalizeTs(raw) {
    var s = String(raw || "").trim();
    if (!s) return "";
    s = s.replace("T", " ").replace("Z", "");
    if (s.length >= 19) return s.slice(0, 19);
    if (s.length === 16) return s + ":00";
    if (s.length === 10) return s + " 00:00:00";
    return s;
  }

  function parseUtcDate(raw) {
    var s = normalizeTs(raw).replace(" ", "T");
    if (!s) return new Date(NaN);
    if (!s.endsWith("Z")) s += "Z";
    return new Date(s);
  }

  function toMytParts(raw) {
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
    var out = {};
    fmt.formatToParts(d).forEach(function (p) { out[p.type] = p.value; });
    return {
      date: (out.year || "") + "-" + (out.month || "") + "-" + (out.day || ""),
      time: (out.hour || "") + ":" + (out.minute || ""),
    };
  }

  function computeLevels(side, a, b, c) {
    var ratios = [0, 0.5, 0.618, 0.786, 1, 1.382, 1.618, 2.618, 3.618, 4.236];
    var ab = Math.abs(b - a);
    var levels = {};
    ratios.forEach(function (r) {
      levels[String(r)] = side === "BUY" ? (c + (ab * r)) : (c - (ab * r));
    });
    return levels;
  }

  function parseProfilesState(raw) {
    if (!raw) {
      try {
        var localRaw = localStorage.getItem("fibofbo_fibo_extension_form_v2") || "";
        if (localRaw) {
          var localParsed = JSON.parse(localRaw);
          if (localParsed && typeof localParsed === "object") return localParsed;
        }
      } catch (_) {
        // ignore
      }
      return null;
    }
    try {
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return null;
      return parsed;
    } catch (_) {
      return null;
    }
  }

  async function fetchCandles(tf, limit) {
    var url = previewUrl + "?tf=" + encodeURIComponent(tf) + "&limit=" + String(limit || 400) + "&t=" + Date.now();
    try {
      var res = await fetch(url, { cache: "no-store" });
      if (res.ok) {
        var payload = await res.json();
        var rows = Array.isArray(payload && payload.candles) ? payload.candles : [];
        if (rows.length) return rows;
      }
    } catch (_) {
      // fallback below
    }
    var fallback = await fetch("./fibo-dev-preview-" + tf + ".json?t=" + Date.now(), { cache: "no-store" });
    if (!fallback.ok) throw new Error("fetch " + tf + " failed");
    var fp = await fallback.json();
    return Array.isArray(fp && fp.candles) ? fp.candles : [];
  }

  async function fetchLivePrice() {
    try {
      var res = await fetch(liveTickUrl + "?t=" + Date.now(), { cache: "no-store" });
      if (res.ok) {
        var payload = await res.json();
        var p = Number(payload && payload.price);
        if (Number.isFinite(p)) return p;
      }
    } catch (_) {
      // fallback below
    }
    try {
      var dev = await fetch("./fibo-dev-live-tick.json?t=" + Date.now(), { cache: "no-store" });
      if (!dev.ok) return NaN;
      var dp = await dev.json();
      return Number(dp && dp.price);
    } catch (_) {
      return NaN;
    }
  }

  function findPointCandle(candles, tf, date, time) {
    if (!date) return null;
    for (var i = candles.length - 1; i >= 0; i--) {
      var c = candles[i];
      var p = toMytParts(c.time || c.ts || "");
      if (!p) continue;
      if (tf === "d1" || tf === "w1") {
        if (p.date === date) return c;
      } else {
        if (p.date === date && p.time === String(time || "")) return c;
      }
    }
    return null;
  }

  function stageForProfile(side, cp, lv) {
    var l05 = Number(lv["0.5"]);
    var l10 = Number(lv["1"]);
    var l138 = Number(lv["1.382"]);
    var l161 = Number(lv["1.618"]);
    if (![l05, l10, l138, l161].every(Number.isFinite) || !Number.isFinite(cp)) {
      return { key: "unknown", text: "Data belum cukup" };
    }
    if (side === "BUY") {
      if (cp < l05) return { key: "below_05", text: "Di bawah 0.5 (deep pullback)" };
      if (cp < l10) return { key: "entry_zone", text: "Dalam zon entry 0.5-1.0" };
      if (cp < l138) return { key: "post_break", text: "Lepas breakout 1.0" };
      if (cp <= l161) return { key: "checkpoint", text: "Area checkpoint 1.382-1.618" };
      return { key: "extended", text: "Melepasi 1.618 (extension lanjut)" };
    }
    if (cp > l05) return { key: "above_05", text: "Di atas 0.5 (deep pullback)" };
    if (cp > l10) return { key: "entry_zone", text: "Dalam zon entry 0.5-1.0" };
    if (cp > l138) return { key: "post_break", text: "Lepas breakout 1.0" };
    if (cp >= l161) return { key: "checkpoint", text: "Area checkpoint 1.382-1.618" };
    return { key: "extended", text: "Melepasi 1.618 (extension lanjut)" };
  }

  function cardHtml(info) {
    var lvl = info.levels;
    var dist1 = Number.isFinite(info.currentPrice) ? pipDiff(info.currentPrice, lvl["1"]) : NaN;
    var lvRows = KEY_LEVELS.map(function (k) {
      var d = Number.isFinite(info.currentPrice) ? pipDiff(info.currentPrice, lvl[k]) : NaN;
      return (
        '<div class="level">' +
        '<div class="lv-name">Level ' + k + "</div>" +
        '<div class="lv-price">' + f2(lvl[k]) + "</div>" +
        '<div class="lv-dist">Jarak: ' + (Number.isFinite(d) ? (d.toFixed(1) + " pips") : "-") + "</div>" +
        "</div>"
      );
    }).join("");
    return (
      '<article class="profile-card">' +
      '<div class="row">' +
      '<div class="title">Profile #' + info.profile + " - " + info.tf.toUpperCase() + "</div>" +
      '<div class="pill ' + info.side.toLowerCase() + '">' + info.side + "</div>" +
      "</div>" +
      '<div class="sub">Priority weight: ' + info.weight + " | Stage: " + info.stage.text + "</div>" +
      '<div class="sub">Structure size (A-B): ' + info.swingPips.toFixed(1) + " pips</div>" +
      '<div class="sub">Level 1 distance: ' + (Number.isFinite(dist1) ? (dist1.toFixed(1) + " pips") : "-") + "</div>" +
      '<div class="levels">' + lvRows + "</div>" +
      "</article>"
    );
  }

  function setBias(biasText, cls) {
    biasPillEl.textContent = biasText;
    biasPillEl.className = "pill " + (cls || "");
  }

  function stageScore(stageKey) {
    if (stageKey === "post_break") return 2;
    if (stageKey === "checkpoint") return 3;
    if (stageKey === "extended") return 4;
    return 1;
  }

  function primaryNarrative(item) {
    var cp = Number(item.currentPrice);
    var lv = item.levels;
    var l05 = Number(lv["0.5"]);
    var l10 = Number(lv["1"]);
    var l138 = Number(lv["1.382"]);
    var l161 = Number(lv["1.618"]);
    if (![cp, l05, l10, l138, l161].every(Number.isFinite)) {
      return "Data harga semasa belum lengkap pada TF utama.";
    }

    if (item.side === "BUY") {
      if (cp < l05) return "TF utama BUY: harga masih di bawah 0.5, struktur belum pulih penuh dan retrace masih dominan.";
      if (cp < l10) return "TF utama BUY: harga sudah lepasi 0.5 tetapi belum break 1.0, jangkaan asas ialah uji 1.0 dahulu.";
      if (cp < l138) return "TF utama BUY: level 1.0 sudah break, peluang sambung ke 1.382 masih terbuka sebelum nilai 1.618.";
      if (cp <= l161) return "TF utama BUY: harga berada di zon 1.382-1.618, ini kawasan continuation atau mula rejection.";
      return "TF utama BUY: harga sudah melepasi 1.618, extension kuat; monitor potensi reversal/new structure.";
    }

    if (cp > l05) return "TF utama SELL: harga masih di atas 0.5, struktur belum bearish penuh dan retrace masih dominan.";
    if (cp > l10) return "TF utama SELL: harga sudah lepasi 0.5 tetapi belum break 1.0, jangkaan asas ialah uji 1.0 dahulu.";
    if (cp > l138) return "TF utama SELL: level 1.0 sudah break, peluang sambung ke 1.382 masih terbuka sebelum nilai 1.618.";
    if (cp >= l161) return "TF utama SELL: harga berada di zon 1.382-1.618, ini kawasan continuation atau mula rejection.";
    return "TF utama SELL: harga sudah melepasi 1.618, extension kuat; monitor potensi reversal/new structure.";
  }

  function ltfAlignmentNarrative(primary, analysed) {
    var ltf = analysed.filter(function (x) { return x.profile !== primary.profile && x.weight < primary.weight; });
    if (!ltf.length) return "Tiada profile timeframe lebih kecil untuk cross-check alignment.";
    var same = ltf.filter(function (x) { return x.side === primary.side; });
    var opp = ltf.filter(function (x) { return x.side !== primary.side; });
    if (same.length === ltf.length) {
      return "LTF seiring dengan HTF (" + primary.side + "), momentum berlapis menyokong arah utama.";
    }
    if (opp.length === ltf.length) {
      return "Semua LTF berlawanan dengan HTF. Anggap sebagai fasa counter-trend selagi HTF belum invalid.";
    }
    if (opp.length > same.length) {
      return "LTF lebih cenderung berlawanan HTF. Risiko pullback tinggi; tunggu re-align sebelum agresif.";
    }
    return "LTF bercampur tetapi masih condong seiring HTF. Fokus konfirmasi di level HTF utama.";
  }

  async function main() {
    var parsed = parseProfilesState(profilesStateRaw);
    var profiles = parsed && parsed.profiles ? parsed.profiles : {};
    var valid = [];
    var idxs = Object.keys(profiles).sort(function (a, b) { return Number(a) - Number(b); });

    var byTf = {};
    var tfsNeeded = {};
    idxs.forEach(function (idx) {
      var p = profiles[idx] || {};
      var tf = String(p.tf || "").toLowerCase();
      var side = String(p.trend || "").toUpperCase();
      if (!TF_WEIGHT[tf]) return;
      if (side !== "BUY" && side !== "SELL") return;
      if (!p.aDate || !p.bDate || !p.cDate) return;
      tfsNeeded[tf] = true;
      valid.push({ profile: Number(idx), raw: p, tf: tf, side: side, weight: TF_WEIGHT[tf] });
    });

    if (!valid.length) {
      setBias("NO DATA", "");
      metaEl.textContent = "Tiada profile FE lengkap untuk dianalisa.";
      emptyEl.style.display = "block";
      return;
    }

    var tfList = Object.keys(tfsNeeded);
    for (var i = 0; i < tfList.length; i++) {
      var tf = tfList[i];
      byTf[tf] = await fetchCandles(tf, tf === "w1" ? 220 : 450);
    }
    var currentPrice = await fetchLivePrice();

    var analysed = [];
    for (var j = 0; j < valid.length; j++) {
      var v = valid[j];
      var cset = byTf[v.tf] || [];
      var a = findPointCandle(cset, v.tf, v.raw.aDate, v.raw.aTime);
      var b = findPointCandle(cset, v.tf, v.raw.bDate, v.raw.bTime);
      var c = findPointCandle(cset, v.tf, v.raw.cDate, v.raw.cTime);
      if (!a || !b || !c) continue;

      var aPrice = v.side === "BUY" ? Number(a.low) : Number(a.high);
      var bPrice = v.side === "BUY" ? Number(b.high) : Number(b.low);
      var cPrice = v.side === "BUY" ? Number(c.low) : Number(c.high);
      if (![aPrice, bPrice, cPrice].every(Number.isFinite)) continue;

      var lv = computeLevels(v.side, aPrice, bPrice, cPrice);
      var stage = stageForProfile(v.side, currentPrice, lv);
      analysed.push({
        profile: v.profile,
        tf: v.tf,
        side: v.side,
        weight: v.weight,
        levels: lv,
        stage: stage,
        currentPrice: currentPrice,
        swingPips: pipDiff(aPrice, bPrice),
      });
    }

    analysed.sort(function (a, b) {
      if (b.weight !== a.weight) return b.weight - a.weight;
      if (b.swingPips !== a.swingPips) return b.swingPips - a.swingPips;
      return a.profile - b.profile;
    });

    if (!analysed.length) {
      setBias("NO DATA", "");
      metaEl.textContent = "Profile ada, tapi point A/B/C tak match candle semasa.";
      emptyEl.style.display = "block";
      return;
    }

    var primary = analysed[0];
    var scoreBuy = 0;
    var scoreSell = 0;
    for (var k = 0; k < analysed.length; k++) {
      var it = analysed[k];
      var delta = stageScore(it.stage.key);
      if (it.side === "BUY") scoreBuy += it.weight * delta;
      else scoreSell += it.weight * delta;
    }
    var biasText = primary.side + " BIAS (HTF Anchor)";
    var biasClass = primary.side === "BUY" ? "buy" : "sell";
    if (scoreBuy === scoreSell) {
      biasText = "MIXED (HTF " + primary.side + ")";
      biasClass = "";
    }
    setBias(biasText, biasClass);

    metaEl.textContent =
      "Current price: " + (Number.isFinite(currentPrice) ? f2(currentPrice) : "-") +
      " | Profiles analysed: " + analysed.length +
      " | Anchor: P#" + primary.profile + " " + primary.tf.toUpperCase();

    var summary = [];
    summary.push("Rujukan utama: Profile #" + primary.profile + " (" + primary.tf.toUpperCase() + ", " + primary.side + ", swing " + primary.swingPips.toFixed(1) + " pips).");
    summary.push(primaryNarrative(primary));
    summary.push(ltfAlignmentNarrative(primary, analysed));
    summary.push("Level fokus FE: 0.5, 1.0, 1.382, 1.618. Level lain (0/0.618/0.786/2.618+) kekal dipantau sebagai konteks lanjutan.");
    summaryListEl.innerHTML = summary.map(function (s) { return "<li>" + s + "</li>"; }).join("");

    profilesEl.innerHTML = analysed.map(cardHtml).join("");
    emptyEl.style.display = "none";
  }

  function backToMenu() {
    if (tg) {
      try {
        tg.close();
      } catch (_) {}
      return;
    }
    window.history.back();
  }

  backBtn.addEventListener("click", backToMenu);
  main().catch(function (err) {
    setBias("ERROR", "");
    metaEl.textContent = "Gagal load insight: " + String(err && err.message ? err.message : err);
    emptyEl.style.display = "block";
  });
})();
