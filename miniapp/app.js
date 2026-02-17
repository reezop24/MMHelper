(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var form = document.getElementById("setupForm");
  var statusEl = document.getElementById("formStatus");
  var topBackBtn = document.getElementById("topBackBtn");
  var initialCapitalInput = document.getElementById("initial_capital_usd");
  var targetBalanceInput = document.getElementById("target_balance_usd");
  var targetDaysSelect = document.getElementById("target_days");
  var growTargetHintEl = document.getElementById("growTargetHint");
  var minTargetHintEl = document.getElementById("minTargetHint");
  var targetInfoEl = document.getElementById("targetInfo");

  topBackBtn.addEventListener("click", function () {
    if (tg) {
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: back hanya aktif dalam Telegram.";
  });

  function getNumberValue(id) {
    var raw = (document.getElementById(id).value || "").trim();
    var normalized = raw
      .replace(/usd/gi, "")
      .replace(/\$/g, "")
      .replace(/,/g, "")
      .replace(/%/g, "")
      .trim();
    if (!normalized) return NaN;
    return Number(normalized);
  }

  function formatUsd(value) {
    return Number(value || 0).toFixed(2);
  }

  function updateGrowTargetPreview() {
    var initialCapital = getNumberValue("initial_capital_usd");
    var targetBalance = getNumberValue("target_balance_usd");
    if (Number.isNaN(initialCapital)) {
      minTargetHintEl.textContent = "Minimum target ialah modal permulaan + USD 100.";
    } else {
      minTargetHintEl.textContent = "Minimum target semasa: USD " + formatUsd(initialCapital + 100);
    }
    if (Number.isNaN(initialCapital) || Number.isNaN(targetBalance)) {
      growTargetHintEl.textContent = "Grow Target: USD 0.00";
      return;
    }
    var growTarget = Math.max(targetBalance - initialCapital, 0);
    growTargetHintEl.textContent = "Grow Target: USD " + formatUsd(growTarget);
  }

  function updateTargetInfo() {
    var selected = (targetDaysSelect.value || "").trim();
    if (selected === "30") {
      targetInfoEl.textContent = "30 hari: pace laju, sesuai untuk target agresif tapi tetap terkawal.";
      return;
    }
    if (selected === "90") {
      targetInfoEl.textContent = "3 bulan: pace seimbang untuk growth konsisten.";
      return;
    }
    if (selected === "180") {
      targetInfoEl.textContent = "6 bulan: pace konservatif untuk bina momentum stabil.";
      return;
    }
    targetInfoEl.textContent = "Pilih tempoh yang realistik ikut pace account semasa.";
  }

  initialCapitalInput.addEventListener("input", function () {
    updateGrowTargetPreview();
    statusEl.textContent = "";
  });
  targetBalanceInput.addEventListener("input", function () {
    updateGrowTargetPreview();
    statusEl.textContent = "";
  });
  targetDaysSelect.addEventListener("change", function () {
    updateTargetInfo();
    statusEl.textContent = "";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var targetDaysRaw = (document.getElementById("target_days").value || "").trim();
    var targetLabel = "";
    if (targetDaysRaw === "30") targetLabel = "30 hari";
    if (targetDaysRaw === "90") targetLabel = "3 bulan";
    if (targetDaysRaw === "180") targetLabel = "6 bulan";

    var payload = {
      type: "setup_profile",
      name: (document.getElementById("name").value || "").trim(),
      initial_capital_usd: getNumberValue("initial_capital_usd"),
      target_balance_usd: getNumberValue("target_balance_usd"),
      target_days: Number(targetDaysRaw),
      target_label: targetLabel
    };

    if (!payload.name) {
      statusEl.textContent = "Nama wajib diisi.";
      return;
    }

    if (Number.isNaN(payload.initial_capital_usd) || payload.initial_capital_usd <= 0) {
      statusEl.textContent = "Modal permulaan mesti lebih besar dari 0.";
      return;
    }

    if (Number.isNaN(payload.target_balance_usd) || payload.target_balance_usd <= 0) {
      statusEl.textContent = "Set New Goal mesti nilai yang valid.";
      return;
    }

    var minTarget = payload.initial_capital_usd + 100;
    if (payload.target_balance_usd < minTarget) {
      statusEl.textContent = "Target Capital minimum ialah USD " + formatUsd(minTarget) + ".";
      return;
    }

    if (targetDaysRaw !== "30" && targetDaysRaw !== "90" && targetDaysRaw !== "180") {
      statusEl.textContent = "Pilih tempoh target dulu.";
      return;
    }

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview sahaja: buka dari Telegram untuk submit ke bot.";
  });

  updateGrowTargetPreview();
  updateTargetInfo();
})();
