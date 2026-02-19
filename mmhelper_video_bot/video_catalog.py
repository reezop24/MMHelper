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
        "message_id": 0,
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
        "message_id": 0,
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
        "message_id": 0,
        "next_only": True,
        "subtopics": [
            "Participant",
            "Volume spike",
        ],
    },
    {
        "topic_no": 10,
        "topic_title": "Risk Management (Level 1)",
        "message_id": 0,
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
        "message_id": 0,
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
        "message_id": 0,
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
        "message_id": 0,
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

