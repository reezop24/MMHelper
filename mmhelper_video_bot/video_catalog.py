"""Video catalog for NEXT eVideo26.

Rule:
- 1 topik = 1 video = 1 message_id (Telegram group database).
- subtopics are points inside that single video.
"""

from __future__ import annotations

from typing import TypedDict


class VideoItem(TypedDict):
    title: str
    message_id: int


class TopicItem(TypedDict):
    topic_no: int
    topic_title: str
    message_id: int  # 1 message_id for the whole topic
    next_only: bool
    subtopics: list[str]


VIDEO_CATALOG: dict[str, list[VideoItem]] = {
    "basic": [
        {"title": "Basic 01 - Placeholder", "message_id": 1},
        {"title": "Basic 02 - Placeholder", "message_id": 2},
    ],
    "intermediate": [
        {"title": "Intermediate 01 - Placeholder", "message_id": 3},
        {"title": "Intermediate 02 - Placeholder", "message_id": 4},
    ],
    "advanced": [
        {"title": "Advanced 01 - Placeholder", "message_id": 5},
        {"title": "Advanced 02 - Placeholder", "message_id": 6},
    ],
}


LEVEL_LABELS: dict[str, str] = {
    "basic": "Basic",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}


# Basic full structure Topik 1-19.
# Fill message_id using your group database (one id per topic).
BASIC_TOPICS: list[TopicItem] = [
    {
        "topic_no": 1,
        "topic_title": "Apa Itu Trading",
        "message_id": 5,
        "next_only": False,
        "subtopics": [
            "Bezakan trading, investing, speculation",
            "Apa yang sebenarnya trader buat",
            "Mitos & salah faham",
        ],
    },
    {
        "topic_no": 2,
        "topic_title": "Bagaimana Harga Bergerak",
        "message_id": 6,
        "next_only": False,
        "subtopics": [
            "Siapa pemain pasaran",
            "Siapa yang menggerakkan harga",
            "Konsep pergerakan harga",
            "Apa itu liquidity",
        ],
    },
    {
        "topic_no": 3,
        "topic_title": "Broker",
        "message_id": 7,
        "next_only": False,
        "subtopics": [
            "Pengenalan",
            "Market maker vs ECN",
            "Spread, swap, leverage",
            "Risiko leverage tinggi",
        ],
    },
    {
        "topic_no": 4,
        "topic_title": "Platform",
        "message_id": 8,
        "next_only": False,
        "subtopics": [
            "MT4/MT5",
            "TradingView",
            "Order type",
            "Cara membaca chart (platform overview)",
        ],
    },
    {
        "topic_no": 5,
        "topic_title": "Psychology (Level 1)",
        "message_id": 9,
        "next_only": False,
        "subtopics": [
            "Kenapa beginner selalu loss",
            "Emotional cycle dalam trading",
            "Apa maksud disiplin dan sabar",
        ],
    },
    {
        "topic_no": 6,
        "topic_title": "Market Structure (Level 1)",
        "message_id": 10,
        "next_only": False,
        "subtopics": [
            "Trend",
            "L, H, HH, HL, LH & LL",
            "Candlestick (Level 1)",
        ],
    },
    {
        "topic_no": 7,
        "topic_title": "Support & Resistant (Level 1)",
        "message_id": 11,
        "next_only": False,
        "subtopics": [
            "Pengenalan",
            "Horizontal & Dynamic",
            "Kenalpasti SNR yang kuat",
            "Fake breakout & kenapa ia berlaku",
        ],
    },
    {
        "topic_no": 8,
        "topic_title": "Trendline (Level 1)",
        "message_id": 12,
        "next_only": False,
        "subtopics": [
            "Apa itu trendline",
            "Bila trendline valid dan tidak valid",
            "Common mistake beginner selalu buat",
        ],
    },
    {
        "topic_no": 9,
        "topic_title": "Volume",
        "message_id": 13,
        "next_only": True,
        "subtopics": [
            "Participant",
            "Volume spike",
        ],
    },
    {
        "topic_no": 10,
        "topic_title": "Risk Management (Level 1)",
        "message_id": 14,
        "next_only": True,
        "subtopics": [
            "Apa itu SL & TP",
            "Kenapa SL penting",
            "1-2% rule",
            "Kenapa account blow berlaku",
        ],
    },
    {
        "topic_no": 11,
        "topic_title": "Candlestick Pattern",
        "message_id": 15,
        "next_only": True,
        "subtopics": [
            "Engulfing",
            "Pin bar candle",
            "Inside bar candle",
        ],
    },
    {
        "topic_no": 12,
        "topic_title": "Chart Pattern",
        "message_id": 16,
        "next_only": True,
        "subtopics": [
            "Double top / bottom",
            "Head & Shoulder",
            "Triangle",
        ],
    },
    {
        "topic_no": 13,
        "topic_title": "Liquidity (Level 1)",
        "message_id": 17,
        "next_only": True,
        "subtopics": [
            "Pengenalan",
            "Liquidity grab",
            "Liquidity sweep",
            "Pentingnya memahami liquidity grab / sweep dan mengapa ia berlaku",
        ],
    },
    {
        "topic_no": 14,
        "topic_title": "BOS & CHoCH (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengenalan",
            "Cara membezakan BOS & CHoCH",
        ],
    },
    {
        "topic_no": 15,
        "topic_title": "FVG & Imbalance (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengenalan",
            "Mengapa zon FVG & Imbalance sangat penting",
        ],
    },
    {
        "topic_no": 16,
        "topic_title": "Orderblock (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengenalan",
            "Mengapa OB zon terhasil dan apa peranan zon OB",
        ],
    },
    {
        "topic_no": 17,
        "topic_title": "Trading Plan (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Setup",
            "Entry rules",
            "Exit rules",
            "Journaling",
        ],
    },
    {
        "topic_no": 18,
        "topic_title": "Psychology (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Overtrading",
            "FOMO",
            "Revenge trade",
            "Bagaimana kekalkan disiplin",
        ],
    },
    {
        "topic_no": 19,
        "topic_title": "Tools & Management",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Timeframe mapping",
            "Multi-timeframe mapping",
            "Intraday & swing planning",
            "Trading session",
        ],
    },
]


