(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  function qs(name) {
    try {
      return new URLSearchParams(window.location.search).get(name) || "";
    } catch (err) {
      return "";
    }
  }

  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var watchBtn = document.getElementById("watchBtn");
  var registerBtn = document.getElementById("registerBtn");
  var statusEl = document.getElementById("status");
  var adminBotUrl = qs("admin_bot_url") || "https://t.me/ReezoAdmin_Bot";
  var evideoBotUrl = qs("evideo_bot_url") || "https://t.me/NEXTeVideo_bot";

  function backToMainMenu() {
    var payload = { type: "risk_calculator_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    if (statusEl) {
      statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke menu.";
    }
  }

  function openAdminBot() {
    if (!adminBotUrl || adminBotUrl.indexOf("https://t.me/") !== 0) {
      if (statusEl) {
        statusEl.textContent = "Link bot admin belum sah. Sila semak tetapan.";
      }
      return;
    }
    if (tg && typeof tg.openTelegramLink === "function") {
      tg.openTelegramLink(adminBotUrl);
      return;
    }
    window.open(adminBotUrl, "_blank", "noopener");
  }

  function openEvideoBot() {
    if (!evideoBotUrl || evideoBotUrl.indexOf("https://t.me/") !== 0) {
      if (statusEl) {
        statusEl.textContent = "Link eVideo bot belum sah. Sila semak tetapan.";
      }
      return;
    }
    if (tg && typeof tg.openTelegramLink === "function") {
      tg.openTelegramLink(evideoBotUrl);
      return;
    }
    window.open(evideoBotUrl, "_blank", "noopener");
  }

  if (topBackBtn) topBackBtn.addEventListener("click", backToMainMenu);
  if (bottomBackBtn) bottomBackBtn.addEventListener("click", backToMainMenu);
  if (watchBtn) watchBtn.addEventListener("click", openEvideoBot);
  if (registerBtn) registerBtn.addEventListener("click", openAdminBot);
})();
