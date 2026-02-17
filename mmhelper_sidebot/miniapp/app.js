(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var tabNewRegistration = document.getElementById("tabNewRegistration");
  var tabVerification = document.getElementById("tabVerification");
  var panelNewRegistration = document.getElementById("panelNewRegistration");
  var panelVerification = document.getElementById("panelVerification");
  var btnDaftarAmarkets = document.getElementById("btnDaftarAmarkets");
  var btnPengesahanPelangganBaru = document.getElementById("btnPengesahanPelangganBaru");

  function openTab(tabName) {
    var isNew = tabName === "new";
    panelNewRegistration.classList.toggle("hidden", !isNew);
    panelVerification.classList.toggle("hidden", isNew);
    tabNewRegistration.classList.toggle("active", isNew);
    tabVerification.classList.toggle("active", !isNew);
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

  topBackBtn.addEventListener("click", backToMainMenu);
  bottomBackBtn.addEventListener("click", backToMainMenu);

  tabNewRegistration.addEventListener("click", function () {
    openTab("new");
  });

  tabVerification.addEventListener("click", function () {
    openTab("verification");
  });

  btnDaftarAmarkets.addEventListener("click", function () {
    sendChoice("new_registration_amarkets");
  });

  btnPengesahanPelangganBaru.addEventListener("click", function () {
    openTab("verification");
  });

  openTab("new");
})();
