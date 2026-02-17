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
  var floatingFullEl = document.getElementById("floatingFull");
  var floatingHalfEl = document.getElementById("floatingHalf");

  function n(id) {
    return Number((document.getElementById(id).value || "").trim());
  }

  function f2(v) {
    return Number(v || 0).toFixed(2);
  }

  function f3(v) {
    return Number(v || 0).toFixed(3);
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
    var zone = n("zoneSize");

    if (Number.isNaN(balance) || balance <= 0) {
      statusEl.textContent = "Modal semasa kena lebih dari 0.";
      return;
    }
    if (Number.isNaN(riskPct) || riskPct <= 0) {
      statusEl.textContent = "Risk % kena lebih dari 0.";
      return;
    }
    if (Number.isNaN(zone) || zone <= 0) {
      statusEl.textContent = "Saiz zon/SL kena lebih dari 0.";
      return;
    }

    // XAUUSD assumption: 1.00 lot moves about USD 100 per USD 1.00 price move.
    var riskUsd = balance * (riskPct / 100);
    var usdPerLotAtZone = zone * 100;
    var lot = usdPerLotAtZone > 0 ? riskUsd / usdPerLotAtZone : 0;
    var floatingFull = lot * zone * 100;
    var floatingHalf = lot * (zone / 2) * 100;

    riskUsdEl.textContent = f2(riskUsd);
    lotSizeEl.textContent = f3(lot);
    floatingFullEl.textContent = f2(floatingFull);
    floatingHalfEl.textContent = f2(floatingHalf);
    statusEl.textContent = "Kiraan siap. Semak balik lot ikut broker min lot/step lot.";
  });
})();
