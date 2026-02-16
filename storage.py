"""JSON storage for MM HELPER with split core + monthly activity DB."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from time_utils import malaysia_now

CORE_DB_PATH = Path(__file__).with_name("mmhelper_core.json")
LEGACY_DB_PATH = Path(__file__).with_name("mmhelper_db.json")
ACTIVITY_DB_DIR = Path(__file__).with_name("db") / "activity"
ACTIVITY_FILE_PREFIX = "activity_"


def _default_core_db() -> dict[str, Any]:
    return {"users": {}}


def _default_activity_db(month_key: str) -> dict[str, Any]:
    return {"month": month_key.replace("_", "-"), "users": {}}


def _default_rollup() -> dict[str, Any]:
    return {
        "total_deposit_usd": 0.0,
        "total_withdrawal_usd": 0.0,
        "total_trading_net_usd": 0.0,
        "total_balance_adjustment_usd": 0.0,
        "deposit_record_count": 0,
        "withdrawal_record_count": 0,
        "trading_record_count": 0,
        "balance_adjustment_record_count": 0,
        "last_activity_at": "",
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _load_json_dict(path: Path, default_factory) -> dict[str, Any]:
    if not path.exists():
        return default_factory()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return default_factory()
    if not isinstance(data, dict):
        return default_factory()
    return data


def _save_json_dict(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_core_db(data: dict[str, Any]) -> dict[str, Any]:
    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    return data


def load_core_db() -> dict[str, Any]:
    core_db = _load_json_dict(CORE_DB_PATH, _default_core_db)
    core_db = _normalize_core_db(core_db)

    if CORE_DB_PATH.exists():
        return core_db

    # One-way bootstrap for existing installs using legacy single DB.
    legacy_db = _load_json_dict(LEGACY_DB_PATH, _default_core_db)
    legacy_db = _normalize_core_db(legacy_db)
    if legacy_db.get("users"):
        _save_json_dict(CORE_DB_PATH, legacy_db)
        return legacy_db
    return core_db


def save_core_db(data: dict[str, Any]) -> None:
    _save_json_dict(CORE_DB_PATH, _normalize_core_db(data))


# Backward-compatible names used by older code.
def load_db() -> dict[str, Any]:
    return load_core_db()


def save_db(data: dict[str, Any]) -> None:
    save_core_db(data)


def _month_key_from_date(dt: date) -> str:
    return dt.strftime("%Y_%m")


def _activity_db_path(month_key: str) -> Path:
    return ACTIVITY_DB_DIR / f"{ACTIVITY_FILE_PREFIX}{month_key}.json"


def _load_activity_db(month_key: str) -> dict[str, Any]:
    data = _load_json_dict(_activity_db_path(month_key), lambda: _default_activity_db(month_key))
    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    if not isinstance(data.get("month"), str):
        data["month"] = month_key.replace("_", "-")
    return data


def _save_activity_db(month_key: str, data: dict[str, Any]) -> None:
    _save_json_dict(_activity_db_path(month_key), data)


def _iter_activity_month_keys() -> list[str]:
    if not ACTIVITY_DB_DIR.exists():
        return []

    month_keys: list[str] = []
    for path in ACTIVITY_DB_DIR.glob(f"{ACTIVITY_FILE_PREFIX}*.json"):
        stem = path.stem
        raw = stem[len(ACTIVITY_FILE_PREFIX) :]
        parts = raw.split("_")
        if len(parts) != 2:
            continue
        year, month = parts
        if not (year.isdigit() and month.isdigit()):
            continue
        month_int = int(month)
        if month_int < 1 or month_int > 12:
            continue
        month_keys.append(f"{year}_{month.zfill(2)}")
    return sorted(set(month_keys))


def _iter_month_keys_between(start_date: date, end_date: date) -> Iterator[str]:
    cur = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    while cur <= end_month:
        yield _month_key_from_date(cur)
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)


def _get_activity_records_from_db(activity_db: dict[str, Any], user_id: int, section_name: str) -> list[dict[str, Any]]:
    users = activity_db.get("users", {})
    user_bucket = users.get(str(user_id), {})
    section_bucket = user_bucket.get(section_name, {})
    records = section_bucket.get("records", [])
    if not isinstance(records, list):
        return []
    return [r for r in records if isinstance(r, dict)]


def _append_monthly_record(user_id: int, section_name: str, record: dict[str, Any], record_date: date) -> None:
    month_key = _month_key_from_date(record_date)
    db = _load_activity_db(month_key)
    users = db.setdefault("users", {})
    user_bucket = users.setdefault(str(user_id), {})
    section_bucket = user_bucket.setdefault(section_name, {"records": []})
    records = section_bucket.setdefault("records", [])
    if not isinstance(records, list):
        records = []
        section_bucket["records"] = records
    records.append(record)
    _save_activity_db(month_key, db)


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
        total += _to_float(item.get(field, 0))
    return total


def _get_user_sections(user_id: int) -> dict[str, Any]:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id), {})
    return user.get("sections", {})


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
    amount = _to_float(record.get("amount_usd", 0))
    if mode == "loss":
        return -abs(amount)
    return abs(amount)


def _iter_legacy_section_records(user_id: int, section_name: str) -> list[dict[str, Any]]:
    sections = _get_user_sections(user_id)
    section_data = sections.get(section_name, {}).get("data")
    if isinstance(section_data, dict):
        records = section_data.get("records", [])
        if isinstance(records, list):
            return [r for r in records if isinstance(r, dict)]
    if isinstance(section_data, list):
        return [r for r in section_data if isinstance(r, dict)]
    return []


def _iter_section_records_between(user_id: int, section_name: str, start_date: date, end_date: date) -> Iterator[dict[str, Any]]:
    # Legacy records still living in core DB.
    for record in _iter_legacy_section_records(user_id, section_name):
        rec_date = _record_date_myt(record)
        if rec_date is None:
            continue
        if start_date <= rec_date <= end_date:
            yield record

    # New records from monthly activity DB.
    for month_key in _iter_month_keys_between(start_date, end_date):
        monthly_db = _load_activity_db(month_key)
        for record in _get_activity_records_from_db(monthly_db, user_id, section_name):
            rec_date = _record_date_myt(record)
            if rec_date is None:
                continue
            if start_date <= rec_date <= end_date:
                yield record


def _sum_trading_net_between(user_id: int, start_date: date, end_date: date) -> float:
    total = 0.0
    for record in _iter_section_records_between(user_id, "trading_activity", start_date, end_date):
        total += _record_net_usd(record)
    for record in _iter_section_records_between(user_id, "balance_adjustment", start_date, end_date):
        total += _record_net_usd(record)
    return total


def _is_rollup_valid(rollup: Any) -> bool:
    if not isinstance(rollup, dict):
        return False
    required = {
        "total_deposit_usd",
        "total_withdrawal_usd",
        "total_trading_net_usd",
        "total_balance_adjustment_usd",
        "deposit_record_count",
        "withdrawal_record_count",
        "trading_record_count",
        "balance_adjustment_record_count",
        "last_activity_at",
    }
    return required.issubset(set(rollup.keys()))


def _normalize_rollup(rollup: dict[str, Any]) -> dict[str, Any]:
    out = _default_rollup()
    out["total_deposit_usd"] = _to_float(rollup.get("total_deposit_usd"))
    out["total_withdrawal_usd"] = _to_float(rollup.get("total_withdrawal_usd"))
    out["total_trading_net_usd"] = _to_float(rollup.get("total_trading_net_usd"))
    out["total_balance_adjustment_usd"] = _to_float(rollup.get("total_balance_adjustment_usd"))
    out["deposit_record_count"] = max(0, _to_int(rollup.get("deposit_record_count")))
    out["withdrawal_record_count"] = max(0, _to_int(rollup.get("withdrawal_record_count")))
    out["trading_record_count"] = max(0, _to_int(rollup.get("trading_record_count")))
    out["balance_adjustment_record_count"] = max(0, _to_int(rollup.get("balance_adjustment_record_count")))
    out["last_activity_at"] = str(rollup.get("last_activity_at") or "")
    return out


def _rebuild_rollup_for_user(user_id: int, user_obj: dict[str, Any]) -> dict[str, Any]:
    rollup = _default_rollup()
    sections = user_obj.get("sections", {})

    dep_legacy = sections.get("deposit_activity", {}).get("data", {}).get("records", [])
    wdr_legacy = sections.get("withdrawal_activity", {}).get("data", {}).get("records", [])
    trd_legacy = sections.get("trading_activity", {}).get("data", {}).get("records", [])
    adj_legacy = sections.get("balance_adjustment", {}).get("data", {}).get("records", [])

    if isinstance(dep_legacy, list):
        rollup["total_deposit_usd"] += _sum_records(dep_legacy, "amount_usd")
        rollup["deposit_record_count"] += len([r for r in dep_legacy if isinstance(r, dict)])
    if isinstance(wdr_legacy, list):
        rollup["total_withdrawal_usd"] += _sum_records(wdr_legacy, "amount_usd")
        rollup["withdrawal_record_count"] += len([r for r in wdr_legacy if isinstance(r, dict)])
    if isinstance(trd_legacy, list):
        for rec in trd_legacy:
            if isinstance(rec, dict):
                rollup["total_trading_net_usd"] += _record_net_usd(rec)
                rollup["trading_record_count"] += 1
    if isinstance(adj_legacy, list):
        for rec in adj_legacy:
            if isinstance(rec, dict):
                net = _record_net_usd(rec)
                rollup["total_balance_adjustment_usd"] += net
                rollup["balance_adjustment_record_count"] += 1

    for month_key in _iter_activity_month_keys():
        monthly_db = _load_activity_db(month_key)

        dep_records = _get_activity_records_from_db(monthly_db, user_id, "deposit_activity")
        wdr_records = _get_activity_records_from_db(monthly_db, user_id, "withdrawal_activity")
        trd_records = _get_activity_records_from_db(monthly_db, user_id, "trading_activity")
        adj_records = _get_activity_records_from_db(monthly_db, user_id, "balance_adjustment")

        rollup["total_deposit_usd"] += _sum_records(dep_records, "amount_usd")
        rollup["total_withdrawal_usd"] += _sum_records(wdr_records, "amount_usd")
        for rec in trd_records:
            rollup["total_trading_net_usd"] += _record_net_usd(rec)
        for rec in adj_records:
            net = _record_net_usd(rec)
            rollup["total_balance_adjustment_usd"] += net

        rollup["deposit_record_count"] += len(dep_records)
        rollup["withdrawal_record_count"] += len(wdr_records)
        rollup["trading_record_count"] += len(trd_records)
        rollup["balance_adjustment_record_count"] += len(adj_records)

    return _normalize_rollup(rollup)


def _get_user_rollup(user_id: int) -> dict[str, Any]:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return _default_rollup()

    rollup = user.get("stats_rollup")
    if _is_rollup_valid(rollup):
        return _normalize_rollup(rollup)

    rebuilt = _rebuild_rollup_for_user(user_id, user)
    user["stats_rollup"] = rebuilt
    user["updated_at"] = malaysia_now().isoformat()
    save_core_db(db)
    return rebuilt


def _bump_rollup(
    user_obj: dict[str, Any],
    *,
    saved_at_iso: str,
    deposit_delta: float = 0.0,
    withdrawal_delta: float = 0.0,
    trading_delta: float = 0.0,
    balance_adjustment_delta: float = 0.0,
    deposit_count: int = 0,
    withdrawal_count: int = 0,
    trading_count: int = 0,
    balance_adjustment_count: int = 0,
) -> None:
    rollup = _normalize_rollup(user_obj.get("stats_rollup", {}))
    rollup["total_deposit_usd"] += float(deposit_delta)
    rollup["total_withdrawal_usd"] += float(withdrawal_delta)
    rollup["total_trading_net_usd"] += float(trading_delta)
    rollup["total_balance_adjustment_usd"] += float(balance_adjustment_delta)
    rollup["deposit_record_count"] += int(deposit_count)
    rollup["withdrawal_record_count"] += int(withdrawal_count)
    rollup["trading_record_count"] += int(trading_count)
    rollup["balance_adjustment_record_count"] += int(balance_adjustment_count)
    if not rollup["last_activity_at"] or saved_at_iso > str(rollup["last_activity_at"]):
        rollup["last_activity_at"] = saved_at_iso
    user_obj["stats_rollup"] = _normalize_rollup(rollup)


def has_initial_setup(user_id: int) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {})
    return bool(sections.get("initial_setup"))


def get_initial_setup_summary(user_id: int) -> dict[str, Any]:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id), {})
    init_section = user.get("sections", {}).get("initial_setup", {})
    init_data = init_section.get("data", {})
    return {
        "name": init_data.get("name") or user.get("telegram_name") or f"User {user_id}",
        "initial_capital_usd": float(init_data.get("initial_capital_usd") or 0),
        "saved_date": init_section.get("saved_date") or "-",
    }


def get_current_profit_usd(user_id: int) -> float:
    rollup = _get_user_rollup(user_id)
    if rollup["trading_record_count"] > 0:
        return float(rollup["total_trading_net_usd"])

    # Fallback for old odd schemas.
    db = load_core_db()
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
    return float(_get_user_rollup(user_id)["total_withdrawal_usd"])


def get_total_deposit_usd(user_id: int) -> float:
    return float(_get_user_rollup(user_id)["total_deposit_usd"])


def get_total_balance_adjustment_usd(user_id: int) -> float:
    return float(_get_user_rollup(user_id)["total_balance_adjustment_usd"])


def get_total_balance_usd(user_id: int) -> float:
    return get_current_balance_usd(user_id) + get_tabung_balance_usd(user_id)


def _get_account_flow_balance_usd(user_id: int) -> float:
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


def get_current_balance_usd(user_id: int) -> float:
    total_balance = _get_account_flow_balance_usd(user_id)
    current_profit = get_current_profit_usd(user_id)
    total_adjustment = get_total_balance_adjustment_usd(user_id)
    return total_balance + current_profit + total_adjustment


def _current_tabung_month_range() -> tuple[date, date]:
    today = malaysia_now().date()
    first_day = today.replace(day=1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first_day, next_month - timedelta(days=1)


def _count_tabung_mode_this_month(user_id: int, mode: str) -> int:
    start_date, end_date = _current_tabung_month_range()
    count = 0
    for record in _tabung_records_since(user_id, start_date):
        rec_date = _record_date_myt(record)
        if rec_date is None or rec_date > end_date:
            continue
        if str(record.get("mode") or "").strip().lower() == mode:
            count += 1
    return count


def get_tabung_update_state(user_id: int) -> dict[str, Any]:
    goal = get_project_grow_goal_summary(user_id)
    target_balance = _to_float(goal.get("target_balance_usd"))
    emergency_limit = 2
    used = _count_tabung_mode_this_month(user_id, "emergency_withdrawal")
    return {
        "target_balance_usd": target_balance,
        "goal_reached": is_project_grow_goal_reached(user_id),
        "emergency_limit": emergency_limit,
        "emergency_used": used,
        "emergency_left": max(emergency_limit - used, 0),
    }


def _ensure_tabung_section(user: dict[str, Any], user_id: int, saved_at_iso: str, saved_date: str, saved_time: str):
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
    if not isinstance(records, list):
        records = []
        tabung_data["records"] = records
    current_tabung_balance = get_tabung_balance_usd(user_id)
    return sections, tabung_section, tabung_data, records, current_tabung_balance


def _append_balance_adjustment_transfer(
    user: dict[str, Any],
    user_id: int,
    mode: str,
    net_usd: float,
    saved_at_iso: str,
    saved_date: str,
    saved_time: str,
    record_date: date,
) -> None:
    sections = user.setdefault("sections", {})
    _append_monthly_record(
        user_id,
        "balance_adjustment",
        {
            "mode": mode,
            "amount_usd": abs(float(net_usd)),
            "net_usd": float(net_usd),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
        },
        record_date,
    )

    adjustment_section = sections.setdefault(
        "balance_adjustment",
        {
            "section": "balance_adjustment",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"record_count": 0},
        },
    )
    adjustment_data = adjustment_section.setdefault("data", {})
    adjustment_data["record_count"] = _to_int(adjustment_data.get("record_count")) + 1
    adjustment_section["saved_at"] = saved_at_iso
    adjustment_section["saved_date"] = saved_date
    adjustment_section["saved_time"] = saved_time
    adjustment_section["timezone"] = "Asia/Kuala_Lumpur"
    _bump_rollup(
        user,
        saved_at_iso=saved_at_iso,
        balance_adjustment_delta=float(net_usd),
        balance_adjustment_count=1,
    )


def apply_tabung_update_action(user_id: int, action: str, amount_usd: float) -> tuple[bool, str]:
    action = str(action or "").strip().lower()
    amount = _to_float(amount_usd)
    if amount <= 0:
        return False, "Jumlah kena lebih dari 0."

    valid_actions = {"save", "emergency_withdrawal", "goal_to_current", "goal_direct_withdrawal"}
    if action not in valid_actions:
        return False, "Action tabung tak dikenali."

    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False, "User tak dijumpai."

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    _, tabung_section, tabung_data, records, current_tabung_balance = _ensure_tabung_section(
        user, user_id, saved_at_iso, saved_date, saved_time
    )
    current_balance = get_current_balance_usd(user_id)
    state = get_tabung_update_state(user_id)

    if action == "save":
        if amount > current_balance:
            return False, f"Current Balance tak cukup. Baki sekarang USD {current_balance:.2f}."
        new_balance = current_tabung_balance + amount
        records.append(
            {
                "mode": "save",
                "amount_usd": float(amount),
                "balance_after_usd": float(new_balance),
                "saved_at": saved_at_iso,
                "saved_date": saved_date,
                "saved_time": saved_time,
                "timezone": "Asia/Kuala_Lumpur",
            }
        )
        tabung_data["balance_usd"] = float(new_balance)
        _append_balance_adjustment_transfer(
            user,
            user_id,
            "tabung_save_transfer_out",
            -float(amount),
            saved_at_iso,
            saved_date,
            saved_time,
            now.date(),
        )

    elif action == "emergency_withdrawal":
        if state["emergency_left"] <= 0:
            return False, "Emergency withdrawal dah capai limit 2 kali bulan ni."
        if amount > current_tabung_balance:
            return False, f"Baki tabung tak cukup. Baki sekarang USD {current_tabung_balance:.2f}."
        new_balance = current_tabung_balance - amount
        records.append(
            {
                "mode": "emergency_withdrawal",
                "amount_usd": -float(amount),
                "balance_after_usd": float(new_balance),
                "saved_at": saved_at_iso,
                "saved_date": saved_date,
                "saved_time": saved_time,
                "timezone": "Asia/Kuala_Lumpur",
            }
        )
        tabung_data["balance_usd"] = float(new_balance)

    elif action == "goal_to_current":
        if not state["goal_reached"]:
            return False, "Action ni hanya boleh guna bila goal dah capai."
        if amount > current_tabung_balance:
            return False, f"Baki tabung tak cukup. Baki sekarang USD {current_tabung_balance:.2f}."
        new_balance = current_tabung_balance - amount
        records.append(
            {
                "mode": "goal_withdraw_to_current",
                "amount_usd": -float(amount),
                "balance_after_usd": float(new_balance),
                "saved_at": saved_at_iso,
                "saved_date": saved_date,
                "saved_time": saved_time,
                "timezone": "Asia/Kuala_Lumpur",
            }
        )
        tabung_data["balance_usd"] = float(new_balance)
        _append_balance_adjustment_transfer(
            user,
            user_id,
            "tabung_goal_withdraw_to_current",
            float(amount),
            saved_at_iso,
            saved_date,
            saved_time,
            now.date(),
        )

    elif action == "goal_direct_withdrawal":
        if not state["goal_reached"]:
            return False, "Action ni hanya boleh guna bila goal dah capai."
        if amount > current_tabung_balance:
            return False, f"Baki tabung tak cukup. Baki sekarang USD {current_tabung_balance:.2f}."
        new_balance = current_tabung_balance - amount
        records.append(
            {
                "mode": "goal_direct_withdrawal",
                "amount_usd": -float(amount),
                "balance_after_usd": float(new_balance),
                "saved_at": saved_at_iso,
                "saved_date": saved_date,
                "saved_time": saved_time,
                "timezone": "Asia/Kuala_Lumpur",
            }
        )
        tabung_data["balance_usd"] = float(new_balance)

    tabung_section["saved_at"] = saved_at_iso
    tabung_section["saved_date"] = saved_date
    tabung_section["saved_time"] = saved_time
    tabung_section["timezone"] = "Asia/Kuala_Lumpur"
    user["updated_at"] = saved_at_iso
    save_core_db(db)

    return True, "ok"


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


def get_weekly_profit_loss_usd(user_id: int) -> float:
    # Mingguan: Ahad-Sabtu, dan dipotong ikut sempadan bulan semasa.
    return get_weekly_performance_usd(user_id)


def get_monthly_profit_loss_usd(user_id: int) -> float:
    return get_monthly_performance_usd(user_id)


def _record_datetime_myt(record: dict[str, Any]) -> datetime | None:
    tzinfo = malaysia_now().tzinfo
    saved_at = record.get("saved_at")
    if isinstance(saved_at, str) and saved_at.strip():
        try:
            dt = datetime.fromisoformat(saved_at.strip())
            if dt.tzinfo is None:
                return dt.replace(tzinfo=tzinfo)
            return dt.astimezone(tzinfo)
        except ValueError:
            pass

    saved_date = str(record.get("saved_date") or "").strip()
    saved_time = str(record.get("saved_time") or "00:00:00").strip() or "00:00:00"
    if saved_date:
        try:
            dt = datetime.fromisoformat(f"{saved_date}T{saved_time}")
            return dt.replace(tzinfo=tzinfo)
        except ValueError:
            return None
    return None


def _build_transaction_history_entry(source: str, record: dict[str, Any]) -> dict[str, Any] | None:
    dt = _record_datetime_myt(record)
    if dt is None:
        return None

    label_map = {
        "deposit_activity": "Deposit",
        "withdrawal_activity": "Withdrawal",
        "trading_activity": "Trading",
        "balance_adjustment": "Adjustment",
        "tabung": "Tabung",
    }
    source_key = source if source in label_map else "transaction"
    amount = _to_float(record.get("amount_usd", 0.0))
    mode = str(record.get("mode") or "").lower()

    if source_key == "withdrawal_activity":
        amount = -abs(amount)
    elif source_key in {"trading_activity", "balance_adjustment"}:
        amount = _record_net_usd(record)

    return {
        "ts": dt.isoformat(),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"),
        "source": source_key,
        "label": label_map[source_key],
        "mode": mode,
        "amount_usd": round(amount, 2),
    }


def get_transaction_history_records(user_id: int, days: int, limit: int = 100) -> list[dict[str, Any]]:
    max_items = max(1, min(int(limit), 100))
    day_window = max(1, int(days))
    end_date = malaysia_now().date()
    start_date = end_date - timedelta(days=day_window - 1)
    hidden_adjustment_modes = {
        "project_grow_unlock_transfer_out",
        "project_grow_goal_reset_transfer",
        "tabung_save_transfer_out",
        "tabung_goal_withdraw_to_current",
    }

    rows: list[dict[str, Any]] = []
    for section_name in ("deposit_activity", "withdrawal_activity", "trading_activity", "balance_adjustment"):
        for record in _iter_section_records_between(user_id, section_name, start_date, end_date):
            if section_name == "balance_adjustment":
                mode = str(record.get("mode") or "").strip().lower()
                if mode in hidden_adjustment_modes:
                    continue
            item = _build_transaction_history_entry(section_name, record)
            if item is not None:
                rows.append(item)

    for record in _tabung_records_since(user_id, start_date):
        rec_date = _record_date_myt(record)
        if rec_date is None or rec_date > end_date:
            continue
        item = _build_transaction_history_entry("tabung", record)
        if item is not None:
            rows.append(item)

    rows.sort(key=lambda r: str(r.get("ts") or ""), reverse=True)
    return rows[:max_items]


def has_any_transactions(user_id: int) -> bool:
    rollup = _get_user_rollup(user_id)
    if (
        rollup["deposit_record_count"] > 0
        or rollup["withdrawal_record_count"] > 0
        or rollup["trading_record_count"] > 0
        or rollup["balance_adjustment_record_count"] > 0
    ):
        return True

    db = load_core_db()
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

    tx = sections.get("transactions", {}).get("data")
    if _has_records(tx):
        return True

    # Tabung remains in core DB.
    tabung_data = sections.get("tabung", {}).get("data")
    if _has_records(tabung_data):
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

    return {
        "target_balance_usd": _to_float(goal_data.get("target_balance_usd")),
        "unlock_amount_usd": _to_float(goal_data.get("unlock_amount_usd")),
        "minimum_target_usd": _to_float(goal_data.get("minimum_target_usd")),
        "current_balance_usd": _to_float(goal_data.get("current_balance_usd")),
        "target_days": int(goal_data.get("target_days") or 0) if str(goal_data.get("target_days") or "").isdigit() else 0,
        "target_label": str(goal_data.get("target_label") or ""),
    }


def is_project_grow_goal_reached(user_id: int) -> bool:
    goal = get_project_grow_goal_summary(user_id)
    target_balance = _to_float(goal.get("target_balance_usd"))
    baseline_balance = _to_float(goal.get("current_balance_usd"))
    grow_target = max(target_balance - baseline_balance, 0.0)
    if grow_target <= 0:
        return False
    return get_tabung_balance_usd(user_id) >= grow_target


def get_tabung_progress_summary(user_id: int) -> dict[str, Any]:
    goal = get_project_grow_goal_summary(user_id)
    sections = _get_user_sections(user_id)
    goal_section = sections.get("project_grow_goal", {})

    tabung_balance = get_tabung_balance_usd(user_id)
    target_balance = _to_float(goal.get("target_balance_usd"))
    baseline_balance = _to_float(goal.get("current_balance_usd"))
    total_grow_target = max(target_balance - baseline_balance, 0.0)
    achieved = max(tabung_balance, 0.0)
    remaining_grow_target = max(total_grow_target - achieved, 0.0)
    grow_progress_pct = 0.0 if total_grow_target <= 0 else min((achieved / total_grow_target) * 100.0, 100.0)

    target_days = int(goal.get("target_days") or 0)
    saved_date = _parse_iso_date(goal_section.get("saved_date"))
    today = malaysia_now().date()
    if saved_date is None:
        saved_date = today

    elapsed_days = max((today - saved_date).days, 0)
    days_left = max(target_days - elapsed_days, 0) if target_days > 0 else 0
    if target_days > 0:
        days_left_label = f"{days_left} hari lagi"
    else:
        days_left_label = "-"

    return {
        "tabung_balance_usd": tabung_balance,
        "grow_target_usd": remaining_grow_target,
        "days_left": days_left,
        "days_left_label": days_left_label,
        "grow_progress_pct": grow_progress_pct,
        "weekly_grow_usd": get_weekly_profit_loss_usd(user_id),
        "monthly_grow_usd": get_monthly_profit_loss_usd(user_id),
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


def _parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _mission_start_date(user_id: int) -> date | None:
    state = get_project_grow_mission_state(user_id)
    started_date = _parse_iso_date(state.get("started_date"))
    if started_date is not None:
        return started_date

    started_at = str(state.get("started_at") or "").strip()
    if started_at:
        try:
            dt = datetime.fromisoformat(started_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=malaysia_now().tzinfo)
            else:
                dt = dt.astimezone(malaysia_now().tzinfo)
            return dt.date()
        except ValueError:
            return None
    return None


def _iter_dates_since(user_id: int, section_name: str, start_date: date, end_date: date) -> Iterator[date]:
    for record in _iter_section_records_between(user_id, section_name, start_date, end_date):
        rec_date = _record_date_myt(record)
        if rec_date is None:
            continue
        yield rec_date


def _consecutive_days_from_start(start_date: date, end_date: date, day_set: set[date]) -> int:
    cur = start_date
    count = 0
    while cur <= end_date:
        if cur not in day_set:
            break
        count += 1
        cur += timedelta(days=1)
    return count


def _tabung_records_since(user_id: int, start_date: date) -> list[dict[str, Any]]:
    sections = _get_user_sections(user_id)
    tabung_data = sections.get("tabung", {}).get("data", {})
    records = tabung_data.get("records") if isinstance(tabung_data, dict) else []
    if not isinstance(records, list):
        return []

    out: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        rec_date = _record_date_myt(record)
        if rec_date is None:
            continue
        if rec_date >= start_date:
            out.append(record)
    return out


def get_mission_progress_summary(user_id: int) -> dict[str, str]:
    state = get_project_grow_mission_state(user_id)
    mission_status = get_project_grow_mission_status_text(user_id)

    if not state["active"]:
        return {
            "active": "0",
            "mode_level": "-",
            "mission_status": mission_status,
            "progress_count": "0/4",
            "mission_1": "Mission 1 : in progress 0/14",
            "mission_2": "Mission 2 : in progress 0/14",
            "mission_3": "Mission 3 : in progress 0/30",
            "mission_4": "Mission 4 : in progress 0%",
        }

    start_date = _mission_start_date(user_id) or malaysia_now().date()
    today = malaysia_now().date()
    if start_date > today:
        start_date = today

    mode_level = f"{state['mode'].capitalize()} | Level 1"

    # Mission 1: 14 hari berturut-turut update (guna aktiviti yang direkod dalam bot).
    update_days: set[date] = set()
    for section_name in ("deposit_activity", "withdrawal_activity", "trading_activity"):
        update_days.update(_iter_dates_since(user_id, section_name, start_date, today))
    mission1_days = _consecutive_days_from_start(start_date, today, update_days)
    mission1_pass = mission1_days >= 14
    mission1_status = "_PASS_" if mission1_pass else "in progress"
    mission1_text = f"Mission 1 : {mission1_status} {min(mission1_days, 14)}/14"

    # Mission 2: 14 hari berturut-turut trading update + minimum 2 transaksi tabung.
    trading_days = set(_iter_dates_since(user_id, "trading_activity", start_date, today))
    mission2_days = _consecutive_days_from_start(start_date, today, trading_days)
    tabung_tx_count = len(_tabung_records_since(user_id, start_date))
    mission2_pass = mission2_days >= 14 and tabung_tx_count >= 2
    mission2_status = "_PASS_" if mission2_pass else "in progress"
    mission2_text = f"Mission 2 : {mission2_status} {min(mission2_days, 14)}/14"

    # Mission 3: jaga had daily max loss selama 30 hari.
    sections = _get_user_sections(user_id)
    init_data = sections.get("initial_setup", {}).get("data", {})
    max_daily_loss_pct = _to_float(init_data.get("max_daily_loss_pct"))
    initial_capital = _to_float(init_data.get("initial_capital_usd"))
    max_daily_loss_usd = (initial_capital * max_daily_loss_pct) / 100.0 if max_daily_loss_pct > 0 else 0.0

    daily_net: dict[date, float] = {}
    for record in _iter_section_records_between(user_id, "trading_activity", start_date, today):
        rec_date = _record_date_myt(record)
        if rec_date is None:
            continue
        daily_net[rec_date] = daily_net.get(rec_date, 0.0) + _record_net_usd(record)

    mission3_days = 0
    mission3_failed = False
    cur = start_date
    while cur <= today:
        day_net = daily_net.get(cur, 0.0)
        if max_daily_loss_usd > 0 and day_net < -abs(max_daily_loss_usd):
            mission3_failed = True
            break
        mission3_days += 1
        cur += timedelta(days=1)

    mission3_pass = mission3_days >= 30 and not mission3_failed
    if mission3_pass:
        mission3_status = "_PASS_"
    elif mission3_failed:
        mission3_status = "_FAIL_"
    else:
        mission3_status = "in progress"
    mission3_text = f"Mission 3 : {mission3_status} {min(mission3_days, 30)}/30"

    # Mission 4: capai 100% grow target melalui amount yang disimpan dalam tabung.
    goal = get_project_grow_goal_summary(user_id)
    baseline_balance = _to_float(goal.get("current_balance_usd"))
    target_balance = _to_float(goal.get("target_balance_usd"))
    grow_target = max(target_balance - baseline_balance, 0.0)
    achieved = max(get_tabung_balance_usd(user_id), 0.0)
    mission4_pct = 0.0 if grow_target <= 0 else min((achieved / grow_target) * 100.0, 100.0)
    mission4_pass = mission4_pct >= 100 and grow_target > 0
    if mission4_pass:
        mission4_text = "Mission 4 : _PASS_ 100%"
    else:
        mission4_text = f"Mission 4 : in progress {mission4_pct:.0f}%"

    pass_count = 0
    if mission1_pass:
        pass_count += 1
    if mission2_pass:
        pass_count += 1
    if mission3_pass:
        pass_count += 1
    if mission4_pass:
        pass_count += 1

    return {
        "active": "1",
        "mode_level": mode_level,
        "mission_status": mission_status,
        "progress_count": f"{pass_count}/4",
        "mission_1": mission1_text,
        "mission_2": mission2_text,
        "mission_3": mission3_text,
        "mission_4": mission4_text,
    }


def apply_project_grow_unlock_to_tabung(user_id: int, unlock_amount_usd: float) -> bool:
    if unlock_amount_usd < 10:
        return False

    db = load_core_db()
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
    current_tabung_balance = 0.0
    for key in ("balance_usd", "tabung_balance_usd", "current_balance_usd", "amount_usd"):
        try:
            current_tabung_balance = float(tabung_data.get(key, 0))
            break
        except (TypeError, ValueError):
            continue
    new_balance = current_tabung_balance + float(unlock_amount_usd)

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

    # Transfer out from current balance into tabung.
    _append_monthly_record(
        user_id,
        "balance_adjustment",
        {
            "mode": "project_grow_unlock_transfer_out",
            "amount_usd": float(unlock_amount_usd),
            "net_usd": -float(unlock_amount_usd),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
        },
        now.date(),
    )
    adjustment_section = sections.setdefault(
        "balance_adjustment",
        {
            "section": "balance_adjustment",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"record_count": 0},
        },
    )
    adjustment_data = adjustment_section.setdefault("data", {})
    adjustment_data["record_count"] = _to_int(adjustment_data.get("record_count")) + 1
    adjustment_section["saved_at"] = saved_at_iso
    adjustment_section["saved_date"] = saved_date
    adjustment_section["saved_time"] = saved_time
    adjustment_section["timezone"] = "Asia/Kuala_Lumpur"

    tabung_section["saved_at"] = saved_at_iso
    tabung_section["saved_date"] = saved_date
    tabung_section["saved_time"] = saved_time
    tabung_section["timezone"] = "Asia/Kuala_Lumpur"
    _bump_rollup(
        user,
        saved_at_iso=saved_at_iso,
        balance_adjustment_delta=-float(unlock_amount_usd),
        balance_adjustment_count=1,
    )
    user["updated_at"] = saved_at_iso
    save_core_db(db)
    return True


def start_project_grow_mission(user_id: int, mode: str) -> bool:
    mode = (mode or "").strip().lower()
    if mode not in {"normal", "advanced"}:
        return False
    if not can_open_project_grow_mission(user_id):
        return False

    db = load_core_db()
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
    save_core_db(db)
    return True


def reset_project_grow_mission(user_id: int) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    sections = user.setdefault("sections", {})
    if "project_grow_mission" not in sections:
        return False

    sections.pop("project_grow_mission", None)
    user["updated_at"] = malaysia_now().isoformat()
    save_core_db(db)
    return True


def reset_project_grow_goal(user_id: int) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    sections = user.setdefault("sections", {})
    has_goal = "project_grow_goal" in sections
    has_mission = "project_grow_mission" in sections
    if not has_goal and not has_mission:
        return False

    changed = False
    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    transfer_amount = max(get_tabung_balance_usd(user_id), 0.0)
    if transfer_amount > 0:
        record = {
            "mode": "project_grow_goal_reset_transfer",
            "amount_usd": float(transfer_amount),
            "net_usd": float(transfer_amount),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
        }
        _append_monthly_record(user_id, "balance_adjustment", record, now.date())

        adjustment_section = sections.setdefault(
            "balance_adjustment",
            {
                "section": "balance_adjustment",
                "user_id": user_id,
                "telegram_name": user.get("telegram_name") or str(user_id),
                "saved_at": saved_at_iso,
                "saved_date": saved_date,
                "saved_time": saved_time,
                "timezone": "Asia/Kuala_Lumpur",
                "data": {"record_count": 0},
            },
        )
        adjustment_data = adjustment_section.setdefault("data", {})
        adjustment_data["record_count"] = _to_int(adjustment_data.get("record_count")) + 1
        adjustment_section["saved_at"] = saved_at_iso
        adjustment_section["saved_date"] = saved_date
        adjustment_section["saved_time"] = saved_time
        adjustment_section["timezone"] = "Asia/Kuala_Lumpur"

        tabung_section = sections.get("tabung", {})
        if isinstance(tabung_section, dict):
            tabung_data = tabung_section.setdefault("data", {})
            records = tabung_data.setdefault("records", [])
            if isinstance(records, list):
                records.append(
                    {
                        "mode": "project_grow_goal_reset_transfer_out",
                        "amount_usd": -float(transfer_amount),
                        "balance_after_usd": 0.0,
                        "saved_at": saved_at_iso,
                        "saved_date": saved_date,
                        "saved_time": saved_time,
                        "timezone": "Asia/Kuala_Lumpur",
                    }
                )
            tabung_data["balance_usd"] = 0.0
            tabung_section["saved_at"] = saved_at_iso
            tabung_section["saved_date"] = saved_date
            tabung_section["saved_time"] = saved_time
            tabung_section["timezone"] = "Asia/Kuala_Lumpur"

        _bump_rollup(
            user,
            saved_at_iso=saved_at_iso,
            balance_adjustment_delta=float(transfer_amount),
            balance_adjustment_count=1,
        )

    if has_goal:
        sections.pop("project_grow_goal", None)
        changed = True
    if has_mission:
        sections.pop("project_grow_mission", None)
        changed = True

    if not changed:
        return False

    user["updated_at"] = saved_at_iso
    save_core_db(db)
    return True


def reset_all_data() -> None:
    save_core_db(_default_core_db())
    if LEGACY_DB_PATH.exists():
        try:
            LEGACY_DB_PATH.unlink()
        except OSError:
            pass
    if ACTIVITY_DB_DIR.exists():
        for path in ACTIVITY_DB_DIR.glob(f"{ACTIVITY_FILE_PREFIX}*.json"):
            try:
                path.unlink()
            except OSError:
                continue


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

    db = load_core_db()
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

    save_core_db(db)


def _append_activity_record(user_id: int, section_name: str, reason: str, amount_usd: float, current_profit_usd: float) -> bool:
    if amount_usd <= 0:
        return False

    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    record = {
        "amount_usd": float(amount_usd),
        "reason": reason,
        "current_profit_usd": float(current_profit_usd),
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
    }
    _append_monthly_record(user_id, section_name, record, now.date())

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
            "data": {"record_count": 0},
        },
    )

    activity_data = activity_section.setdefault("data", {})
    activity_data["record_count"] = _to_int(activity_data.get("record_count")) + 1
    activity_section["saved_at"] = saved_at_iso
    activity_section["saved_date"] = saved_date
    activity_section["saved_time"] = saved_time
    activity_section["timezone"] = "Asia/Kuala_Lumpur"

    if section_name == "deposit_activity":
        _bump_rollup(user, saved_at_iso=saved_at_iso, deposit_delta=float(amount_usd), deposit_count=1)
    elif section_name == "withdrawal_activity":
        _bump_rollup(user, saved_at_iso=saved_at_iso, withdrawal_delta=float(amount_usd), withdrawal_count=1)

    user["updated_at"] = saved_at_iso
    save_core_db(db)
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

    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not user:
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")
    net_usd = float(amount_usd) if mode == "profit" else -float(amount_usd)

    record = {
        "mode": mode,
        "amount_usd": float(amount_usd),
        "net_usd": net_usd,
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
    }
    _append_monthly_record(user_id, "trading_activity", record, now.date())

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
            "data": {"record_count": 0, "current_profit_usd": 0.0},
        },
    )

    trading_data = trading_section.setdefault("data", {})
    trading_data["record_count"] = _to_int(trading_data.get("record_count")) + 1
    existing_profit = _to_float(trading_data.get("current_profit_usd"))
    trading_data["current_profit_usd"] = existing_profit + net_usd

    trading_section["saved_at"] = saved_at_iso
    trading_section["saved_date"] = saved_date
    trading_section["saved_time"] = saved_time
    trading_section["timezone"] = "Asia/Kuala_Lumpur"

    _bump_rollup(user, saved_at_iso=saved_at_iso, trading_delta=net_usd, trading_count=1)
    user["updated_at"] = saved_at_iso
    save_core_db(db)
    return True


def apply_initial_capital_reset(user_id: int, new_initial_capital: float) -> bool:
    if new_initial_capital <= 0:
        return False

    db = load_core_db()
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
    save_core_db(db)
    return True


def get_balance_adjustment_rules(user_id: int) -> dict[str, Any]:
    today = malaysia_now().date()
    month_start, month_end = _month_range(today)
    window_start = month_end - timedelta(days=6)
    # Temporary bypass: allow testing outside last-7-days window.
    window_open = True
    month_key = _month_key_from_date(today)
    monthly_db = _load_activity_db(month_key)
    used_records = _get_activity_records_from_db(monthly_db, user_id, "balance_adjustment")
    used_this_month = len(used_records) > 0
    can_adjust = window_open and not used_this_month
    return {
        "can_adjust": can_adjust,
        "used_this_month": used_this_month,
        "window_open": window_open,
        "window_start": window_start.isoformat(),
        "window_end": month_end.isoformat(),
        "window_label": f"{window_start.isoformat()} hingga {month_end.isoformat()}",
    }


def apply_balance_adjustment(user_id: int, mode: str, amount_usd: float) -> tuple[bool, str]:
    mode = (mode or "").strip().lower()
    if mode not in {"add", "subtract"}:
        return False, "Mode adjustment tak sah."
    if amount_usd <= 0:
        return False, "Nilai adjustment mesti lebih dari 0."

    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return False, "User tak dijumpai."

    sections = user.setdefault("sections", {})
    if "initial_setup" not in sections:
        return False, "Initial setup belum ada."

    rules = get_balance_adjustment_rules(user_id)
    if not rules["window_open"]:
        return False, f"Adjustment hanya dibenarkan pada 7 hari terakhir bulan ({rules['window_label']})."
    if rules["used_this_month"]:
        return False, "Bulan ni dah guna balance adjustment sekali."

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")
    net_usd = float(amount_usd) if mode == "add" else -float(amount_usd)

    record = {
        "mode": mode,
        "amount_usd": float(amount_usd),
        "net_usd": net_usd,
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
    }
    _append_monthly_record(user_id, "balance_adjustment", record, now.date())

    adjustment_section = sections.setdefault(
        "balance_adjustment",
        {
            "section": "balance_adjustment",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": saved_at_iso,
            "saved_date": saved_date,
            "saved_time": saved_time,
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"record_count": 0},
        },
    )
    adjustment_data = adjustment_section.setdefault("data", {})
    adjustment_data["record_count"] = _to_int(adjustment_data.get("record_count")) + 1
    adjustment_section["saved_at"] = saved_at_iso
    adjustment_section["saved_date"] = saved_date
    adjustment_section["saved_time"] = saved_time
    adjustment_section["timezone"] = "Asia/Kuala_Lumpur"

    _bump_rollup(
        user,
        saved_at_iso=saved_at_iso,
        balance_adjustment_delta=net_usd,
        balance_adjustment_count=1,
    )
    user["updated_at"] = saved_at_iso
    save_core_db(db)
    return True, "Balance adjustment berjaya disimpan."


def _normalize_date_str(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def _normalize_time_str(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.strptime(text, "%H:%M")
        return parsed.strftime("%H:%M")
    except ValueError:
        return ""


def save_notification_settings(user_id: int, payload: dict[str, Any]) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    manual_payload = payload.get("manual_push")
    daily_payload = payload.get("daily_notification")
    report_payload = payload.get("report_notification")
    maintenance_payload = payload.get("maintenance_notification")

    manual_obj = manual_payload if isinstance(manual_payload, dict) else {}
    daily_obj = daily_payload if isinstance(daily_payload, dict) else {}
    report_obj = report_payload if isinstance(report_payload, dict) else {}
    maintenance_obj = maintenance_payload if isinstance(maintenance_payload, dict) else {}

    raw_times = daily_obj.get("times")
    daily_times: list[str] = []
    if isinstance(raw_times, list):
        for item in raw_times:
            normalized = _normalize_time_str(item)
            if normalized:
                daily_times.append(normalized)
    # Keep order, remove duplicates.
    seen: set[str] = set()
    dedup_times: list[str] = []
    for item in daily_times:
        if item in seen:
            continue
        seen.add(item)
        dedup_times.append(item)
    daily_times = dedup_times[:6]

    try:
        daily_count = int(daily_obj.get("times_per_day") or 1)
    except (TypeError, ValueError):
        daily_count = 1
    daily_count = max(1, min(daily_count, 6))

    sections = user.setdefault("sections", {})
    existing_section = sections.get("notification_settings", {})
    existing_data = existing_section.get("data", {}) if isinstance(existing_section, dict) else {}
    existing_runtime = existing_data.get("runtime", {}) if isinstance(existing_data, dict) else {}

    data = {
        "manual_push": {
            "enabled": bool(manual_obj.get("enabled")),
            "date": _normalize_date_str(manual_obj.get("date")),
            "time": _normalize_time_str(manual_obj.get("time")),
            "message": str(manual_obj.get("message") or "").strip(),
        },
        "daily_notification": {
            "enabled": bool(daily_obj.get("enabled")),
            "times_per_day": daily_count,
            "times": daily_times[:daily_count],
            "preset_message": str(daily_obj.get("preset_message") or "").strip(),
        },
        "report_notification": {
            "enabled": bool(report_obj.get("enabled")),
            "weekly_remind_date": _normalize_date_str(report_obj.get("weekly_remind_date")),
            "monthly_remind_date": _normalize_date_str(report_obj.get("monthly_remind_date")),
        },
        "maintenance_notification": {
            "enabled": bool(maintenance_obj.get("enabled")),
            "start_date": _normalize_date_str(maintenance_obj.get("start_date")),
            "start_time": _normalize_time_str(maintenance_obj.get("start_time")),
            "end_date": _normalize_date_str(maintenance_obj.get("end_date")),
            "end_time": _normalize_time_str(maintenance_obj.get("end_time")),
            "message": str(maintenance_obj.get("message") or "").strip(),
        },
        "runtime": existing_runtime if isinstance(existing_runtime, dict) else {},
    }

    sections["notification_settings"] = {
        "section": "notification_settings",
        "user_id": user_id,
        "telegram_name": user.get("telegram_name") or str(user_id),
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
        "data": data,
    }

    user["updated_at"] = saved_at_iso
    save_core_db(db)
    return True


def get_notification_settings(user_id: int) -> dict[str, Any]:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {}) if isinstance(user, dict) else {}
    section = sections.get("notification_settings", {}) if isinstance(sections, dict) else {}
    data = section.get("data", {}) if isinstance(section, dict) else {}
    return data if isinstance(data, dict) else {}


def list_active_user_ids() -> list[int]:
    db = load_core_db()
    users = db.get("users", {})
    if not isinstance(users, dict):
        return []

    active_ids: list[int] = []
    for raw_user_id, user_obj in users.items():
        if not isinstance(user_obj, dict):
            continue
        sections = user_obj.get("sections", {})
        if not isinstance(sections, dict):
            continue
        if "initial_setup" not in sections:
            continue
        try:
            active_ids.append(int(raw_user_id))
        except (TypeError, ValueError):
            continue
    return sorted(set(active_ids))


def was_notification_sent(user_id: int, category: str, marker: str) -> bool:
    if not category or not marker:
        return False
    data = get_notification_settings(user_id)
    runtime = data.get("runtime", {})
    if not isinstance(runtime, dict):
        return False
    bucket = runtime.get(category, [])
    if not isinstance(bucket, list):
        return False
    return marker in bucket


def mark_notification_sent(user_id: int, category: str, marker: str) -> bool:
    if not category or not marker:
        return False

    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return False

    sections = user.setdefault("sections", {})
    notification_section = sections.setdefault(
        "notification_settings",
        {
            "section": "notification_settings",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": "",
            "saved_date": "",
            "saved_time": "",
            "timezone": "Asia/Kuala_Lumpur",
            "data": {},
        },
    )
    data = notification_section.setdefault("data", {})
    runtime = data.setdefault("runtime", {})
    bucket = runtime.setdefault(category, [])
    if not isinstance(bucket, list):
        bucket = []
        runtime[category] = bucket

    if marker in bucket:
        return False
    bucket.append(marker)

    # Keep runtime compact.
    if len(bucket) > 400:
        runtime[category] = bucket[-400:]

    now = malaysia_now()
    notification_section["saved_at"] = now.isoformat()
    notification_section["saved_date"] = now.strftime("%Y-%m-%d")
    notification_section["saved_time"] = now.strftime("%H:%M:%S")
    notification_section["timezone"] = "Asia/Kuala_Lumpur"
    user["updated_at"] = now.isoformat()
    save_core_db(db)
    return True
