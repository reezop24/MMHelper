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

  var seriesSelect = document.getElementById("seriesSelect");
  var btnStartRegister = document.getElementById("btnStartRegister");
  var seriesHighlight = document.getElementById("seriesHighlight");
  var seriesLabel = document.getElementById("seriesLabel");
  var seriesDateText = document.getElementById("seriesDateText");
  var seriesStatusBox = document.getElementById("seriesStatusBox");
  var seriesStatusTitle = document.getElementById("seriesStatusTitle");
  var seriesStatusText = document.getElementById("seriesStatusText");
  var seriesActionList = document.getElementById("seriesActionList");

  var btnHomeNewRegistration = document.getElementById("btnHomeNewRegistration");
  var btnHomeIbTransfer = document.getElementById("btnHomeIbTransfer");
  var btnHomeUnderIbReezo = document.getElementById("btnHomeUnderIbReezo");
  var btnHomeSpecialInvitation = document.getElementById("btnHomeSpecialInvitation");

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
  var btnGoIbVerification = document.getElementById("btnGoIbVerification");
  var btnBackFromUnderIbReezo = document.getElementById("btnBackFromUnderIbReezo");

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
  var reezoCheckWalletInput = document.getElementById("reezoCheckWalletInput");
  var reezoDepositYesBtn = document.getElementById("reezoDepositYesBtn");
  var reezoDepositNoBtn = document.getElementById("reezoDepositNoBtn");
  var reezoFullNameInput = document.getElementById("reezoFullNameInput");
  var reezoPhoneInput = document.getElementById("reezoPhoneInput");
  var submitReezoVerificationBtn = document.getElementById("submitReezoVerificationBtn");
  var btnCheckUnderIbReezoMiniapp = document.getElementById("btnCheckUnderIbReezoMiniapp");
  var reezoCheckStatus = document.getElementById("reezoCheckStatus");

  var newRegistrationTitle = document.getElementById("newRegistrationTitle");
  var newRegistrationIntro = document.getElementById("newRegistrationIntro");
  var verificationTitle = document.getElementById("verificationTitle");
  var verificationIntro = document.getElementById("verificationIntro");
  var ibTransferTitle = document.getElementById("ibTransferTitle");
  var ibVerificationTitle = document.getElementById("ibVerificationTitle");
  var reezoTitle = document.getElementById("reezoTitle");

  var AMARKETS_SIGNUP_URL = "https://amarketstrading.co/sign-up/real-en/?g=REEZO24";
  var activeView = "home";
  var selectedSeries = "1";
  var hasDeposited50 = null;
  var ibRequestSubmitted = null;
  var ibHasDeposited50 = null;
  var reezoHasDeposited50 = null;

  var SERIES_META = {
    "1": { label: "SIRI 1", date: "7 & 8 April 2026" },
    "2": { label: "SIRI 2", date: "22 & 23 April 2026" },
    "3": { label: "SIRI 3", date: "14 & 15 May 2026" }
  };

  function parseWebinarStatusPayload() {
    try {
      var raw = new URLSearchParams(window.location.search || "").get("webinar_status_payload");
      if (!raw) return { series: {} };
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return { series: {} };
      return parsed;
    } catch (err) {
      return { series: {} };
    }
  }

  var webinarStatusPayload = parseWebinarStatusPayload();

  function getSeriesStatus(seriesId) {
    var series = webinarStatusPayload && webinarStatusPayload.series;
    var row = series && typeof series === "object" ? series[String(seriesId)] : null;
    return row && typeof row === "object" ? String(row.status || "opened") : "opened";
  }

  function getSeriesMeta(seriesId) {
    return SERIES_META[String(seriesId)] || SERIES_META["1"];
  }

  function getRegistrationFlow(baseFlow) {
    return "webinar_s" + String(selectedSeries) + "_" + String(baseFlow);
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
      try { tg.sendData(JSON.stringify(payload)); } catch (err) {}
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

  function isValidWalletId(walletId) {
    return /^[0-9]{7}$/.test(walletId);
  }

  function readText(el) {
    return String((el && el.value) || "").trim();
  }

  function setDepositChoice(value) {
    hasDeposited50 = value;
    depositYesBtn.classList.toggle("active-yes", value === true);
    depositNoBtn.classList.toggle("active-no", value === false);
  }

  function setIbRequestChoice(value) {
    ibRequestSubmitted = value;
    ibRequestYesBtn.classList.toggle("active-yes", value === true);
    ibRequestNoBtn.classList.toggle("active-no", value === false);
  }

  function setIbDepositChoice(value) {
    ibHasDeposited50 = value;
    ibDepositYesBtn.classList.toggle("active-yes", value === true);
    ibDepositNoBtn.classList.toggle("active-no", value === false);
  }

  function setReezoDepositChoice(value) {
    reezoHasDeposited50 = value;
    reezoDepositYesBtn.classList.toggle("active-yes", value === true);
    reezoDepositNoBtn.classList.toggle("active-no", value === false);
  }

  function refreshSeriesTexts() {
    var meta = getSeriesMeta(selectedSeries);
    seriesLabel.textContent = meta.label;
    seriesDateText.textContent = meta.date;
    newRegistrationTitle.textContent = "Syarat Pendaftaran Webinar " + meta.label;
    newRegistrationIntro.textContent = "Untuk melayakkan akses webinar " + meta.label + ", syarat berikut perlu dipenuhi:";
    verificationTitle.textContent = "Pengesahan Pendaftaran Webinar " + meta.label;
    verificationIntro.textContent = "Sila isi maklumat di bawah untuk semakan pendaftaran webinar " + meta.label + ".";
    ibTransferTitle.textContent = "Penukaran IB untuk Webinar " + meta.label;
    ibVerificationTitle.textContent = "Pengesahan Penukaran IB Webinar " + meta.label;
    reezoTitle.textContent = "Client AMarkets under IB Reezo - Webinar " + meta.label;
  }

  function renderSeriesActions() {
    selectedSeries = String(seriesSelect.value || "1");
    var status = getSeriesStatus(selectedSeries);
    var meta = getSeriesMeta(selectedSeries);

    refreshSeriesTexts();
    seriesHighlight.classList.remove("hidden");
    seriesStatusBox.classList.add("hidden");
    seriesStatusBox.classList.remove("not-opened");
    seriesActionList.classList.add("hidden");
    statusEl.textContent = "";

    if (status === "opened") {
      seriesActionList.classList.remove("hidden");
      return;
    }

    seriesStatusTitle.textContent = meta.label;
    seriesStatusText.textContent = status === "not_opened" ? "Pendaftaran belum dibuka untuk siri ini. Sila tunggu pengumuman seterusnya." : "Pendaftaran telah ditutup untuk siri ini.";
    seriesStatusBox.classList.remove("hidden");
    seriesStatusBox.classList.toggle("not-opened", status === "not_opened");
  }

  function submitVerification() {
    var walletId = readText(walletIdInput);
    var fullName = readText(fullNameInput);
    var phoneNumber = readText(phoneInput);
    if (!walletId || !fullName || !phoneNumber) {
      statusEl.textContent = "Sila lengkapkan semua maklumat pengesahan.";
      return;
    }
    if (!isValidWalletId(walletId)) {
      statusEl.textContent = "AMarkets Wallet ID mesti tepat 7 angka.";
      return;
    }
    if (hasDeposited50 === null) {
      statusEl.textContent = "Sila pilih status deposit USD 50.";
      return;
    }
    var payload = {
      type: "sidebot_verification_submit",
      registration_flow: getRegistrationFlow("new_registration"),
      wallet_id: walletId,
      has_deposit_100: hasDeposited50,
      full_name: fullName,
      phone_number: phoneNumber
    };
    if (tg) {
      try { tg.sendData(JSON.stringify(payload)); } catch (err) {}
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: borang pengesahan webinar dihantar.";
  }

  function submitIbVerification() {
    var walletId = readText(ibWalletIdInput);
    var fullName = readText(ibFullNameInput);
    var phoneNumber = readText(ibPhoneInput);
    if (!walletId || !fullName || !phoneNumber) {
      statusEl.textContent = "Sila lengkapkan semua maklumat pengesahan penukaran IB.";
      return;
    }
    if (!isValidWalletId(walletId)) {
      statusEl.textContent = "AMarkets Wallet ID mesti tepat 7 angka.";
      return;
    }
    if (ibRequestSubmitted === null) {
      statusEl.textContent = "Sila pilih status submit request penukaran IB.";
      return;
    }
    if (ibHasDeposited50 === null) {
      statusEl.textContent = "Sila pilih status deposit USD 50.";
      return;
    }
    var payload = {
      type: "sidebot_verification_submit",
      registration_flow: getRegistrationFlow("ib_transfer"),
      wallet_id: walletId,
      has_deposit_100: ibHasDeposited50,
      full_name: fullName,
      phone_number: phoneNumber,
      ib_request_submitted: ibRequestSubmitted
    };
    if (tg) {
      try { tg.sendData(JSON.stringify(payload)); } catch (err) {}
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: borang pengesahan penukaran IB webinar dihantar.";
  }

  function submitReezoVerification() {
    var walletId = readText(reezoWalletIdInput);
    var fullName = readText(reezoFullNameInput);
    var phoneNumber = readText(reezoPhoneInput);
    if (!walletId || !fullName || !phoneNumber) {
      statusEl.textContent = "Sila lengkapkan semua maklumat pengesahan deposit.";
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
    var payload = {
      type: "sidebot_verification_submit",
      registration_flow: getRegistrationFlow("under_ib_reezo"),
      wallet_id: walletId,
      has_deposit_100: reezoHasDeposited50,
      full_name: fullName,
      phone_number: phoneNumber
    };
    if (tg) {
      try { tg.sendData(JSON.stringify(payload)); } catch (err) {}
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: borang pengesahan deposit webinar dihantar.";
  }

  function checkUnderIbReezo() {
    var walletId = readText(reezoCheckWalletInput);
    if (!isValidWalletId(walletId)) {
      reezoCheckStatus.textContent = "Wallet ID mesti tepat 7 angka.";
      return;
    }
    var payload = { type: "sidebot_check_under_ib_reezo", wallet_id: walletId };
    if (tg) {
      try { tg.sendData(JSON.stringify(payload)); } catch (err) {}
      tg.close();
      return;
    }
    reezoCheckStatus.textContent = "Preview mode: semakan under IB Reezo dihantar.";
  }

  btnStartRegister.addEventListener("click", renderSeriesActions);
  btnHomeNewRegistration.addEventListener("click", function () { showView("new_registration"); openTab("new"); });
  btnHomeIbTransfer.addEventListener("click", function () { showView("ib_transfer"); openIbTab("transfer"); openIbGuideTab("web"); });
  btnHomeUnderIbReezo.addEventListener("click", function () { showView("under_ib_reezo"); });
  btnHomeSpecialInvitation.addEventListener("click", function () {
    statusEl.textContent = "Special Invitation masih placeholder. Flow ini belum dibuka lagi.";
  });
  if (btnDaftarAmarkets) {
    btnDaftarAmarkets.addEventListener("click", function () {
      if (tg && typeof tg.openLink === "function") {
        tg.openLink(AMARKETS_SIGNUP_URL);
        return;
      }
      window.open(AMARKETS_SIGNUP_URL, "_blank");
    });
  }
  btnPengesahanPelangganBaru.addEventListener("click", function () { openTab("verification"); });
  tabNewRegistration.addEventListener("click", function () { openTab("new"); });
  tabVerification.addEventListener("click", function () { openTab("verification"); });
  tabIbTransfer.addEventListener("click", function () { openIbTab("transfer"); });
  tabIbVerification.addEventListener("click", function () { openIbTab("verification"); });
  tabIbGuideWeb.addEventListener("click", function () { openIbGuideTab("web"); });
  tabIbGuideMobile.addEventListener("click", function () { openIbGuideTab("mobile"); });
  btnGoIbVerification.addEventListener("click", function () { openIbTab("verification"); });
  depositYesBtn.addEventListener("click", function () { setDepositChoice(true); });
  depositNoBtn.addEventListener("click", function () { setDepositChoice(false); });
  ibRequestYesBtn.addEventListener("click", function () { setIbRequestChoice(true); });
  ibRequestNoBtn.addEventListener("click", function () { setIbRequestChoice(false); });
  ibDepositYesBtn.addEventListener("click", function () { setIbDepositChoice(true); });
  ibDepositNoBtn.addEventListener("click", function () { setIbDepositChoice(false); });
  reezoDepositYesBtn.addEventListener("click", function () { setReezoDepositChoice(true); });
  reezoDepositNoBtn.addEventListener("click", function () { setReezoDepositChoice(false); });
  submitVerificationBtn.addEventListener("click", submitVerification);
  submitIbVerificationBtn.addEventListener("click", submitIbVerification);
  submitReezoVerificationBtn.addEventListener("click", submitReezoVerification);
  btnCheckUnderIbReezoMiniapp.addEventListener("click", checkUnderIbReezo);
  if (btnBackFromUnderIbReezo) {
    btnBackFromUnderIbReezo.addEventListener("click", function () { showView("home"); });
  }
  topBackBtn.addEventListener("click", backToPreviousMenu);
  bottomPrevBtn.addEventListener("click", backToPreviousMenu);
  bottomBackBtn.addEventListener("click", sendToMainMenu);

  refreshSeriesTexts();
  updateBottomPrevState();
})();
