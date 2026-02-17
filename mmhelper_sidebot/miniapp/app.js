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
  var btnBackToChoicesA = document.getElementById("btnBackToChoicesA");
  var btnBackToChoicesB = document.getElementById("btnBackToChoicesB");
  var btnBackToChoicesC = document.getElementById("btnBackToChoicesC");

  var homeView = document.getElementById("homeView");
  var newRegistrationView = document.getElementById("newRegistrationView");
  var ibTransferView = document.getElementById("ibTransferView");
  var underIbReezoView = document.getElementById("underIbReezoView");
  var activeView = "home";

  function showHome() {
    homeView.classList.remove("hidden");
    newRegistrationView.classList.add("hidden");
    ibTransferView.classList.add("hidden");
    underIbReezoView.classList.add("hidden");
    activeView = "home";
  }

  function showView(viewName) {
    homeView.classList.add("hidden");
    newRegistrationView.classList.add("hidden");
    ibTransferView.classList.add("hidden");
    underIbReezoView.classList.add("hidden");

    if (viewName === "new_registration") {
      newRegistrationView.classList.remove("hidden");
      activeView = "new_registration";
      return;
    }
    if (viewName === "ib_transfer") {
      ibTransferView.classList.remove("hidden");
      activeView = "ib_transfer";
      return;
    }
    if (viewName === "under_ib_reezo") {
      underIbReezoView.classList.remove("hidden");
      activeView = "under_ib_reezo";
      return;
    }
    showHome();
  }

  function backToMainMenu() {
    if (activeView !== "home") {
      showHome();
      return;
    }

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
    showView("new_registration");
  });

  btnIbTransfer.addEventListener("click", function () {
    showView("ib_transfer");
  });

  btnUnderIbReezo.addEventListener("click", function () {
    showView("under_ib_reezo");
  });

  btnBackToChoicesA.addEventListener("click", showHome);
  btnBackToChoicesB.addEventListener("click", showHome);
  btnBackToChoicesC.addEventListener("click", showHome);

  showHome();
})();
