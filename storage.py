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
