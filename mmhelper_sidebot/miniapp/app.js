(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var btnNewRegistration = document.getElementById("btnNewRegistration");
  var btnIbTransfer = document.getElementById("btnIbTransfer");
  var btnUnderIbReezo = document.getElementById("btnUnderIbReezo");

  function sendChoice(choice) {
    var payload = {
      type: "next_member_request_type",
      choice: choice
    };

    if (tg) {
      try {
        tg.sendData(JSON.stringify(payload));
      } catch (err) {
        // no-op
      }
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: pilihan direkod -> " + choice;
  }

  function backToMainMenu() {
    var payload = { type: "sidebot_back_to_main_menu" };

    if (tg) {
      try {
        tg.sendData(JSON.stringify(payload));
      } catch (err) {
        // no-op
      }
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk guna butang back.";
  }

  topBackBtn.addEventListener("click", backToMainMenu);
  bottomBackBtn.addEventListener("click", backToMainMenu);

  btnNewRegistration.addEventListener("click", function () {
    sendChoice("new_registration_amarkets");
  });

  btnIbTransfer.addEventListener("click", function () {
    sendChoice("ib_transfer_existing_amarkets");
  });

  btnUnderIbReezo.addEventListener("click", function () {
    sendChoice("client_under_ib_reezo");
  });
})();
