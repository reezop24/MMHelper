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
  var reezoWalletIdInput = document.getElementById("reezoWalletIdInput");
  var reezoDepositYesBtn = document.getElementById("reezoDepositYesBtn");
  var reezoDepositNoBtn = document.getElementById("reezoDepositNoBtn");
  var reezoFullNameInput = document.getElementById("reezoFullNameInput");
  var reezoPhoneInput = document.getElementById("reezoPhoneInput");
  var submitReezoVerificationBtn = document.getElementById("submitReezoVerificationBtn");
  var AMARKETS_SIGNUP_URL = "https://amarketstrading.co/sign-up/real-en/?g=REEZO24";

  var activeView = "home";
  var hasDeposited100 = null;
  var ibRequestSubmitted = null;
  var ibHasDeposited100 = null;
  var reezoHasDeposited50 = null;

  function getEntryParam() {
    try {
      var params = new URLSearchParams(window.location.search || "");
      return String(params.get("entry") || "").trim().toLowerCase();
    } catch (err) {
      return "";
    }
  }

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
    btnGoIbVerification.classList.toggle("hidden", !isTransfer);
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

  function setReezoDepositChoice(value) {
    reezoHasDeposited50 = value;
    reezoDepositYesBtn.classList.toggle("active-yes", value === true);
    reezoDepositNoBtn.classList.toggle("active-no", value === false);
  }

  function readText(el) {
    return String((el && el.value) || "").trim();
  }

  function isValidWalletId(walletId) {
    return /^[0-9]{7}$/.test(walletId);
  }

  function submitVerification() {
    var walletId = readText(walletIdInput);
    var fullName = readText(fullNameInput);
    var phoneNumber = readText(phoneInput);

    if (!walletId) {
      statusEl.textContent = "Sila isi AMarkets Wallet ID.";
      return;
    }
    if (!isValidWalletId(walletId)) {
      statusEl.textContent = "AMarkets Wallet ID mesti tepat 7 angka.";
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
    if (!isValidWalletId(walletId)) {
      statusEl.textContent = "AMarkets Wallet ID mesti tepat 7 angka.";
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

  function submitReezoVerification() {
    var walletId = readText(reezoWalletIdInput);
    var fullName = readText(reezoFullNameInput);
    var phoneNumber = readText(reezoPhoneInput);

    if (!walletId) {
      statusEl.textContent = "Sila isi AMarkets Wallet ID.";
      return;
    }
    if (!isValidWalletId(walletId)) {
      statusEl.textContent = "AMarkets Wallet ID mesti tepat 7 angka.";
      return;
    }
    if (reezoHasDeposited50 === null) {
      statusEl.textContent = "Sila pilih status deposit USD 50.";
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
      registration_flow: "under_ib_reezo",
      wallet_id: walletId,
      has_deposit_100: reezoHasDeposited50,
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

    statusEl.textContent = "Preview mode: borang pengesahan client under IB Reezo dihantar.";
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
  reezoDepositYesBtn.addEventListener("click", function () {
    setReezoDepositChoice(true);
  });
  reezoDepositNoBtn.addEventListener("click", function () {
    setReezoDepositChoice(false);
  });
  submitReezoVerificationBtn.addEventListener("click", submitReezoVerification);

  var entry = getEntryParam();
  if (entry === "under_ib_reezo") {
    showView("under_ib_reezo");
  } else {
    showView("home");
  }
  openTab("new");
  openIbTab("transfer");
  openIbGuideTab("web");
  setDepositChoice(null);
  setIbRequestChoice(null);
  setIbDepositChoice(null);
  setReezoDepositChoice(null);
})();
