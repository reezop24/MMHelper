"""Runtime settings for MM HELPER."""

from __future__ import annotations

import json
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


def get_risk_calculator_webapp_url(
    current_balance_usd: float | None = None,
    target_days: int | None = None,
    grow_target_usd: float | None = None,
) -> str:
    page = f"{_miniapp_base_url()}/risk-calculator.html"
    if current_balance_usd is None and target_days is None and grow_target_usd is None:
        return page
    query_data: dict[str, str] = {}
    if current_balance_usd is not None:
        query_data["current_balance_usd"] = f"{float(current_balance_usd):.2f}"
    if target_days is not None:
        query_data["target_days"] = str(max(0, int(target_days)))
    if grow_target_usd is not None:
        query_data["grow_target_usd"] = f"{float(grow_target_usd):.2f}"
    query = urlencode(query_data)
    return f"{page}?{query}"


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


def get_balance_adjustment_webapp_url(
    name: str,
    current_balance: float,
    saved_date: str,
    can_adjust: bool,
    used_this_month: bool,
    window_open: bool,
    window_label: str,
) -> str:
    page = f"{_miniapp_base_url()}/balance-adjustment.html"
    query = urlencode(
        {
            "name": name,
            "current_balance": f"{current_balance:.2f}",
            "saved_date": saved_date,
            "can_adjust": "1" if can_adjust else "0",
            "used_this_month": "1" if used_this_month else "0",
            "window_open": "1" if window_open else "0",
            "window_label": window_label,
        }
    )
    return f"{page}?{query}"


def _build_activity_query(
    name: str,
    initial_capital_usd: float,
    current_balance_usd: float,
    saved_date: str,
    tabung_start_date: str,
    current_profit_usd: float,
    total_balance_usd: float,
    tabung_balance_usd: float,
    weekly_performance_usd: float,
    monthly_performance_usd: float,
    target_balance_usd: float,
    grow_target_usd: float,
    target_days: int,
    goal_reached: bool,
    goal_baseline_balance_usd: float,
    tabung_update_url: str,
    daily_target_reached_today: bool,
    has_tabung_save_today: bool,
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
            "weekly_performance_usd": f"{weekly_performance_usd:.2f}",
            "monthly_performance_usd": f"{monthly_performance_usd:.2f}",
            "target_balance_usd": f"{target_balance_usd:.2f}",
            "grow_target_usd": f"{grow_target_usd:.2f}",
            "target_days": str(max(0, int(target_days))),
            "goal_reached": "1" if goal_reached else "0",
            "goal_baseline_balance_usd": f"{goal_baseline_balance_usd:.2f}",
            "tabung_update_url": tabung_update_url,
            "daily_target_reached_today": "1" if daily_target_reached_today else "0",
            "has_tabung_save_today": "1" if has_tabung_save_today else "0",
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
    weekly_performance_usd: float,
    monthly_performance_usd: float,
    target_balance_usd: float,
    grow_target_usd: float,
    target_days: int,
    goal_reached: bool,
    goal_baseline_balance_usd: float,
    tabung_update_url: str,
    daily_target_reached_today: bool,
    has_tabung_save_today: bool,
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
        weekly_performance_usd=weekly_performance_usd,
        monthly_performance_usd=monthly_performance_usd,
        target_balance_usd=target_balance_usd,
        grow_target_usd=grow_target_usd,
        target_days=target_days,
        goal_reached=goal_reached,
        goal_baseline_balance_usd=goal_baseline_balance_usd,
        tabung_update_url=tabung_update_url,
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=has_tabung_save_today,
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
    weekly_performance_usd: float,
    monthly_performance_usd: float,
    target_balance_usd: float,
    grow_target_usd: float,
    target_days: int,
    goal_reached: bool,
    goal_baseline_balance_usd: float,
    tabung_update_url: str,
    daily_target_reached_today: bool,
    has_tabung_save_today: bool,
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
        weekly_performance_usd=weekly_performance_usd,
        monthly_performance_usd=monthly_performance_usd,
        target_balance_usd=target_balance_usd,
        grow_target_usd=grow_target_usd,
        target_days=target_days,
        goal_reached=goal_reached,
        goal_baseline_balance_usd=goal_baseline_balance_usd,
        tabung_update_url=tabung_update_url,
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=has_tabung_save_today,
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
    weekly_performance_usd: float,
    monthly_performance_usd: float,
    target_balance_usd: float,
    grow_target_usd: float,
    target_days: int,
    goal_reached: bool,
    goal_baseline_balance_usd: float,
    tabung_update_url: str,
    daily_target_reached_today: bool,
    has_tabung_save_today: bool,
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
        weekly_performance_usd=weekly_performance_usd,
        monthly_performance_usd=monthly_performance_usd,
        target_balance_usd=target_balance_usd,
        grow_target_usd=grow_target_usd,
        target_days=target_days,
        goal_reached=goal_reached,
        goal_baseline_balance_usd=goal_baseline_balance_usd,
        tabung_update_url=tabung_update_url,
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=has_tabung_save_today,
    )
    return f"{page}?{query}"


