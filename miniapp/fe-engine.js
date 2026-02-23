(function () {
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

  function parseUtcDate(raw) {
    var s = normalizeTs(raw).replace(" ", "T");
    if (!s) return new Date(NaN);
    if (!s.endsWith("Z")) s = s + "Z";
    return new Date(s);
  }

  function toChartTime(rawTs) {
    var d = parseUtcDate(rawTs);
    if (Number.isNaN(d.getTime())) return 0;
    return Math.floor(d.getTime() / 1000);
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
    parts.forEach(function (p) { out[p.type] = p.value; });
    return {
      full: (out.year || "") + "-" + (out.month || "") + "-" + (out.day || "") + " " + (out.hour || "") + ":" + (out.minute || "") + ":" + (out.second || ""),
    };
  }

  function computeLevels(side, a, b, c) {
    var ratios = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.382, 1.414, 1.618, 2.272, 2.618, 3.618, 4.236];
    var ab = Math.abs(b - a);
    var levels = {};
    ratios.forEach(function (r) {
      levels[String(r)] = side === "BUY" ? (c + (ab * r)) : (c - (ab * r));
    });
    return levels;
  }

  function esc(text) {
    return String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function wrapByClass(text, cls) {
    if (!cls) return esc(text);
    return '<span class="' + esc(cls) + '">' + esc(text) + "</span>";
  }

  function calculate(input) {
    var side = String(input.side || "").toUpperCase();
    var candles = Array.isArray(input.candles) ? input.candles : [];
    var aC = input.aC;
    var bC = input.bC;
    var cC = input.cC;
    var currentPrice = Number(input.currentPrice);
    var latestTs = String(input.latestTs || "");

    if (side !== "BUY" && side !== "SELL") {
      return { ok: false, error: "Sila pilih trend dulu (Uptrend / Downtrend)." };
    }
    if (!aC || !bC || !cC) {
      return { ok: false, error: "Sila isi Point A/B/C dulu.\nPastikan tarikh/masa wujud dalam candle timeframe dipilih." };
    }

    var aPrice = side === "BUY" ? Number(aC.low) : Number(aC.high);
    var bPrice = side === "BUY" ? Number(bC.high) : Number(bC.low);
    var cPrice = side === "BUY" ? Number(cC.low) : Number(cC.high);
    if (!Number.isFinite(aPrice) || !Number.isFinite(bPrice) || !Number.isFinite(cPrice)) {
      return { ok: false, error: "Data candle point tak lengkap untuk kira FE." };
    }

    var levels = computeLevels(side, aPrice, bPrice, cPrice);
    var level1 = Number(levels["1"]);
    var broken1 = Number.isFinite(currentPrice) && (side === "BUY" ? currentPrice >= level1 : currentPrice <= level1);

    var level1382 = Number(levels["1.382"]);
    var level1618 = Number(levels["1.618"]);
    var level2618 = Number(levels["2.618"]);
    var level4236 = Number(levels["4.236"]);
    var mid1618To2618 = (level1618 + level2618) / 2;

    var cTs = toChartTime(cC.time || cC.ts || "");
    var postC = candles.filter(function (row) {
      return toChartTime(row.time || row.ts || "") >= cTs;
    });

    var postHigh = null;
    var postLow = null;
    if (postC.length) {
      postHigh = Math.max.apply(null, postC.map(function (r) { return Number(r.high); }).filter(Number.isFinite));
      postLow = Math.min.apply(null, postC.map(function (r) { return Number(r.low); }).filter(Number.isFinite));
    }

    var reached1382 = false;
    var reached1618 = false;
    if (Number.isFinite(postHigh) && Number.isFinite(postLow)) {
      if (side === "BUY") {
        reached1382 = postHigh >= level1382;
        reached1618 = postHigh >= level1618;
      } else {
        reached1382 = postLow <= level1382;
        reached1618 = postLow <= level1618;
      }
    }

    var liveReached1382 = false;
    var liveReached1618 = false;
    if (Number.isFinite(currentPrice)) {
      if (side === "BUY") {
        liveReached1382 = currentPrice >= level1382;
        liveReached1618 = currentPrice >= level1618;
      } else {
        liveReached1382 = currentPrice <= level1382;
        liveReached1618 = currentPrice <= level1618;
      }
    }
    var superHighRiskActive = reached1382 || reached1618 || liveReached1382 || liveReached1618;

    var reachedMidByHistory = false;
    var broke2618ByHistory = false;
    if (Number.isFinite(postHigh) && Number.isFinite(postLow)) {
      if (side === "BUY") {
        reachedMidByHistory = postHigh >= mid1618To2618;
        broke2618ByHistory = postHigh >= level2618;
      } else {
        reachedMidByHistory = postLow <= mid1618To2618;
        broke2618ByHistory = postLow <= level2618;
      }
    }

    var reachedMidByLive = false;
    var broke2618ByLive = false;
    var broke4236ByLive = false;
    if (Number.isFinite(currentPrice)) {
      if (side === "BUY") {
        reachedMidByLive = currentPrice >= mid1618To2618;
        broke2618ByLive = currentPrice >= level2618;
        broke4236ByLive = currentPrice >= level4236;
      } else {
        reachedMidByLive = currentPrice <= mid1618To2618;
        broke2618ByLive = currentPrice <= level2618;
        broke4236ByLive = currentPrice <= level4236;
      }
    }
    var reachedMidState = reachedMidByHistory || reachedMidByLive;
    var broke2618State = broke2618ByHistory || broke2618ByLive;

    var broke4236ByHistory = false;
    if (Number.isFinite(postHigh) && Number.isFinite(postLow)) {
      broke4236ByHistory = side === "BUY" ? postHigh >= level4236 : postLow <= level4236;
    }
    var broke4236State = broke4236ByHistory || broke4236ByLive;

    var statusMap = {
      "0": "Anchor",
      "0.5": "Low Risk",
      "0.618": "Medium Risk",
      "0.786": superHighRiskActive ? "Super High Risk" : "High Risk",
      "1": superHighRiskActive ? "Super High Risk" : "Breakout Risk",
      "1.382": "Checkpoint",
      "1.618": "Checkpoint",
      "2.618": "Checkpoint",
      "3.618": "Possible Reverse/New Structure",
      "4.236": "Possible Reverse/New Structure",
    };
    var invalidMap = {};
    var retraceOnlyKeys = ["0.618", "0.786", "1"];
    if (reachedMidState && !broke2618State) {
      statusMap["0.5"] = "Super High Risk";
      statusMap["0"] = "High Risk / Possible Reversal";
      retraceOnlyKeys.forEach(function (k) { invalidMap[k] = true; statusMap[k] = "INVALID"; });
    }
    if (broke2618State) {
      statusMap["0"] = "High Risk / Possible Reversal";
      statusMap["0.5"] = "Super High Risk";
      ["0.5", "0.618", "0.786", "1"].forEach(function (k) { invalidMap[k] = true; statusMap[k] = "INVALID"; });
    }
    if (broke4236State) {
      ["0", "0.5", "0.618", "0.786", "1", "1.382", "1.618", "2.618", "3.618", "4.236"].forEach(function (k) {
        invalidMap[k] = true;
        statusMap[k] = "INVALID";
      });
    }

    var extKeys = ["1.382", "1.618", "2.618", "3.618", "4.236"];
    var extToneMap = {};
    var postCloseHigh = null;
    var postCloseLow = null;
    if (postC.length) {
      postCloseHigh = Math.max.apply(null, postC.map(function (r) { return Number(r.close); }).filter(Number.isFinite));
      postCloseLow = Math.min.apply(null, postC.map(function (r) { return Number(r.close); }).filter(Number.isFinite));
    }
    for (var t = 0; t < extKeys.length; t++) {
      var keyTone = extKeys[t];
      if (Boolean(invalidMap[keyTone])) {
        extToneMap[keyTone] = "invalid";
        continue;
      }
      var lv = Number(levels[keyTone]);
      var reachedLive = Number.isFinite(currentPrice) && (side === "BUY" ? currentPrice >= lv : currentPrice <= lv);
      var reachedBefore = Number.isFinite(postHigh) && Number.isFinite(postLow) && (side === "BUY" ? postHigh >= lv : postLow <= lv);
      var brokeByClose = Number.isFinite(postCloseHigh) && Number.isFinite(postCloseLow) && (side === "BUY" ? postCloseHigh >= lv : postCloseLow <= lv);
      if (brokeByClose) {
        extToneMap[keyTone] = "green";
      } else if (reachedLive || reachedBefore) {
        extToneMap[keyTone] = "yellow";
      } else {
        extToneMap[keyTone] = "";
      }
    }

    function levelLine(zoneName, levelKey, statusText, isInvalid, priceClass, statusClass, lineClass) {
      var status = isInvalid
        ? '<span class="status-invalid">' + esc(statusText) + "</span>"
        : wrapByClass(statusText, statusClass);
      var priceText = wrapByClass(f2(levels[levelKey]), priceClass);
      var body = "- " + esc(zoneName) + " : " + priceText + " [" + status + "]";
      if (!lineClass) return body;
      return '<span class="' + esc(lineClass) + '">' + body + "</span>";
    }

    var sideHtml = side === "BUY" ? '<span class="side-buy">BUY</span>' : '<span class="side-sell">SELL</span>';
    var lines = [];
    lines.push("Fibo Extension Preview");
    lines.push("TF: " + String(input.tf || "").toUpperCase());
    lines.push("__SIDE__" + side);
    if (Number.isFinite(currentPrice)) {
      lines.push("Current price: " + f2(currentPrice) + " (" + (latestTs || "latest") + ")");
      lines.push("__BOS__" + (broken1 ? "YES" : "NO"));
    } else {
      lines.push("Current price: -");
      lines.push("__BOS__UNKNOWN");
    }
    lines.push("");
    var aMyt = toMYTParts(aC.time || aC.ts || "");
    var bMyt = toMYTParts(bC.time || bC.ts || "");
    var cMyt = toMYTParts(cC.time || cC.ts || "");
    lines.push("Point A: " + (aMyt ? (aMyt.full + " MYT") : normalizeTs(aC.time || aC.ts || "")) + " @ " + f2(aPrice));
    lines.push("Point B: " + (bMyt ? (bMyt.full + " MYT") : normalizeTs(bC.time || bC.ts || "")) + " @ " + f2(bPrice));
    lines.push("Point C: " + (cMyt ? (cMyt.full + " MYT") : normalizeTs(cC.time || cC.ts || "")) + " @ " + f2(cPrice));
    lines.push("");
    if (!broken1) lines.push("Belum pecah level 1.");

    var html = [];
    for (var i = 0; i < lines.length; i++) {
      var line = String(lines[i] || "");
      if (line.indexOf("__SIDE__") === 0) {
        html.push("Side: " + sideHtml);
      } else if (line.indexOf("__BOS__") === 0) {
        var bos = line.slice("__BOS__".length);
        if (bos === "YES") {
          html.push('Break Of Structure: <span class="bos-yes">YES</span>');
        } else if (bos === "NO") {
          html.push('Break Of Structure: <span class="bos-no">NO</span>');
        } else {
          html.push("Break Of Structure: unknown");
        }
      } else {
        html.push(esc(line));
      }
    }

    var entryKeys = ["1", "0.786", "0.618", "0.5", "0"];
    var entryBuffer = 0.50; // 50 pips for XAU-style quoting (0.01 per pip)
    html.push("");
    html.push('<span class="zone-title">Entry Zone</span>');
    for (var e = 0; e < entryKeys.length; e++) {
      var ek = entryKeys[e];
      var isHalfLevel = ek === "0.5" && !Boolean(invalidMap[ek]);
      var entryPriceClass = isHalfLevel ? "zone-purple" : "";
      var entryStatusClass = isHalfLevel ? "zone-purple" : "";
      var entryLineClass = "";
      if (broken1 && !Boolean(invalidMap[ek])) {
        var lv = Number(levels[ek]);
        var zMin = lv - entryBuffer;
        var zMax = lv + entryBuffer;
        var enteredByHistory = Number.isFinite(postHigh) && Number.isFinite(postLow) && postHigh >= zMin && postLow <= zMax;
        var inZoneNow = Number.isFinite(currentPrice) && currentPrice >= zMin && currentPrice <= zMax;
        var entered = enteredByHistory || inZoneNow;
        if (entered) {
          entryLineClass = inZoneNow ? "entry-zone-yellow" : "entry-zone-green";
        }
      }
      html.push(levelLine("Entry Zone " + String(e + 1), ek, statusMap[ek] || "-", Boolean(invalidMap[ek]), entryPriceClass, entryStatusClass, entryLineClass));
    }

    html.push("");
    html.push('<span class="zone-title">Extension Zone</span>');
    for (var x = 0; x < extKeys.length; x++) {
      var xk = extKeys[x];
      var tone = extToneMap[xk] || "";
      var priceCls = tone === "green" ? "zone-green" : (tone === "yellow" ? "zone-yellow" : "");
      html.push(levelLine("Extension Zone " + String(x + 1), xk, statusMap[xk] || "-", Boolean(invalidMap[xk]), priceCls, priceCls, ""));
    }
    if (broke4236State) {
      html.push("");
      html.push('<span class="status-invalid">Extension Completed. Sila buat penandaan baru pada structure semasa.</span>');
    }

    return { ok: true, html: html.join("<br>") };
  }

  window.FEEngine = { calculate: calculate };
})();