# Intermediate full structure Topik 1-21.
# Rule requested:
# - next_only: topik 3-21
# - coming soon label handled in miniapp (topik 4-21)
INTERMEDIATE_TOPICS: list[TopicItem] = [
    {
        "topic_no": 1,
        "topic_title": "Market Structure (Level 2)",
        "message_id": 18,
        "next_only": False,
        "subtopics": [
            "Internal vs external structure",
            "Complex pullback",
            "Trend correction & trend change",
            "Micro consolidation",
            "Multi BOS",
        ],
    },
    {
        "topic_no": 2,
        "topic_title": "Liquidity (Level 2)",
        "message_id": 19,
        "next_only": False,
        "subtopics": [
            "Jenis liquidity",
            "Kumpulan liquidity",
            "Bagaimana liquidity dicipta oleh pergerakan harga",
            "Liquidity tujuan entry vs liquidity tujuan target",
        ],
    },
    {
        "topic_no": 3,
        "topic_title": "Supply & Demand",
        "message_id": 20,
        "next_only": True,
        "subtopics": [
            "Perbezaan SNR dan SND",
            "Fresh & test zone",
            "Weak vs strong SND",
            "Kesilapan biasa marking SND",
            "Hubungan SND dengan liquidity",
        ],
    },
    {
        "topic_no": 4,
        "topic_title": "Memahami Breakout Behavior",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "True breakout vs fake breakout",
            "Retest type A vs retest type B",
            "Breakout failure & perangkap",
            "Accumulation sebelum breakout (micro buildup)",
        ],
    },
    {
        "topic_no": 5,
        "topic_title": "Candlestick Advanced Behavior",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Candle volume behavior",
            "Impulsive candle vs corrective candle",
            "Wick sebagai liquidity grab",
            "Candle yang tidak mempunyai volume",
        ],
    },
    {
        "topic_no": 6,
        "topic_title": "Momentum & Correction",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Impulse > correction > impulse",
            "Deep & shallow retracement",
            "Trend melemah sebelum perubahan trend",
        ],
    },
    {
        "topic_no": 7,
        "topic_title": "Fibonacci",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengenalan",
            "Fibonacci retracement",
            "Fibonacci extension",
            "Fibo Dewa (quarter zone: discount vs premium)",
            "AB=CD (Level 1)",
        ],
    },
    {
        "topic_no": 8,
        "topic_title": "Support & Resistant (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Flip zone",
            "Strong zone vs weak zone",
            "Bagaimana zone dimakan",
            "Multi-timeframe SNR alignment",
        ],
    },
    {
        "topic_no": 9,
        "topic_title": "Trendline (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Trendline channel",
            "Break of trendline - momentum shift",
            "Trendline liquidity",
            "Bagaimana trendline digunakan sebagai perangkap",
        ],
    },
    {
        "topic_no": 10,
        "topic_title": "Entry Refinement",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Confirmation entry vs blind entry",
            "Entry pada pullback vs breakout entry",
            "Mencari POI kecil dalam zon besar",
            "Scaling in / out",
        ],
    },
    {
        "topic_no": 11,
        "topic_title": "Risk Management (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Position sizing calculation",
            "Fixed fractional vs fixed risk",
            "Risk to reward ratio & mapping",
            "SL placement based on structure",
        ],
    },
    {
        "topic_no": 12,
        "topic_title": "Trade Management (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Breakeven rules",
            "Partial TP strategy",
            "Trailing TP strategy",
            "Trailing TP based on structure",
            "Menguruskan drawdown",
        ],
    },
    {
        "topic_no": 13,
        "topic_title": "Multi-Timeframe Analysis",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Top-down mapping",
            "HTF bias vs LTF entry",
            "Cara elakkan perangkap LTF",
            "Bagaimana melihat big picture untuk entry kecil",
        ],
    },
    {
        "topic_no": 14,
        "topic_title": "Accumulation / Distribution (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Sideway",
            "Range high / low manipulation",
            "Fake breakout dua hala",
            "Re-entry dalam range",
        ],
    },
    {
        "topic_no": 15,
        "topic_title": "FVG & Imbalance (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Jenis FVG dan peranan FVG",
            "Clean vs messy imbalance",
            "Mengapa FVG diuji semula",
            "FVG + structure alignment",
            "FVG yang gagal",
        ],
    },
    {
        "topic_no": 16,
        "topic_title": "Orderblock (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Weak vs valid OB",
            "OB dalam trend vs reversal",
            "OB & BOS / CHoCH alignment",
            "Entry refinement di OB",
            "Orderblock to breakerblock",
        ],
    },
    {
        "topic_no": 17,
        "topic_title": "BOS & CHoCH (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Confirmation BOS valid & failed",
            "Early CHoCH vs valid CHoCH",
            "CHoCH dalam range vs trend",
            "Multi-timeframe BOS & CHoCH",
        ],
    },
    {
        "topic_no": 18,
        "topic_title": "Mitigation Candlestick",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengenalan",
            "Impulse vs mitigation",
            "Candle mitigation vs candle manipulation",
            "Peranan mitigation dalam OB dan FVG",
            "Kesilapan baca candle mitigation",
        ],
    },
    {
        "topic_no": 19,
        "topic_title": "Trading Plan (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Setup-specific rules (SOP)",
            "Entry model (A, B, C)",
            "Exit model",
            "Time-of-day filter",
            "Risk filter",
        ],
    },
    {
        "topic_no": 20,
        "topic_title": "Money Management (Level 1)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pembahagian risk per setup mengikut capital",
            "Dynamic equity based on trade risk",
        ],
    },
    {
        "topic_no": 21,
        "topic_title": "Psychology (Level 2)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Menguruskan winning streak",
            "Menguruskan losing streak",
            "Mengenalpasti emotional trading pattern",
            "Kaedah membina disiplin",
        ],
    },
]


