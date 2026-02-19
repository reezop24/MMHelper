(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var tabs = [
    { btn: document.getElementById("tabBasic"), panel: document.getElementById("panelBasic") },
    { btn: document.getElementById("tabIntermediate"), panel: document.getElementById("panelIntermediate") },
    { btn: document.getElementById("tabAdvanced"), panel: document.getElementById("panelAdvanced") },
  ];
  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var topicPickButtons = document.querySelectorAll(".js-topic-pick");

  function activate(index) {
    tabs.forEach(function (t, i) {
      var active = i === index;
      t.btn.classList.toggle("active", active);
      t.panel.classList.toggle("active", active);
    });
  }

  tabs.forEach(function (t, i) {
    t.btn.addEventListener("click", function () {
      activate(i);
    });
  });

  function backToMainMenu() {
    var payload = { type: "video_bot_back_to_main_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    if (statusEl) {
      statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke menu utama.";
    }
  }

  if (topBackBtn) {
    topBackBtn.addEventListener("click", backToMainMenu);
  }
  if (bottomBackBtn) {
    bottomBackBtn.addEventListener("click", backToMainMenu);
  }

  topicPickButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var level = btn.getAttribute("data-level") || "";
      var topic = btn.getAttribute("data-topic") || "";
      var title = btn.getAttribute("data-title") || "";
      var payload = {
        type: "video_topic_pick",
        level: level,
        topic: topic,
        title: title
      };
      if (tg) {
        tg.sendData(JSON.stringify(payload));
        if (statusEl) {
          statusEl.textContent = "Topik dipilih. Bot akan proses video untuk anda.";
        }
        return;
      }
      if (statusEl) {
        statusEl.textContent = "Preview mode: " + level + " topik " + topic + " - " + title;
      }
    });
  });
})();
