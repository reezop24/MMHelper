(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var bottomPrevBtn = document.getElementById("bottomPrevBtn");

  var homeView = document.getElementById("homeView");
  var newRegistrationView = document.getElementById("newRegistrationView");
  var ibTransferView = document.getElementById("ibTransferView");
  var underIbReezoView = document.getElementById("underIbReezoView");

  var btnHomeNewRegistration = document.getElementById("btnHomeNewRegistration");
  var btnHomeIbTransfer = document.getElementById("btnHomeIbTransfer");
  var btnHomeUnderIbReezo = document.getElementById("btnHomeUnderIbReezo");
  var btnBackFromIbTransfer = document.getElementById("btnBackFromIbTransfer");
  var btnGoIbVerification = document.getElementById("btnGoIbVerification");
  var btnBackFromUnderIbReezo = document.getElementById("btnBackFromUnderIbReezo");

  var tabNewRegistration = document.getElementById("tabNewRegistration");
  var tabVerification = document.getElementById("tabVerification");
  var panelNewRegistration = document.getElementById("panelNewRegistration");
  var panelVerification = document.getElementById("panelVerification");
  var btnDaftarAmarkets = document.getElementById("btnDaftarAmarkets");
  var btnPengesahanPelangganBaru = document.getElementById("btnPengesahanPelangganBaru");
  var tabIbTransfer = document.getElementById("tabIbTransfer");
  var tabIbVerification = document.getElementById("tabIbVerification");
  var panelIbTransfer = document.getElementById("panelIbTransfer");
  var panelIbVerification = document.getElementById("panelIbVerification");
  var tabIbGuideWeb = document.getElementById("tabIbGuideWeb");
  var tabIbGuideMobile = document.getElementById("tabIbGuideMobile");
  var panelIbGuideWeb = document.getElementById("panelIbGuideWeb");
  var panelIbGuideMobile = document.getElementById("panelIbGuideMobile");
  var walletIdInput = document.getElementById("walletIdInput");
  var fullNameInput = document.getElementById("fullNameInput");
  var phoneInput = document.getElementById("phoneInput");
  var depositYesBtn = document.getElementById("depositYesBtn");
  var depositNoBtn = document.getElementById("depositNoBtn");
  var submitVerificationBtn = document.getElementById("submitVerificationBtn");
  var ibRequestYesBtn = document.getElementById("ibRequestYesBtn");
  var ibRequestNoBtn = document.getElementById("ibRequestNoBtn");
  var ibWalletIdInput = document.getElementById("ibWalletIdInput");
  var ibDepositYesBtn = document.getElementById("ibDepositYesBtn");
  var ibDepositNoBtn = document.getElementById("ibDepositNoBtn");
  var ibFullNameInput = document.getElementById("ibFullNameInput");
  var ibPhoneInput = document.getElementById("ibPhoneInput");
  var submitIbVerificationBtn = document.getElementById("submitIbVerificationBtn");
  var AMARKETS_SIGNUP_URL = "https://amarketstrading.co/sign-up/real-en/?g=REEZO24";

  var activeView = "home";
  var hasDeposited100 = null;
  var ibRequestSubmitted = null;
  var ibHasDeposited100 = null;

  function updateBottomPrevState() {
    bottomPrevBtn.classList.toggle("hidden", activeView === "home");
  }

  function showView(name) {
    homeView.classList.add("hidden");
    newRegistrationView.classList.add("hidden");
    ibTransferView.classList.add("hidden");
    underIbReezoView.classList.add("hidden");

    if (name === "new_registration") {
      newRegistrationView.classList.remove("hidden");
      activeView = name;
      updateBottomPrevState();
      return;
    }
    if (name === "ib_transfer") {
      ibTransferView.classList.remove("hidden");
      activeView = name;
      updateBottomPrevState();
      return;
    }
    if (name === "under_ib_reezo") {
      underIbReezoView.classList.remove("hidden");
      activeView = name;
      updateBottomPrevState();
      return;
    }

    homeView.classList.remove("hidden");
    activeView = "home";
    updateBottomPrevState();
  }

  function openTab(tabName) {
    var isNew = tabName === "new";
    panelNewRegistration.classList.toggle("hidden", !isNew);
    panelVerification.classList.toggle("hidden", isNew);
    tabNewRegistration.classList.toggle("active", isNew);
    tabVerification.classList.toggle("active", !isNew);
  }

  function openIbTab(tabName) {
    var isTransfer = tabName === "transfer";
    panelIbTransfer.classList.toggle("hidden", !isTransfer);
    panelIbVerification.classList.toggle("hidden", isTransfer);
    tabIbTransfer.classList.toggle("active", isTransfer);
    tabIbVerification.classList.toggle("active", !isTransfer);
  }

  function openIbGuideTab(tabName) {
    var isWeb = tabName === "web";
    panelIbGuideWeb.classList.toggle("hidden", !isWeb);
    panelIbGuideMobile.classList.toggle("hidden", isWeb);
    tabIbGuideWeb.classList.toggle("active", isWeb);
    tabIbGuideMobile.classList.toggle("active", !isWeb);
  }

  function sendToMainMenu() {
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

  function backToPreviousMenu() {
    if (activeView !== "home") {
      showView("home");
      return;
    }
    sendToMainMenu();
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

  function setDepositChoice(value) {
    hasDeposited100 = value;
    depositYesBtn.classList.toggle("active-yes", value === true);
    depositNoBtn.classList.toggle("active-no", value === false);
  }

  function setIbRequestChoice(value) {
    ibRequestSubmitted = value;
    ibRequestYesBtn.classList.toggle("active-yes", value === true);
    ibRequestNoBtn.classList.toggle("active-no", value === false);
  }

  function setIbDepositChoice(value) {
    ibHasDeposited100 = value;
    ibDepositYesBtn.classList.toggle("active-yes", value === true);
    ibDepositNoBtn.classList.toggle("active-no", value === false);
  }

  function readText(el) {
    return String((el && el.value) || "").trim();
  }

  function submitVerification() {
    var walletId = readText(walletIdInput);
    var fullName = readText(fullNameInput);
    var phoneNumber = readText(phoneInput);

    if (!walletId) {
      statusEl.textContent = "Sila isi AMarkets Wallet ID.";
      return;
    }
    if (hasDeposited100 === null) {
      statusEl.textContent = "Sila pilih status deposit USD 100.";
      return;
    }
    if (!fullName) {
      statusEl.textContent = "Sila isi nama penuh.";
      return;
    }
    if (!phoneNumber) {
      statusEl.textContent = "Sila isi no telefon.";
      return;
    }

    var payload = {
      type: "sidebot_verification_submit",
      wallet_id: walletId,
      has_deposit_100: hasDeposited100,
      full_name: fullName,
      phone_number: phoneNumber
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

    statusEl.textContent = "Preview mode: borang pengesahan dihantar.";
  }

  function submitIbVerification() {
    var walletId = readText(ibWalletIdInput);
    var fullName = readText(ibFullNameInput);
    var phoneNumber = readText(ibPhoneInput);

    if (ibRequestSubmitted === null) {
      statusEl.textContent = "Sila pilih status submit request penukaran IB.";
      return;
    }
    if (!walletId) {
      statusEl.textContent = "Sila isi AMarkets Wallet ID.";
      return;
    }
    if (ibHasDeposited100 === null) {
      statusEl.textContent = "Sila pilih status deposit USD 100.";
      return;
    }
    if (!fullName) {
      statusEl.textContent = "Sila isi nama penuh.";
      return;
    }
    if (!phoneNumber) {
      statusEl.textContent = "Sila isi no telefon.";
      return;
    }

    var payload = {
      type: "sidebot_verification_submit",
      registration_flow: "ib_transfer",
      ib_request_submitted: ibRequestSubmitted,
      wallet_id: walletId,
      has_deposit_100: ibHasDeposited100,
      full_name: fullName,
      phone_number: phoneNumber
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

    statusEl.textContent = "Preview mode: borang pengesahan penukaran IB dihantar.";
  }

  topBackBtn.addEventListener("click", backToPreviousMenu);
  bottomBackBtn.addEventListener("click", sendToMainMenu);
  bottomPrevBtn.addEventListener("click", backToPreviousMenu);

  btnHomeNewRegistration.addEventListener("click", function () {
    showView("new_registration");
    openTab("new");
  });

  btnHomeIbTransfer.addEventListener("click", function () {
    showView("ib_transfer");
    openIbTab("transfer");
    openIbGuideTab("web");
  });

  btnHomeUnderIbReezo.addEventListener("click", function () {
    showView("under_ib_reezo");
  });

  btnBackFromIbTransfer.addEventListener("click", function () {
    showView("home");
  });

  btnGoIbVerification.addEventListener("click", function () {
    openIbTab("verification");
  });

  btnBackFromUnderIbReezo.addEventListener("click", function () {
    showView("home");
  });

  tabNewRegistration.addEventListener("click", function () {
    openTab("new");
  });

  tabVerification.addEventListener("click", function () {
    openTab("verification");
  });

  tabIbTransfer.addEventListener("click", function () {
    openIbTab("transfer");
  });

  tabIbVerification.addEventListener("click", function () {
    openIbTab("verification");
  });

  tabIbGuideWeb.addEventListener("click", function () {
    openIbGuideTab("web");
  });

  tabIbGuideMobile.addEventListener("click", function () {
    openIbGuideTab("mobile");
  });

  btnDaftarAmarkets.addEventListener("click", function () {
    if (tg && typeof tg.openLink === "function") {
      tg.openLink(AMARKETS_SIGNUP_URL);
      return;
    }
    window.open(AMARKETS_SIGNUP_URL, "_blank", "noopener");
  });

  btnPengesahanPelangganBaru.addEventListener("click", function () {
    openTab("verification");
  });

  depositYesBtn.addEventListener("click", function () {
    setDepositChoice(true);
  });

  depositNoBtn.addEventListener("click", function () {
    setDepositChoice(false);
  });

  submitVerificationBtn.addEventListener("click", submitVerification);
  ibRequestYesBtn.addEventListener("click", function () {
    setIbRequestChoice(true);
  });
  ibRequestNoBtn.addEventListener("click", function () {
    setIbRequestChoice(false);
  });
  ibDepositYesBtn.addEventListener("click", function () {
    setIbDepositChoice(true);
  });
  ibDepositNoBtn.addEventListener("click", function () {
    setIbDepositChoice(false);
  });
  submitIbVerificationBtn.addEventListener("click", submitIbVerification);

  showView("home");
  openTab("new");
  openIbTab("transfer");
  openIbGuideTab("web");
  setDepositChoice(null);
  setIbRequestChoice(null);
  setIbDepositChoice(null);
})();
