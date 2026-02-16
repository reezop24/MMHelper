"""Runtime settings for MM HELPER."""

from __future__ import annotations

import os
from urllib.parse import urlencode

DEFAULT_SETUP_WEBAPP_URL = "https://example.com/mmhelper/setup"


def get_setup_webapp_url() -> str:
    url = (os.getenv("MMHELPER_SETUP_URL") or "").strip()
    return url or DEFAULT_SETUP_WEBAPP_URL


def get_initial_capital_reset_webapp_url(
    name: str,
    initial_capital: float,
    saved_date: str,
    can_reset: bool,
) -> str:
    base = get_setup_webapp_url().rstrip("/")

    if base.endswith("index.html"):
        base = base[: -len("index.html")].rstrip("/")

    reset_page = f"{base}/capital-reset.html"
    query = urlencode(
        {
            "name": name,
            "initial_capital": f"{initial_capital:.2f}",
            "saved_date": saved_date,
            "can_reset": "1" if can_reset else "0",
        }
    )
    return f"{reset_page}?{query}"
