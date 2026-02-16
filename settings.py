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


def _build_activity_query(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    tabung_start_date: str,
    current_profit_usd: float,
    total_balance_usd: float,
    tabung_balance_usd: float,
    capital_usd: float,
    weekly_performance_usd: float,
    monthly_performance_usd: float,
) -> str:
    return urlencode(
        {
            "name": name,
            "initial_capital_usd": f"{initial_capital_usd:.2f}",
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "saved_date": saved_date,
            "tabung_start_date": tabung_start_date,
            "current_profit_usd": f"{current_profit_usd:.2f}",
            "total_balance_usd": f"{total_balance_usd:.2f}",
            "tabung_balance_usd": f"{tabung_balance_usd:.2f}",
            "capital_usd": f"{capital_usd:.2f}",
            "weekly_performance_usd": f"{weekly_performance_usd:.2f}",
            "monthly_performance_usd": f"{monthly_performance_usd:.2f}",
        }
    )


def get_withdrawal_activity_webapp_url(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    tabung_start_date: str,
    current_profit_usd: float,
    total_balance_usd: float,
    tabung_balance_usd: float,
    capital_usd: float,
    weekly_performance_usd: float,
    monthly_performance_usd: float,
) -> str:
    page = f"{_miniapp_base_url()}/withdrawal-activity.html"
    query = _build_activity_query(
        name=name,
        initial_capital_usd=initial_capital_usd,
        current_balance_usd=current_balance_usd,
        saved_date=saved_date,
        tabung_start_date=tabung_start_date,
        current_profit_usd=current_profit_usd,
        total_balance_usd=total_balance_usd,
        tabung_balance_usd=tabung_balance_usd,
        capital_usd=capital_usd,
        weekly_performance_usd=weekly_performance_usd,
        monthly_performance_usd=monthly_performance_usd,
    )
    return f"{page}?{query}"


def get_deposit_activity_webapp_url(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    tabung_start_date: str,
    current_profit_usd: float,
    total_balance_usd: float,
    tabung_balance_usd: float,
    capital_usd: float,
    weekly_performance_usd: float,
    monthly_performance_usd: float,
) -> str:
    page = f"{_miniapp_base_url()}/deposit-activity.html"
    query = _build_activity_query(
        name=name,
        initial_capital_usd=initial_capital_usd,
        current_balance_usd=current_balance_usd,
        saved_date=saved_date,
        tabung_start_date=tabung_start_date,
        current_profit_usd=current_profit_usd,
        total_balance_usd=total_balance_usd,
        tabung_balance_usd=tabung_balance_usd,
        capital_usd=capital_usd,
        weekly_performance_usd=weekly_performance_usd,
        monthly_performance_usd=monthly_performance_usd,
    )
    return f"{page}?{query}"


def get_trading_activity_webapp_url(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    tabung_start_date: str,
    current_profit_usd: float,
    total_balance_usd: float,
    tabung_balance_usd: float,
    capital_usd: float,
    weekly_performance_usd: float,
    monthly_performance_usd: float,
) -> str:
    page = f"{_miniapp_base_url()}/trading-activity.html"
    query = _build_activity_query(
        name=name,
        initial_capital_usd=initial_capital_usd,
        current_balance_usd=current_balance_usd,
        saved_date=saved_date,
        tabung_start_date=tabung_start_date,
        current_profit_usd=current_profit_usd,
        total_balance_usd=total_balance_usd,
        tabung_balance_usd=tabung_balance_usd,
        capital_usd=capital_usd,
        weekly_performance_usd=weekly_performance_usd,
        monthly_performance_usd=monthly_performance_usd,
    )
    return f"{page}?{query}"


def get_set_new_goal_webapp_url(
    name: str,
    current_balance_usd: float,
    capital_usd: float,
    saved_date: str,
    tabung_start_date: str,
    mission_status: str,
    has_goal: bool,
    target_balance_usd: float,
    grow_target_usd: float,
    target_label: str,
) -> str:
    page = f"{_miniapp_base_url()}/set-new-goal.html"
    query = urlencode(
        {
            "name": name,
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "capital_usd": f"{capital_usd:.2f}",
            "saved_date": saved_date,
            "tabung_start_date": tabung_start_date,
            "mission_status": mission_status,
            "has_goal": "1" if has_goal else "0",
            "target_balance_usd": f"{target_balance_usd:.2f}",
            "grow_target_usd": f"{grow_target_usd:.2f}",
            "target_label": target_label,
        }
    )
    return f"{page}?{query}"


def get_project_grow_mission_webapp_url(
    name: str,
    current_balance_usd: float,
    capital_usd: float,
    saved_date: str,
    target_balance_usd: float,
    target_days: int,
    target_label: str,
    tabung_balance_usd: float,
    tabung_start_date: str,
    mission_status: str,
    mission_active: bool,
    mission_mode: str,
    mission_started_date: str,
) -> str:
    page = f"{_miniapp_base_url()}/mission.html"
    query = urlencode(
        {
            "name": name,
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "capital_usd": f"{capital_usd:.2f}",
            "saved_date": saved_date,
            "target_balance_usd": f"{target_balance_usd:.2f}",
            "target_days": str(target_days),
            "target_label": target_label,
            "tabung_balance_usd": f"{tabung_balance_usd:.2f}",
            "tabung_start_date": tabung_start_date,
            "mission_status": mission_status,
            "mission_active": "1" if mission_active else "0",
            "mission_mode": mission_mode,
            "mission_started_date": mission_started_date,
        }
    )
    return f"{page}?{query}"