# Advanced full structure Topik 1-19.
# Rule requested:
# - next_only: topik 2-19
# - coming soon label handled in miniapp (topik 3-19)
ADVANCED_TOPICS: list[TopicItem] = [
    {
        "topic_no": 1,
        "topic_title": "Market Narrative & Context Building",
        "message_id": 22,
        "next_only": False,
        "subtopics": [
            "Siapa aktif sekarang",
            "Continuation day vs reversal day",
            "Expansion vs contraction day",
            "High probability vs chop day",
        ],
    },
    {
        "topic_no": 2,
        "topic_title": "Liquidity (Level 3)",
        "message_id": 21,
        "next_only": True,
        "subtopics": [
            "Session liquidity map",
            "External vs internal liquidity target",
            "Partial liquidity grab vs full sweep",
            "Liquidity run & exhaustion",
        ],
    },
    {
        "topic_no": 3,
        "topic_title": "Algorithmic Price Behavior",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Mengapa price menguji zon sama berulang kali",
            "Time based manipulation",
            "Engineered pullback vs real weakness",
        ],
    },
    {
        "topic_no": 4,
        "topic_title": "Entry Framework Overview",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Mengapa SOP diperlukan",
            "Environment filter sebelum guna SOP",
            "Bila tak boleh guna SOP",
        ],
    },
    {
        "topic_no": 5,
        "topic_title": "SOP1 - DBO (Double Breakout)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengenalan konsep dan struktur wajib DBO",
            "Entry origin & invalidation",
            "DBO dalam DBO",
            "Risk profile",
        ],
    },
    {
        "topic_no": 6,
        "topic_title": "SOP2 - BtB (Break to Back)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "BtB logic sebagai perubahan karektor (CHoCH)",
            "BtB dalam range vs trend",
            "High possibility fake BtB yang menyebabkan trend bersambung",
        ],
    },
    {
        "topic_no": 7,
        "topic_title": "SOP3 - Pattern Failure Models",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Mengapa pattern gagal lebih padu dari pattern jadi",
            "DBO failed = fake DBO (fDBO)",
        ],
    },
    {
        "topic_no": 8,
        "topic_title": "SOP Alignment",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Confirmation berkembar",
            "DBO + BtB",
            "DBO > fDBO + BtB",
            "Trendline & Fibonacci alignment",
            "Multi-timeframe & structure alignment",
        ],
    },
    {
        "topic_no": 9,
        "topic_title": "Execution Timing & Precision",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Entry candle selection",
            "Micro POI dalam POI besar",
            "Spread & slippage awareness",
            "Killzone-based execution",
        ],
    },
    {
        "topic_no": 10,
        "topic_title": "Risk Management (Level 3) - Dynamic",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Risk scaling mengikut conviction",
            "Partial risk off",
            "Reduce exposure during chop",
            "News aware risk adjustment",
        ],
    },
    {
        "topic_no": 11,
        "topic_title": "Trade Management (Level 2) - Advanced",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Stack TP logic",
            "Structure trail vs time-based trail",
            "Reentry logic selepas TP1",
            "Position add-on rules",
        ],
    },
    {
        "topic_no": 12,
        "topic_title": "System Validation & Expectancy",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Winrate vs RR trade-off",
            "Setup expectancy",
            "Sample size logic",
            "Abaikan sementara SOP yang tak perform",
        ],
    },
    {
        "topic_no": 13,
        "topic_title": "Trading Plan (Level 2) - Journaling",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Tagging SOP & context",
            "Screenshot classification",
            "Error pattern detection",
            "Forward testing framework",
        ],
    },
    {
        "topic_no": 14,
        "topic_title": "Psychology (Level 3)",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Ego spike selepas win besar",
            "Trauma selepas loss streak",
            "Detachment from result",
            "Trading as execution, bukan emosi",
        ],
    },
    {
        "topic_no": 15,
        "topic_title": "Live Market Breakdown",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "HTF > LTF breakdown lengkap",
            "Kenapa entry diambil",
            "Kenapa entry dielakkan",
            "Post-trade autopsy",
        ],
    },
    {
        "topic_no": 16,
        "topic_title": "Money Management (Level 2) - Business Model",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Pengurusan kewangan cekap",
            "Ledger in out capital",
            "Performance ledger based on profit loss",
        ],
    },
    {
        "topic_no": 17,
        "topic_title": "Bonus 1",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Multi-SOP - liquidity based",
        ],
    },
    {
        "topic_no": 18,
        "topic_title": "Bonus 2",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Market analysis - FiboExtension based",
        ],
    },
    {
        "topic_no": 19,
        "topic_title": "Bonus 3",
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Scalping within range",
        ],
    },
]


LEVEL_TOPICS: dict[str, list[TopicItem]] = {
    "basic": BASIC_TOPICS,
    "intermediate": INTERMEDIATE_TOPICS,
    "advanced": ADVANCED_TOPICS,
}
