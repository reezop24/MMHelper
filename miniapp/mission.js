(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var content = window.MMHELPER_CONTENT || {};
  var params = new URLSearchParams(window.location.search);

  function formatUsd(value) {
    return Number(value || 0).toFixed(2);
  }

  function capitalize(value) {
    if (!value) return "-";
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  var name = params.get("name") || "-";
  var currentBalance = Number(params.get("current_balance_usd") || 0);
  var savedDate = params.get("saved_date") || "-";
  var tabungStartDate = params.get("tabung_start_date") || "-";
  var missionStatus = params.get("mission_status") || "-";
  var targetBalance = Number(params.get("target_balance_usd") || 0);
  var targetDays = Number(params.get("target_days") || 0);
  var targetLabel = params.get("target_label") || (targetDays ? String(targetDays) + " hari" : "-");
  var tabungBalance = Number(params.get("tabung_balance_usd") || 0);

  var missionActive = (params.get("mission_active") || "0") === "1";
  var missionMode = (params.get("mission_mode") || "").toLowerCase();
  var missionStartedDate = params.get("mission_started_date") || "-";

  var canOpen = targetBalance > 0 && tabungBalance >= 10;

  document.getElementById("summaryName").textContent = name;
  document.getElementById("summaryBalance").textContent = formatUsd(currentBalance);
  document.getElementById("summaryDate").textContent = savedDate;
  document.getElementById("summaryTabungStartDate").textContent = tabungStartDate;
  document.getElementById("summaryMissionStatus").textContent = missionStatus;

  var lockedCard = document.getElementById("lockedCard");
  var beforeLayer = document.getElementById("beforeStartLayer");
  var runningLayer = document.getElementById("runningLayer");
  var topBackBtn = document.getElementById("topBackBtn");
  var backToMenuBtn = document.getElementById("backToMenuBtn");
  var resetMissionBtn = document.getElementById("resetMissionBtn");
  var runningStatus = document.getElementById("runningStatus");

  var normalModeBtn = document.getElementById("normalModeBtn");
  var advancedModeBtn = document.getElementById("advancedModeBtn");
  var normalModePanel = document.getElementById("normalModePanel");
  var advancedModePanel = document.getElementById("advancedModePanel");
  var startMissionBtn = document.getElementById("startMissionBtn");
  var beforeStatus = document.getElementById("beforeStatus");
  var beforeBackToMenuBtn = document.getElementById("beforeBackToMenuBtn");

  var level1Toggle = document.getElementById("level1Toggle");
  var level2Toggle = document.getElementById("level2Toggle");
  var level3Toggle = document.getElementById("level3Toggle");
  var level1Panel = document.getElementById("level1Panel");
  var level2Panel = document.getElementById("level2Panel");
  var level3Panel = document.getElementById("level3Panel");

  var selectedMode = "normal";

  function setOpenLevel(level) {
    level1Panel.classList.toggle("hidden", level !== 1);
    level2Panel.classList.toggle("hidden", level !== 2);
    level3Panel.classList.toggle("hidden", level !== 3);
  }

  function setMode(mode) {
    selectedMode = mode;
    normalModeBtn.classList.toggle("active", mode === "normal");
    advancedModeBtn.classList.toggle("active", mode === "advanced");

    normalModePanel.classList.toggle("hidden", mode !== "normal");
    advancedModePanel.classList.toggle("hidden", mode !== "advanced");

    if (mode === "normal") {
      startMissionBtn.textContent = content.missionStartNormalBtn || "🚀 Start Mission (Normal)";
    } else {
      startMissionBtn.textContent = content.missionStartAdvancedBtn || "🚀 Start Mission (Advanced)";
    }
  }

  function renderLevelContent() {
    var items = content.missionLevel1Items || [];
    level1Panel.innerHTML = items
      .map(function (item) {
        return [
          '<div class="mission-item">',
          '<p class="mission-item-title">' + (item.title || "") + "</p>",
          '<p class="mission-item-desc">' + (item.desc || "") + "</p>",
          "</div>"
        ].join("");
      })
      .join("");

    level2Panel.innerHTML = '<p class="mission-item-desc">' + (content.missionLevelComingSoonText || "Akan datang") + "</p>";
    level3Panel.innerHTML = '<p class="mission-item-desc">' + (content.missionLevelComingSoonText || "Akan datang") + "</p>";

    level1Toggle.textContent = content.missionLevel1Title || "Level 1";
    level2Toggle.textContent = content.missionLevel2Title || "Level 2 (Akan Datang)";
    level3Toggle.textContent = content.missionLevel3Title || "Level 3 (Akan Datang)";
  }

  function renderBeforeStart() {
    beforeLayer.classList.remove("hidden");
    document.getElementById("beforeIntro").textContent = content.missionBeforeStartIntro || "";
    document.getElementById("advancedComingSoon").textContent = content.missionLevelComingSoonText || "Akan datang";

    normalModeBtn.textContent = content.missionNormalLabel || "Normal Mode";
    advancedModeBtn.textContent = content.missionAdvancedLabel || "Advanced Mode";

    renderLevelContent();
    setMode("normal");
    setOpenLevel(1);
  }

  function renderRunning() {
    runningLayer.classList.remove("hidden");
    document.getElementById("runningBadge").textContent = content.missionRunningBadge || "Mission Active";
    document.getElementById("runningIntro").textContent = content.missionRunningIntro || "";
    document.getElementById("runningMode").textContent = capitalize(missionMode);
    document.getElementById("runningStartDate").textContent = missionStartedDate;
    document.getElementById("runningTargetBalance").textContent = formatUsd(targetBalance);
    document.getElementById("runningTargetLabel").textContent = targetLabel || "-";
    document.getElementById("runningTabungBalance").textContent = formatUsd(tabungBalance);
    backToMenuBtn.textContent = content.missionBackToMenuBtn || "⬅️ Back to Menu";
  }

  function sendBackToProjectGrow(statusEl) {
    var payload = { type: "project_grow_back_to_menu" };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke Project Grow.";
  }

  topBackBtn.textContent = content.missionBackToMenuBtn || "⬅️ Back to Project Grow";
  topBackBtn.addEventListener("click", function () {
    if (missionActive) {
      sendBackToProjectGrow(runningStatus);
      return;
    }
    sendBackToProjectGrow(beforeStatus);
  });

  if (!canOpen) {
    lockedCard.classList.remove("hidden");
    document.getElementById("lockedText").textContent = content.missionLockedText || "Mission locked.";
    return;
  }

  if (missionActive) {
    renderRunning();

    backToMenuBtn.addEventListener("click", function () {
      sendBackToProjectGrow(runningStatus);
    });

    resetMissionBtn.addEventListener("click", function () {
      var confirmed = window.confirm(
        content.missionResetConfirmText || "Reset mission sekarang? Progress mission semasa akan dipadam."
      );
      if (!confirmed) {
        runningStatus.textContent = content.missionResetCancelledText || "Reset mission dibatalkan.";
        return;
      }

      var payload = {
        type: "project_grow_mission_reset",
        confirm_reset: 1
      };

      if (tg) {
        tg.sendData(JSON.stringify(payload));
        tg.close();
        return;
      }

      runningStatus.textContent = content.missionResetPreviewText || "Preview mode: reset mission hanya berfungsi bila buka dari Telegram.";
    });

    return;
  }

  renderBeforeStart();

  beforeBackToMenuBtn.textContent = content.missionBackToMenuBtn || "⬅️ Back to Project Grow";
  beforeBackToMenuBtn.addEventListener("click", function () {
    sendBackToProjectGrow(beforeStatus);
  });

  normalModeBtn.addEventListener("click", function () {
    setMode("normal");
    beforeStatus.textContent = "";
  });

  advancedModeBtn.addEventListener("click", function () {
    setMode("advanced");
    beforeStatus.textContent = "";
  });

  level1Toggle.addEventListener("click", function () { setOpenLevel(1); });
  level2Toggle.addEventListener("click", function () { setOpenLevel(2); });
  level3Toggle.addEventListener("click", function () { setOpenLevel(3); });

  startMissionBtn.addEventListener("click", function () {
    var payload = {
      type: "project_grow_mission_start",
      mode: selectedMode
    };

    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }

    beforeStatus.textContent = "Preview mode: buka dari Telegram untuk start mission.";
  });
})();
