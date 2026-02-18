(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var summaryName = document.getElementById("summaryName");
  var summaryDate = document.getElementById("summaryDate");
  var targetUserEl = document.getElementById("targetUserId");
  var overrideDateEl = document.getElementById("overrideDate");
  var currentStatusEl = document.getElementById("currentStatus");
  var formStatusEl = document.getElementById("formStatus");

  summaryName.textContent = params.get("name") || "-";
  summaryDate.textContent = params.get("saved_date") || "-";

  var defaultSelected = String(params.get("selected_user_id") || "").trim();
  var currentEnabled = String(params.get("current_enabled") || "0") === "1";
  var currentOverrideDate = String(params.get("current_override_date") || "").trim();
  var currentUpdatedAt = String(params.get("current_updated_at") || "").trim();

  if (defaultSelected) {
    targetUserEl.value = defaultSelected;
  }

  function refreshStatus() {
    var uid = String(targetUserEl.value || "").trim();
    if (uid && defaultSelected && uid === defaultSelected && currentEnabled && currentOverrideDate) {
      currentStatusEl.textContent = "ACTIVE on " + currentOverrideDate + (currentUpdatedAt ? (" | updated " + currentUpdatedAt) : "");
      overrideDateEl.value = currentOverrideDate;
      return;
    }
    if (uid && defaultSelected && uid === defaultSelected) {
      currentStatusEl.textContent = "INACTIVE";
    } else {
      currentStatusEl.textContent = "Status tak dimuatkan untuk user ini (akan disahkan selepas submit).";
    }
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

  targetUserEl.addEventListener("input", function () {
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
      formStatusEl.textContent = "Sila isi target user ID.";
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
      formStatusEl.textContent = "Sila isi target user ID.";
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
      formStatusEl.textContent = "Sila isi target user ID.";
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
