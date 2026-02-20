(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var tfEl = document.getElementById("tf");
  var reloadBtn = document.getElementById("reloadBtn");
  var summaryEl = document.getElementById("summary");
  var backBtn = document.getElementById("topBackBtn");
  var canvas = document.getElementById("chart");
  var ctx = canvas.getContext("2d");

  function backToMenu() {
    if (tg) {
      tg.close();
      return;
    }
    window.history.back();
  }

  function fitCanvas() {
    var rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(320, Math.floor(rect.width * window.devicePixelRatio));
    canvas.height = Math.floor(420 * window.devicePixelRatio);
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  }

  function yScale(price, minP, maxP, top, h) {
    if (maxP <= minP) return top + h / 2;
    return top + ((maxP - price) / (maxP - minP)) * h;
  }

  function draw(payload) {
    fitCanvas();
    var w = canvas.clientWidth;
    var h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);

    var candles = payload.candles || [];
    if (!candles.length) {
      summaryEl.textContent = "Tiada data candle.";
      return;
    }

    var minP = Infinity;
    var maxP = -Infinity;
    candles.forEach(function (c) {
      minP = Math.min(minP, Number(c.low));
      maxP = Math.max(maxP, Number(c.high));
    });
    var pad = (maxP - minP) * 0.08 || 1;
    minP -= pad;
    maxP += pad;

    var left = 14, right = w - 14, top = 12, bottom = h - 24;
    var plotW = right - left;
    var plotH = bottom - top;
    var step = plotW / candles.length;
    var bodyW = Math.max(2, step * 0.65);

    // grid
    ctx.strokeStyle = "rgba(120,150,200,0.2)";
    ctx.lineWidth = 1;
    for (var g = 0; g <= 4; g++) {
      var gy = top + (plotH * g) / 4;
      ctx.beginPath();
      ctx.moveTo(left, gy);
      ctx.lineTo(right, gy);
      ctx.stroke();
    }

    var tsToIdx = {};
    candles.forEach(function (c, i) { tsToIdx[String(c.ts)] = i; });

    candles.forEach(function (c, i) {
      var x = left + (i + 0.5) * step;
      var o = Number(c.open), hi = Number(c.high), lo = Number(c.low), cl = Number(c.close);
      var yO = yScale(o, minP, maxP, top, plotH);
      var yC = yScale(cl, minP, maxP, top, plotH);
      var yH = yScale(hi, minP, maxP, top, plotH);
      var yL = yScale(lo, minP, maxP, top, plotH);
      var up = cl >= o;

      ctx.strokeStyle = up ? "#22c55e" : "#ef4444";
      ctx.beginPath();
      ctx.moveTo(x, yH);
      ctx.lineTo(x, yL);
      ctx.stroke();

      ctx.fillStyle = up ? "#22c55e" : "#ef4444";
      var yTop = Math.min(yO, yC);
      var bH = Math.max(1, Math.abs(yC - yO));
      ctx.fillRect(x - bodyW / 2, yTop, bodyW, bH);
    });

    var setup = payload.setup || {};
    var points = setup.points || {};
    ["left_shoulder", "head", "right_shoulder"].forEach(function (k) {
      var p = points[k];
      if (!p) return;
      var idx = tsToIdx[String(p.ts)];
      if (idx === undefined) return;
      var x = left + (idx + 0.5) * step;
      var y = yScale(Number(p.price), minP, maxP, top, plotH);
      ctx.beginPath();
      ctx.fillStyle = "#ffd166";
      ctx.strokeStyle = "#1f2937";
      ctx.lineWidth = 2;
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });

    var lines = [
      "TF: " + String(payload.timeframe || "-").toUpperCase(),
      "status: " + String(setup.status || "NO_SETUP"),
      "side: " + String(setup.side || "-"),
      "pattern: " + String(setup.pattern || "-"),
      "trigger: " + (setup.trigger_level !== undefined ? Number(setup.trigger_level).toFixed(2) : "-"),
      "close: " + (setup.latest_close !== undefined ? Number(setup.latest_close).toFixed(2) : "-")
    ];
    summaryEl.textContent = lines.join("\n");
  }

  async function refresh() {
    var tf = String(tfEl.value || "m5").toLowerCase();
    summaryEl.textContent = "Loading...";
    try {
      var res = await fetch("/api/dbo-preview?tf=" + encodeURIComponent(tf) + "&limit=400&t=" + Date.now(), { cache: "no-store" });
      var payload = await res.json();
      if (!res.ok || !payload.ok) {
        summaryEl.textContent = "Fail: " + (payload.error || "api_error");
        return;
      }
      draw(payload);
    } catch (err) {
      summaryEl.textContent = "Error network/API";
    }
  }

  backBtn.addEventListener("click", backToMenu);
  reloadBtn.addEventListener("click", refresh);
  tfEl.addEventListener("change", refresh);
  window.addEventListener("resize", refresh);
  refresh();
})();
