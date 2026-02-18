(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var summaryName = document.getElementById("summaryName");
  var summaryDate = document.getElementById("summaryDate");
  var targetUserEl = document.getElementById("targetUser");
  var overrideDateEl = document.getElementById("overrideDate");
  var currentStatusEl = document.getElementById("currentStatus");
  var formStatusEl = document.getElementById("formStatus");

  summaryName.textContent = params.get("name") || "-";
  summaryDate.textContent = params.get("saved_date") || "-";

  function parseJsonParam(name, fallback) {
    var raw = params.get(name);
    if (!raw) return fallback;
    try {
      var parsed = JSON.parse(raw);
      return parsed;
    } catch (err) {
      return fallback;
    }
  }

  var users = parseJsonParam("users", []);
  var overrides = parseJsonParam("overrides", {});
  var defaultSelected = String(params.get("selected_user_id") || "").trim();

  function normalizeUsers(rows) {
    if (!Array.isArray(rows)) return [];
    return rows
      .filter(function (row) { return row && typeof row === "object"; })
      .map(function (row) {
        var userId = String(row.user_id || "").trim();
        if (!userId) return null;
        var name = String(row.name || "User " + userId).trim();
        var username = String(row.telegram_username || "").trim();
        var label = username && username !== "-" ? (name + " (" + username + ")") : name;
        return { user_id: userId, label: label };
      })
      .filter(Boolean);
  }

  var userOptions = normalizeUsers(users);
  if (userOptions.length === 0 && defaultSelected) {
    userOptions.push({ user_id: defaultSelected, label: "User " + defaultSelected });
  }

  userOptions.forEach(function (item) {
    var option = document.createElement("option");
    option.value = item.user_id;
    option.textContent = item.label + " [" + item.user_id + "]";
    targetUserEl.appendChild(option);
  });

  if (defaultSelected) {
    targetUserEl.value = defaultSelected;
  }
  if (!targetUserEl.value && userOptions.length > 0) {
    targetUserEl.value = userOptions[0].user_id;
  }

  function overrideRowForUser(userId) {
    var row = overrides && typeof overrides === "object" ? overrides[String(userId)] : null;
    if (!row || typeof row !== "object") {
      return { enabled: false, override_date: "" };
    }
    return {
      enabled: !!row.enabled,
      override_date: String(row.override_date || "").trim(),
      updated_by: String(row.updated_by || "").trim(),
      updated_at: String(row.updated_at || "").trim()
    };
  }

  function refreshStatus() {
    var uid = String(targetUserEl.value || "").trim();
    var row = overrideRowForUser(uid);
    if (row.enabled && row.override_date) {
      currentStatusEl.textContent = "ACTIVE on " + row.override_date + (row.updated_at ? (" | updated " + row.updated_at) : "");
      overrideDateEl.value = row.override_date;
      return;
    }
    currentStatusEl.textContent = "INACTIVE";
    if (!overrideDateEl.value) {
      overrideDateEl.value = "";
    }
  }

  function backToAdmin() {
    var payload = { type: "admin_panel_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    formStatusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Admin Panel.";
  }

  document.getElementById("topBackBtn").addEventListener("click", backToAdmin);
  document.getElementById("backToAdminBtn").addEventListener("click", backToAdmin);

  targetUserEl.addEventListener("change", function () {
    formStatusEl.textContent = "";
    overrideDateEl.value = "";
    refreshStatus();
  });

  function submitPayload(payload) {
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    formStatusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  }

  document.getElementById("overrideForm").addEventListener("submit", function (event) {
    event.preventDefault();
    var targetUserId = String(targetUserEl.value || "").trim();
    var overrideDate = String(overrideDateEl.value || "").trim();
    if (!targetUserId) {
      formStatusEl.textContent = "Sila pilih target account.";
      return;
    }
    if (!overrideDate) {
      formStatusEl.textContent = "Sila pilih tarikh override.";
      return;
    }
    submitPayload({
      type: "date_override_save",
      action: "set",
      target_user_id: targetUserId,
      override_date: overrideDate
    });
  });

  document.getElementById("disableBtn").addEventListener("click", function () {
    var targetUserId = String(targetUserEl.value || "").trim();
    if (!targetUserId) {
      formStatusEl.textContent = "Sila pilih target account.";
      return;
    }
    submitPayload({
      type: "date_override_save",
      action: "disable",
      target_user_id: targetUserId
    });
  });

  document.getElementById("clearBtn").addEventListener("click", function () {
    var targetUserId = String(targetUserEl.value || "").trim();
    if (!targetUserId) {
      formStatusEl.textContent = "Sila pilih target account.";
      return;
    }
    submitPayload({
      type: "date_override_save",
      action: "clear",
      target_user_id: targetUserId
    });
  });

  refreshStatus();
})();
