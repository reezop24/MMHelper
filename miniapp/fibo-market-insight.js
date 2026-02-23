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
  var CONFLUENCE_BAND_PIPS = 50;

  function f2(v) { return Number(v || 0).toFixed(2); }
  function pipDiff(a, b) { return Math.abs(Number(a) - Number(b)) / PIP_SIZE; }
  function levelLabel(k) { return k === "1" ? "1.0" : String(k); }
  function levelText(k, price, pips, mode) {
    var cls = "price-hl";
    if (mode === "warn") cls = "price-warn";
    if (mode === "bad") cls = "price-bad";
    return "L" + levelLabel(k) + " @ <span class=\"" + cls + "\">" + f2(price) + "</span> (" + (Number.isFinite(pips) ? pips.toFixed(1) : "-") + " pips)";
  }

  function computeBosAndCollected(side, levels, rowsFromSetup) {
    var out = { bosBroken: false, collected: {} };
    KEY_LEVELS.forEach(function (k) { out.collected[k] = 0; });
    var rows = Array.isArray(rowsFromSetup) ? rowsFromSetup : [];
    if (!rows.length) return out;

    var l1 = Number(levels["1"]);
    if (!Number.isFinite(l1)) return out;

    var bosIdx = -1;
    for (var i = 0; i < rows.length; i++) {
      var h = Number(rows[i].high);
      var l = Number(rows[i].low);
      if (!Number.isFinite(h) || !Number.isFinite(l)) continue;
      if ((side === "BUY" && h >= l1) || (side === "SELL" && l <= l1)) {
        bosIdx = i;
        break;
      }
    }
    if (bosIdx < 0) return out;

    out.bosBroken = true;
    var postBos = rows.slice(bosIdx);
    var touchBand = 5.0; // 50 pips
    var moveBand = 10.0; // 100 pips

    KEY_LEVELS.forEach(function (k) {
      var lv = Number(levels[k]);
      if (!Number.isFinite(lv)) return;
      var state = "seek_touch";
      var count = 0;
      for (var r = 0; r < postBos.length; r++) {
        var row = postBos[r];
        var high = Number(row.high);
        var low = Number(row.low);
        var close = Number(row.close);
        if (!Number.isFinite(high) || !Number.isFinite(low) || !Number.isFinite(close)) continue;
        var touched = high >= (lv - touchBand) && low <= (lv + touchBand);
        if (state === "seek_touch") {
          if (touched) state = "seek_move";
          continue;
        }
        if (state === "seek_move") {
          if (Math.abs(close - lv) >= moveBand) {
            count += 1;
            state = "seek_touch";
          }
        }
      }
      out.collected[k] = count;
    });
    return out;
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
    if (raw && typeof raw === "object") {
      return raw;
    }
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

  async function loadProfilesState() {
    var parsed = parseProfilesState(profilesStateRaw);
    if (parsed) return parsed;
    try {
      var res = await fetch("./fibo-dev-profiles-state.json?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) return null;
      var payload = await res.json();
      return parseProfilesState(payload);
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
      var collected = (info.collectedByLevel && Number(info.collectedByLevel[k])) || 0;
      var collectedClass = collected > 0 ? " collected" : "";
      return (
        '<div class="level' + collectedClass + '">' +
        '<div class="lv-name">Level ' + k + "</div>" +
        '<div class="lv-price">' + f2(lvl[k]) + "</div>" +
        '<div class="lv-dist">Jarak: ' + (Number.isFinite(d) ? (d.toFixed(1) + " pips") : "-") + "</div>" +
        '<div class="lv-collect">ZON COLLECTED : ' + (info.bosBroken ? String(collected) : "-") + "</div>" +
        "</div>"
      );
    }).join("");
    return (
      '<article class="profile-card">' +
      '<div class="row">' +
      '<div class="title">Profile #' + info.profile + " - " + info.tf.toUpperCase() + "</div>" +
      '<div class="row">' +
      '<div class="pill ' + info.side.toLowerCase() + '">' + info.side + "</div>" +
      '<div class="pill ' + (info.bosBroken ? "buy" : "") + '">' + "BOS: " + (info.bosBroken ? "YES" : "NO") + "</div>" +
      "</div>" +
      "</div>" +
      '<div class="sub">Priority weight: ' + info.weight + " | Stage: " + info.stage.text + "</div>" +
      '<div class="sub">Level 1 distance: ' + (Number.isFinite(dist1) ? (dist1.toFixed(1) + " pips") : "-") + "</div>" +
      '<div class="sub">Entry terdekat: ' + info.nearestEntryText + " | Target seterusnya: " + info.nextCheckpointText + "</div>" +
      '<div class="sub">Breakout zone: ' + info.breakoutText + " | Invalid: " + info.invalidStatus.text + "</div>" +
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
      if (cp < l10) return "TF utama BUY: harga masih di bawah 1.0, fokus utama ialah re-test breakout zone 1.0 (kawasan rejection/confirmation) sebelum checkpoint 1.382-1.618.";
      if (cp < l138) return "TF utama BUY: level 1.0 sudah break, peluang sambung ke 1.382 masih terbuka sebelum nilai 1.618.";
      if (cp <= l161) return "TF utama BUY: harga berada di zon 1.382-1.618, ini kawasan continuation atau mula rejection.";
      return "TF utama BUY: harga sudah melepasi 1.618, extension kuat; monitor potensi reversal/new structure.";
    }

    if (cp > l05) return "TF utama SELL: harga masih di atas 0.5, struktur belum bearish penuh dan retrace masih dominan.";
    if (cp > l10) return "TF utama SELL: harga masih di atas 1.0, fokus utama ialah re-test breakout zone 1.0 (kawasan rejection/confirmation) sebelum checkpoint 1.382-1.618.";
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

  function invalidByExtension(side, cp, lv) {
    var l2618 = Number(lv["2.618"]);
    var l3618 = Number(lv["3.618"]);
    var l4236 = Number(lv["4.236"]);
    if (![l2618, l3618, l4236, cp].every(Number.isFinite)) {
      return { key: "unknown", text: "unknown" };
    }
    if (side === "BUY") {
      if (cp >= l4236) return { key: "ext_done", text: "EXT done (>=4.236)" };
      if (cp >= l3618) return { key: "ext_high", text: "High extension (>=3.618)" };
      if (cp >= l2618) return { key: "entry_invalid", text: "Entry zone invalid (>=2.618)" };
      return { key: "valid", text: "Valid" };
    }
    if (cp <= l4236) return { key: "ext_done", text: "EXT done (<=4.236)" };
    if (cp <= l3618) return { key: "ext_high", text: "High extension (<=3.618)" };
    if (cp <= l2618) return { key: "entry_invalid", text: "Entry zone invalid (<=2.618)" };
    return { key: "valid", text: "Valid" };
  }

  function ltfHtfConfluence(ltf, htf) {
    var ext = ["2.618", "3.618", "4.236"];
    var htfZones = ["0.5", "1", "1.382", "1.618"];
    var best = null;
    for (var i = 0; i < ext.length; i++) {
      var ek = ext[i];
      var ev = Number(ltf.levels[ek]);
      if (!Number.isFinite(ev)) continue;
      for (var j = 0; j < htfZones.length; j++) {
        var hk = htfZones[j];
        var hv = Number(htf.levels[hk]);
        if (!Number.isFinite(hv)) continue;
        var d = pipDiff(ev, hv);
        if (d <= CONFLUENCE_BAND_PIPS && (!best || d < best.pips)) {
          best = { extKey: ek, extPrice: ev, htfKey: hk, htfPrice: hv, pips: d };
        }
      }
    }
    return best;
  }

  function nearestEntryAndCheckpoint(side, cp, lv) {
    var entries = ["0.5", "0.618", "0.786", "1"];
    var checkpoints = ["1.382", "1.618", "2.618"];
    var nearestEntry = entries[0];
    var nearestEntryPips = Number.POSITIVE_INFINITY;
    for (var i = 0; i < entries.length; i++) {
      var ek = entries[i];
      var ev = Number(lv[ek]);
      if (!Number.isFinite(ev) || !Number.isFinite(cp)) continue;
      var d = pipDiff(cp, ev);
      if (d < nearestEntryPips) {
        nearestEntryPips = d;
        nearestEntry = ek;
      }
    }

    var l1 = Number(lv["1"]);
    var l05 = Number(lv["0.5"]);
    var l0786 = Number(lv["0.786"]);
    var level1Broken = Number.isFinite(cp) && Number.isFinite(l1) ? (side === "BUY" ? (cp >= l1) : (cp <= l1)) : false;
    var atBandPips = 5.0;

    // Friendly nearest-entry text: if currently at level, mark as "sedang berada".
    var nearestEntryVal = Number(lv[nearestEntry]);
    var nearestEntryLabel = levelText(nearestEntry, nearestEntryVal, nearestEntryPips, "");
    if (Number.isFinite(nearestEntryPips) && nearestEntryPips <= atBandPips) {
      nearestEntryLabel = "Sedang di " + levelText(nearestEntry, nearestEntryVal, nearestEntryPips, "warn");
    }

    if (!level1Broken) {
      var nextNoBosKey = "1";
      if (side === "BUY") {
        if (Number.isFinite(l05) && cp < l05) nextNoBosKey = "0.5";
        else if (Number.isFinite(l0786) && cp < l0786) nextNoBosKey = "0.786";
        else nextNoBosKey = "1";
      } else {
        if (Number.isFinite(l05) && cp > l05) nextNoBosKey = "0.5";
        else if (Number.isFinite(l0786) && cp > l0786) nextNoBosKey = "0.786";
        else nextNoBosKey = "1";
      }
      var nextNoBosVal = Number(lv[nextNoBosKey]);
      var nextNoBosPips = Number.isFinite(cp) && Number.isFinite(nextNoBosVal) ? pipDiff(cp, nextNoBosVal) : NaN;
      if (nextNoBosKey === nearestEntry && nextNoBosKey === "0.786") {
        nextNoBosKey = "1";
        nextNoBosVal = Number(lv[nextNoBosKey]);
        nextNoBosPips = Number.isFinite(cp) && Number.isFinite(nextNoBosVal) ? pipDiff(cp, nextNoBosVal) : NaN;
      }
      var nextNoBosText = nextNoBosKey === "1"
        ? "Breakout zone " + levelText("1", Number(lv["1"]), nextNoBosPips, "warn")
        : levelText(nextNoBosKey, nextNoBosVal, nextNoBosPips, "");
      var l1p = Number.isFinite(cp) && Number.isFinite(l1) ? pipDiff(cp, l1) : NaN;
      return {
        nearestEntryText: nearestEntryLabel,
        nextCheckpointText: nextNoBosText,
        nearestEntryKey: nearestEntry,
        nearestEntryPips: nearestEntryPips,
        nextCheckpointKey: nextNoBosKey,
        nextCheckpointPips: Number.isFinite(nextNoBosPips) ? nextNoBosPips : l1p,
        bosBroken: false,
      };
    }

    var nextCp = checkpoints[0];
    var nextCpPips = Number.POSITIVE_INFINITY;
    for (var j = 0; j < checkpoints.length; j++) {
      var ck = checkpoints[j];
      var cv = Number(lv[ck]);
      if (!Number.isFinite(cv) || !Number.isFinite(cp)) continue;
      if (side === "BUY") {
        if (cv >= cp) {
          var dBuy = pipDiff(cp, cv);
          if (dBuy < nextCpPips) {
            nextCpPips = dBuy;
            nextCp = ck;
          }
        }
      } else if (cv <= cp) {
        var dSell = pipDiff(cp, cv);
        if (dSell < nextCpPips) {
          nextCpPips = dSell;
          nextCp = ck;
        }
      }
    }

    if (!Number.isFinite(nextCpPips)) {
      var fallback = Number(lv[nextCp]);
      nextCpPips = Number.isFinite(fallback) && Number.isFinite(cp) ? pipDiff(cp, fallback) : NaN;
    }

    return {
      nearestEntryText: nearestEntryLabel,
      nextCheckpointText: levelText(nextCp, Number(lv[nextCp]), nextCpPips, ""),
      nearestEntryKey: nearestEntry,
      nearestEntryPips: nearestEntryPips,
      nextCheckpointKey: nextCp,
      nextCheckpointPips: nextCpPips,
      bosBroken: true,
    };
  }

  async function main() {
    var parsed = await loadProfilesState();
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
      var target = nearestEntryAndCheckpoint(v.side, currentPrice, lv);
      var invalidStatus = invalidByExtension(v.side, currentPrice, lv);
      var cTs = parseUtcDate(c.time || c.ts || "").getTime();
      var rowsFromSetup = cset.filter(function (row) {
        var t = parseUtcDate(row.time || row.ts || "").getTime();
        return Number.isFinite(t) && Number.isFinite(cTs) && t >= cTs;
      });
      var bosCollected = computeBosAndCollected(v.side, lv, rowsFromSetup);
      analysed.push({
        profile: v.profile,
        tf: v.tf,
        side: v.side,
        weight: v.weight,
        levels: lv,
        stage: stage,
        currentPrice: currentPrice,
        nearestEntryText: target.nearestEntryText,
        nextCheckpointText: target.nextCheckpointText,
        nearestEntryKey: target.nearestEntryKey,
        nearestEntryPips: target.nearestEntryPips,
        nextCheckpointKey: target.nextCheckpointKey,
        nextCheckpointPips: target.nextCheckpointPips,
        bosBroken: Boolean(bosCollected.bosBroken),
        breakoutText: levelText("1", Number(lv["1"]), pipDiff(currentPrice, Number(lv["1"])), bosCollected.bosBroken ? "" : "warn"),
        invalidStatus: invalidStatus,
        collectedByLevel: bosCollected.collected,
      });
    }

    analysed.sort(function (a, b) {
      if (b.weight !== a.weight) return b.weight - a.weight;
      if (a.nextCheckpointPips !== b.nextCheckpointPips) return a.nextCheckpointPips - b.nextCheckpointPips;
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
    summary.push("Rujukan utama: Profile #" + primary.profile + " (" + primary.tf.toUpperCase() + ", " + primary.side + ").");
    summary.push(primaryNarrative(primary));
    summary.push(ltfAlignmentNarrative(primary, analysed));
    summary.push("Jarak semasa (HTF utama): breakout zone " + primary.breakoutText + " | checkpoint seterusnya " + primary.nextCheckpointText + " | entry terdekat " + primary.nearestEntryText + ".");
    var ltf = analysed.filter(function (x) { return x.profile !== primary.profile && x.weight < primary.weight; });
    if (ltf.length) {
      var ltfInvalid = ltf.filter(function (x) { return x.invalidStatus && x.invalidStatus.key !== "valid"; });
      if (ltfInvalid.length) {
        summary.push("LTF invalid check: " + ltfInvalid.map(function (x) {
          return "P#" + x.profile + " " + x.tf.toUpperCase() + " (" + x.side + ") = " + x.invalidStatus.text;
        }).join(" | "));
      } else {
        summary.push("LTF invalid check: tiada invalid extension kritikal setakat ini.");
      }
      var confluenceMsgs = [];
      for (var ci = 0; ci < ltf.length; ci++) {
        var conf = ltfHtfConfluence(ltf[ci], primary);
        if (!conf) continue;
        confluenceMsgs.push(
          "P#" + ltf[ci].profile + " L" + conf.extKey + " @" + f2(conf.extPrice) +
          " cross HTF L" + levelLabel(conf.htfKey) + " @" + f2(conf.htfPrice) +
          " (" + conf.pips.toFixed(1) + " pips)"
        );
      }
      summary.push(confluenceMsgs.length
        ? ("Cross-zone (LTF ext vs HTF zone): " + confluenceMsgs.join(" | "))
        : "Cross-zone (LTF ext vs HTF zone): tiada confluence rapat dalam 50 pips.");
    }
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
