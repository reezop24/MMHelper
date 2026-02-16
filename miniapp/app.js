(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var form = document.getElementById("setupForm");
  var statusEl = document.getElementById("formStatus");
  var topBackBtn = document.getElementById("topBackBtn");

  topBackBtn.addEventListener("click", function () {
    if (tg) {
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: back hanya aktif dalam Telegram.";
  });

  function getNumberValue(id) {
    var raw = (document.getElementById(id).value || "").trim();
    var normalized = raw.replace(/%/g, "").trim();
    if (!normalized) return NaN;
    return Number(normalized);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var payload = {
      type: "setup_profile",
      name: (document.getElementById("name").value || "").trim(),
      initial_capital_usd: getNumberValue("initial_capital_usd"),
      risk_per_trade_pct: getNumberValue("risk_per_trade_pct"),
      max_daily_loss_pct: getNumberValue("max_daily_loss_pct"),
      daily_profit_target_pct: getNumberValue("daily_profit_target_pct")
    };

    if (!payload.name) {
      statusEl.textContent = "Nama wajib diisi.";
      return;
    }

    var numbers = [
      payload.initial_capital_usd,
      payload.risk_per_trade_pct,
      payload.max_daily_loss_pct,
      payload.daily_profit_target_pct
    ];

    if (numbers.some(function (num) { return Number.isNaN(num) || num <= 0; })) {
      statusEl.textContent = "Semua nilai nombor mesti lebih besar dari 0.";
      return;
    }

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview sahaja: buka dari Telegram untuk submit ke bot.";
  });
})();