def get_set_new_goal_webapp_url(
    name: str,
    current_balance_usd: float,
    saved_date: str,
    tabung_start_date: str,
    mission_status: str,
    has_goal: bool,
    goal_reached: bool,
    target_balance_usd: float,
    grow_target_usd: float,
    target_days: int,
    target_label: str,
    tabung_update_url: str,
    goal_baseline_balance_usd: float,
    daily_target_reached_today: bool,
    has_tabung_save_today: bool,
) -> str:
    page = f"{_miniapp_base_url()}/set-new-goal.html"
    query = urlencode(
        {
            "name": name,
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "saved_date": saved_date,
            "tabung_start_date": tabung_start_date,
            "mission_status": mission_status,
            "has_goal": "1" if has_goal else "0",
            "goal_reached": "1" if goal_reached else "0",
            "target_balance_usd": f"{target_balance_usd:.2f}",
            "grow_target_usd": f"{grow_target_usd:.2f}",
            "target_days": str(max(0, int(target_days))),
            "target_label": target_label,
            "tabung_update_url": tabung_update_url,
            "goal_baseline_balance_usd": f"{goal_baseline_balance_usd:.2f}",
            "daily_target_reached_today": "1" if daily_target_reached_today else "0",
            "has_tabung_save_today": "1" if has_tabung_save_today else "0",
        }
    )
    return f"{page}?{query}"


def get_project_grow_mission_webapp_url(
    name: str,
    current_balance_usd: float,
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


def get_tabung_progress_webapp_url(
    name: str,
    saved_date: str,
    tabung_start_date: str,
    tabung_balance_usd: float,
    grow_target_usd: float,
    days_left: int,
    days_left_label: str,
    grow_progress_pct: float,
    weekly_grow_usd: float,
    monthly_grow_usd: float,
) -> str:
    page = f"{_miniapp_base_url()}/tabung-progress.html"
    query = urlencode(
        {
            "name": name,
            "saved_date": saved_date,
            "tabung_start_date": tabung_start_date,
            "tabung_balance_usd": f"{tabung_balance_usd:.2f}",
            "grow_target_usd": f"{grow_target_usd:.2f}",
            "days_left": str(max(0, int(days_left))),
            "days_left_label": days_left_label,
            "grow_progress_pct": f"{grow_progress_pct:.2f}",
            "weekly_grow_usd": f"{weekly_grow_usd:.2f}",
            "monthly_grow_usd": f"{monthly_grow_usd:.2f}",
        }
    )
    return f"{page}?{query}"


def get_notification_setting_webapp_url(name: str, saved_date: str) -> str:
    page = f"{_miniapp_base_url()}/notification-setting.html"
    query = urlencode(
        {
            "name": name,
            "saved_date": saved_date,
        }
    )
    return f"{page}?{query}"


def get_transaction_history_webapp_url(
    name: str,
    saved_date: str,
    records_7d: list[dict[str, object]],
    records_30d: list[dict[str, object]],
) -> str:
    page = f"{_miniapp_base_url()}/transaction-history.html"
    query = urlencode(
        {
            "name": name,
            "saved_date": saved_date,
            "records_7d": json.dumps(records_7d, separators=(",", ":")),
            "records_30d": json.dumps(records_30d, separators=(",", ":")),
        }
    )
    return f"{page}?{query}"


def get_tabung_update_webapp_url(
    name: str,
    saved_date: str,
    current_balance_usd: float,
    tabung_balance_usd: float,
    total_balance_usd: float,
    target_balance_usd: float,
    goal_reached: bool,
    emergency_left: int,
    set_new_goal_url: str,
) -> str:
    page = f"{_miniapp_base_url()}/tabung-update.html"
    query = urlencode(
        {
            "name": name,
            "saved_date": saved_date,
            "current_balance_usd": f"{current_balance_usd:.2f}",
            "tabung_balance_usd": f"{tabung_balance_usd:.2f}",
            "total_balance_usd": f"{total_balance_usd:.2f}",
            "target_balance_usd": f"{target_balance_usd:.2f}",
            "goal_reached": "1" if goal_reached else "0",
            "emergency_left": str(max(0, int(emergency_left))),
            "set_new_goal_url": set_new_goal_url,
        }
    )
    return f"{page}?{query}"
