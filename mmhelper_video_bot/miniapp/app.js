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

  var INTERMEDIATE_TOPICS = [
    {
      topic: 1,
      title: "Market Structure (Level 2)",
      subtopics: ["Internal vs external structure", "Complex pullback", "Trend correction & trend change", "Micro consolidation", "Multi BOS"]
    },
    {
      topic: 2,
      title: "Liquidity (Level 2)",
      subtopics: ["Jenis liquidity", "Kumpulan liquidity", "Bagaimana liquidity dicipta oleh pergerakan harga", "Liquidity tujuan entry vs liquidity tujuan target"]
    },
    {
      topic: 3,
      title: "Supply & Demand",
      subtopics: ["Perbezaan SNR dan SND", "Fresh & test zone", "Weak vs strong SND", "Kesilapan biasa marking SND", "Hubungan SND dengan liquidity"]
    },
    {
      topic: 4,
      title: "Memahami Breakout Behavior",
      subtopics: ["True breakout vs fake breakout", "Retest type A vs retest type B", "Breakout failure & perangkap", "Accumulation sebelum breakout (micro buildup)"]
    },
    {
      topic: 5,
      title: "Candlestick Advanced Behavior",
      subtopics: ["Candle volume behavior", "Impulsive candle vs corrective candle", "Wick sebagai liquidity grab", "Candle yang tidak mempunyai volume"]
    },
    {
      topic: 6,
      title: "Momentum & Correction",
      subtopics: ["Impulse > correction > impulse", "Deep & shallow retracement", "Trend melemah sebelum perubahan trend"]
    },
    {
      topic: 7,
      title: "Fibonacci",
      subtopics: ["Pengenalan", "Fibonacci retracement", "Fibonacci extension", "Fibo Dewa (quarter zone: discount vs premium)", "AB=CD (Level 1)"]
    },
    {
      topic: 8,
      title: "Support & Resistant (Level 2)",
      subtopics: ["Flip zone", "Strong zone vs weak zone", "Bagaimana zone dimakan", "Multi-timeframe SNR alignment"]
    },
    {
      topic: 9,
      title: "Trendline (Level 2)",
      subtopics: ["Trendline channel", "Break of trendline - momentum shift", "Trendline liquidity", "Bagaimana trendline digunakan sebagai perangkap"]
    },
    {
      topic: 10,
      title: "Entry Refinement",
      subtopics: ["Confirmation entry vs blind entry", "Entry pada pullback vs breakout entry", "Mencari POI kecil dalam zon besar", "Scaling in / out"]
    },
    {
      topic: 11,
      title: "Risk Management (Level 2)",
      subtopics: ["Position sizing calculation", "Fixed fractional vs fixed risk", "Risk to reward ratio & mapping", "SL placement based on structure"]
    },
    {
      topic: 12,
      title: "Trade Management (Level 1)",
      subtopics: ["Breakeven rules", "Partial TP strategy", "Trailing TP strategy", "Trailing TP based on structure", "Menguruskan drawdown"]
    },
    {
      topic: 13,
      title: "Multi-Timeframe Analysis",
      subtopics: ["Top-down mapping", "HTF bias vs LTF entry", "Cara elakkan perangkap LTF", "Bagaimana melihat big picture untuk entry kecil"]
    },
    {
      topic: 14,
      title: "Accumulation / Distribution (Level 1)",
      subtopics: ["Sideway", "Range high / low manipulation", "Fake breakout dua hala", "Re-entry dalam range"]
    },
    {
      topic: 15,
      title: "FVG & Imbalance (Level 2)",
      subtopics: ["Jenis FVG dan peranan FVG", "Clean vs messy imbalance", "Mengapa FVG diuji semula", "FVG + structure alignment", "FVG yang gagal"]
    },
    {
      topic: 16,
      title: "Orderblock (Level 2)",
      subtopics: ["Weak vs valid OB", "OB dalam trend vs reversal", "OB & BOS / CHoCH alignment", "Entry refinement di OB", "Orderblock to breakerblock"]
    },
    {
      topic: 17,
      title: "BOS & CHoCH (Level 2)",
      subtopics: ["Confirmation BOS valid & failed", "Early CHoCH vs valid CHoCH", "CHoCH dalam range vs trend", "Multi-timeframe BOS & CHoCH"]
    },
    {
      topic: 18,
      title: "Mitigation Candlestick",
      subtopics: ["Pengenalan", "Impulse vs mitigation", "Candle mitigation vs candle manipulation", "Peranan mitigation dalam OB dan FVG", "Kesilapan baca candle mitigation"]
    },
    {
      topic: 19,
      title: "Trading Plan (Level 2)",
      subtopics: ["Setup-specific rules (SOP)", "Entry model (A, B, C)", "Exit model", "Time-of-day filter", "Risk filter"]
    },
    {
      topic: 20,
      title: "Money Management (Level 1)",
      subtopics: ["Pembahagian risk per setup mengikut capital", "Dynamic equity based on trade risk"]
    },
    {
      topic: 21,
      title: "Psychology (Level 2)",
      subtopics: ["Menguruskan winning streak", "Menguruskan losing streak", "Mengenalpasti emotional trading pattern", "Kaedah membina disiplin"]
    }
  ];

  var ADVANCED_TOPICS = [
    {
      topic: 1,
      title: "Market Narrative & Context Building",
      subtopics: ["Siapa aktif sekarang", "Continuation day vs reversal day", "Expansion vs contraction day", "High probability vs chop day"]
    },
    {
      topic: 2,
      title: "Liquidity (Level 3)",
      subtopics: ["Session liquidity map", "External vs internal liquidity target", "Partial liquidity grab vs full sweep", "Liquidity run & exhaustion"]
    },
    {
      topic: 3,
      title: "Algorithmic Price Behavior",
      subtopics: ["Mengapa price menguji zon sama berulang kali", "Time based manipulation", "Engineered pullback vs real weakness"]
    },
    {
      topic: 4,
      title: "Entry Framework Overview",
      subtopics: ["Mengapa SOP diperlukan", "Environment filter sebelum guna SOP", "Bila tak boleh guna SOP"]
    },
    {
      topic: 5,
      title: "SOP1 - DBO (Double Breakout)",
      subtopics: ["Pengenalan konsep dan struktur wajib DBO", "Entry origin & invalidation", "DBO dalam DBO", "Risk profile"]
    },
    {
      topic: 6,
      title: "SOP2 - BtB (Break to Back)",
      subtopics: ["BtB logic sebagai perubahan karektor (CHoCH)", "BtB dalam range vs trend", "High possibility fake BtB yang menyebabkan trend bersambung"]
    },
    {
      topic: 7,
      title: "SOP3 - Pattern Failure Models",
      subtopics: ["Mengapa pattern gagal lebih padu dari pattern jadi", "DBO failed = fake DBO (fDBO)"]
    },
    {
      topic: 8,
      title: "SOP Alignment",
      subtopics: ["Confirmation berkembar", "DBO + BtB", "DBO > fDBO + BtB", "Trendline & Fibonacci alignment", "Multi-timeframe & structure alignment"]
    },
    {
      topic: 9,
      title: "Execution Timing & Precision",
      subtopics: ["Entry candle selection", "Micro POI dalam POI besar", "Spread & slippage awareness", "Killzone-based execution"]
    },
    {
      topic: 10,
      title: "Risk Management (Level 3) - Dynamic",
      subtopics: ["Risk scaling mengikut conviction", "Partial risk off", "Reduce exposure during chop", "News aware risk adjustment"]
    },
    {
      topic: 11,
      title: "Trade Management (Level 2) - Advanced",
      subtopics: ["Stack TP logic", "Structure trail vs time-based trail", "Reentry logic selepas TP1", "Position add-on rules"]
    },
    {
      topic: 12,
      title: "System Validation & Expectancy",
      subtopics: ["Winrate vs RR trade-off", "Setup expectancy", "Sample size logic", "Abaikan sementara SOP yang tak perform"]
    },
    {
      topic: 13,
      title: "Trading Plan (Level 2) - Journaling",
      subtopics: ["Tagging SOP & context", "Screenshot classification", "Error pattern detection", "Forward testing framework"]
    },
    {
      topic: 14,
      title: "Psychology (Level 3)",
      subtopics: ["Ego spike selepas win besar", "Trauma selepas loss streak", "Detachment from result", "Trading as execution, bukan emosi"]
    },
    {
      topic: 15,
      title: "Live Market Breakdown",
      subtopics: ["HTF > LTF breakdown lengkap", "Kenapa entry diambil", "Kenapa entry dielakkan", "Post-trade autopsy"]
    },
    {
      topic: 16,
      title: "Money Management (Level 2) - Business Model",
      subtopics: ["Pengurusan kewangan cekap", "Ledger in out capital", "Performance ledger based on profit loss"]
    },
    {
      topic: 17,
      title: "Bonus 1",
      subtopics: ["Multi-SOP - liquidity based"]
    },
    {
      topic: 18,
      title: "Bonus 2",
      subtopics: ["Market analysis - FiboExtension based"]
    },
    {
      topic: 19,
      title: "Bonus 3",
      subtopics: ["Scalping within range"]
    }
  ];

  function parseTopicMessageIdsFromUrl() {
    var fallback = { basic: {}, intermediate: {}, advanced: {} };
    try {
      var raw = new URLSearchParams(window.location.search).get("topic_ids");
      if (!raw) return fallback;
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return fallback;
      return parsed;
    } catch (err) {
      return fallback;
    }
  }

  function parseVideoStatusFromUrl() {
    var fallback = { basic: {}, intermediate: {}, advanced: {} };
    try {
      var raw = new URLSearchParams(window.location.search).get("video_status");
      if (!raw) return fallback;
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return fallback;
      return parsed;
    } catch (err) {
      return fallback;
    }
  }

  // UI availability comes from bot-injected URL param topic_ids.
  // Bot-side validation remains authoritative (video_catalog.py).
  var TOPIC_MESSAGE_IDS = parseTopicMessageIdsFromUrl();
  var VIDEO_STATUS = parseVideoStatusFromUrl();

  var tabs = [
    { btn: document.getElementById("tabBasic"), panel: document.getElementById("panelBasic") },
    { btn: document.getElementById("tabIntermediate"), panel: document.getElementById("panelIntermediate") },
    { btn: document.getElementById("tabAdvanced"), panel: document.getElementById("panelAdvanced") }
  ];
  var statusEl = document.getElementById("status");
  var topBackBtn = document.getElementById("topBackBtn");
  var bottomBackBtn = document.getElementById("bottomBackBtn");
  var basicTopicList = document.getElementById("basicTopicList");
  var intermediateTopicList = document.getElementById("intermediateTopicList");
  var advancedTopicList = document.getElementById("advancedTopicList");
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

  function renderTopicList(container, topics, level, nextOnlyFrom, comingSoonFrom) {
    if (!container) return;
    container.innerHTML = "";

    topics.forEach(function (row) {
      var card = document.createElement("div");
      card.className = "topic-card";

      var title = document.createElement("p");
      title.className = "topic-title";
      var topicLabel = "Topik " + row.topic + ": " + row.title;
      var statusMap = VIDEO_STATUS[level] || {};
      var override = statusMap[String(row.topic)] || statusMap[row.topic] || null;
      if (override && typeof override === "object") {
        var st = String(override.status || "").toLowerCase();
        if (st === "coming_soon") {
          title.innerHTML = topicLabel + ' <em>(coming soon)</em>';
        } else if (st === "available_on") {
          var onDate = String(override.available_on || "").trim();
          if (onDate) {
            title.innerHTML = topicLabel + ' <em>(available on: ' + onDate + ')</em>';
          } else {
            title.innerHTML = topicLabel + ' <em>(available on)</em>';
          }
        } else if (st === "online") {
          title.innerHTML = topicLabel + ' <span>🟢 online</span>';
        } else {
          title.textContent = topicLabel;
        }
      } else if (row.topic >= comingSoonFrom) {
        title.innerHTML = topicLabel + ' <em>(coming soon)</em>';
      } else {
        title.textContent = topicLabel;
      }
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
      btn.setAttribute("data-level", level);
      btn.setAttribute("data-topic", String(row.topic));
      btn.setAttribute("data-title", row.title);

      var levelMap = TOPIC_MESSAGE_IDS[level] || {};
      var topicMessageId = Number(levelMap[String(row.topic)] || levelMap[row.topic] || 0);
      if (topicMessageId <= 0) {
        btn.classList.add("is-unavailable");
      }

      if (row.topic >= nextOnlyFrom) {
        var badge = document.createElement("img");
        badge.src = "nextexc.png";
        badge.alt = "NEXT only";
        badge.className = "next-badge";
        btn.appendChild(badge);
      }

      btn.addEventListener("click", function () {
        sendTopicPickPayload(level, String(row.topic), row.title);
      });

      actions.appendChild(btn);
      card.appendChild(actions);
      container.appendChild(card);
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

  renderTopicList(basicTopicList, BASIC_TOPICS, "basic", 9, 14);
  renderTopicList(intermediateTopicList, INTERMEDIATE_TOPICS, "intermediate", 3, 4);
  renderTopicList(advancedTopicList, ADVANCED_TOPICS, "advanced", 2, 3);
  activate(0);
})();
