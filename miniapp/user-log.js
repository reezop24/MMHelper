(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var summaryText = document.getElementById("summaryText");
  var logList = document.getElementById("logList");
  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");

  function safeText(value, fallback) {
    var text = (value || "").toString().trim();
    return text || fallback;
  }

  function parseUsersPayload() {
    var raw = params.get("users") || "[]";
    try {
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function renderRow(label, value) {
    var p = document.createElement("p");
    p.innerHTML = "<strong>" + label + ":</strong> " + value;
    return p;
  }

  function renderUsers(users) {
    logList.innerHTML = "";

    if (!users.length) {
      summaryText.innerHTML = "<em>Tiada user berdaftar lagi.</em>";
      return;
    }

    summaryText.innerHTML = "<em>Jumlah user berdaftar: " + users.length + "</em>";

    users.forEach(function (user) {
      var card = document.createElement("article");
      card.className = "log-card";

      card.appendChild(renderRow("Nama", safeText(user.name, "-")));
      card.appendChild(renderRow("User ID", safeText(user.user_id, "-")));
      card.appendChild(renderRow("Telegram", safeText(user.telegram_username, "-")));
      card.appendChild(renderRow("Daftar", safeText(user.registered_at, "-")));

      logList.appendChild(card);
    });
  }

  function backToAdminPanel() {
    var payload = { type: "admin_panel_back_to_menu" };

    if (tg) {
      try {
        tg.sendData(JSON.stringify(payload));
      } catch (err) {
        // no-op
      }
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Admin Panel.";
  }

  topBackBtn.addEventListener("click", backToAdminPanel);
  bottomBackBtn.addEventListener("click", backToAdminPanel);

  renderUsers(parseUsersPayload());
})();
