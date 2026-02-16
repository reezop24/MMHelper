"""Runtime settings for MM HELPER."""

from __future__ import annotations

import os
from urllib.parse import urlencode

DEFAULT_SETUP_WEBAPP_URL = "https://example.com/mmhelper/setup"


def get_setup_webapp_url() -> str:
    url = (os.getenv("MMHELPER_SETUP_URL") or "").strip()
    return url or DEFAULT_SETUP_WEBAPP_URL


def _miniapp_base_url() -> str:
    base = get_setup_webapp_url().rstrip("/")
    if base.endswith("index.html"):
        base = base[: -len("index.html")].rstrip("/")
    return base


def get_initial_capital_reset_webapp_url(
    name: str,
    initial_capital: float,
    current_balance: float,
    saved_date: str,
    can_reset: bool,
) -> str:
    reset_page = f"{_miniapp_base_url()}/capital-reset.html"
    query = urlencode(
        {
            "name": name,
            "initial_capital": f"{initial_capital:.2f}",
            "current_balance": f"{current_balance:.2f}",
            "saved_date": saved_date,
            "can_reset": "1" if can_reset else "0",
        }
    )
    return f"{reset_page}?{query}"


def get_withdrawal_activity_webapp_url(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    current_profit_usd: float,
) -> str:
    page = f"{_miniapp_base_url()}/withdrawal-activity.html"
    query = urlencode(
        {
            "name": name,
            "initial_capital_usd": f"{initial_capital_usd:.2f}",
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "saved_date": saved_date,
            "current_profit_usd": f"{current_profit_usd:.2f}",
        }
    )
    return f"{page}?{query}"


def get_deposit_activity_webapp_url(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    current_profit_usd: float,
) -> str:
    page = f"{_miniapp_base_url()}/deposit-activity.html"
    query = urlencode(
        {
            "name": name,
            "initial_capital_usd": f"{initial_capital_usd:.2f}",
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "saved_date": saved_date,
            "current_profit_usd": f"{current_profit_usd:.2f}",
        }
    )
    return f"{page}?{query}"
