"""Simple JSON storage for MM HELPER setup data."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from time_utils import malaysia_now

DB_PATH = Path(__file__).with_name("mmhelper_db.json")


def _default_db() -> dict[str, Any]:
    return {"users": {}}


def load_db() -> dict[str, Any]:
    if not DB_PATH.exists():
        return _default_db()

    try:
        with DB_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_db()

    if not isinstance(data, dict):
        return _default_db()

    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    return data


def save_db(data: dict[str, Any]) -> None:
    with DB_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def has_initial_setup(user_id: int) -> bool:
    db = load_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {})
    return bool(sections.get("initial_setup"))


def get_initial_setup_summary(user_id: int) -> dict[str, Any]:
    db = load_db()
    user = db.get("users", {}).get(str(user_id), {})
    init_section = user.get("sections", {}).get("initial_setup", {})
    init_data = init_section.get("data", {})
    return {
        "name": init_data.get("name") or user.get("telegram_name") or f"User {user_id}",
        "initial_capital_usd": float(init_data.get("initial_capital_usd") or 0),
        "saved_date": init_section.get("saved_date") or "-",
    }


def _extract_profit_from_obj(obj: Any) -> float:
    if not isinstance(obj, dict):
        return 0.0

    for key in ("current_profit_usd", "net_profit_usd", "total_pnl_usd", "profit_usd"):
        value = obj.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _sum_records(records: Any, field: str) -> float:
    total = 0.0
    if not isinstance(records, list):
        return total
    for item in records:
        if not isinstance(item, dict):
            continue
        try:
            total += float(item.get(field, 0))
        except (TypeError, ValueError):
            continue
    return total


def _get_user_sections(user_id: int) -> dict[str, Any]:
    db = load_db()
    user = db.get("users", {}).get(str(user_id), {})
    return user.get("sections", {})


def _get_trading_records(user_id: int) -> list[dict[str, Any]]:
    sections = _get_user_sections(user_id)
    trading_data = sections.get("trading_activity", {}).get("data")

    if isinstance(trading_data, dict):
        records = trading_data.get("records", [])
        if isinstance(records, list):
            return [r for r in records if isinstance(r, dict)]

    if isinstance(trading_data, list):
        return [r for r in trading_data if isinstance(r, dict)]

    return []


def _record_date_myt(record: dict[str, Any]) -> date | None:
    tzinfo = malaysia_now().tzinfo

    saved_at = record.get("saved_at")
    if isinstance(saved_at, str):
        try:
            dt = datetime.fromisoformat(saved_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tzinfo)
            else:
                dt = dt.astimezone(tzinfo)
            return dt.date()
        except ValueError:
            pass

    saved_date = record.get("saved_date")
    if isinstance(saved_date, str):
        try:
            return date.fromisoformat(saved_date)
        except ValueError:
            return None

    return None


def _record_net_usd(record: dict[str, Any]) -> float:
    for key in ("net_usd", "pnl_usd", "profit_usd"):
        try:
            return float(record.get(key, 0))
        except (TypeError, ValueError):
            continue

    mode = (record.get("mode") or "").lower()
    try:
        amount = float(record.get("amount_usd", 0))
    except (TypeError, ValueError):
        return 0.0

    if mode == "loss":
        return -abs(amount)
    return abs(amount)


def _sum_trading_net_between(user_id: int, start_date: date, end_date: date) -> float:
    total = 0.0
    for record in _get_trading_records(user_id):
        rec_date = _record_date_myt(record)
        if rec_date is None:
            continue
        if start_date <= rec_date <= end_date:
            total += _record_net_usd(record)
    return total


def get_current_profit_usd(user_id: int) -> float:
    db = load_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {})

    trading_section = sections.get("trading_activity", {})
    data = trading_section.get("data")

    if isinstance(data, dict):
        value = _extract_profit_from_obj(data)
        if value != 0:
            return value

    if isinstance(data, list):
        total = 0.0
        used = False
        for item in data:
            if not isinstance(item, dict):
                continue
            for key in ("pnl_usd", "profit_usd", "net_usd"):
                try:
                    total += float(item.get(key, 0))
                    used = True
                    break
                except (TypeError, ValueError):
                    continue
        if used:
            return total

    summary = sections.get("account_summary", {}).get("data", {})
    summary_profit = _extract_profit_from_obj(summary)
    if summary_profit != 0:
        return summary_profit

    return 0.0


def get_total_withdrawal_usd(user_id: int) -> float:
    sections = _get_user_sections(user_id)
    records = sections.get("withdrawal_activity", {}).get("data", {}).get("records", [])
    return _sum_records(records, "amount_usd")


def get_total_deposit_usd(user_id: int) -> float:
    sections = _get_user_sections(user_id)
    records = sections.get("deposit_activity", {}).get("data", {}).get("records", [])
    return _sum_records(records, "amount_usd")


def get_total_balance_usd(user_id: int) -> float:
    summary = get_initial_setup_summary(user_id)
    initial_balance = float(summary.get("initial_capital_usd") or 0)
    total_withdrawn = get_total_withdrawal_usd(user_id)
    total_deposited = get_total_deposit_usd(user_id)
    return initial_balance + total_deposited - total_withdrawn


def get_tabung_balance_usd(user_id: int) -> float:
    sections = _get_user_sections(user_id)
    tabung_data = sections.get("tabung", {}).get("data")

    if isinstance(tabung_data, dict):
        for key in ("balance_usd", "tabung_balance_usd", "current_balance_usd", "amount_usd"):
            try:
                return float(tabung_data.get(key, 0))
            except (TypeError, ValueError):
                continue

        records = tabung_data.get("records")
        if isinstance(records, list):
            total = 0.0
            for item in records:
                if not isinstance(item, dict):
                    continue
                for key in ("net_usd", "amount_usd"):
                    try:
                        total += float(item.get(key, 0))
                        break
                    except (TypeError, ValueError):
                        continue
            return total

    if isinstance(tabung_data, list):
        return _sum_records(tabung_data, "amount_usd")

    return 0.0


def get_capital_usd(user_id: int) -> float:
    return get_current_balance_usd(user_id) + get_tabung_balance_usd(user_id)


def get_current_balance_usd(user_id: int) -> float:
    total_balance = get_total_balance_usd(user_id)
    current_profit = get_current_profit_usd(user_id)
    return total_balance + current_profit


def _month_range(reference_date: date) -> tuple[date, date]:
    first_day = reference_date.replace(day=1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = next_month - timedelta(days=1)
    return first_day, last_day


def _bounded_current_week(reference_date: date) -> tuple[date, date]:
    sunday_offset = (reference_date.weekday() + 1) % 7
    week_start = reference_date - timedelta(days=sunday_offset)
    week_end = week_start + timedelta(days=6)

    month_start, month_end = _month_range(reference_date)
    if week_start < month_start:
        week_start = month_start
    if week_end > month_end:
        week_end = month_end

    return week_start, week_end


def get_weekly_performance_usd(user_id: int) -> float:
    today = malaysia_now().date()
    start_date, end_date = _bounded_current_week(today)
    return _sum_trading_net_between(user_id, start_date, end_date)


def get_monthly_performance_usd(user_id: int) -> float:
    today = malaysia_now().date()
    month_start, month_end = _month_range(today)
    return _sum_trading_net_between(user_id, month_start, month_end)


def has_any_transactions(user_id: int) -> bool:
    db = load_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {})

    def _has_records(data: Any) -> bool:
        if isinstance(data, list):
            return len(data) > 0
        if isinstance(data, dict):
            records = data.get("records")
            if isinstance(records, list):
                return len(records) > 0
            return len(data) > 0
        return bool(data)

    # Legacy section (older schema)
    tx = sections.get("transactions", {}).get("data")
    if _has_records(tx):
        return True

    # Active sections in current schema
    for section_name in ("deposit_activity", "withdrawal_activity", "trading_activity", "tabung"):
        section_data = sections.get(section_name, {}).get("data")
        if _has_records(section_data):
            return True

    return False


def can_reset_initial_capital(user_id: int) -> bool:
    return not has_any_transactions(user_id)


def has_project_grow_goal(user_id: int) -> bool:
    sections = _get_user_sections(user_id)
    goal_data = sections.get("project_grow_goal", {}).get("data", {})
    try:
        return float(goal_data.get("target_balance_usd") or 0) > 0
    except (TypeError, ValueError):
        return False


def get_project_grow_goal_summary(user_id: int) -> dict[str, Any]:
    sections = _get_user_sections(user_id)
    goal_data = sections.get("project_grow_goal", {}).get("data", {})

    def _to_float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    return {
        "target_balance_usd": _to_float(goal_data.get("target_balance_usd")),
        "unlock_amount_usd": _to_float(goal_data.get("unlock_amount_usd")),
        "minimum_target_usd": _to_float(goal_data.get("minimum_target_usd")),
        "current_balance_usd": _to_float(goal_data.get("current_balance_usd")),
        "target_days": int(goal_data.get("target_days") or 0) if str(goal_data.get("target_days") or "").isdigit() else 0,
        "target_label": str(goal_data.get("target_label") or ""),
    }


def can_open_project_grow_mission(user_id: int) -> bool:
    return has_project_grow_goal(user_id) and get_tabung_balance_usd(user_id) >= 10


def get_tabung_start_date(user_id: int) -> str:
    sections = _get_user_sections(user_id)
    tabung_section = sections.get("tabung", {})
    tabung_data = tabung_section.get("data", {})

    earliest: date | None = None

    records = tabung_data.get("records") if isinstance(tabung_data, dict) else None
    if isinstance(records, list):
        for rec in records:
            if not isinstance(rec, dict):
                continue
            rec_date = _record_date_myt(rec)
            if rec_date is None:
                continue
            if earliest is None or rec_date < earliest:
                earliest = rec_date

    if earliest is not None:
        return earliest.isoformat()

    saved_date = tabung_section.get("saved_date")
    if isinstance(saved_date, str) and saved_date:
        return saved_date

    return "-"


def get_project_grow_mission_state(user_id: int) -> dict[str, Any]:
    sections = _get_user_sections(user_id)
    mission_data = sections.get("project_grow_mission", {}).get("data", {})
    mode = str(mission_data.get("mode") or "")
    active = bool(mission_data.get("active")) and mode in {"normal", "advanced"}

    return {
        "active": active,
        "mode": mode if active else "",
        "started_at": str(mission_data.get("started_at") or ""),
        "started_date": str(mission_data.get("started_date") or ""),
    }


def get_project_grow_mission_status_text(user_id: int) -> str:
    state = get_project_grow_mission_state(user_id)
    if state["active"]:
        return f"Active ({state['mode'].capitalize()})"
    if can_open_project_grow_mission(user_id):
        return "Ready to Start"
    return "Locked"


def apply_project_grow_unlock_to_tabung(user_id: int, unlock_amount_usd: float) -> bool:
    if unlock_amount_usd < 10:
        return False

    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    sections = user.setdefault("sections", {})
    tabung_section = sections.setdefault(
        "tabung",
        {
            "section": "tabung",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"balance_usd": 0.0, "records": []},
        },
    )

    tabung_data = tabung_section.setdefault("data", {})
    records = tabung_data.setdefault("records", [])
    current_balance = 0.0
    for key in ("balance_usd", "tabung_balance_usd", "current_balance_usd", "amount_usd"):
        try:
            current_balance = float(tabung_data.get(key, 0))
            break
        except (TypeError, ValueError):
            continue
    new_balance = max(current_balance, float(unlock_amount_usd))

    tabung_data["balance_usd"] = new_balance
    records.append(
        {
            "mode": "project_grow_unlock",
            "amount_usd": float(unlock_amount_usd),
            "balance_after_usd": new_balance,
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
        }
    )

    tabung_section["saved_at"] = saved_at_iso
    tabung_section["saved_date"] = saved_date
    tabung_section["saved_time"] = saved_time
    tabung_section["timezone"] = "Asia/Kuala_Lumpur"
    user["updated_at"] = saved_at_iso
    save_db(db)
    return True


def start_project_grow_mission(user_id: int, mode: str) -> bool:
    mode = (mode or "").strip().lower()
    if mode not in {"normal", "advanced"}:
        return False
    if not can_open_project_grow_mission(user_id):
        return False

    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    sections = user.setdefault("sections", {})
    sections["project_grow_mission"] = {
        "section": "project_grow_mission",
        "user_id": user_id,
        "telegram_name": user.get("telegram_name") or str(user_id),
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
        "data": {
            "active": True,
            "mode": mode,
            "started_at": saved_at_iso,
            "started_date": saved_date,
        },
    }

    user["updated_at"] = saved_at_iso
    save_db(db)
    return True


def reset_project_grow_mission(user_id: int) -> bool:
    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    sections = user.setdefault("sections", {})
    if "project_grow_mission" not in sections:
        return False

    sections.pop("project_grow_mission", None)
    user["updated_at"] = malaysia_now().isoformat()
    save_db(db)
    return True


def reset_project_grow_goal(user_id: int) -> bool:
    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    sections = user.setdefault("sections", {})
    changed = False
    if "project_grow_goal" in sections:
        sections.pop("project_grow_goal", None)
        changed = True
    if "project_grow_mission" in sections:
        sections.pop("project_grow_mission", None)
        changed = True

    if not changed:
        return False

    user["updated_at"] = malaysia_now().isoformat()
    save_db(db)
    return True


def reset_all_data() -> None:
    save_db(_default_db())


def save_user_setup_section(
    user_id: int,
    telegram_name: str,
    section: str,
    payload: dict[str, Any],
) -> None:
    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    db = load_db()
    users = db.setdefault("users", {})
    user_key = str(user_id)
    user_obj = users.setdefault(
        user_key,
        {
            "user_id": user_id,
            "telegram_name": telegram_name,
            "sections": {},
        },
    )

    user_obj["user_id"] = user_id
    user_obj["telegram_name"] = telegram_name
    user_obj["updated_at"] = saved_at_iso

    sections = user_obj.setdefault("sections", {})
    sections[section] = {
        "section": section,
        "user_id": user_id,
        "telegram_name": telegram_name,
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
        "data": payload,
    }

    save_db(db)


def _append_activity_record(user_id: int, section_name: str, reason: str, amount_usd: float, current_profit_usd: float) -> bool:
    if amount_usd <= 0:
        return False

    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    sections = user.setdefault("sections", {})
    activity_section = sections.setdefault(
        section_name,
        {
            "section": section_name,
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"records": []},
        },
    )

    records = activity_section.setdefault("data", {}).setdefault("records", [])
    records.append(
        {
            "amount_usd": float(amount_usd),
            "reason": reason,
            "current_profit_usd": float(current_profit_usd),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
        }
    )

    activity_section["saved_at"] = saved_at_iso
    activity_section["saved_date"] = saved_date
    activity_section["saved_time"] = saved_time
    activity_section["timezone"] = "Asia/Kuala_Lumpur"

    user["updated_at"] = saved_at_iso
    save_db(db)
    return True


def add_withdrawal_activity(user_id: int, reason: str, amount_usd: float, current_profit_usd: float) -> bool:
    return _append_activity_record(user_id, "withdrawal_activity", reason, amount_usd, current_profit_usd)


def add_deposit_activity(user_id: int, reason: str, amount_usd: float, current_profit_usd: float) -> bool:
    return _append_activity_record(user_id, "deposit_activity", reason, amount_usd, current_profit_usd)


def add_trading_activity_update(user_id: int, mode: str, amount_usd: float) -> bool:
    if mode not in {"profit", "loss"}:
        return False
    if amount_usd <= 0:
        return False

    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    net_usd = float(amount_usd) if mode == "profit" else -float(amount_usd)

    sections = user.setdefault("sections", {})
    trading_section = sections.setdefault(
        "trading_activity",
        {
            "section": "trading_activity",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"records": [], "current_profit_usd": 0.0},
        },
    )

    trading_data = trading_section.setdefault("data", {})
    records = trading_data.setdefault("records", [])
    running_profit = float(trading_data.get("current_profit_usd", 0) or 0)
    running_profit += net_usd

    records.append(
        {
            "mode": mode,
            "amount_usd": float(amount_usd),
            "net_usd": net_usd,
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
        }
    )

    trading_data["current_profit_usd"] = running_profit

    trading_section["saved_at"] = saved_at_iso
    trading_section["saved_date"] = saved_date
    trading_section["saved_time"] = saved_time
    trading_section["timezone"] = "Asia/Kuala_Lumpur"

    user["updated_at"] = saved_at_iso
    save_db(db)
    return True


def apply_initial_capital_reset(user_id: int, new_initial_capital: float) -> bool:
    if new_initial_capital <= 0:
        return False

    db = load_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    sections = user.setdefault("sections", {})
    initial_setup = sections.get("initial_setup")
    if not initial_setup:
        return False

    if has_any_transactions(user_id):
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    init_data = initial_setup.setdefault("data", {})
    init_data["initial_capital_usd"] = float(new_initial_capital)

    initial_setup["saved_at"] = saved_at_iso
    initial_setup["saved_date"] = saved_date
    initial_setup["saved_time"] = saved_time
    initial_setup["timezone"] = "Asia/Kuala_Lumpur"

    # Legacy cleanup for older schema.
    sections.pop("transactions", None)

    user["updated_at"] = saved_at_iso
    save_db(db)
    return True
