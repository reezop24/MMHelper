"""JSON storage for MM HELPER with split core + monthly activity DB."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from time_utils import malaysia_now

CORE_DB_PATH = Path(__file__).with_name("mmhelper_core.json")
LEGACY_DB_PATH = Path(__file__).with_name("mmhelper_db.json")
ACTIVITY_DB_DIR = Path(__file__).with_name("db") / "activity"
ACTIVITY_FILE_PREFIX = "activity_"
DEFAULT_SHARED_DB_PATH = Path(__file__).with_name("db") / "mmhelper_shared.db"
MMHELPER_CORE_KV_KEY = "mmhelper_core_state"
MMHELPER_ACTIVITY_TABLE = "mmhelper_activity_monthly"
MMHELPER_FIBO_PROFILES_TABLE = "fibo_extension_profiles"


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


def _to_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


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


def _get_shared_db_path() -> Path:
    raw = (os.getenv("MMHELPER_SHARED_DB_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_SHARED_DB_PATH


def _connect_shared_db() -> sqlite3.Connection:
    db_path = _get_shared_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_mmhelper_kv_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mmhelper_kv_state (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _ensure_mmhelper_activity_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MMHELPER_ACTIVITY_TABLE} (
            month_key TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _ensure_fibo_profiles_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MMHELPER_FIBO_PROFILES_TABLE} (
            user_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _read_core_state_from_sqlite(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT value_json FROM mmhelper_kv_state WHERE key = ?",
        (MMHELPER_CORE_KV_KEY,),
    ).fetchone()
    if row is None:
        return None
    raw = str(row["value_json"] or "").strip()
    if not raw:
        return _default_core_db()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _default_core_db()
    if not isinstance(data, dict):
        return _default_core_db()
    return _normalize_core_db(data)


def _write_core_state_to_sqlite(conn: sqlite3.Connection, data: dict[str, Any]) -> None:
    payload = json.dumps(_normalize_core_db(data), ensure_ascii=False)
    conn.execute(
        """
        INSERT OR REPLACE INTO mmhelper_kv_state (key, value_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (MMHELPER_CORE_KV_KEY, payload, malaysia_now().isoformat()),
    )


def _load_core_db_from_files() -> dict[str, Any]:
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


def _normalize_core_db(data: dict[str, Any]) -> dict[str, Any]:
    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    return data


def load_core_db() -> dict[str, Any]:
    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_kv_table(conn)
            db = _read_core_state_from_sqlite(conn)
            if db is None:
                db = _load_core_db_from_files()
                _write_core_state_to_sqlite(conn, db)
            _save_json_dict(CORE_DB_PATH, db)
            return _normalize_core_db(db)
    except sqlite3.Error:
        return _load_core_db_from_files()


def save_core_db(data: dict[str, Any]) -> None:
    normalized = _normalize_core_db(data)
    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_kv_table(conn)
            _write_core_state_to_sqlite(conn, normalized)
    except sqlite3.Error:
        pass
    _save_json_dict(CORE_DB_PATH, normalized)


# Backward-compatible names used by older code.
def load_db() -> dict[str, Any]:
    return load_core_db()


def save_db(data: dict[str, Any]) -> None:
    save_core_db(data)


def _month_key_from_date(dt: date) -> str:
    return dt.strftime("%Y_%m")


def _beta_date_override_bucket(db: dict[str, Any]) -> dict[str, Any]:
    bucket = db.setdefault("beta_date_override", {})
    if not isinstance(bucket, dict):
        bucket = {}
        db["beta_date_override"] = bucket
    users = bucket.setdefault("users", {})
    if not isinstance(users, dict):
        users = {}
        bucket["users"] = users
    return bucket


def _parse_override_date(raw: Any) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def get_beta_date_override(target_user_id: int) -> dict[str, Any]:
    db = load_core_db()
    bucket = _beta_date_override_bucket(db)
    users = bucket.get("users", {})
    row = users.get(str(target_user_id), {}) if isinstance(users, dict) else {}
    if not isinstance(row, dict):
        row = {}
    return {
        "enabled": bool(row.get("enabled")),
        "override_date": str(row.get("override_date") or "").strip(),
        "updated_by": _to_int(row.get("updated_by")),
        "updated_at": str(row.get("updated_at") or "").strip(),
    }


