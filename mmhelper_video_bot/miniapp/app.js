(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var BASIC_TOPICS = [
    {
      topic: 1,
      title: "Apa Itu Trading",
      nextOnly: false,
      subtopics: [
        "Bezakan trading, investing, speculation",
        "Apa yang sebenarnya trader buat",
        "Mitos & salah faham"
      ]
    },
    {
      topic: 2,
      title: "Bagaimana Harga Bergerak",
      nextOnly: false,
      subtopics: [
        "Siapa pemain pasaran",
        "Siapa yang menggerakkan harga",
        "Konsep pergerakan harga",
        "Apa itu liquidity"
      ]
    },
    {
      topic: 3,
      title: "Broker",
      nextOnly: false,
      subtopics: [
        "Pengenalan",
        "Market maker vs ECN",
        "Spread, swap, leverage",
        "Risiko leverage tinggi"
      ]
    },
    {
      topic: 4,
      title: "Platform",
      nextOnly: false,
      subtopics: [
        "MT4/MT5",
        "TradingView",
        "Order type",
        "Cara membaca chart (platform overview)"
      ]
    },
    {
      topic: 5,
      title: "Psychology (Level 1)",
      nextOnly: false,
      subtopics: [
        "Kenapa beginner selalu loss",
        "Emotional cycle dalam trading",
        "Apa maksud disiplin dan sabar"
      ]
    },
    {
      topic: 6,
      title: "Market Structure (Level 1)",
      nextOnly: false,
      subtopics: [
        "Trend",
        "L, H, HH, HL, LH & LL",
        "Candlestick (Level 1)"
      ]
    },
    {
      topic: 7,
      title: "Support & Resistant (Level 1)",
      nextOnly: false,
      subtopics: [
        "Pengenalan",
        "Horizontal & Dynamic",
        "Kenalpasti SNR yang kuat",
        "Fake breakout & kenapa ia berlaku"
      ]
    },
    {
      topic: 8,
      title: "Trendline (Level 1)",
      nextOnly: false,
      subtopics: [
        "Apa itu trendline",
        "Bila trendline valid dan tidak valid",
        "Common mistake beginner selalu buat"
      ]
    },
    {
      topic: 9,
      title: "Volume",
      nextOnly: true,
      subtopics: [
        "Participant",
        "Volume spike"
      ]
    },
    {
      topic: 10,
      title: "Risk Management (Level 1)",
      nextOnly: true,
      subtopics: [
        "Apa itu SL & TP",
        "Kenapa SL penting",
        "1-2% rule",
        "Kenapa account blow berlaku"
      ]
    },
    {
      topic: 11,
      title: "Candlestick Pattern",
      nextOnly: true,
      subtopics: [
        "Engulfing",
        "Pin bar candle",
        "Inside bar candle"
      ]
    },
    {
      topic: 12,
      title: "Chart Pattern",
      nextOnly: true,
      subtopics: [
        "Double top / bottom",
        "Head & Shoulder",
        "Triangle"
      ]
    },
    {
      topic: 13,
      title: "Liquidity (Level 1)",
      nextOnly: true,
      subtopics: [
        "Pengenalan",
        "Liquidity grab",
        "Liquidity sweep",
        "Pentingnya memahami liquidity grab / sweep dan mengapa ia berlaku"
      ]
    },
    {
      topic: 14,
      title: "BOS & CHoCH (Level 1)",
      nextOnly: true,
      subtopics: [
        "Pengenalan",
        "Cara membezakan BOS & CHoCH"
      ]
    },
    {
      topic: 15,
      title: "FVG & Imbalance (Level 1)",
      nextOnly: true,
      subtopics: [
        "Pengenalan",
        "Mengapa zon FVG & Imbalance sangat penting"
      ]
    },
    {
      topic: 16,
      title: "Orderblock (Level 1)",
      nextOnly: true,
      subtopics: [
        "Pengenalan",
        "Mengapa OB zon terhasil dan apa peranan zon OB"
      ]
    },
    {
      topic: 17,
      title: "Trading Plan (Level 1)",
      nextOnly: true,
      subtopics: [
        "Setup",
        "Entry rules",
        "Exit rules",
        "Journaling"
      ]
    },
    {
      topic: 18,
      title: "Psychology (Level 2)",
      nextOnly: true,
      subtopics: [
        "Overtrading",
        "FOMO",
        "Revenge trade",
        "Bagaimana kekalkan disiplin"
      ]
    },
    {
      topic: 19,
      title: "Tools & Management",
      nextOnly: true,
      subtopics: [
        "Timeframe mapping",
        "Multi-timeframe mapping",
        "Intraday & swing planning",
        "Trading session"
      ]
    }
  ];

  var tabs = [
    { btn: document.getElementById("tabBasic"), panel: document.getElementById("panelBasic") },
    { btn: document.getElementById("tabIntermediate"), panel: document.getElementById("panelIntermediate") },
    { btn: document.getElementById("tabAdvanced"), panel: document.getElementById("panelAdvanced") }
  ];
  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var basicTopicList = document.getElementById("basicTopicList");
  var evideoCard = document.getElementById("evideoCard");

  function activate(index) {
    var levelClass = "level-basic";
    if (index === 1) levelClass = "level-intermediate";
    if (index === 2) levelClass = "level-advanced";
    if (evideoCard) {
      evideoCard.classList.remove("level-basic", "level-intermediate", "level-advanced");
      evideoCard.classList.add(levelClass);
    }
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

  function renderBasicTopics() {
    if (!basicTopicList) return;
    basicTopicList.innerHTML = "";

    BASIC_TOPICS.forEach(function (row) {
      var card = document.createElement("div");
      card.className = "topic-card";

      var title = document.createElement("p");
      title.className = "topic-title";
      title.textContent = "Topik " + row.topic + ": " + row.title;
      card.appendChild(title);

      var ul = document.createElement("ul");
      row.subtopics.forEach(function (sub) {
        var li = document.createElement("li");
        li.textContent = sub;
        ul.appendChild(li);
      });
      card.appendChild(ul);

      var actions = document.createElement("div");
      actions.className = "topic-actions";

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "topic-select-btn";
      btn.textContent = "Pilih Topik Ini";
      btn.setAttribute("data-level", "basic");
      btn.setAttribute("data-topic", String(row.topic));
      btn.setAttribute("data-title", row.title);

      if (row.nextOnly) {
        var badge = document.createElement("img");
        badge.src = "nextexc.png";
        badge.alt = "NEXT only";
        badge.className = "next-badge";
        btn.appendChild(badge);
      }

      btn.addEventListener("click", function () {
        sendTopicPickPayload("basic", String(row.topic), row.title);
      });

      actions.appendChild(btn);
      card.appendChild(actions);
      basicTopicList.appendChild(card);
    });
  }

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

  function sendTopicPickPayload(level, topic, title) {
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
  }

  if (topBackBtn) {
    topBackBtn.addEventListener("click", backToMainMenu);
  }
  if (bottomBackBtn) {
    bottomBackBtn.addEventListener("click", backToMainMenu);
  }

  renderBasicTopics();
  activate(0);
})();
