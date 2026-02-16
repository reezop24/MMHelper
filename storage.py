"""Simple JSON storage for MM HELPER setup data."""

from __future__ import annotations

import json
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


def has_any_transactions(user_id: int) -> bool:
    db = load_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {})
    tx = sections.get("transactions", {}).get("data")

    if isinstance(tx, list):
        return len(tx) > 0
    if isinstance(tx, dict):
        return len(tx) > 0
    return bool(tx)


def can_reset_initial_capital(user_id: int) -> bool:
    return not has_any_transactions(user_id)


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


def add_withdrawal_activity(user_id: int, reason: str, amount_usd: float, current_profit_usd: float) -> bool:
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
    withdrawal_section = sections.setdefault(
        "withdrawal_activity",
        {
            "section": "withdrawal_activity",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"records": []},
        },
    )

    records = withdrawal_section.setdefault("data", {}).setdefault("records", [])
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

    withdrawal_section["saved_at"] = saved_at_iso
    withdrawal_section["saved_date"] = saved_date
    withdrawal_section["saved_time"] = saved_time
    withdrawal_section["timezone"] = "Asia/Kuala_Lumpur"

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

    # Rekod lama berkaitan kiraan dibersihkan.
    sections.pop("transactions", None)

    user["updated_at"] = saved_at_iso
    save_db(db)
    return True
