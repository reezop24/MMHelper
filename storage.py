"""Simple JSON storage for MM HELPER setup data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def save_user_setup(user_id: int, payload: dict[str, Any]) -> None:
    db = load_db()
    users = db.setdefault("users", {})
    users[str(user_id)] = payload
    save_db(db)
