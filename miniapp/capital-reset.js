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
  var topBackBtn = document.getElementById("topBackBtn");
  var submitBtn = document.getElementById("submitBtn");
  var statusEl = document.getElementById("formStatus");
  var confirmResetAll = document.getElementById("confirmResetAll");

  topBackBtn.addEventListener("click", function () {
    var payload = { type: "mm_setting_back_to_menu" };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke MM Helper Setting.";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    if (!canReset) {
      statusEl.textContent = "Reset tak dibenarkan untuk akaun ni sekarang.";
      return;
    }

    if (!confirmResetAll.checked) {
      statusEl.textContent = "Sila tick pengesahan dulu sebelum reset.";
      return;
    }

    var payload = {
      type: "initial_capital_reset",
      confirm_reset_all: true
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
