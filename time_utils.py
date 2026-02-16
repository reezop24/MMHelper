"""Timezone utilities for MM HELPER."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

MALAYSIA_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def malaysia_now() -> datetime:
    return datetime.now(MALAYSIA_TZ)
