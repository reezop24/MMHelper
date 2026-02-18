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

