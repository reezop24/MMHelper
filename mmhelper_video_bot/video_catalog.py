"""Video catalog for NEXT eVideo26.

Maintain this file only when adding/removing videos.
Each video item needs a title and Telegram group message_id.
"""

from __future__ import annotations

from typing import TypedDict


class VideoItem(TypedDict):
    title: str
    message_id: int


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


# Draft structure for Basic (Topik 1-5). Replace placeholders with real titles.
BASIC_TOPIC_DRAFT: dict[str, list[str]] = {
    "Topik 1": [
        "1. APA ITU TRADING",
        "Bezakan trading, investing, speculation",
        "Apa yang sebenarnya trader buat",
        "Mitos & salah faham",
    ],
    "Topik 2": [
        "2. BAGAIMANA HARGA BERGERAK",
        "Siapa pemain pasaran",
        "Siapa yang menggerakkan harga",
        "Konsep pergerakan harga",
        "Apa itu liquidity",
    ],
    "Topik 3": [
        "3. BROKER",
        "Pengenalan",
        "Market maker vs ECN",
        "Spread, swap, leverage",
        "Risiko leverage tinggi",
    ],
    "Topik 4": [
        "4. PLATFORM",
        "MT4/MT5",
        "TradingView",
        "Order type",
        "Cara membaca chart (platform overview)",
    ],
    "Topik 5": [
        "5. PSYCHOLOGY (Level 1)",
        "Kenapa beginner selalu loss",
        "Emotional cycle dalam trading",
        "Apa maksud disiplin dan sabar",
    ],
}
