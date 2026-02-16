(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var name = params.get("name") || "-";
  var initialCapital = params.get("initial_capital") || "0.00";
  var savedDate = params.get("saved_date") || "-";
  var currentBalance = Number(params.get("current_balance") || 0);
  var canReset = (params.get("can_reset") || "0") === "1";

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryCapital").textContent = initialCapital;
  document.getElementById("summaryBalance").textContent = currentBalance.toFixed(2);
  document.getElementById("summaryDate").textContent = savedDate;

  var form = document.getElementById("resetForm");
  var submitBtn = document.getElementById("submitBtn");
  var disabledNote = document.getElementById("disabledNote");
  var statusEl = document.getElementById("formStatus");

  if (!canReset) {
    submitBtn.disabled = true;
    disabledNote.hidden = false;
  }

  function getNewCapital() {
    var raw = (document.getElementById("newInitialCapital").value || "").trim();
    if (!raw) return NaN;
    return Number(raw);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    if (!canReset) {
      statusEl.textContent = "Reset tak dibenarkan untuk akaun ni.";
      return;
    }

    var newInitialCapital = getNewCapital();
    if (Number.isNaN(newInitialCapital) || newInitialCapital <= 0) {
      statusEl.textContent = "Isi jumlah baru yang valid dulu.";
      return;
    }

    var payload = {
      type: "initial_capital_reset",
      new_initial_capital_usd: newInitialCapital
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
