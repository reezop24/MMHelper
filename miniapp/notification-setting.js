(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var summaryName = document.getElementById("summaryName");
  var summaryDate = document.getElementById("summaryDate");
  var statusEl = document.getElementById("formStatus");

  summaryName.textContent = params.get("name") || "-";
  summaryDate.textContent = params.get("saved_date") || "-";

  var dailyPresetOptions = [
    "Bro, jangan lupa update transaksi hari ni. 1 minit je, bagi rekod sentiasa clear.",
    "Check-in sekejap: kau dah update MM Helper untuk transaksi hari ni ke belum?",
    "Reminder kawan: before habis hari, update dulu transaksi supaya kiraan esok tak lari."
  ];

  var maintenancePresetOptions = [
    "Heads up team, MM Helper akan masuk maintenance sementara. Data kekal selamat, kita sambung balik lepas siap.",
    "Notis maintenance: ada kerja upgrade sistem sekejap. Lepas siap nanti flow akan jadi lebih smooth.",
    "Update penting: server maintenance dijalankan ikut jadual di bawah. Terima kasih sebab sabar tunggu."
  ];

  function fillPresetOptions(selectEl, options) {
    options.forEach(function (text, index) {
      var option = document.createElement("option");
      option.value = text;
      option.textContent = "Preset " + (index + 1);
      selectEl.appendChild(option);
    });
  }

  var dailyPresetSelect = document.getElementById("dailyPresetMessage");
  var maintenancePresetSelect = document.getElementById("maintenancePresetMessage");
  fillPresetOptions(dailyPresetSelect, dailyPresetOptions);
  fillPresetOptions(maintenancePresetSelect, maintenancePresetOptions);

  var dailyTimesPerDay = document.getElementById("dailyTimesPerDay");
  var dailyTimesContainer = document.getElementById("dailyTimesContainer");

  function defaultTimeByIndex(idx) {
    var defaults = ["09:00", "13:00", "17:00", "20:00", "22:00", "23:30"];
    return defaults[idx] || "09:00";
  }

  function renderDailyTimePickers() {
    var count = Number(dailyTimesPerDay.value || 1);
    if (Number.isNaN(count) || count < 1) count = 1;
    if (count > 6) count = 6;

    var existing = Array.prototype.slice.call(dailyTimesContainer.querySelectorAll("input"));
    var oldValues = existing.map(function (el) { return (el.value || "").trim(); });

    dailyTimesContainer.innerHTML = "";
    for (var i = 0; i < count; i += 1) {
      var wrap = document.createElement("div");
      wrap.className = "field";

      var label = document.createElement("label");
      label.textContent = "Masa #" + (i + 1);
      label.setAttribute("for", "dailyTime" + i);

      var input = document.createElement("input");
      input.type = "time";
      input.id = "dailyTime" + i;
      input.value = oldValues[i] || defaultTimeByIndex(i);

      wrap.appendChild(label);
      wrap.appendChild(input);
      dailyTimesContainer.appendChild(wrap);
    }
  }

  dailyTimesPerDay.addEventListener("change", function () {
    renderDailyTimePickers();
    statusEl.textContent = "";
  });
  renderDailyTimePickers();

  function wireToggle(toggleId, fieldsId) {
    var toggleEl = document.getElementById(toggleId);
    var fieldsEl = document.getElementById(fieldsId);
    function sync() {
      fieldsEl.classList.toggle("hidden", !toggleEl.checked);
    }
    toggleEl.addEventListener("change", function () {
      sync();
      statusEl.textContent = "";
    });
    sync();
  }

  wireToggle("manualEnabled", "manualFields");
  wireToggle("dailyEnabled", "dailyFields");
  wireToggle("reportEnabled", "reportFields");
  wireToggle("maintenanceEnabled", "maintenanceFields");

  function backToAdmin() {
    var payload = { type: "admin_panel_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Admin Panel.";
  }

  document.getElementById("topBackBtn").addEventListener("click", backToAdmin);
  document.getElementById("backToAdminBtn").addEventListener("click", backToAdmin);

  function getTimesFromUi() {
    return Array.prototype.slice.call(dailyTimesContainer.querySelectorAll("input")).map(function (el) {
      return (el.value || "").trim();
    });
  }

  document.getElementById("notificationForm").addEventListener("submit", function (event) {
    event.preventDefault();

    var manualEnabled = document.getElementById("manualEnabled").checked;
    var dailyEnabled = document.getElementById("dailyEnabled").checked;
    var reportEnabled = document.getElementById("reportEnabled").checked;
    var maintenanceEnabled = document.getElementById("maintenanceEnabled").checked;

    var manualDate = (document.getElementById("manualDate").value || "").trim();
    var manualTime = (document.getElementById("manualTime").value || "").trim();
    var manualMessage = (document.getElementById("manualMessage").value || "").trim();

    var dailyTimes = getTimesFromUi();
    var timesPerDay = Number(dailyTimesPerDay.value || 1);
    var dailyPresetMessage = dailyPresetSelect.value || dailyPresetOptions[0];

    var weeklyReportDate = (document.getElementById("weeklyReportDate").value || "").trim();
    var monthlyReportDate = (document.getElementById("monthlyReportDate").value || "").trim();

    var maintenanceStartDate = (document.getElementById("maintenanceStartDate").value || "").trim();
    var maintenanceStartTime = (document.getElementById("maintenanceStartTime").value || "").trim();
    var maintenanceEndDate = (document.getElementById("maintenanceEndDate").value || "").trim();
    var maintenanceEndTime = (document.getElementById("maintenanceEndTime").value || "").trim();
    var maintenanceMessage = maintenancePresetSelect.value || maintenancePresetOptions[0];

    if (manualEnabled && (!manualDate || !manualTime || !manualMessage)) {
      statusEl.textContent = "Manual Push perlukan tarikh, masa, dan mesej.";
      return;
    }

    if (dailyEnabled && dailyTimes.some(function (t) { return !t; })) {
      statusEl.textContent = "Sila lengkapkan semua masa Daily Notification.";
      return;
    }

    if (reportEnabled && (!weeklyReportDate || !monthlyReportDate)) {
      statusEl.textContent = "Sila isi tarikh weekly dan monthly report.";
      return;
    }

    if (maintenanceEnabled && (!maintenanceStartDate || !maintenanceStartTime || !maintenanceEndDate || !maintenanceEndTime)) {
      statusEl.textContent = "Sila lengkapkan jadual mula dan tamat maintenance.";
      return;
    }

    var payload = {
      type: "notification_settings_save",
      manual_push: {
        enabled: manualEnabled,
        date: manualDate,
        time: manualTime,
        message: manualMessage
      },
      daily_notification: {
        enabled: dailyEnabled,
        times_per_day: timesPerDay,
        times: dailyTimes,
        preset_message: dailyPresetMessage
      },
      report_notification: {
        enabled: reportEnabled,
        weekly_remind_date: weeklyReportDate,
        monthly_remind_date: monthlyReportDate
      },
      maintenance_notification: {
        enabled: maintenanceEnabled,
        start_date: maintenanceStartDate,
        start_time: maintenanceStartTime,
        end_date: maintenanceEndDate,
        end_time: maintenanceEndTime,
        message: maintenanceMessage
      }
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk submit.";
  });
})();