def get_beta_date_overrides_snapshot() -> dict[str, dict[str, Any]]:
    db = load_core_db()
    bucket = _beta_date_override_bucket(db)
    users = bucket.get("users", {})
    if not isinstance(users, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in users.items():
        if not isinstance(value, dict):
            continue
        out[str(key)] = {
            "enabled": bool(value.get("enabled")),
            "override_date": str(value.get("override_date") or "").strip(),
            "updated_by": _to_int(value.get("updated_by")),
            "updated_at": str(value.get("updated_at") or "").strip(),
        }
    return out


def set_beta_date_override(target_user_id: int, override_date: str, enabled: bool, updated_by: int) -> tuple[bool, str]:
    db = load_core_db()
    users = db.get("users", {})
    if not isinstance(users, dict) or str(target_user_id) not in users:
        return False, "Target user tak dijumpai."

    if enabled:
        parsed = _parse_override_date(override_date)
        if parsed is None:
            return False, "Tarikh override tak sah."
        normalized_date = parsed.isoformat()
    else:
        normalized_date = ""

    now = malaysia_now().isoformat()
    bucket = _beta_date_override_bucket(db)
    row_users = bucket.setdefault("users", {})
    if not isinstance(row_users, dict):
        row_users = {}
        bucket["users"] = row_users
    row_users[str(target_user_id)] = {
        "enabled": bool(enabled),
        "override_date": normalized_date,
        "updated_by": int(updated_by),
        "updated_at": now,
    }
    save_core_db(db)
    return True, "ok"


def clear_beta_date_override(target_user_id: int) -> bool:
    db = load_core_db()
    bucket = _beta_date_override_bucket(db)
    users = bucket.get("users", {})
    if not isinstance(users, dict):
        return False
    removed = users.pop(str(target_user_id), None)
    save_core_db(db)
    return removed is not None


def current_user_date(user_id: int) -> date:
    db = load_core_db()
    bucket = _beta_date_override_bucket(db)
    users = bucket.get("users", {})
    if isinstance(users, dict):
        row = users.get(str(user_id), {})
        if isinstance(row, dict) and bool(row.get("enabled")):
            parsed = _parse_override_date(row.get("override_date"))
            if parsed is not None:
                return parsed
    return malaysia_now().date()


def _user_now(user_id: int) -> datetime:
    real_now = malaysia_now()
    target_date = current_user_date(user_id)
    if target_date == real_now.date():
        return real_now
    return real_now.replace(year=target_date.year, month=target_date.month, day=target_date.day)


def _activity_db_path(month_key: str) -> Path:
    return ACTIVITY_DB_DIR / f"{ACTIVITY_FILE_PREFIX}{month_key}.json"


def _read_activity_from_sqlite(conn: sqlite3.Connection, month_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT payload_json FROM {MMHELPER_ACTIVITY_TABLE} WHERE month_key = ?",
        (month_key,),
    ).fetchone()
    if row is None:
        return None
    raw = str(row["payload_json"] or "").strip()
    if not raw:
        return _default_activity_db(month_key)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _default_activity_db(month_key)
    if not isinstance(parsed, dict):
        return _default_activity_db(month_key)
    return parsed


def _write_activity_to_sqlite(conn: sqlite3.Connection, month_key: str, data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    conn.execute(
        f"""
        INSERT OR REPLACE INTO {MMHELPER_ACTIVITY_TABLE} (month_key, payload_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (month_key, payload, malaysia_now().isoformat()),
    )


def _load_activity_db(month_key: str) -> dict[str, Any]:
    data: dict[str, Any]
    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_activity_table(conn)
            sqlite_data = _read_activity_from_sqlite(conn, month_key)
            if sqlite_data is not None:
                data = sqlite_data
            else:
                data = _load_json_dict(_activity_db_path(month_key), lambda: _default_activity_db(month_key))
                _write_activity_to_sqlite(conn, month_key, data)
    except sqlite3.Error:
        data = _load_json_dict(_activity_db_path(month_key), lambda: _default_activity_db(month_key))

    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    if not isinstance(data.get("month"), str):
        data["month"] = month_key.replace("_", "-")
    # Keep JSON mirror for compatibility/debug.
    _save_json_dict(_activity_db_path(month_key), data)
    return data


def _save_activity_db(month_key: str, data: dict[str, Any]) -> None:
    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_activity_table(conn)
            _write_activity_to_sqlite(conn, month_key, data)
    except sqlite3.Error:
        pass
    _save_json_dict(_activity_db_path(month_key), data)


def _iter_activity_month_keys() -> list[str]:
    month_keys: list[str] = []
    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_activity_table(conn)
            rows = conn.execute(f"SELECT month_key FROM {MMHELPER_ACTIVITY_TABLE}").fetchall()
            for row in rows:
                key = str(row["month_key"] or "").strip()
                if key:
                    month_keys.append(key)
    except sqlite3.Error:
        pass

    if ACTIVITY_DB_DIR.exists():
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
    return total


def _sum_adjustment_net_between(user_id: int, start_date: date, end_date: date) -> float:
    total = 0.0
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


def has_tnc_accepted(user_id: int) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id), {})
    sections = user.get("sections", {})
    tnc_section = sections.get("tnc_acceptance", {})
    tnc_data = tnc_section.get("data", {}) if isinstance(tnc_section, dict) else {}
    return bool(tnc_data.get("accepted"))


def save_tnc_acceptance(user_id: int, telegram_name: str, accepted: bool, telegram_username: str = "") -> None:
    now = _user_now(user_id)
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
    if telegram_username:
        user_obj["telegram_username"] = telegram_username
    user_obj["updated_at"] = saved_at_iso

    sections = user_obj.setdefault("sections", {})
    sections["tnc_acceptance"] = {
        "section": "tnc_acceptance",
        "user_id": user_id,
        "telegram_name": telegram_name,
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
        "data": {"accepted": bool(accepted)},
    }

    save_core_db(db)


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


def _current_tabung_month_range(user_id: int) -> tuple[date, date]:
    today = current_user_date(user_id)
    first_day = today.replace(day=1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first_day, next_month - timedelta(days=1)


def _count_tabung_mode_this_month(user_id: int, mode: str) -> int:
    start_date, end_date = _current_tabung_month_range(user_id)
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

    now = _user_now(user_id)
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
        floor_balance = get_current_balance_floor_usd(user_id, now.date())
        max_save_allowed = current_balance - floor_balance
        if amount > max_save_allowed:
            if max_save_allowed <= 0:
                return False, (
                    f"Simpanan ke tabung tak dibenarkan sekarang. "
                    f"Current Balance minimum yang perlu kekal ialah USD {floor_balance:.2f}."
                )
            return False, (
                f"Simpanan melebihi had. Maksimum simpanan sekarang USD {max_save_allowed:.2f} "
                f"(minimum Current Balance perlu kekal USD {floor_balance:.2f})."
            )
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

    if action == "save" and _is_daily_target_hit_on_date(user_id, now.date()):
        mark_daily_target_reached_today(user_id)

    return True, "ok"


def _month_range(reference_date: date) -> tuple[date, date]:
    first_day = reference_date.replace(day=1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = next_month - timedelta(days=1)
    return first_day, last_day


def _sum_amount_usd_between(user_id: int, section_name: str, start_date: date, end_date: date) -> float:
    total = 0.0
    for record in _iter_section_records_between(user_id, section_name, start_date, end_date):
        total += _to_float(record.get("amount_usd", 0.0))
    return total


def _sum_net_usd_between(user_id: int, section_name: str, start_date: date, end_date: date) -> float:
    total = 0.0
    for record in _iter_section_records_between(user_id, section_name, start_date, end_date):
        total += _record_net_usd(record)
    return total


def get_current_balance_floor_usd(user_id: int, reference_date: date | None = None) -> float:
    ref_date = reference_date or current_user_date(user_id)
    month_start, month_end = _month_range(ref_date)
    current_balance = get_current_balance_usd(user_id)

    monthly_deposit = _sum_amount_usd_between(user_id, "deposit_activity", month_start, month_end)
    monthly_withdrawal = _sum_amount_usd_between(user_id, "withdrawal_activity", month_start, month_end)
    monthly_trading_net = _sum_net_usd_between(user_id, "trading_activity", month_start, month_end)
    monthly_adjustment_net = _sum_net_usd_between(user_id, "balance_adjustment", month_start, month_end)

    # Carry-forward = balance at start of current month.
    month_start_balance = (
        current_balance
        - monthly_deposit
        + monthly_withdrawal
        - monthly_trading_net
        - monthly_adjustment_net
    )

    # Floor only reduced by withdrawal activity, never by balance adjustment.
    return month_start_balance - monthly_withdrawal


def get_month_start_balance_usd(user_id: int, reference_date: date | None = None) -> float:
    ref_date = reference_date or current_user_date(user_id)
    month_start, month_end = _month_range(ref_date)
    current_balance = get_current_balance_usd(user_id)

    monthly_deposit = _sum_amount_usd_between(user_id, "deposit_activity", month_start, month_end)
    monthly_withdrawal = _sum_amount_usd_between(user_id, "withdrawal_activity", month_start, month_end)
    monthly_trading_net = _sum_net_usd_between(user_id, "trading_activity", month_start, month_end)
    monthly_adjustment_net = _sum_net_usd_between(user_id, "balance_adjustment", month_start, month_end)

    return (
        current_balance
        - monthly_deposit
        + monthly_withdrawal
        - monthly_trading_net
        - monthly_adjustment_net
    )


def get_current_balance_as_of(user_id: int, as_of_date: date) -> float:
    ref_date = current_user_date(user_id)
    current_balance = get_current_balance_usd(user_id)
    if as_of_date >= ref_date:
        return current_balance

    start = as_of_date + timedelta(days=1)
    end = ref_date
    if start > end:
        return current_balance

    dep = _sum_amount_usd_between(user_id, "deposit_activity", start, end)
    wdr = _sum_amount_usd_between(user_id, "withdrawal_activity", start, end)
    trd = _sum_net_usd_between(user_id, "trading_activity", start, end)
    adj = _sum_net_usd_between(user_id, "balance_adjustment", start, end)

    return current_balance - dep + wdr - trd - adj


def get_tabung_balance_as_of(user_id: int, as_of_date: date) -> float:
    sections = _get_user_sections(user_id)
    tabung_section = sections.get("tabung", {})
    tabung_data = tabung_section.get("data", {}) if isinstance(tabung_section, dict) else {}
    records = tabung_data.get("records", []) if isinstance(tabung_data, dict) else []
    if not isinstance(records, list):
        return 0.0

    latest_balance: float = 0.0
    found = False
    for rec in records:
        if not isinstance(rec, dict):
            continue
        rec_date = _record_date_myt(rec)
        if rec_date is None or rec_date > as_of_date:
            continue
        latest_balance = _to_float(rec.get("balance_after_usd", latest_balance))
        found = True

    if found:
        return latest_balance
    return 0.0


def _trading_days_by_target_days(target_days: int) -> int:
    mapping = {30: 22, 90: 66, 180: 132}
    return mapping.get(int(target_days), 0)


def _remaining_grow_target_usd(user_id: int) -> float:
    goal = get_project_grow_goal_summary(user_id)
    target_balance = _to_float(goal.get("target_balance_usd"))
    baseline_balance = _to_float(goal.get("current_balance_usd"))
    total_grow_target = max(target_balance - baseline_balance, 0.0)
    return max(total_grow_target - get_tabung_balance_usd(user_id), 0.0)


def _floating_progress_usd(user_id: int) -> float:
    goal = get_project_grow_goal_summary(user_id)
    baseline_balance = _to_float(goal.get("current_balance_usd"))
    return get_current_balance_usd(user_id) - baseline_balance


def _daily_target_usd(user_id: int) -> float:
    goal = get_project_grow_goal_summary(user_id)
    target_days = _to_int(goal.get("target_days"))
    trading_days = _trading_days_by_target_days(target_days)
    if trading_days <= 0:
        return 0.0
    return _remaining_grow_target_usd(user_id) / float(trading_days)


def _daily_target_tracker_dates_from_user(user_obj: dict[str, Any]) -> list[str]:
    sections = user_obj.get("sections", {})
    tracker = sections.get("daily_target_tracker", {})
    data = tracker.get("data", {}) if isinstance(tracker, dict) else {}
    dates = data.get("reached_dates", [])
    if not isinstance(dates, list):
        return []
    out: list[str] = []
    for raw in dates:
        text = str(raw or "").strip()
        if _normalize_date_str(text):
            out.append(text)
    return out


def _daily_target_tracker_weekly_targets_from_user(user_obj: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = user_obj.get("sections", {})
    tracker = sections.get("daily_target_tracker", {})
    data = tracker.get("data", {}) if isinstance(tracker, dict) else {}
    raw = data.get("weekly_targets", {})
    if not isinstance(raw, dict):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for key, payload in raw.items():
        week_key = str(key or "").strip()
        if not week_key or not isinstance(payload, dict):
            continue
        out[week_key] = payload
    return out


def _is_daily_target_hit_now(user_id: int) -> bool:
    today = current_user_date(user_id)
    return _is_daily_target_hit_on_date(user_id, today)


def _week_key(week_start: date, week_end: date) -> str:
    return f"{week_start.isoformat()}__{week_end.isoformat()}"


def _count_trading_days_between(start_date: date, end_date: date) -> int:
    if end_date < start_date:
        return 0
    count = 0
    cur = start_date
    while cur <= end_date:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


def _goal_saved_date(user_id: int) -> date | None:
    sections = _get_user_sections(user_id)
    goal_section = sections.get("project_grow_goal", {})
    return _parse_iso_date(goal_section.get("saved_date"))


def _remaining_target_usd_before_date(user_id: int, before_date: date) -> float:
    goal = get_project_grow_goal_summary(user_id)
    target_balance = _to_float(goal.get("target_balance_usd"))
    baseline_balance = _to_float(goal.get("current_balance_usd"))
    total_grow_target = max(target_balance - baseline_balance, 0.0)
    achieved = max(get_tabung_balance_as_of(user_id, before_date), 0.0)
    return max(total_grow_target - achieved, 0.0)


def _get_or_create_weekly_daily_target_usd(user_id: int, reference_date: date) -> float:
    week_start, week_end = _bounded_current_week(reference_date)
    week_key = _week_key(week_start, week_end)

    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return 0.0

    weekly_targets = _daily_target_tracker_weekly_targets_from_user(user)
    existing = weekly_targets.get(week_key, {})
    if isinstance(existing, dict):
        existing_target = _to_float(existing.get("daily_target_usd"))
        if existing_target > 0:
            return existing_target

    goal = get_project_grow_goal_summary(user_id)
    target_days = _to_int(goal.get("target_days"))
    if _to_float(goal.get("target_balance_usd")) <= 0 or target_days <= 0:
        return 0.0

    saved_date = _goal_saved_date(user_id) or week_start
    deadline_exclusive = saved_date + timedelta(days=target_days)
    remaining_trading_days = _count_trading_days_between(week_start, deadline_exclusive - timedelta(days=1))
    if remaining_trading_days <= 0:
        return 0.0

    achieved_before_week = week_start - timedelta(days=1)
    remaining_target = _remaining_target_usd_before_date(user_id, achieved_before_week)
    if remaining_target <= 0:
        return 0.0

    daily_target_usd = remaining_target / float(remaining_trading_days)
    now = _user_now(user_id)

    sections = user.setdefault("sections", {})
    tracker = sections.setdefault(
        "daily_target_tracker",
        {
            "section": "daily_target_tracker",
            "user_id": user_id,
            "telegram_name": user.get("telegram_name") or str(user_id),
            "saved_at": now.isoformat(),
            "saved_date": now.strftime("%Y-%m-%d"),
            "saved_time": now.strftime("%H:%M:%S"),
            "timezone": "Asia/Kuala_Lumpur",
            "data": {"reached_dates": [], "weekly_targets": {}},
        },
    )
    tracker_data = tracker.setdefault("data", {})
    reached_dates = tracker_data.get("reached_dates", [])
    if not isinstance(reached_dates, list):
        reached_dates = []
    tracker_data["reached_dates"] = reached_dates

    raw_targets = tracker_data.get("weekly_targets", {})
    if not isinstance(raw_targets, dict):
        raw_targets = {}
    raw_targets[week_key] = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "daily_target_usd": float(daily_target_usd),
        "remaining_target_usd": float(remaining_target),
        "remaining_trading_days": int(remaining_trading_days),
        "saved_at": now.isoformat(),
    }
    tracker_data["weekly_targets"] = raw_targets

    tracker["saved_at"] = now.isoformat()
    tracker["saved_date"] = now.strftime("%Y-%m-%d")
    tracker["saved_time"] = now.strftime("%H:%M:%S")
    tracker["timezone"] = "Asia/Kuala_Lumpur"
    user["updated_at"] = now.isoformat()
    save_core_db(db)
    return float(daily_target_usd)


def get_weekly_frozen_daily_target_usd(user_id: int, reference_date: date | None = None) -> float:
    ref = reference_date or current_user_date(user_id)
    return _get_or_create_weekly_daily_target_usd(user_id, ref)


def _trading_profit_usd_on_date(user_id: int, target_date: date) -> float:
    net = _sum_trading_net_between(user_id, target_date, target_date)
    if net <= 0:
        return 0.0
    return float(net)


def _tabung_save_usd_on_date(user_id: int, target_date: date) -> float:
    total = 0.0
    for record in _tabung_records_since(user_id, target_date):
        rec_date = _record_date_myt(record)
        if rec_date != target_date:
            continue
        mode = str(record.get("mode") or "").strip().lower()
        if mode != "save":
            continue
        total += abs(_to_float(record.get("amount_usd")))
    return total


def _is_daily_target_hit_on_date(user_id: int, target_date: date) -> bool:
    daily_target = get_weekly_frozen_daily_target_usd(user_id, target_date)
    if daily_target <= 0:
        return False
    trading_profit = _trading_profit_usd_on_date(user_id, target_date)
    if trading_profit <= 0:
        return False
    tabung_saved = _tabung_save_usd_on_date(user_id, target_date)
    return tabung_saved >= daily_target


def has_reached_daily_target_today(user_id: int) -> bool:
    today = current_user_date(user_id).isoformat()
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return False

    if today in _daily_target_tracker_dates_from_user(user):
        return True
    if _is_daily_target_hit_now(user_id):
        mark_daily_target_reached_today(user_id)
        return True
    return False


def is_daily_target_hit_now(user_id: int) -> bool:
    return _is_daily_target_hit_now(user_id)


def mark_daily_target_reached_today(user_id: int) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return False

    now = _user_now(user_id)
    today = current_user_date(user_id).isoformat()
    dates = _daily_target_tracker_dates_from_user(user)
    if today in dates:
        return False

    dates.append(today)
    # Keep tracker compact.
    dates = dates[-120:]

    sections = user.setdefault("sections", {})
    sections["daily_target_tracker"] = {
        "section": "daily_target_tracker",
        "user_id": user_id,
        "telegram_name": user.get("telegram_name") or str(user_id),
        "saved_at": now.isoformat(),
        "saved_date": now.strftime("%Y-%m-%d"),
        "saved_time": now.strftime("%H:%M:%S"),
        "timezone": "Asia/Kuala_Lumpur",
        "data": {"reached_dates": dates},
    }

    user["updated_at"] = now.isoformat()
    save_core_db(db)
    return True


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
    today = current_user_date(user_id)
    start_date, end_date = _bounded_current_week(today)
    return _sum_trading_net_between(user_id, start_date, end_date)


def get_monthly_performance_usd(user_id: int) -> float:
    today = current_user_date(user_id)
    month_start, month_end = _month_range(today)
    return _sum_trading_net_between(user_id, month_start, month_end)


def get_weekly_adjustment_usd(user_id: int) -> float:
    today = current_user_date(user_id)
    start_date, end_date = _bounded_current_week(today)
    return _sum_adjustment_net_between(user_id, start_date, end_date)


def get_monthly_adjustment_usd(user_id: int) -> float:
    today = current_user_date(user_id)
    month_start, month_end = _month_range(today)
    return _sum_adjustment_net_between(user_id, month_start, month_end)


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


def _collect_transaction_history_rows(
    user_id: int,
    start_date: date,
    end_date: date,
    *,
    include_hidden_adjustments: bool,
) -> list[dict[str, Any]]:
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
                if not include_hidden_adjustments and mode in hidden_adjustment_modes:
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
    return rows


def get_transaction_history_records_between(
    user_id: int,
    start_date: date,
    end_date: date,
    *,
    limit: int | None = None,
    include_hidden_adjustments: bool = False,
) -> list[dict[str, Any]]:
    rows = _collect_transaction_history_rows(
        user_id,
        start_date,
        end_date,
        include_hidden_adjustments=include_hidden_adjustments,
    )
    if limit is None:
        return rows
    max_items = max(1, min(int(limit), 100))
    return rows[:max_items]


def get_transaction_history_records(user_id: int, days: int, limit: int = 100) -> list[dict[str, Any]]:
    day_window = max(1, int(days))
    end_date = current_user_date(user_id)
    start_date = end_date - timedelta(days=day_window - 1)
    return get_transaction_history_records_between(
        user_id,
        start_date,
        end_date,
        limit=limit,
        include_hidden_adjustments=False,
    )


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
    today = current_user_date(user_id)
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
    return get_tabung_balance_usd(user_id) >= 20


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


def has_tabung_save_today(user_id: int) -> bool:
    today = current_user_date(user_id)
    for record in _tabung_records_since(user_id, today):
        mode = str(record.get("mode") or "").strip().lower()
        if mode == "save":
            return True
    return False


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

    start_date = _mission_start_date(user_id) or current_user_date(user_id)
    today = current_user_date(user_id)
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

    now = _user_now(user_id)
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

    now = _user_now(user_id)
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
    user["updated_at"] = _user_now(user_id).isoformat()
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
    now = _user_now(user_id)
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
    if CORE_DB_PATH.exists():
        try:
            CORE_DB_PATH.unlink()
        except OSError:
            pass
    save_core_db(_default_core_db())
    if LEGACY_DB_PATH.exists():
        try:
            LEGACY_DB_PATH.unlink()
        except OSError:
            pass
    if ACTIVITY_DB_DIR.exists():
        for path in ACTIVITY_DB_DIR.rglob("*.json"):
            try:
                path.unlink()
            except OSError:
                continue
    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_kv_table(conn)
            _ensure_mmhelper_activity_table(conn)
            conn.execute(f"DELETE FROM {MMHELPER_ACTIVITY_TABLE}")
            _write_core_state_to_sqlite(conn, _default_core_db())
    except sqlite3.Error:
        pass


def save_user_setup_section(
    user_id: int,
    telegram_name: str,
    section: str,
    payload: dict[str, Any],
    telegram_username: str = "",
) -> None:
    now = _user_now(user_id)
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
    if telegram_username:
        user_obj["telegram_username"] = telegram_username
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

    now = _user_now(user_id)
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

    now = _user_now(user_id)
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

    now = _user_now(user_id)
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


def reset_user_all_settings(user_id: int) -> bool:
    db = load_core_db()
    users = db.get("users", {})
    if not isinstance(users, dict):
        return False

    removed = users.pop(str(user_id), None)
    if removed is None:
        return False
    save_core_db(db)

    for month_key in _iter_activity_month_keys():
        monthly_db = _load_activity_db(month_key)
        month_users = monthly_db.get("users", {})
        if not isinstance(month_users, dict):
            continue
        if str(user_id) not in month_users:
            continue
        month_users.pop(str(user_id), None)
        _save_activity_db(month_key, monthly_db)

    return True


def get_balance_adjustment_rules(user_id: int) -> dict[str, Any]:
    today = current_user_date(user_id)
    month_start, month_end = _month_range(today)
    window_start = month_end - timedelta(days=6)
    window_open = window_start <= today <= month_end

    used_count = 0
    for record in _iter_section_records_between(user_id, "balance_adjustment", month_start, month_end):
        mode = str(record.get("mode") or "").strip().lower()
        if mode in {"add", "subtract"}:
            used_count += 1
    used_this_month = used_count > 0

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

    now = _user_now(user_id)
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


def stop_all_notification_settings(user_id: int) -> bool:
    db = load_core_db()
    user = db.get("users", {}).get(str(user_id))
    if not isinstance(user, dict):
        return False

    now = malaysia_now()
    saved_at_iso = now.isoformat()
    saved_date = now.strftime("%Y-%m-%d")
    saved_time = now.strftime("%H:%M:%S")

    sections = user.setdefault("sections", {})
    sections["notification_settings"] = {
        "section": "notification_settings",
        "user_id": user_id,
        "telegram_name": user.get("telegram_name") or str(user_id),
        "saved_at": saved_at_iso,
        "saved_date": saved_date,
        "saved_time": saved_time,
        "timezone": "Asia/Kuala_Lumpur",
        "data": {
            "manual_push": {
                "enabled": False,
                "date": "",
                "time": "",
                "message": "",
            },
            "daily_notification": {
                "enabled": False,
                "times_per_day": 1,
                "times": [],
                "preset_message": "",
            },
            "report_notification": {
                "enabled": False,
                "weekly_remind_date": "",
                "monthly_remind_date": "",
            },
            "maintenance_notification": {
                "enabled": False,
                "start_date": "",
                "start_time": "",
                "end_date": "",
                "end_time": "",
                "message": "",
            },
            "runtime": {},
        },
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


def list_registered_user_logs(limit: int = 500) -> list[dict[str, str]]:
    db = load_core_db()
    users = db.get("users", {})
    if not isinstance(users, dict):
        return []

    rows: list[dict[str, str]] = []
    for raw_user_id, user_obj in users.items():
        if not isinstance(user_obj, dict):
            continue
        sections = user_obj.get("sections", {})
        if not isinstance(sections, dict):
            continue
        init_section = sections.get("initial_setup", {})
        if not isinstance(init_section, dict):
            continue
        init_data = init_section.get("data", {})
        if not isinstance(init_data, dict):
            init_data = {}

        user_id_text = str(user_obj.get("user_id") or raw_user_id)
        name = str(init_data.get("name") or user_obj.get("telegram_name") or ("User " + user_id_text))
        telegram_username = str(user_obj.get("telegram_username") or "").strip()
        if telegram_username and not telegram_username.startswith("@"):
            telegram_username = "@" + telegram_username
        if not telegram_username:
            telegram_username = "-"

        date_text = str(init_section.get("saved_date") or "-")
        time_text = str(init_section.get("saved_time") or "-")

        rows.append(
            {
                "name": name,
                "user_id": user_id_text,
                "telegram_username": telegram_username,
                "registered_at": f"{date_text} {time_text}",
                "saved_at": str(init_section.get("saved_at") or ""),
            }
        )

    rows.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
    max_items = max(1, min(int(limit), 2000))
    trimmed = rows[:max_items]
    for item in trimmed:
        item.pop("saved_at", None)
    return trimmed


def list_registered_user_logs_grouped_by_month(limit_total: int = 2000) -> dict[str, list[dict[str, str]]]:
    rows = list_registered_user_logs(limit=limit_total)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        registered_at = str(row.get("registered_at") or "").strip()
        month_key = registered_at[:7] if len(registered_at) >= 7 else "unknown"
        grouped.setdefault(month_key, []).append(row)
    return grouped


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


def _empty_fibo_profiles_state() -> dict[str, Any]:
    return {"active_profile": 1, "profiles": {}}


def _normalize_fibo_profile_payload(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        payload = {}
    out: dict[str, str] = {
        "trend": "",
        "tf": "h4",
        "aDate": "",
        "bDate": "",
        "cDate": "",
        "aTime": "",
        "bTime": "",
        "cTime": "",
    }
    out["trend"] = _to_text(payload.get("trend")).upper()
    if out["trend"] not in {"BUY", "SELL"}:
        out["trend"] = ""
    out["tf"] = _to_text(payload.get("tf"), "h4").lower()
    if out["tf"] not in {"h4", "d1"}:
        out["tf"] = "h4"
    for key in ("aDate", "bDate", "cDate", "aTime", "bTime", "cTime"):
        out[key] = _to_text(payload.get(key))
    return out


def _normalize_fibo_profiles_state(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    active_profile = max(1, min(7, _to_int(payload.get("active_profile"), 1)))
    raw_profiles = payload.get("profiles", {})
    profiles_out: dict[str, dict[str, str]] = {}
    if isinstance(raw_profiles, dict):
        for key, row in raw_profiles.items():
            idx = _to_int(key, -1)
            if 1 <= idx <= 7:
                profiles_out[str(idx)] = _normalize_fibo_profile_payload(row)
    return {"active_profile": active_profile, "profiles": profiles_out}


def load_fibo_extension_profiles(user_id: int) -> dict[str, Any]:
    try:
        with _connect_shared_db() as conn:
            _ensure_fibo_profiles_table(conn)
            row = conn.execute(
                f"SELECT payload_json FROM {MMHELPER_FIBO_PROFILES_TABLE} WHERE user_id = ?",
                (str(int(user_id)),),
            ).fetchone()
            if row is None:
                return _empty_fibo_profiles_state()
            raw = _to_text(row["payload_json"])
            if not raw:
                return _empty_fibo_profiles_state()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return _empty_fibo_profiles_state()
            return _normalize_fibo_profiles_state(parsed)
    except sqlite3.Error:
        return _empty_fibo_profiles_state()


def save_fibo_extension_profiles(user_id: int, payload: Any) -> bool:
    normalized = _normalize_fibo_profiles_state(payload)
    try:
        with _connect_shared_db() as conn:
            _ensure_fibo_profiles_table(conn)
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {MMHELPER_FIBO_PROFILES_TABLE}
                (user_id, payload_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (
                    str(int(user_id)),
                    json.dumps(normalized, ensure_ascii=False),
                    malaysia_now().isoformat(),
                ),
            )
        return True
    except sqlite3.Error:
        return False


def reset_fibo_extension_profiles(user_id: int) -> bool:
    try:
        with _connect_shared_db() as conn:
            _ensure_fibo_profiles_table(conn)
            conn.execute(
                f"DELETE FROM {MMHELPER_FIBO_PROFILES_TABLE} WHERE user_id = ?",
                (str(int(user_id)),),
            )
        return True
    except sqlite3.Error:
        return False


def has_fibo_next_profile_access(user_id: int) -> bool:
    try:
        with _connect_shared_db() as conn:
            row = conn.execute(
                """
                SELECT 1 AS ok
                FROM vip_whitelist
                WHERE user_id = ?
                  AND tier IN ('vip1', 'vip2')
                  AND status IN ('active', 'approved')
                LIMIT 1
                """,
                (str(int(user_id)),),
            ).fetchone()
            if row is not None:
                return True
    except sqlite3.Error:
        pass
    return False


def get_shared_db_health_snapshot() -> dict[str, Any]:
    db_path = _get_shared_db_path()
    snapshot: dict[str, Any] = {
        "shared_db_path": str(db_path),
        "exists": db_path.exists(),
        "size_bytes": int(db_path.stat().st_size) if db_path.exists() else 0,
        "tables": {},
        "core_users": 0,
        "activity_month_keys": _iter_activity_month_keys(),
    }

    db = load_core_db()
    users = db.get("users", {}) if isinstance(db, dict) else {}
    snapshot["core_users"] = len(users) if isinstance(users, dict) else 0

    if not db_path.exists():
        return snapshot

    try:
        with _connect_shared_db() as conn:
            _ensure_mmhelper_kv_table(conn)
            _ensure_mmhelper_activity_table(conn)
            _ensure_fibo_profiles_table(conn)
            table_names = [
                "mmhelper_kv_state",
                "mmhelper_activity_monthly",
                "fibo_extension_profiles",
                "vip_whitelist",
                "sidebot_users",
                "sidebot_submissions",
                "sidebot_kv_state",
            ]
            tables: dict[str, int | None] = {}
            for table in table_names:
                try:
                    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
                    tables[table] = int(row["c"] if row is not None else 0)
                except sqlite3.Error:
                    tables[table] = None
            snapshot["tables"] = tables
    except sqlite3.Error:
        snapshot["tables"] = {}
    return snapshot


def backup_shared_db(target_path: str | Path) -> tuple[bool, str]:
    out_path = Path(target_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with _connect_shared_db() as src:
            _ensure_mmhelper_kv_table(src)
            _ensure_mmhelper_activity_table(src)
            with sqlite3.connect(out_path) as dst:
                src.backup(dst)
    except sqlite3.Error as exc:
        return False, f"backup_failed:{exc}"
    return True, str(out_path)


def restore_shared_db(source_path: str | Path) -> tuple[bool, str]:
    src_path = Path(source_path).expanduser()
    if not src_path.exists():
        return False, "source_not_found"

    try:
        with sqlite3.connect(src_path) as src:
            with _connect_shared_db() as dst:
                src.backup(dst)
    except sqlite3.Error as exc:
        return False, f"restore_failed:{exc}"

    # Refresh JSON mirror after restore.
    _save_json_dict(CORE_DB_PATH, load_core_db())
    return True, str(_get_shared_db_path())
