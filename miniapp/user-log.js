(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var monthTabsEl = document.getElementById("monthTabs");
  var summaryText = document.getElementById("summaryText");
  var logList = document.getElementById("logList");
  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");

  function safeText(value, fallback) {
    var text = (value || "").toString().trim();
    return text || fallback;
  }

  function parsePayload() {
    var raw = params.get("data") || "";
    if (!raw) {
      raw = params.get("users") || "[]";
      try {
        var legacyUsers = JSON.parse(raw);
        return {
          logsByMonth: { all: Array.isArray(legacyUsers) ? legacyUsers : [] },
          monthOrder: ["all"],
          selectedMonth: "all",
        };
      } catch (errLegacy) {
        return { logsByMonth: {}, monthOrder: [], selectedMonth: "" };
      }
    }

    try {
      var parsed = JSON.parse(raw);
      var logsByMonth = {};
      if (parsed && typeof parsed === "object" && parsed.m && typeof parsed.m === "object") {
        Object.keys(parsed.m).forEach(function (monthKey) {
          var monthRows = parsed.m[monthKey];
          if (!Array.isArray(monthRows)) {
            logsByMonth[monthKey] = [];
            return;
          }
          logsByMonth[monthKey] = monthRows.map(function (row) {
            if (!Array.isArray(row)) {
              return { name: "-", user_id: "-", telegram_username: "-", registered_at: "-" };
            }
            return {
              name: safeText(row[0], "-"),
              user_id: safeText(row[1], "-"),
              telegram_username: safeText(row[2], "-"),
              registered_at: safeText(row[3], "-"),
            };
          });
        });
      } else if (parsed && typeof parsed === "object" && parsed.logs_by_month && typeof parsed.logs_by_month === "object") {
        logsByMonth = parsed.logs_by_month;
      }
      var monthOrder = Object.keys(logsByMonth).sort().reverse();
      return {
        logsByMonth: logsByMonth,
        monthOrder: monthOrder,
        selectedMonth: monthOrder[0] || "",
      };
    } catch (err) {
      return { logsByMonth: {}, monthOrder: [], selectedMonth: "" };
    }
  }

  function renderRow(label, value) {
    var p = document.createElement("p");
    p.innerHTML = "<strong>" + label + ":</strong> " + value;
    return p;
  }

  function renderMonths(state) {
    monthTabsEl.innerHTML = "";
    state.monthOrder.forEach(function (monthKey) {
      var monthUsers = state.logsByMonth[monthKey];
      var count = Array.isArray(monthUsers) ? monthUsers.length : 0;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "month-tab" + (state.selectedMonth === monthKey ? " active" : "");
      btn.textContent = monthKey + " (" + count + ")";
      btn.addEventListener("click", function () {
        state.selectedMonth = monthKey;
        renderMonths(state);
        renderUsersForMonth(state);
      });
      monthTabsEl.appendChild(btn);
    });
  }

  function renderUsersForMonth(state) {
    logList.innerHTML = "";
    if (!state.selectedMonth) {
      summaryText.innerHTML = "<em>Tiada data bulan pendaftaran.</em>";
      return;
    }

    var users = state.logsByMonth[state.selectedMonth];
    if (!Array.isArray(users) || users.length === 0) {
      summaryText.innerHTML = "<em>Bulan " + state.selectedMonth + " tiada user berdaftar.</em>";
      return;
    }

    summaryText.innerHTML = "<em>Bulan " + state.selectedMonth + ": " + users.length + " user berdaftar</em>";

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

  var state = parsePayload();
  renderMonths(state);
  renderUsersForMonth(state);
})();
