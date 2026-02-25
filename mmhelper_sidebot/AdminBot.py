"""Admin side bot scaffold with TnC gate and starter menu."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from texts import (
    ADMIN_PANEL_TEXT,
    BETA_RESET_DONE_TEXT,
    BETA_RESET_PROMPT_TEXT,
    DECLINED_TEXT,
    MAIN_MENU_TEXT,
    TNC_TEXT,
)

logger = logging.getLogger(__name__)

TNC_ACCEPT = "ADMIN_TNC_ACCEPT"
TNC_DECLINE = "ADMIN_TNC_DECLINE"
CB_BETA_RESET_CONFIRM = "ADMIN_BETA_RESET_CONFIRM"
CB_BETA_RESET_CANCEL = "ADMIN_BETA_RESET_CANCEL"
CB_VERIF_APPROVE = "VERIF_APPROVE"
CB_VERIF_PENDING = "VERIF_PENDING"
CB_VERIF_REJECT = "VERIF_REJECT"
CB_VERIF_REQUEST_DEPOSIT = "VERIF_REQUEST_DEPOSIT"
CB_VERIF_REQUEST_PAYMENT_CUSTOM = "VERIF_REQUEST_PAYMENT_CUSTOM"
CB_VERIF_REQUEST_CHANGE_IB = "VERIF_REQUEST_CHANGE_IB"
CB_VERIF_REVOKE_VIP = "VERIF_REVOKE_VIP"
CB_USER_DEPOSIT_DONE = "USER_DEPOSIT_DONE"
CB_USER_DEPOSIT_CANCEL = "USER_DEPOSIT_CANCEL"
CB_USER_IB_DONE = "USER_IB_DONE"
CB_USER_IB_CANCEL = "USER_IB_CANCEL"

ADMIN_USER_IDS = {627116869}
STATE_PATH = Path(__file__).with_name("sidebot_state.json")
VIP_WHITELIST_PATH = Path(__file__).with_name("sidebot_vip_whitelist.json")
DEFAULT_SHARED_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "mmhelper_shared.db"
KV_STATE_LEGACY_KEY = "sidebot_state"
KV_STATE_SNAPSHOT_KEY = "sidebot_state_snapshot"

MENU_DAFTAR_NEXT_MEMBER = "🚀 Daftar NEXTexclusive"
MENU_BELI_EVIDEO26 = "🎬 One Time Purchase NEXT eVideo26"
MENU_OPEN_MMHELPER_BOT = "🤖 Buka MM Helper Bot"
MENU_OPEN_EVIDEO_BOT = "🎥 Buka NEXT eVideo Bot"
MENU_ALL_PRODUCT_PREVIEW = "🛍️ All Product Preview (coming soon)"
MENU_ADMIN_PANEL = "🛡️ Admin Panel"
MENU_ADMIN_USERS = "👥 User Directory"
MENU_BETA_RESET = "🧪 BETA RESET"
MENU_CHECK_UNDER_IB = "🔎 Check Under IB"
MENU_BACK_MAIN = "⬅️ Back to Main Menu"


def load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_shared_db_path() -> Path:
    raw = (os.getenv("SIDEBOT_SHARED_DB_PATH") or os.getenv("MMHELPER_SHARED_DB_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_SHARED_DB_PATH


def _connect_shared_db() -> sqlite3.Connection:
    db_path = get_shared_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_whitelist_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vip_whitelist (
            tier TEXT NOT NULL,
            user_id TEXT NOT NULL,
            telegram_username TEXT NOT NULL DEFAULT '',
            full_name TEXT NOT NULL DEFAULT '',
            wallet_id TEXT NOT NULL DEFAULT '',
            source_submission_id TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            PRIMARY KEY (tier, user_id)
        )
        """
    )


def _json_whitelist_fallback() -> dict:
    if not VIP_WHITELIST_PATH.exists():
        return {"vip1": {"users": {}}}
    try:
        data = json.loads(VIP_WHITELIST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"vip1": {"users": {}}}
    if not isinstance(data, dict):
        return {"vip1": {"users": {}}}
    return data


def _migrate_json_whitelist_if_needed(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) AS c FROM vip_whitelist").fetchone()["c"]
    if count:
        return
    data = _json_whitelist_fallback()
    for tier, tier_obj in data.items():
        if not isinstance(tier_obj, dict):
            continue
        users = tier_obj.get("users")
        if not isinstance(users, dict):
            continue
        for user_id, row in users.items():
            if not isinstance(row, dict):
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO vip_whitelist
                (tier, user_id, telegram_username, full_name, wallet_id, source_submission_id, added_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(tier),
                    str(row.get("user_id") or user_id),
                    str(row.get("telegram_username") or ""),
                    str(row.get("full_name") or ""),
                    str(row.get("wallet_id") or ""),
                    str(row.get("source_submission_id") or ""),
                    str(row.get("added_at") or ""),
                    str(row.get("status") or "active"),
                ),
            )


def _read_whitelist_from_db(conn: sqlite3.Connection) -> dict:
    out: dict = {"vip1": {"users": {}}, "vip2": {"users": {}}, "vip3": {"users": {}}}
    rows = conn.execute(
        """
        SELECT tier, user_id, telegram_username, full_name, wallet_id, source_submission_id, added_at, status
        FROM vip_whitelist
        ORDER BY tier, user_id
        """
    ).fetchall()
    for row in rows:
        tier = str(row["tier"] or "vip1")
        out.setdefault(tier, {"users": {}})
        users = out[tier].setdefault("users", {})
        user_id = str(row["user_id"])
        users[user_id] = {
            "user_id": int(user_id) if user_id.isdigit() else user_id,
            "telegram_username": str(row["telegram_username"] or ""),
            "full_name": str(row["full_name"] or ""),
            "wallet_id": str(row["wallet_id"] or ""),
            "source_submission_id": str(row["source_submission_id"] or ""),
            "added_at": str(row["added_at"] or ""),
            "status": str(row["status"] or "active"),
        }
    return out


def _write_json_mirror(data: dict) -> None:
    try:
        VIP_WHITELIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        logger.warning("Failed to write whitelist JSON mirror", exc_info=True)


def _ensure_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sidebot_kv_state (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        )
        """
    )


def _ensure_users_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sidebot_users (
            user_id TEXT PRIMARY KEY,
            telegram_username TEXT NOT NULL DEFAULT '',
            full_name TEXT NOT NULL DEFAULT '',
            phone_number TEXT NOT NULL DEFAULT '',
            wallet_id TEXT NOT NULL DEFAULT '',
            tnc_accepted INTEGER NOT NULL DEFAULT 0,
            latest_submission_id TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _ensure_submissions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sidebot_submissions (
            submission_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            registration_flow TEXT NOT NULL DEFAULT 'new_registration',
            wallet_id TEXT NOT NULL DEFAULT '',
            full_name TEXT NOT NULL DEFAULT '',
            telegram_username TEXT NOT NULL DEFAULT '',
            phone_number TEXT NOT NULL DEFAULT '',
            has_deposit_100 INTEGER NOT NULL DEFAULT 0,
            ib_request_submitted INTEGER,
            deposit_required_usd INTEGER NOT NULL DEFAULT 100,
            api_is_client_under_ib INTEGER,
            api_check_message TEXT NOT NULL DEFAULT '',
            admin_group_message_id INTEGER,
            user_deposit_prompt_message_id INTEGER,
            user_ib_prompt_message_id INTEGER,
            reviewed_by TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT NOT NULL DEFAULT '',
            submitted_at TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sidebot_submissions_user_id ON sidebot_submissions(user_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sidebot_submissions_submitted_at ON sidebot_submissions(submitted_at)"
    )


def _to_optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None


def _upsert_user_row(
    conn: sqlite3.Connection,
    user_id: int | str,
    *,
    telegram_username: str = "",
    full_name: str = "",
    phone_number: str = "",
    wallet_id: str = "",
    tnc_accepted: bool = False,
    latest_submission_id: str = "",
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO sidebot_users
        (user_id, telegram_username, full_name, phone_number, wallet_id, tnc_accepted, latest_submission_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            telegram_username=excluded.telegram_username,
            full_name=excluded.full_name,
            phone_number=excluded.phone_number,
            wallet_id=excluded.wallet_id,
            tnc_accepted=excluded.tnc_accepted,
            latest_submission_id=CASE
                WHEN excluded.latest_submission_id <> '' THEN excluded.latest_submission_id
                ELSE sidebot_users.latest_submission_id
            END,
            updated_at=excluded.updated_at
        """,
        (
            str(user_id),
            telegram_username,
            full_name,
            phone_number,
            wallet_id,
            1 if tnc_accepted else 0,
            latest_submission_id,
            now_iso,
        ),
    )


def _submission_payload_to_row(payload: dict) -> tuple:
    reviewed_by = payload.get("reviewed_by")
    reviewed_by_text = "" if reviewed_by is None else str(reviewed_by)
    return (
        str(payload.get("submission_id") or ""),
        str(payload.get("user_id") or ""),
        str(payload.get("status") or "pending"),
        str(payload.get("registration_flow") or "new_registration"),
        str(payload.get("wallet_id") or ""),
        str(payload.get("full_name") or ""),
        str(payload.get("telegram_username") or ""),
        str(payload.get("phone_number") or ""),
        1 if bool(payload.get("has_deposit_100")) else 0,
        _to_optional_int(payload.get("ib_request_submitted")),
        int(payload.get("deposit_required_usd") or get_required_deposit_amount(str(payload.get("registration_flow") or ""))),
        _to_optional_int(payload.get("api_is_client_under_ib")),
        str(payload.get("api_check_message") or ""),
        _to_optional_int(payload.get("admin_group_message_id")),
        _to_optional_int(payload.get("user_deposit_prompt_message_id")),
        _to_optional_int(payload.get("user_ib_prompt_message_id")),
        reviewed_by_text,
        str(payload.get("reviewed_at") or ""),
        str(payload.get("submitted_at") or datetime.now(timezone.utc).isoformat()),
        json.dumps(payload, ensure_ascii=False),
    )


def _insert_or_replace_submission(conn: sqlite3.Connection, payload: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO sidebot_submissions
        (submission_id, user_id, status, registration_flow, wallet_id, full_name, telegram_username, phone_number,
         has_deposit_100, ib_request_submitted, deposit_required_usd, api_is_client_under_ib, api_check_message,
         admin_group_message_id, user_deposit_prompt_message_id, user_ib_prompt_message_id, reviewed_by, reviewed_at,
         submitted_at, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _submission_payload_to_row(payload),
    )


def _decode_submission_payload(row: sqlite3.Row) -> dict | None:
    raw = str(row["payload_json"] or "").strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["submission_id"] = str(row["submission_id"] or payload.get("submission_id") or "")
    user_id_text = str(row["user_id"] or payload.get("user_id") or "")
    payload["user_id"] = int(user_id_text) if user_id_text.isdigit() else payload.get("user_id")
    payload["status"] = str(row["status"] or payload.get("status") or "pending")
    payload["registration_flow"] = str(row["registration_flow"] or payload.get("registration_flow") or "new_registration")
    payload["wallet_id"] = str(row["wallet_id"] or payload.get("wallet_id") or "")
    payload["full_name"] = str(row["full_name"] or payload.get("full_name") or "")
    payload["telegram_username"] = str(row["telegram_username"] or payload.get("telegram_username") or "")
    payload["phone_number"] = str(row["phone_number"] or payload.get("phone_number") or "")
    payload["has_deposit_100"] = bool(int(row["has_deposit_100"] or 0))
    payload["ib_request_submitted"] = _to_optional_bool(row["ib_request_submitted"])
    payload["deposit_required_usd"] = int(row["deposit_required_usd"] or payload.get("deposit_required_usd") or 0)
    payload["api_is_client_under_ib"] = _to_optional_bool(row["api_is_client_under_ib"])
    payload["api_check_message"] = str(row["api_check_message"] or payload.get("api_check_message") or "")
    payload["admin_group_message_id"] = _to_optional_int(row["admin_group_message_id"])
    payload["user_deposit_prompt_message_id"] = _to_optional_int(row["user_deposit_prompt_message_id"])
    payload["user_ib_prompt_message_id"] = _to_optional_int(row["user_ib_prompt_message_id"])
    payload["reviewed_by"] = _to_optional_int(row["reviewed_by"])
    payload["reviewed_at"] = str(row["reviewed_at"] or payload.get("reviewed_at") or "")
    payload["submitted_at"] = str(row["submitted_at"] or payload.get("submitted_at") or "")
    return payload


def _migrate_state_to_structured_tables_if_needed(conn: sqlite3.Connection) -> None:
    users_count = conn.execute("SELECT COUNT(*) AS c FROM sidebot_users").fetchone()["c"]
    submissions_count = conn.execute("SELECT COUNT(*) AS c FROM sidebot_submissions").fetchone()["c"]
    if users_count and submissions_count:
        return

    data: dict
    try:
        _ensure_state_table(conn)
        _migrate_json_state_if_needed(conn)
        data = _read_state_from_db(conn)
    except sqlite3.Error:
        data = _json_state_fallback()

    users = data.get("users", {})
    if not isinstance(users, dict):
        users = {}
    submissions = data.get("verification_submissions", {})
    if not isinstance(submissions, dict):
        submissions = {}

    for user_id, user_obj in users.items():
        if not isinstance(user_obj, dict):
            continue
        _upsert_user_row(
            conn,
            user_id,
            telegram_username=str(user_obj.get("telegram_username") or ""),
            tnc_accepted=bool(user_obj.get("tnc_accepted")),
        )

    for payload in submissions.values():
        if not isinstance(payload, dict):
            continue
        _insert_or_replace_submission(conn, payload)
        uid = payload.get("user_id")
        if uid is None:
            continue
        _upsert_user_row(
            conn,
            uid,
            telegram_username=str(payload.get("telegram_username") or ""),
            full_name=str(payload.get("full_name") or ""),
            phone_number=str(payload.get("phone_number") or ""),
            wallet_id=str(payload.get("wallet_id") or ""),
            latest_submission_id=str(payload.get("submission_id") or ""),
            tnc_accepted=bool(users.get(str(uid), {}).get("tnc_accepted")),
        )


def _build_state_mirror_from_db(conn: sqlite3.Connection) -> dict:
    data: dict = {"users": {}, "verification_submissions": {}}
    users: dict = data["users"]

    user_rows = conn.execute(
        """
        SELECT user_id, telegram_username, full_name, phone_number, wallet_id, tnc_accepted, latest_submission_id
        FROM sidebot_users
        ORDER BY user_id
        """
    ).fetchall()
    for row in user_rows:
        user_id = str(row["user_id"] or "")
        if not user_id:
            continue
        users[user_id] = {
            "user_id": int(user_id) if user_id.isdigit() else user_id,
            "telegram_username": str(row["telegram_username"] or ""),
            "full_name": str(row["full_name"] or ""),
            "phone_number": str(row["phone_number"] or ""),
            "wallet_id": str(row["wallet_id"] or ""),
            "tnc_accepted": bool(int(row["tnc_accepted"] or 0)),
            "latest_verification": None,
            "verification_history": [],
            "_latest_submission_id": str(row["latest_submission_id"] or ""),
        }

    submission_rows = conn.execute(
        "SELECT * FROM sidebot_submissions ORDER BY submitted_at ASC, submission_id ASC"
    ).fetchall()
    for row in submission_rows:
        payload = _decode_submission_payload(row)
        if not isinstance(payload, dict):
            continue
        submission_id = str(payload.get("submission_id") or "")
        if not submission_id:
            continue
        data["verification_submissions"][submission_id] = payload

        user_id = payload.get("user_id")
        user_key = str(user_id)
        user_obj = users.setdefault(
            user_key,
            {
                "user_id": user_id,
                "telegram_username": str(payload.get("telegram_username") or ""),
                "full_name": str(payload.get("full_name") or ""),
                "phone_number": str(payload.get("phone_number") or ""),
                "wallet_id": str(payload.get("wallet_id") or ""),
                "tnc_accepted": False,
                "latest_verification": None,
                "verification_history": [],
                "_latest_submission_id": submission_id,
            },
        )
        history = user_obj.setdefault("verification_history", [])
        if isinstance(history, list):
            history.append(payload)
        if str(user_obj.get("_latest_submission_id") or "") == submission_id:
            user_obj["latest_verification"] = payload

    for user_obj in users.values():
        if not isinstance(user_obj, dict):
            continue
        if user_obj.get("latest_verification") is None:
            history = user_obj.get("verification_history")
            if isinstance(history, list) and history:
                user_obj["latest_verification"] = history[-1]
        user_obj.pop("_latest_submission_id", None)

    return data


def _sync_state_json_mirror_from_db(conn: sqlite3.Connection) -> None:
    try:
        snapshot = _build_state_mirror_from_db(conn)
        _write_state_json_mirror(snapshot)
        _write_state_snapshot_kv(conn, snapshot)
    except Exception:
        logger.warning("Failed to refresh sidebot JSON mirror from SQLite tables", exc_info=True)


def init_sidebot_storage() -> None:
    with _connect_shared_db() as conn:
        _ensure_state_table(conn)
        _ensure_users_table(conn)
        _ensure_submissions_table(conn)
        _migrate_json_state_if_needed(conn)
        _migrate_state_to_structured_tables_if_needed(conn)
        _sync_state_json_mirror_from_db(conn)


def _json_state_fallback() -> dict:
    if not STATE_PATH.exists():
        return {"users": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": {}}
    if not isinstance(data, dict):
        return {"users": {}}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    return data


def _write_state_json_mirror(data: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        logger.warning("Failed to write sidebot state JSON mirror", exc_info=True)


def _migrate_json_state_if_needed(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT value_json FROM sidebot_kv_state WHERE key = ?", (KV_STATE_LEGACY_KEY,)).fetchone()
    if row is not None:
        return
    data = _json_state_fallback()
    conn.execute(
        "INSERT OR REPLACE INTO sidebot_kv_state (key, value_json) VALUES (?, ?)",
        (KV_STATE_LEGACY_KEY, json.dumps(data, ensure_ascii=False)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO sidebot_kv_state (key, value_json) VALUES (?, ?)",
        (KV_STATE_SNAPSHOT_KEY, json.dumps(data, ensure_ascii=False)),
    )


def _read_state_kv(conn: sqlite3.Connection, key: str) -> dict | None:
    row = conn.execute("SELECT value_json FROM sidebot_kv_state WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    raw = str(row["value_json"] or "").strip()
    if not raw:
        return {"users": {}}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"users": {}}
    if not isinstance(data, dict):
        return {"users": {}}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    return data


def _read_state_from_db(conn: sqlite3.Connection) -> dict:
    snapshot = _read_state_kv(conn, KV_STATE_SNAPSHOT_KEY)
    if snapshot is not None:
        return snapshot
    legacy = _read_state_kv(conn, KV_STATE_LEGACY_KEY)
    if legacy is not None:
        return legacy
    return {"users": {}}


def _write_state_snapshot_kv(conn: sqlite3.Connection, data: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sidebot_kv_state (key, value_json) VALUES (?, ?)",
        (KV_STATE_SNAPSHOT_KEY, json.dumps(data, ensure_ascii=False)),
    )


def _write_state_legacy_kv(conn: sqlite3.Connection, data: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sidebot_kv_state (key, value_json) VALUES (?, ?)",
        (KV_STATE_LEGACY_KEY, json.dumps(data, ensure_ascii=False)),
    )


def get_token() -> str:
    load_local_env()
    token = (os.getenv("SIDEBOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set SIDEBOT_TOKEN in mmhelper_sidebot/.env")
    return token


def get_register_next_webapp_url() -> str:
    url = (os.getenv("SIDEBOT_REGISTER_WEBAPP_URL") or "").strip()
    if not url.lower().startswith("https://"):
        return ""
    return url


def get_onetime_evideo_webapp_url() -> str:
    explicit = (os.getenv("SIDEBOT_ONETIME_EVIDEO_WEBAPP_URL") or "").strip()
    if explicit.lower().startswith("https://"):
        return explicit

    base = get_register_next_webapp_url()
    if not base:
        return ""
    try:
        parts = urlsplit(base)
        path = parts.path or "/"
        if path.endswith("/"):
            new_path = f"{path}one-time-purchase.html"
        elif path.endswith(".html"):
            parent = path.rsplit("/", 1)[0] if "/" in path else ""
            new_path = f"{parent}/one-time-purchase.html" if parent else "/one-time-purchase.html"
        else:
            new_path = f"{path}/one-time-purchase.html"
        return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))
    except Exception:
        if base.endswith("/"):
            return f"{base}one-time-purchase.html"
        if base.endswith(".html"):
            return f"{base.rsplit('/', 1)[0]}/one-time-purchase.html"
        return f"{base}/one-time-purchase.html"


def get_admin_users_webapp_base_url() -> str:
    explicit = (os.getenv("SIDEBOT_ADMIN_USERS_WEBAPP_URL") or "").strip()
    if explicit.lower().startswith("https://"):
        return explicit

    base = get_register_next_webapp_url()
    if not base:
        return ""
    try:
        parts = urlsplit(base)
        path = parts.path or "/"
        if path.endswith("/"):
            new_path = f"{path}admin-users.html"
        elif path.endswith(".html"):
            parent = path.rsplit("/", 1)[0] if "/" in path else ""
            new_path = f"{parent}/admin-users.html" if parent else "/admin-users.html"
        else:
            new_path = f"{path}/admin-users.html"
        return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))
    except Exception:
        if base.endswith("/"):
            return f"{base}admin-users.html"
        if base.endswith(".html"):
            return f"{base.rsplit('/', 1)[0]}/admin-users.html"
        return f"{base}/admin-users.html"


def _format_dt_display(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _admin_users_payload() -> str:
    out: dict[str, list[dict[str, str]]] = {"next_member": [], "evideo_subscriber": []}
    try:
        with _connect_shared_db() as conn:
            _ensure_submissions_table(conn)
            rows = conn.execute(
                """
                SELECT submission_id, user_id, telegram_username, full_name, registration_flow, submitted_at, reviewed_at
                FROM sidebot_submissions
                WHERE LOWER(COALESCE(status, '')) = 'approved'
                ORDER BY COALESCE(reviewed_at, submitted_at) DESC, submission_id DESC
                """
            ).fetchall()
    except sqlite3.Error:
        logger.warning("Failed to build admin users payload from DB", exc_info=True)
        return json.dumps(out, ensure_ascii=False)

    seen_next: set[str] = set()
    seen_evideo: set[str] = set()
    for row in rows:
        user_id = str(row["user_id"] or "").strip()
        if not user_id:
            continue
        flow = str(row["registration_flow"] or "").strip().lower()
        user_item = {
            "name": str(row["full_name"] or "-"),
            "telegram_username": str(row["telegram_username"] or ""),
            "user_id": user_id,
            "verification_date": _format_dt_display(str(row["submitted_at"] or "")),
            "approval_date": _format_dt_display(str(row["reviewed_at"] or "")),
        }
        if flow == "one_time_purchase":
            if user_id in seen_evideo:
                continue
            seen_evideo.add(user_id)
            out["evideo_subscriber"].append(user_item)
            continue
        if user_id in seen_next:
            continue
        seen_next.add(user_id)
        out["next_member"].append(user_item)

    return json.dumps(out, ensure_ascii=False)


def get_admin_users_webapp_url() -> str:
    base = get_admin_users_webapp_base_url()
    if not base:
        return ""
    payload = quote(_admin_users_payload(), safe="")
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}admin_users_payload={payload}"


def get_mmhelper_bot_url() -> str:
    url = (os.getenv("SIDEBOT_MMHELPER_BOT_URL") or "").strip()
    if url.startswith("https://t.me/"):
        return url
    return ""


def get_evideo_bot_url() -> str:
    url = (os.getenv("SIDEBOT_EVIDEO_BOT_URL") or "").strip()
    if url.startswith("https://t.me/"):
        return url
    return ""


def get_admin_group_id() -> int | None:
    raw = (os.getenv("SIDEBOT_ADMIN_GROUP_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def get_amarkets_api_base_url() -> str:
    return (os.getenv("AMARKETS_API_BASE_URL") or "").strip().rstrip("/")


def get_amarkets_api_token() -> str:
    return (os.getenv("AMARKETS_API_TOKEN") or "").strip()


def get_amarkets_api_refresh_token() -> str:
    return (os.getenv("AMARKETS_API_REFRESH_TOKEN") or "").strip()


def get_amarkets_api_username() -> str:
    return (os.getenv("AMARKETS_API_USERNAME") or "").strip()


def get_amarkets_api_password() -> str:
    return (os.getenv("AMARKETS_API_PASSWORD") or "").strip()


def get_amarkets_auth_url() -> str:
    return (os.getenv("AMARKETS_AUTH_URL") or "https://auth.prod.amarkets.dev/api/v1/token").strip()


def _persist_amarkets_tokens(access_token: str, refresh_token: str) -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    def _set_or_append(key: str, value: str) -> None:
        nonlocal lines
        prefix = f"{key}="
        for i, line in enumerate(lines):
            if line.strip().startswith(prefix):
                lines[i] = f"{key}={value}"
                return
        lines.append(f"{key}={value}")

    _set_or_append("AMARKETS_API_TOKEN", access_token)
    if refresh_token:
        _set_or_append("AMARKETS_API_REFRESH_TOKEN", refresh_token)

    try:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        return


def _amarkets_token_request(payload: dict[str, str]) -> tuple[bool, str, str]:
    auth_url = get_amarkets_auth_url()
    if not auth_url:
        return False, "", ""
    body = urlencode(payload).encode("utf-8")
    req = Request(
        auth_url,
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore").strip()
    except HTTPError as exc:
        preview = ""
        try:
            preview = exc.read().decode("utf-8", errors="ignore")[:180]
        except Exception:
            preview = ""
        logger.warning("AMarkets token request HTTP error code=%s body_preview=%s", exc.code, preview)
        return False, "", ""
    except Exception:
        logger.exception("AMarkets token request failed")
        return False, "", ""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("AMarkets token response not JSON preview=%s", raw[:180])
        return False, "", ""

    if not isinstance(parsed, dict):
        return False, "", ""
    access_token = str(parsed.get("access_token") or "").strip()
    refresh_token = str(parsed.get("refresh_token") or "").strip()
    if not access_token:
        return False, "", ""
    return True, access_token, refresh_token


def _amarkets_refresh_access_token() -> tuple[bool, str]:
    refresh_token = get_amarkets_api_refresh_token()
    if not refresh_token:
        return False, "refresh_token_not_set"
    ok, access_token, new_refresh = _amarkets_token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
    if not ok:
        return False, "refresh_failed"
    os.environ["AMARKETS_API_TOKEN"] = access_token
    if new_refresh:
        os.environ["AMARKETS_API_REFRESH_TOKEN"] = new_refresh
    _persist_amarkets_tokens(access_token, new_refresh or refresh_token)
    logger.info("AMarkets token refreshed successfully access_len=%s", len(access_token))
    return True, "ok"


def _amarkets_login_access_token() -> tuple[bool, str]:
    username = get_amarkets_api_username()
    password = get_amarkets_api_password()
    if not username or not password:
        return False, "username_password_not_set"
    ok, access_token, refresh_token = _amarkets_token_request(
        {
            "grant_type": "password",
            "username": username,
            "password": password,
        }
    )
    if not ok:
        return False, "password_grant_failed"
    os.environ["AMARKETS_API_TOKEN"] = access_token
    if refresh_token:
        os.environ["AMARKETS_API_REFRESH_TOKEN"] = refresh_token
    _persist_amarkets_tokens(access_token, refresh_token)
    logger.info("AMarkets token acquired via password grant access_len=%s", len(access_token))
    return True, "ok"


def _amarkets_check_is_client_once(wallet_id: str, token: str) -> tuple[bool | None, str]:
    base_url = get_amarkets_api_base_url()
    if not base_url or not token:
        logger.warning(
            "AMarkets API config missing (base_url_set=%s token_set=%s)",
            bool(base_url),
            bool(token),
        )
        return None, "AMarkets API belum dikonfigurasi"

    endpoint = f"{base_url}/partner/is_client/{quote(wallet_id)}"
    token_hint = f"{token[:8]}...len={len(token)}" if len(token) >= 8 else f"len={len(token)}"
    logger.info("AMarkets check start wallet_id=%s endpoint=%s token_hint=%s", wallet_id, endpoint, token_hint)
    req = Request(
        endpoint,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="ignore").strip()
            logger.info("AMarkets check response wallet_id=%s http=%s body_preview=%s", wallet_id, getattr(resp, "status", "?"), raw[:180])
    except HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="ignore")[:180]
        except Exception:
            err_body = ""
        logger.warning("AMarkets check HTTP error wallet_id=%s code=%s body_preview=%s", wallet_id, exc.code, err_body)
        if exc.code == 401:
            return None, "HTTP 401"
        return None, f"HTTP {exc.code}"
    except URLError as exc:
        logger.warning("AMarkets check connection error wallet_id=%s reason=%s", wallet_id, exc.reason)
        return None, "Connection failed"
    except Exception:
        logger.exception("AMarkets check unknown error wallet_id=%s", wallet_id)
        return None, "Unknown error"

    lowered = raw.lower()
    if lowered in {"true", "1", "yes"}:
        return True, "ok"
    if lowered in {"false", "0", "no"}:
        return False, "ok"

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, "Unexpected response"

    if isinstance(parsed, bool):
        return parsed, "ok"
    if isinstance(parsed, dict):
        for key in ("is_client", "exists", "result", "data", "value"):
            value = parsed.get(key)
            if isinstance(value, bool):
                return value, "ok"
            if isinstance(value, str) and value.lower() in {"true", "false"}:
                return value.lower() == "true", "ok"
    return None, "Unexpected response"


def amarkets_check_is_client(wallet_id: str) -> tuple[bool | None, str]:
    token = get_amarkets_api_token()
    result, message = _amarkets_check_is_client_once(wallet_id, token)
    if message != "HTTP 401":
        return result, message

    # Auto refresh flow on unauthorized.
    refreshed, reason = _amarkets_refresh_access_token()
    if not refreshed:
        logger.warning("AMarkets auto-refresh unavailable reason=%s; trying password grant fallback", reason)
        refreshed, reason = _amarkets_login_access_token()
        if not refreshed:
            logger.warning("AMarkets token recovery failed reason=%s", reason)
            return None, "HTTP 401"

    token = get_amarkets_api_token()
    return _amarkets_check_is_client_once(wallet_id, token)


def load_state() -> dict:
    try:
        with _connect_shared_db() as conn:
            _ensure_state_table(conn)
            _migrate_json_state_if_needed(conn)
            data = _read_state_from_db(conn)
            _write_state_json_mirror(data)
            _write_state_snapshot_kv(conn, data)
            return data
    except sqlite3.Error:
        logger.warning("Shared DB state unavailable, fallback to JSON", exc_info=True)
        return _json_state_fallback()


def save_state(data: dict) -> None:
    if not isinstance(data, dict):
        data = {"users": {}}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    try:
        with _connect_shared_db() as conn:
            _ensure_state_table(conn)
            _write_state_legacy_kv(conn, data)
            _write_state_snapshot_kv(conn, data)
            _write_state_json_mirror(data)
            return
    except sqlite3.Error:
        logger.warning("Failed to persist sidebot state into shared DB; writing JSON fallback", exc_info=True)
    _write_state_json_mirror(data)


def load_vip_whitelist() -> dict:
    try:
        with _connect_shared_db() as conn:
            _ensure_whitelist_table(conn)
            _migrate_json_whitelist_if_needed(conn)
            data = _read_whitelist_from_db(conn)
            _write_json_mirror(data)
            return data
    except sqlite3.Error:
        logger.warning("Shared DB whitelist unavailable, fallback to JSON", exc_info=True)
        data = _json_whitelist_fallback()
        if not isinstance(data.get("vip1"), dict):
            data["vip1"] = {"users": {}}
        if not isinstance(data["vip1"].get("users"), dict):
            data["vip1"]["users"] = {}
        return data


def save_vip_whitelist(data: dict) -> None:
    try:
        with _connect_shared_db() as conn:
            _ensure_whitelist_table(conn)
            conn.execute("DELETE FROM vip_whitelist")
            for tier, tier_obj in data.items():
                if not isinstance(tier_obj, dict):
                    continue
                users = tier_obj.get("users")
                if not isinstance(users, dict):
                    continue
                for user_id, row in users.items():
                    if not isinstance(row, dict):
                        continue
                    uid = str(row.get("user_id") or user_id)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO vip_whitelist
                        (tier, user_id, telegram_username, full_name, wallet_id, source_submission_id, added_at, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(tier),
                            uid,
                            str(row.get("telegram_username") or ""),
                            str(row.get("full_name") or ""),
                            str(row.get("wallet_id") or ""),
                            str(row.get("source_submission_id") or ""),
                            str(row.get("added_at") or ""),
                            str(row.get("status") or "active"),
                        ),
                    )
            _write_json_mirror(_read_whitelist_from_db(conn))
            return
    except sqlite3.Error:
        logger.warning("Failed to persist whitelist into shared DB; writing JSON fallback", exc_info=True)
    _write_json_mirror(data)


def add_user_to_vip_tier(item: dict, tier: str) -> None:
    tier_key = str(tier or "").strip().lower()
    if tier_key not in {"vip1", "vip2", "vip3"}:
        return
    data = load_vip_whitelist()
    vip_users = data.setdefault(tier_key, {}).setdefault("users", {})
    user_id = str(item.get("user_id"))
    vip_users[user_id] = {
        "user_id": item.get("user_id"),
        "telegram_username": item.get("telegram_username") or "",
        "full_name": item.get("full_name") or "",
        "wallet_id": item.get("wallet_id") or "",
        "source_submission_id": item.get("submission_id"),
        "added_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    save_vip_whitelist(data)


def remove_user_from_vip_tier(user_id: int, tier: str) -> bool:
    tier_key = str(tier or "").strip().lower()
    if tier_key not in {"vip1", "vip2", "vip3"}:
        return False
    data = load_vip_whitelist()
    vip_users = data.setdefault(tier_key, {}).setdefault("users", {})
    removed = vip_users.pop(str(user_id), None)
    save_vip_whitelist(data)
    return removed is not None


def _tier_for_registration_flow(registration_flow: str) -> str:
    return "vip3" if str(registration_flow or "").strip().lower() == "one_time_purchase" else "vip2"


def get_required_deposit_amount(registration_flow: str) -> int:
    if registration_flow == "under_ib_reezo":
        return 50
    return 100


def is_valid_wallet_id(wallet_id: str) -> bool:
    return wallet_id.isdigit() and len(wallet_id) == 7


def has_tnc_accepted(user_id: int) -> bool:
    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            _migrate_state_to_structured_tables_if_needed(conn)
            row = conn.execute(
                "SELECT tnc_accepted FROM sidebot_users WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            return bool(int(row["tnc_accepted"])) if row is not None else False
    except sqlite3.Error:
        logger.warning("Failed reading tnc_accepted from shared DB, fallback to JSON state", exc_info=True)
        state = load_state()
        users = state.get("users", {})
        user_obj = users.get(str(user_id), {})
        if not isinstance(user_obj, dict):
            return False
        return bool(user_obj.get("tnc_accepted"))


def mark_tnc_accepted(user_id: int, accepted: bool) -> None:
    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            _migrate_state_to_structured_tables_if_needed(conn)
            existing = conn.execute(
                "SELECT telegram_username, full_name, phone_number, wallet_id, latest_submission_id FROM sidebot_users WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            _upsert_user_row(
                conn,
                user_id=user_id,
                telegram_username=str(existing["telegram_username"] or "") if existing is not None else "",
                full_name=str(existing["full_name"] or "") if existing is not None else "",
                phone_number=str(existing["phone_number"] or "") if existing is not None else "",
                wallet_id=str(existing["wallet_id"] or "") if existing is not None else "",
                tnc_accepted=bool(accepted),
                latest_submission_id=str(existing["latest_submission_id"] or "") if existing is not None else "",
            )
            _sync_state_json_mirror_from_db(conn)
            return
    except sqlite3.Error:
        logger.warning("Failed writing tnc_accepted into shared DB, fallback to JSON state", exc_info=True)

    state = load_state()
    users = state.setdefault("users", {})
    user_obj = users.setdefault(str(user_id), {})
    user_obj["tnc_accepted"] = bool(accepted)
    save_state(state)


def store_verification_submission(
    user_id: int,
    telegram_username: str,
    wallet_id: str,
    has_deposit_100: bool,
    full_name: str,
    phone_number: str,
    registration_flow: str = "new_registration",
    ib_request_submitted: bool | None = None,
) -> dict:
    # Keep it short so callback_data stays under Telegram 64-byte limit.
    submission_id = f"{user_id}-{uuid4().hex[:12]}"

    deposit_required_usd = get_required_deposit_amount(registration_flow)

    payload = {
        "submission_id": submission_id,
        "user_id": user_id,
        "telegram_username": telegram_username or "",
        "wallet_id": wallet_id,
        "has_deposit_100": bool(has_deposit_100),
        "full_name": full_name,
        "phone_number": phone_number,
        "registration_flow": registration_flow,
        "ib_request_submitted": ib_request_submitted,
        "deposit_required_usd": deposit_required_usd,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "admin_group_message_id": None,
        "user_deposit_prompt_message_id": None,
        "user_ib_prompt_message_id": None,
    }

    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            _migrate_state_to_structured_tables_if_needed(conn)
            row = conn.execute(
                "SELECT tnc_accepted FROM sidebot_users WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            tnc_accepted = bool(int(row["tnc_accepted"])) if row is not None else False
            _upsert_user_row(
                conn,
                user_id=user_id,
                telegram_username=telegram_username or "",
                full_name=full_name,
                phone_number=phone_number,
                wallet_id=wallet_id,
                tnc_accepted=tnc_accepted,
                latest_submission_id=submission_id,
            )
            _insert_or_replace_submission(conn, payload)
            _sync_state_json_mirror_from_db(conn)
            return payload
    except sqlite3.Error:
        logger.warning("Failed writing submission into shared DB, fallback to JSON state", exc_info=True)

    state = load_state()
    users = state.setdefault("users", {})
    user_obj = users.setdefault(str(user_id), {})
    submissions = state.setdefault("verification_submissions", {})
    if not isinstance(submissions, dict):
        submissions = {}
        state["verification_submissions"] = submissions
    user_obj["telegram_username"] = telegram_username or ""
    user_obj["latest_verification"] = payload
    history = user_obj.setdefault("verification_history", [])
    if not isinstance(history, list):
        history = []
        user_obj["verification_history"] = history
    history.append(payload)
    submissions[submission_id] = payload
    save_state(state)
    return payload


def store_onetime_payment_submission(
    *,
    user_id: int,
    telegram_username: str,
    full_name: str,
    phone_number: str,
    transfer_to: str,
    amount_paid: int,
) -> dict:
    submission_id = f"{user_id}-{uuid4().hex[:12]}"
    payload = {
        "submission_id": submission_id,
        "user_id": user_id,
        "telegram_username": telegram_username or "",
        "wallet_id": "",
        "has_deposit_100": True,
        "full_name": full_name,
        "phone_number": phone_number,
        "registration_flow": "one_time_purchase",
        "ib_request_submitted": None,
        "deposit_required_usd": 0,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "admin_group_message_id": None,
        "user_deposit_prompt_message_id": None,
        "user_ib_prompt_message_id": None,
        "transfer_to": transfer_to,
        "amount_paid": int(amount_paid),
        "payment_request_amount_rm": 350,
    }

    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            _migrate_state_to_structured_tables_if_needed(conn)
            row = conn.execute(
                "SELECT tnc_accepted FROM sidebot_users WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            tnc_accepted = bool(int(row["tnc_accepted"])) if row is not None else False
            _upsert_user_row(
                conn,
                user_id=user_id,
                telegram_username=telegram_username or "",
                full_name=full_name,
                phone_number=phone_number,
                wallet_id="",
                tnc_accepted=tnc_accepted,
                latest_submission_id=submission_id,
            )
            _insert_or_replace_submission(conn, payload)
            _sync_state_json_mirror_from_db(conn)
            return payload
    except sqlite3.Error:
        logger.warning("Failed writing one-time purchase submission into shared DB, fallback to JSON state", exc_info=True)

    state = load_state()
    users = state.setdefault("users", {})
    user_obj = users.setdefault(str(user_id), {})
    existing = user_obj.get("verification_history")
    history = existing if isinstance(existing, list) else []
    history.append(payload)
    user_obj.update(
        {
            "user_id": user_id,
            "telegram_username": telegram_username or "",
            "full_name": full_name,
            "phone_number": phone_number,
            "wallet_id": "",
            "latest_verification": payload,
            "verification_history": history,
        }
    )
    submissions = state.setdefault("verification_submissions", {})
    if not isinstance(submissions, dict):
        submissions = {}
        state["verification_submissions"] = submissions
    submissions[submission_id] = payload
    save_state(state)
    return payload


def verification_action_keyboard(submission_id: str, registration_flow: str) -> InlineKeyboardMarkup:
    request_label = "💸 Request Payment" if registration_flow == "one_time_purchase" else "💸 Request Deposit"
    second_row = [InlineKeyboardButton(request_label, callback_data=f"{CB_VERIF_REQUEST_DEPOSIT}:{submission_id}")]
    if registration_flow == "one_time_purchase":
        second_row.append(InlineKeyboardButton("✍️ Request Payment (Custom)", callback_data=f"{CB_VERIF_REQUEST_PAYMENT_CUSTOM}:{submission_id}"))
    if registration_flow == "ib_transfer":
        second_row.append(InlineKeyboardButton("🔁 Request Change IB", callback_data=f"{CB_VERIF_REQUEST_CHANGE_IB}:{submission_id}"))
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"{CB_VERIF_APPROVE}:{submission_id}"),
                InlineKeyboardButton("⏳ Pending", callback_data=f"{CB_VERIF_PENDING}:{submission_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"{CB_VERIF_REJECT}:{submission_id}"),
            ],
            second_row,
        ]
    )


def approved_admin_keyboard(submission_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 Revoke User", callback_data=f"{CB_VERIF_REVOKE_VIP}:{submission_id}")],
        ]
    )


def user_deposit_keyboard(submission_id: str, registration_flow: str = "") -> InlineKeyboardMarkup:
    done_label = "✅ Payment Selesai" if registration_flow == "one_time_purchase" else "✅ Deposit Selesai"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(done_label, callback_data=f"{CB_USER_DEPOSIT_DONE}:{submission_id}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"{CB_USER_DEPOSIT_CANCEL}:{submission_id}"),
            ]
        ]
    )


def user_ib_request_keyboard(submission_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Change IB Selesai", callback_data=f"{CB_USER_IB_DONE}:{submission_id}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"{CB_USER_IB_CANCEL}:{submission_id}"),
            ]
        ]
    )


def update_submission_status(submission_id: str, status: str, reviewer_id: int) -> dict | None:
    reviewed_at = datetime.now(timezone.utc).isoformat()
    item = update_submission_fields(
        submission_id=submission_id,
        fields={
            "status": status,
            "reviewed_at": reviewed_at,
            "reviewed_by": reviewer_id,
        },
    )
    return item


def get_submission(submission_id: str) -> dict | None:
    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            _migrate_state_to_structured_tables_if_needed(conn)
            row = conn.execute(
                "SELECT * FROM sidebot_submissions WHERE submission_id = ?",
                (submission_id,),
            ).fetchone()
            if row is not None:
                return _decode_submission_payload(row)
    except sqlite3.Error:
        logger.warning("Failed reading submission from shared DB, fallback to JSON state", exc_info=True)

    state = load_state()
    submissions = state.get("verification_submissions", {})
    if not isinstance(submissions, dict):
        return None
    item = submissions.get(submission_id)
    if not isinstance(item, dict):
        return None
    return item


def update_submission_fields(submission_id: str, fields: dict) -> dict | None:
    if not isinstance(fields, dict):
        return None

    db_item: dict | None = None
    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            _migrate_state_to_structured_tables_if_needed(conn)
            row = conn.execute(
                "SELECT * FROM sidebot_submissions WHERE submission_id = ?",
                (submission_id,),
            ).fetchone()
            if row is not None:
                item = _decode_submission_payload(row)
                if item is not None:
                    item.update(fields)
                    _insert_or_replace_submission(conn, item)
                    user_id = item.get("user_id")
                    if user_id is not None:
                        user_row = conn.execute(
                            "SELECT tnc_accepted FROM sidebot_users WHERE user_id = ?",
                            (str(user_id),),
                        ).fetchone()
                        tnc_accepted = bool(int(user_row["tnc_accepted"])) if user_row is not None else False
                        _upsert_user_row(
                            conn,
                            user_id=user_id,
                            telegram_username=str(item.get("telegram_username") or ""),
                            full_name=str(item.get("full_name") or ""),
                            phone_number=str(item.get("phone_number") or ""),
                            wallet_id=str(item.get("wallet_id") or ""),
                            tnc_accepted=tnc_accepted,
                            latest_submission_id=str(item.get("submission_id") or ""),
                        )
                    db_item = item
                    _sync_state_json_mirror_from_db(conn)
                    return db_item
    except sqlite3.Error:
        logger.warning("Failed updating submission in shared DB, fallback to JSON state", exc_info=True)

    state = load_state()
    submissions = state.setdefault("verification_submissions", {})
    if not isinstance(submissions, dict):
        return db_item
    item = submissions.get(submission_id)
    if isinstance(item, dict):
        item.update(fields)
        user_id = item.get("user_id")
        users = state.setdefault("users", {})
        user_obj = users.get(str(user_id), {})
        if isinstance(user_obj, dict):
            latest = user_obj.get("latest_verification")
            if isinstance(latest, dict) and latest.get("submission_id") == submission_id:
                latest.update(fields)
            history = user_obj.get("verification_history", [])
            if isinstance(history, list):
                for row in history:
                    if isinstance(row, dict) and row.get("submission_id") == submission_id:
                        row.update(fields)
                        break
        save_state(state)
        return item

    if db_item is not None:
        # Keep JSON state mirror aligned if DB row exists but JSON mapping missing.
        submissions[submission_id] = db_item
        user_id = db_item.get("user_id")
        users = state.setdefault("users", {})
        user_obj = users.setdefault(str(user_id), {})
        user_obj["telegram_username"] = db_item.get("telegram_username") or ""
        user_obj["latest_verification"] = db_item
        history = user_obj.setdefault("verification_history", [])
        if isinstance(history, list):
            found = False
            for row in history:
                if isinstance(row, dict) and row.get("submission_id") == submission_id:
                    row.update(db_item)
                    found = True
                    break
            if not found:
                history.append(db_item)
        save_state(state)
    return db_item


def render_admin_submission_text(item: dict) -> str:
    raw_status = str(item.get("status") or "pending").lower()
    status_text = {
        "approved": "✅ APPROVED",
        "rejected": "❌ REJECTED",
    }.get(raw_status, raw_status.upper())
    user_id = item.get("user_id")
    username = item.get("telegram_username") or "-"
    username_text = f"@{username}" if username != "-" else "-"
    deposit_text = "Ya" if bool(item.get("has_deposit_100")) else "Belum"
    flow = str(item.get("registration_flow") or "new_registration")
    deposit_required_usd = int(item.get("deposit_required_usd") or get_required_deposit_amount(flow))
    flow_text_map = {
        "new_registration": "Pelanggan Baru",
        "ib_transfer": "Penukaran IB",
        "under_ib_reezo": "Client Under IB Reezo",
    }
    flow_text = flow_text_map.get(flow, flow)
    if flow == "one_time_purchase":
        channel = str(item.get("transfer_to") or "").strip().lower()
        channel_text = {"maybank": "Maybank", "tng": "TNG"}.get(channel, channel or "-")
        amount_paid = int(item.get("amount_paid") or 0)
        requested_amount_rm = int(item.get("payment_request_amount_rm") or 0)
        requested_line = f"Requested Payment: RM{requested_amount_rm}\n" if requested_amount_rm > 0 else ""
        return (
            "🧾 One-Time Purchase Payment Submit\n\n"
            f"Flow: One-Time Purchase\n"
            f"Submission ID: {item.get('submission_id')}\n"
            f"User ID: {user_id}\n"
            f"Username: {username_text}\n"
            f"Nama: {item.get('full_name')}\n"
            f"No Telefon: {item.get('phone_number')}\n"
            f"Saluran Pembayaran: {channel_text}\n"
            f"Jumlah Bayaran: RM{amount_paid}\n"
            f"{requested_line}"
            f"Status: {status_text}"
        )
    ib_req = item.get("ib_request_submitted")
    ib_req_text = ""
    if flow == "ib_transfer":
        ib_req_text = f"Submit Request IB: {'Ya' if ib_req else 'Belum'}\n"
    api_check_text = ""
    api_ib_status = item.get("api_is_client_under_ib")
    api_message = str(item.get("api_check_message") or "").strip()
    if api_ib_status is True:
        api_check_text = "API Check (Under IB): ✅ PASS\n"
    elif api_ib_status is False:
        api_check_text = "API Check (Under IB): ❌ FAIL\n"
    elif api_message:
        api_check_text = f"API Check (Under IB): ⚠️ {api_message}\n"
    return (
        "🆕 NEXTexclusive Verification Submit\n\n"
        f"Flow: {flow_text}\n"
        f"Submission ID: {item.get('submission_id')}\n"
        f"User ID: {user_id}\n"
        f"Username: {username_text}\n"
        f"Nama: {item.get('full_name')}\n"
        f"Wallet ID: {item.get('wallet_id')}\n"
        f"{ib_req_text}"
        f"{api_check_text}"
        f"Deposit Minimum USD{deposit_required_usd}: {deposit_text}\n"
        f"No Telefon: {item.get('phone_number')}\n"
        f"Status: {status_text}"
    )


async def send_submission_to_admin_group(context: ContextTypes.DEFAULT_TYPE, item: dict) -> bool:
    admin_group_id = get_admin_group_id()
    if not admin_group_id:
        return False
    text = render_admin_submission_text(item)
    try:
        sent = await context.bot.send_message(
            chat_id=admin_group_id,
            text=text,
            reply_markup=verification_action_keyboard(str(item.get("submission_id")), str(item.get("registration_flow") or "")),
        )
    except BadRequest as exc:
        if "button_data_invalid" not in str(exc).lower():
            raise
        logger.warning("Admin submission buttons invalid; sending without inline keyboard submission_id=%s", item.get("submission_id"))
        sent = await context.bot.send_message(chat_id=admin_group_id, text=text)
    update_submission_fields(str(item.get("submission_id")), {"admin_group_message_id": sent.message_id})
    return True


async def clear_user_deposit_prompt(context: ContextTypes.DEFAULT_TYPE, item: dict) -> None:
    user_id = item.get("user_id")
    prompt_message_id = item.get("user_deposit_prompt_message_id")
    if not isinstance(user_id, int) or not isinstance(prompt_message_id, int):
        return
    try:
        await context.bot.delete_message(chat_id=user_id, message_id=prompt_message_id)
    except Exception:
        logger.exception("Failed to delete old user deposit prompt message")
    finally:
        update_submission_fields(str(item.get("submission_id")), {"user_deposit_prompt_message_id": None})


async def clear_user_ib_prompt(context: ContextTypes.DEFAULT_TYPE, item: dict) -> None:
    user_id = item.get("user_id")
    prompt_message_id = item.get("user_ib_prompt_message_id")
    if not isinstance(user_id, int) or not isinstance(prompt_message_id, int):
        return
    try:
        await context.bot.delete_message(chat_id=user_id, message_id=prompt_message_id)
    except Exception:
        logger.exception("Failed to delete old user change-IB prompt message")
    finally:
        update_submission_fields(str(item.get("submission_id")), {"user_ib_prompt_message_id": None})


async def clear_user_deposit_prompt_by_submission(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str
) -> None:
    item = get_submission(submission_id)
    if not item:
        return
    await clear_user_deposit_prompt(context, item)


async def clear_user_ib_prompt_by_submission(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str
) -> None:
    item = get_submission(submission_id)
    if not item:
        return
    await clear_user_ib_prompt(context, item)


async def refresh_admin_submission_message(context: ContextTypes.DEFAULT_TYPE, submission_id: str) -> None:
    admin_group_id = get_admin_group_id()
    item = get_submission(submission_id)
    if not admin_group_id or not item:
        return
    old_message_id = item.get("admin_group_message_id")
    if isinstance(old_message_id, int):
        try:
            await context.bot.delete_message(chat_id=admin_group_id, message_id=old_message_id)
        except Exception:
            logger.exception("Failed to delete old admin verification message")
    await send_submission_to_admin_group(context, item)


async def send_user_deposit_request_message(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str, item: dict
) -> None:
    user_id = item.get("user_id")
    if not isinstance(user_id, int):
        return
    registration_flow = str(item.get("registration_flow") or "")
    deposit_required_usd = int(item.get("deposit_required_usd") or get_required_deposit_amount(registration_flow))
    await clear_user_deposit_prompt(context, item)
    await clear_user_ib_prompt(context, item)
    if registration_flow == "one_time_purchase":
        requested_amount_rm = int(item.get("payment_request_amount_rm") or 350)
        request_text = (
            f"Sila buat pembayaran RM{requested_amount_rm} untuk melengkapkan proses one-time purchase.\n\n"
            "Tekan butang PAYMENT SELESAI untuk pengesahan semula."
        )
    else:
        request_text = (
            f"Sila buat deposit USD{deposit_required_usd} ke akaun Amarkets ({item.get('wallet_id')}) "
            "untuk melengkapkan proses pendaftaran.\n\n"
            "Tekan butang DEPOSIT SELESAI untuk pengesahan semula."
        )
    sent = await context.bot.send_message(
        chat_id=user_id,
        text=request_text,
        reply_markup=user_deposit_keyboard(submission_id, registration_flow=registration_flow),
    )
    update_submission_fields(submission_id, {"user_deposit_prompt_message_id": sent.message_id})


async def send_user_change_ib_request_message(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str, item: dict
) -> None:
    user_id = item.get("user_id")
    if not isinstance(user_id, int):
        return
    await clear_user_ib_prompt(context, item)
    await clear_user_deposit_prompt(context, item)
    sent = await context.bot.send_message(
        chat_id=user_id,
        text=(
            "Sila submit request penukaran IB di dashboard AMarkets terlebih dahulu.\n\n"
            "Tekan butang CHANGE IB SELESAI untuk pengesahan semula."
        ),
        reply_markup=user_ib_request_keyboard(submission_id),
    )
    update_submission_fields(submission_id, {"user_ib_prompt_message_id": sent.message_id})


def is_admin_user(user_id: int | None) -> bool:
    return user_id in ADMIN_USER_IDS


def reset_all_data() -> None:
    try:
        with _connect_shared_db() as conn:
            _ensure_users_table(conn)
            _ensure_submissions_table(conn)
            conn.execute("DELETE FROM sidebot_submissions")
            conn.execute("DELETE FROM sidebot_users")
            _ensure_state_table(conn)
            empty_state = {"users": {}, "verification_submissions": {}}
            _write_state_legacy_kv(conn, empty_state)
            _write_state_snapshot_kv(conn, empty_state)
            _write_state_json_mirror(empty_state)
            return
    except sqlite3.Error:
        logger.warning("Failed resetting structured sidebot state tables", exc_info=True)
    save_state({"users": {}})


def tnc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Setuju & Teruskan", callback_data=TNC_ACCEPT)],
            [InlineKeyboardButton("❌ Batal", callback_data=TNC_DECLINE)],
        ]
    )


def main_menu_keyboard(user_id: int | None) -> ReplyKeyboardMarkup:
    register_url = get_register_next_webapp_url()
    if register_url:
        register_button = KeyboardButton(MENU_DAFTAR_NEXT_MEMBER, web_app=WebAppInfo(url=register_url))
    else:
        register_button = KeyboardButton(MENU_DAFTAR_NEXT_MEMBER)

    onetime_url = get_onetime_evideo_webapp_url()
    if onetime_url:
        onetime_button = KeyboardButton(MENU_BELI_EVIDEO26, web_app=WebAppInfo(url=onetime_url))
    else:
        onetime_button = KeyboardButton(MENU_BELI_EVIDEO26)

    rows = [
        [register_button],
        [onetime_button],
        [KeyboardButton(MENU_OPEN_MMHELPER_BOT), KeyboardButton(MENU_OPEN_EVIDEO_BOT)],
        [KeyboardButton(MENU_ALL_PRODUCT_PREVIEW)],
    ]
    if is_admin_user(user_id):
        rows.append([KeyboardButton(MENU_ADMIN_PANEL)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(MENU_CHECK_UNDER_IB)],
            [KeyboardButton(MENU_ADMIN_USERS)],
            [KeyboardButton(MENU_BETA_RESET)],
            [KeyboardButton(MENU_BACK_MAIN)],
        ],
        resize_keyboard=True,
    )


def beta_reset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirm BETA RESET", callback_data=CB_BETA_RESET_CONFIRM)],
            [InlineKeyboardButton("❌ Batal", callback_data=CB_BETA_RESET_CANCEL)],
        ]
    )


async def _reply_to_query_message(query, text: str, **kwargs) -> None:
    if not query:
        return
    if query.message is None:
        try:
            await query.get_bot().send_message(chat_id=query.from_user.id, text=text, **kwargs)
        except Exception:
            logger.exception("Failed to send callback response without source message")
        return
    try:
        await query.message.reply_text(text, **kwargs)
        return
    except BadRequest as exc:
        if "message to be replied not found" not in str(exc).lower():
            raise
    except Exception:
        logger.exception("Failed replying to callback message")
        return

    # Source message was removed; send direct message to same chat as fallback.
    try:
        await query.get_bot().send_message(chat_id=query.message.chat_id, text=text, **kwargs)
    except Exception:
        logger.exception("Failed sending fallback callback response")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    if has_tnc_accepted(user.id):
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
        return

    await message.reply_text("Sila baca dan setuju TnC dulu.", reply_markup=ReplyKeyboardRemove())
    await message.reply_text(TNC_TEXT, reply_markup=tnc_keyboard())


async def handle_tnc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    if query.data == TNC_ACCEPT:
        mark_tnc_accepted(query.from_user.id, True)
        await _reply_to_query_message(query, MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(query.from_user.id))
        return

    mark_tnc_accepted(query.from_user.id, False)
    await _reply_to_query_message(query, DECLINED_TEXT)


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if not is_admin_user(query.from_user.id):
        await _reply_to_query_message(query, "❌ Akses ditolak.")
        return

    if query.data == CB_BETA_RESET_CANCEL:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await _reply_to_query_message(query, "BETA RESET dibatalkan.", reply_markup=admin_panel_keyboard())
        return

    if query.data == CB_BETA_RESET_CONFIRM:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        reset_all_data()
        await _reply_to_query_message(query, BETA_RESET_DONE_TEXT)
        await _reply_to_query_message(query, "Sila baca dan setuju TnC dulu.", reply_markup=ReplyKeyboardRemove())
        await _reply_to_query_message(query, TNC_TEXT, reply_markup=tnc_keyboard())
        return

    if ":" in str(query.data):
        action, submission_id = str(query.data).split(":", 1)
        action_status_map = {
            CB_VERIF_APPROVE: "approved",
            CB_VERIF_PENDING: "pending",
            CB_VERIF_REJECT: "rejected",
        }
        if action == CB_VERIF_REQUEST_DEPOSIT:
            current = get_submission(submission_id)
            registration_flow = str(current.get("registration_flow") or "") if isinstance(current, dict) else ""
            next_status = "request_payment" if registration_flow == "one_time_purchase" else "request_deposit"
            request_amount = 350 if registration_flow == "one_time_purchase" else None
            item = update_submission_fields(
                submission_id=submission_id,
                fields={
                    "status": next_status,
                    "has_deposit_100": False,
                    "payment_request_amount_rm": request_amount,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": query.from_user.id,
                },
            )
            if not item:
                await _reply_to_query_message(query, "❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            user_id = item.get("user_id")
            if isinstance(user_id, int):
                try:
                    await send_user_deposit_request_message(context, submission_id, item)
                except Exception:
                    logger.exception("Failed to notify user for deposit request")
            await refresh_admin_submission_message(context, submission_id)
            if registration_flow == "one_time_purchase":
                await _reply_to_query_message(query, f"✅ Request payment RM350 dihantar kepada user untuk submission {submission_id}.")
            else:
                await _reply_to_query_message(query, f"✅ Request deposit dihantar kepada user untuk submission {submission_id}.")
            return

        if action == CB_VERIF_REQUEST_PAYMENT_CUSTOM:
            current = get_submission(submission_id)
            if not isinstance(current, dict):
                await _reply_to_query_message(query, "❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            registration_flow = str(current.get("registration_flow") or "")
            if registration_flow != "one_time_purchase":
                await _reply_to_query_message(query, "⚠️ Mode ini hanya untuk one-time purchase.")
                return
            context.user_data["awaiting_custom_payment_submission_id"] = submission_id
            await _reply_to_query_message(
                query,
                "Masukkan amaun payment dalam RM untuk user ini.\nContoh: `350` atau `RM350`\n\nTaip `cancel` untuk batal.",
                parse_mode="Markdown",
            )
            return

        if action == CB_VERIF_REQUEST_CHANGE_IB:
            item = update_submission_fields(
                submission_id=submission_id,
                fields={
                    "status": "request_change_ib",
                    "ib_request_submitted": False,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": query.from_user.id,
                },
            )
            if not item:
                await _reply_to_query_message(query, "❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            user_id = item.get("user_id")
            if isinstance(user_id, int):
                try:
                    await send_user_change_ib_request_message(context, submission_id, item)
                except Exception:
                    logger.exception("Failed to notify user for change-IB request")
            await refresh_admin_submission_message(context, submission_id)
            await _reply_to_query_message(query, f"✅ Request change IB dihantar kepada user untuk submission {submission_id}.")
            return

        if action == CB_VERIF_REVOKE_VIP:
            item = get_submission(submission_id)
            if not item:
                await _reply_to_query_message(query, "❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            user_id = item.get("user_id")
            registration_flow = str(item.get("registration_flow") or "")
            if not isinstance(user_id, int):
                await _reply_to_query_message(query, "❌ User ID tak sah.")
                return
            remove_user_from_vip_tier(user_id, _tier_for_registration_flow(registration_flow))
            update_submission_fields(
                submission_id=submission_id,
                fields={
                    "status": "revoked",
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": query.from_user.id,
                },
            )
            await clear_user_deposit_prompt_by_submission(context, submission_id)
            await clear_user_ib_prompt_by_submission(context, submission_id)
            try:
                revoked_text = (
                    "Akses one-time purchase NEXT eVideo26 anda telah ditarik semula oleh admin.\n"
                    "Sila hubungi admin untuk maklumat lanjut."
                    if registration_flow == "one_time_purchase"
                    else "Akses NEXTexclusive anda telah ditarik semula oleh admin.\n"
                    "Sila hubungi admin untuk maklumat lanjut."
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=revoked_text,
                )
            except Exception:
                logger.exception("Failed to notify user after revoke")
            item = get_submission(submission_id)
            if item:
                await query.message.edit_text(render_admin_submission_text(item), reply_markup=approved_admin_keyboard(submission_id))
            return

        status = action_status_map.get(action)
        if not status:
            return

        updated = update_submission_status(submission_id=submission_id, status=status, reviewer_id=query.from_user.id)
        if not updated:
            await _reply_to_query_message(query, "❌ Rekod submission tak jumpa atau dah dipadam.")
            return

        target_user_id = updated.get("user_id")
        registration_flow = str(updated.get("registration_flow") or "")
        if isinstance(target_user_id, int):
            await clear_user_deposit_prompt_by_submission(context, submission_id)
            await clear_user_ib_prompt_by_submission(context, submission_id)
            try:
                if status == "rejected":
                    rejected_text = (
                        "Permohonan NEXT eVideo26 one-time purchase anda tidak diluluskan.\n"
                        "Sila hubungi admin untuk maklumat lanjut."
                        if registration_flow == "one_time_purchase"
                        else "Permohonan akses NEXTexclusive anda tidak diluluskan.\n"
                        "Sila buat pendaftaran baru."
                    )
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=rejected_text,
                    )
                elif status == "pending":
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            "Permohonan anda sedang disemak semula.\n"
                            "Sila tunggu maklum balas seterusnya daripada admin."
                        ),
                    )
                elif status == "approved":
                    add_user_to_vip_tier(updated, _tier_for_registration_flow(registration_flow))
                    approved_text = (
                        "Tahniah! Pembayaran one-time purchase NEXT eVideo26 anda telah diluluskan.\n"
                        "Sila tunggu arahan akses seterusnya daripada admin."
                        if registration_flow == "one_time_purchase"
                        else "Tahniah! Anda kini boleh menikmati semua keistimewaan/privilege NEXTexclusive."
                    )
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=approved_text,
                    )
            except Exception:
                logger.exception("Failed to send status update to user")

        status_label = {
            "approved": "✅ APPROVED",
            "pending": "PENDING",
            "rejected": "❌ REJECTED",
        }.get(status, status.upper())
        if status == "approved":
            refreshed = get_submission(submission_id)
            if refreshed:
                await query.message.edit_text(
                    render_admin_submission_text(refreshed),
                    reply_markup=approved_admin_keyboard(submission_id),
                )
            return

        if status == "rejected":
            refreshed = get_submission(submission_id)
            if refreshed:
                await query.message.edit_text(render_admin_submission_text(refreshed))
            return

        await refresh_admin_submission_message(context, submission_id)
        await _reply_to_query_message(query, f"✅ Status submission {submission_id} ditetapkan kepada {status_label}.")
        return


async def handle_user_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if ":" not in str(query.data):
        return

    action, submission_id = str(query.data).split(":", 1)
    item = get_submission(submission_id)
    if not item:
        await _reply_to_query_message(query, "❌ Rekod submission tak jumpa.")
        return

    user_id = item.get("user_id")
    if query.from_user.id != user_id:
        await _reply_to_query_message(query, "❌ Butang ini bukan untuk anda.")
        return

    if action == CB_USER_DEPOSIT_CANCEL:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_deposit_prompt_message_id": None})
        await _reply_to_query_message(query, "Baik, status deposit anda kekal belum selesai.")
        return

    if action == CB_USER_DEPOSIT_DONE:
        updated = update_submission_fields(
            submission_id=submission_id,
            fields={
                "has_deposit_100": True,
                "status": "pending",
                "deposit_completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not updated:
            await _reply_to_query_message(query, "❌ Rekod submission tak jumpa.")
            return
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_deposit_prompt_message_id": None})
        await refresh_admin_submission_message(context, submission_id)
        await _reply_to_query_message(query, 
            "✅ Deposit selesai direkod.\n"
            "Permohonan anda dihantar semula kepada admin untuk semakan."
        )
        return


async def handle_user_ib_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if ":" not in str(query.data):
        return

    action, submission_id = str(query.data).split(":", 1)
    item = get_submission(submission_id)
    if not item:
        await _reply_to_query_message(query, "❌ Rekod submission tak jumpa.")
        return

    user_id = item.get("user_id")
    if query.from_user.id != user_id:
        await _reply_to_query_message(query, "❌ Butang ini bukan untuk anda.")
        return

    if action == CB_USER_IB_CANCEL:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_ib_prompt_message_id": None})
        await _reply_to_query_message(query, "Baik, status submit request penukaran IB anda kekal belum selesai.")
        return

    if action == CB_USER_IB_DONE:
        updated = update_submission_fields(
            submission_id=submission_id,
            fields={
                "ib_request_submitted": True,
                "status": "pending",
                "ib_request_completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not updated:
            await _reply_to_query_message(query, "❌ Rekod submission tak jumpa.")
            return
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_ib_prompt_message_id": None})
        await refresh_admin_submission_message(context, submission_id)
        await _reply_to_query_message(query, 
            "✅ Request penukaran IB selesai direkod.\n"
            "Permohonan anda dihantar semula kepada admin untuk semakan."
        )
        return


async def group_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat:
        return
    if not is_admin_user(user.id):
        await message.reply_text("❌ Akses ditolak.")
        return
    await message.reply_text(
        "📌 Group/Chat Info\n"
        f"- chat_id: {chat.id}\n"
        f"- type: {chat.type}\n\n"
        "Salin chat_id ini dan letak dalam `.env`:\n"
        "SIDEBOT_ADMIN_GROUP_ID=<chat_id>",
    )


def _db_report_summary() -> str:
    with _connect_shared_db() as conn:
        _ensure_users_table(conn)
        _ensure_submissions_table(conn)
        users_total = int(conn.execute("SELECT COUNT(*) FROM sidebot_users").fetchone()[0])
        users_tnc_yes = int(conn.execute("SELECT COUNT(*) FROM sidebot_users WHERE tnc_accepted = 1").fetchone()[0])
        submissions_total = int(conn.execute("SELECT COUNT(*) FROM sidebot_submissions").fetchone()[0])
        status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS c
            FROM sidebot_submissions
            GROUP BY status
            ORDER BY status
            """
        ).fetchall()
        latest_row = conn.execute(
            "SELECT submitted_at, submission_id FROM sidebot_submissions ORDER BY submitted_at DESC, submission_id DESC LIMIT 1"
        ).fetchone()

    by_status = {str(row["status"] or "unknown"): int(row["c"] or 0) for row in status_rows}
    approved = by_status.get("approved", 0)
    pending = by_status.get("pending", 0)
    rejected = by_status.get("rejected", 0)
    other = submissions_total - approved - pending - rejected
    latest_text = "-"
    if latest_row is not None:
        latest_text = f"{latest_row['submitted_at']} ({latest_row['submission_id']})"
    return (
        "📊 Sidebot DB Report\n\n"
        f"Users total: {users_total}\n"
        f"TnC accepted: {users_tnc_yes}\n"
        f"Submissions total: {submissions_total}\n"
        f"Approved: {approved}\n"
        f"Pending: {pending}\n"
        f"Rejected: {rejected}\n"
        f"Other status: {other}\n"
        f"Latest submission: {latest_text}"
    )


async def db_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if not is_admin_user(user.id):
        await message.reply_text("❌ Akses ditolak.")
        return
    try:
        await message.reply_text(_db_report_summary())
    except sqlite3.Error:
        logger.exception("Failed to build DB report")
        await message.reply_text("❌ Gagal baca DB report.")


async def db_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await db_report(update, context)


async def handle_application_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.error is None:
        logger.error("Unhandled sidebot error without exception object")
        return
    logger.error(
        "Unhandled sidebot exception: %s",
        context.error,
        exc_info=(type(context.error), context.error, context.error.__traceback__),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.text:
        return

    text = message.text.strip()

    if not has_tnc_accepted(user.id):
        await message.reply_text(
            "❌ Akses menu dikunci sehingga anda setuju TnC. Tekan /start untuk teruskan.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    awaiting_wallet_check = bool(context.user_data.get("awaiting_under_ib_wallet_check"))
    if awaiting_wallet_check:
        if text == MENU_BACK_MAIN:
            context.user_data["awaiting_under_ib_wallet_check"] = False
            await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
            return
        if text == MENU_ADMIN_PANEL:
            context.user_data["awaiting_under_ib_wallet_check"] = False
            await message.reply_text(ADMIN_PANEL_TEXT, reply_markup=admin_panel_keyboard())
            return
        if not is_admin_user(user.id):
            context.user_data["awaiting_under_ib_wallet_check"] = False
            await message.reply_text("❌ Akses ditolak.")
            return
        wallet_id = text
        if not is_valid_wallet_id(wallet_id):
            await message.reply_text("❌ Wallet ID mesti 7 angka. Sila masukkan semula atau tekan Back.")
            return
        context.user_data["awaiting_under_ib_wallet_check"] = False
        is_client, check_message = amarkets_check_is_client(wallet_id)
        if is_client is True:
            result = "✅ YA, client ini under affiliate/IB anda."
        elif is_client is False:
            result = "❌ TIDAK, client ini bukan under affiliate/IB anda."
        else:
            result = f"⚠️ Semakan gagal: {check_message}"
        await message.reply_text(
            f"Semakan Wallet ID: {wallet_id}\n{result}",
            reply_markup=admin_panel_keyboard(),
        )
        return

    awaiting_custom_payment_submission_id = str(context.user_data.get("awaiting_custom_payment_submission_id") or "").strip()
    if awaiting_custom_payment_submission_id:
        if not is_admin_user(user.id):
            context.user_data.pop("awaiting_custom_payment_submission_id", None)
            await message.reply_text("❌ Akses ditolak.")
            return
        lowered = text.lower().strip()
        if lowered in {"cancel", "batal"}:
            context.user_data.pop("awaiting_custom_payment_submission_id", None)
            await message.reply_text("Request payment custom dibatalkan.", reply_markup=admin_panel_keyboard())
            return
        amount_text = lowered.replace("rm", "").replace(",", "").replace(" ", "")
        if not amount_text.isdigit():
            await message.reply_text("❌ Amaun tak sah. Masukkan nombor sahaja, contoh `350` atau `RM350`.", parse_mode="Markdown")
            return
        amount_rm = int(amount_text)
        if amount_rm <= 0:
            await message.reply_text("❌ Amaun mesti lebih besar dari 0.")
            return

        context.user_data.pop("awaiting_custom_payment_submission_id", None)
        item = update_submission_fields(
            submission_id=awaiting_custom_payment_submission_id,
            fields={
                "status": "request_payment",
                "has_deposit_100": False,
                "payment_request_amount_rm": amount_rm,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "reviewed_by": user.id,
            },
        )
        if not item:
            await message.reply_text("❌ Rekod submission tak jumpa atau dah dipadam.", reply_markup=admin_panel_keyboard())
            return
        target_user_id = item.get("user_id")
        if isinstance(target_user_id, int):
            try:
                await send_user_deposit_request_message(context, awaiting_custom_payment_submission_id, item)
            except Exception:
                logger.exception("Failed to send custom payment request")
        await refresh_admin_submission_message(context, awaiting_custom_payment_submission_id)
        await message.reply_text(
            f"✅ Request payment RM{amount_rm} dihantar kepada user untuk submission {awaiting_custom_payment_submission_id}.",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if text == MENU_ADMIN_PANEL:
        if not is_admin_user(user.id):
            await message.reply_text("❌ Akses ditolak.", reply_markup=main_menu_keyboard(user.id))
            return
        await message.reply_text(ADMIN_PANEL_TEXT, reply_markup=admin_panel_keyboard())
        return

    if text == MENU_CHECK_UNDER_IB:
        if not is_admin_user(user.id):
            await message.reply_text("❌ Akses ditolak.", reply_markup=main_menu_keyboard(user.id))
            return
        context.user_data["awaiting_under_ib_wallet_check"] = True
        await message.reply_text(
            "Masukkan AMarkets Wallet ID (7 angka) untuk semakan under IB.",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if text == MENU_ADMIN_USERS:
        if not is_admin_user(user.id):
            await message.reply_text("❌ Akses ditolak.", reply_markup=main_menu_keyboard(user.id))
            return
        admin_users_url = get_admin_users_webapp_url()
        if not admin_users_url:
            await message.reply_text("Miniapp URL belum diset. Isi SIDEBOT_ADMIN_USERS_WEBAPP_URL atau SIDEBOT_REGISTER_WEBAPP_URL dalam .env dulu.")
            return
        button = KeyboardButton(MENU_ADMIN_USERS, web_app=WebAppInfo(url=admin_users_url))
        await message.reply_text(
            "Buka miniapp User Directory di bawah.",
            reply_markup=ReplyKeyboardMarkup(
                [[button], [KeyboardButton(MENU_ADMIN_PANEL)], [KeyboardButton(MENU_BACK_MAIN)]],
                resize_keyboard=True,
            ),
        )
        return

    if text == MENU_DAFTAR_NEXT_MEMBER:
        if get_register_next_webapp_url():
            await message.reply_text("Buka miniapp melalui butang web app pada menu.")
            return
        await message.reply_text("Miniapp URL belum diset. Isi SIDEBOT_REGISTER_WEBAPP_URL dalam .env dulu.")
        return

    if text == MENU_BELI_EVIDEO26:
        if get_onetime_evideo_webapp_url():
            await message.reply_text("Buka miniapp One Time Purchase melalui butang web app pada menu.")
            return
        await message.reply_text("Miniapp URL belum diset. Isi SIDEBOT_ONETIME_EVIDEO_WEBAPP_URL dalam .env dulu.")
        return

    if text == MENU_OPEN_MMHELPER_BOT:
        url = get_mmhelper_bot_url()
        if not url:
            await message.reply_text("Link MM Helper belum diset. Isi SIDEBOT_MMHELPER_BOT_URL dalam .env dulu.")
            return
        await message.reply_text(
            "Tekan butang di bawah untuk buka MM Helper Bot.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Buka MM Helper Bot", url=url)]]),
        )
        return

    if text == MENU_OPEN_EVIDEO_BOT:
        url = get_evideo_bot_url()
        if not url:
            await message.reply_text("Link eVideo bot belum diset. Isi SIDEBOT_EVIDEO_BOT_URL dalam .env dulu.")
            return
        await message.reply_text(
            "Tekan butang di bawah untuk buka NEXT eVideo Bot.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Buka NEXT eVideo Bot", url=url)]]),
        )
        return

    if text == MENU_ALL_PRODUCT_PREVIEW:
        await message.reply_text("🛍️ All Product Preview (coming soon).", reply_markup=main_menu_keyboard(user.id))
        return

    if text == MENU_BETA_RESET:
        if not is_admin_user(user.id):
            await message.reply_text("❌ Akses ditolak.", reply_markup=main_menu_keyboard(user.id))
            return
        await message.reply_text("Mode pengesahan reset diaktifkan.", reply_markup=ReplyKeyboardRemove())
        await message.reply_text(BETA_RESET_PROMPT_TEXT, reply_markup=beta_reset_keyboard())
        return

    if text == MENU_BACK_MAIN:
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
        return


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not message.web_app_data or not user:
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.reply_text("❌ Data miniapp tak sah. Cuba buka semula.")
        return

    if not has_tnc_accepted(user.id):
        await message.reply_text(
            "❌ Akses menu dikunci sehingga anda setuju TnC. Tekan /start untuk teruskan.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    payload_type = str(payload.get("type") or "").strip()
    if payload_type == "sidebot_back_to_main_menu":
        if has_tnc_accepted(user.id):
            await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
            return
        await message.reply_text("Sila baca dan setuju TnC dulu.", reply_markup=ReplyKeyboardRemove())
        await message.reply_text(TNC_TEXT, reply_markup=tnc_keyboard())
        return

    if payload_type == "next_member_request_type":
        choice = str(payload.get("choice") or "").strip()
        labels = {
            "new_registration_amarkets": "Pendaftaran baru AMarkets",
            "ib_transfer_existing_amarkets": "Penukaran IB (Pelanggan sedia ada AMarkets)",
            "client_under_ib_reezo": "Client AMarkets under IB Reezo",
        }
        selected = labels.get(choice) or "Pilihan tidak dikenali"
        await message.reply_text(
            f"✅ Pilihan diterima: {selected}\n\nFlow seterusnya akan kita sambung dalam step berikutnya.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    if payload_type == "sidebot_check_under_ib_reezo":
        wallet_id = str(payload.get("wallet_id") or "").strip()
        if not is_valid_wallet_id(wallet_id):
            await message.reply_text("❌ Wallet ID mesti 7 angka.")
            return
        is_client, check_message = amarkets_check_is_client(wallet_id)
        if is_client is True:
            await message.reply_text(
                f"✅ Wallet {wallet_id} disahkan berada di bawah Affiliate/IB Reezo.\n"
                "Anda boleh teruskan isi borang pengesahan dalam miniapp."
            )
            return
        if is_client is False:
            await message.reply_text(
                f"❌ Wallet {wallet_id} tidak berada di bawah Affiliate/IB Reezo.\n"
                "Sila gunakan flow Pendaftaran Baru atau Penukaran IB."
            )
            return
        await message.reply_text(f"⚠️ Semakan gagal: {check_message}")
        return

    if payload_type == "sidebot_verification_submit":
        registration_flow = str(payload.get("registration_flow") or "new_registration").strip() or "new_registration"
        ib_request_raw = payload.get("ib_request_submitted", None)
        ib_request_submitted = None
        if registration_flow == "ib_transfer":
            if isinstance(ib_request_raw, bool):
                ib_request_submitted = ib_request_raw

        wallet_id = str(payload.get("wallet_id") or "").strip()
        full_name = str(payload.get("full_name") or "").strip()
        phone_number = str(payload.get("phone_number") or "").strip()
        has_deposit_100 = bool(payload.get("has_deposit_100"))

        if not wallet_id or not full_name or not phone_number:
            await message.reply_text("❌ Data pengesahan tak lengkap. Sila isi semula dalam miniapp.")
            return
        if not is_valid_wallet_id(wallet_id):
            await message.reply_text("❌ AMarkets Wallet ID mesti tepat 7 angka.")
            return
        if registration_flow == "ib_transfer" and ib_request_submitted is None:
            await message.reply_text("❌ Status submit request penukaran IB belum dipilih. Sila isi semula.")
            return

        saved = store_verification_submission(
            user_id=user.id,
            telegram_username=str(user.username or ""),
            wallet_id=wallet_id,
            has_deposit_100=has_deposit_100,
            full_name=full_name,
            phone_number=phone_number,
            registration_flow=registration_flow,
            ib_request_submitted=ib_request_submitted,
        )
        api_is_client_under_ib = None
        api_check_message = ""
        if registration_flow in {"ib_transfer", "under_ib_reezo"}:
            api_is_client_under_ib, api_check_message = amarkets_check_is_client(wallet_id)
            update_submission_fields(
                submission_id=str(saved.get("submission_id")),
                fields={
                    "api_checked_at": datetime.now(timezone.utc).isoformat(),
                    "api_is_client_under_ib": api_is_client_under_ib,
                    "api_check_message": api_check_message,
                },
            )
            saved = get_submission(str(saved.get("submission_id"))) or saved

        deposit_required_usd = get_required_deposit_amount(registration_flow)
        deposit_text = "Ya" if has_deposit_100 else "Belum"
        submission_id = str(saved.get("submission_id") or "-")

        admin_notified = False
        try:
            admin_notified = await send_submission_to_admin_group(context, saved)
        except Exception:
            logger.exception("Failed to send verification notification to admin group")

        notify_text = (
            "Permohonan anda telah direkod dan dihantar ke admin.\n"
            if admin_notified
            else "Permohonan anda telah direkod. Notifikasi admin belum berjaya dihantar.\n"
        )
        await message.reply_text(
            "✅ Pengesahan diterima.\n"
            f"{notify_text}"
            "Sila tunggu approval.\n\n"
            f"Submission ID: {submission_id}\n"
            f"Wallet ID: {wallet_id}\n"
            f"Deposit Minimum USD{deposit_required_usd}: {deposit_text}\n"
            f"Nama: {full_name}\n"
            f"Telefon: {phone_number}",
            reply_markup=main_menu_keyboard(user.id),
        )
        if registration_flow == "ib_transfer":
            if not ib_request_submitted:
                try:
                    latest = get_submission(submission_id)
                    if latest:
                        await send_user_change_ib_request_message(context, submission_id, latest)
                except Exception:
                    logger.exception("Failed to send change-IB request after IB verification submit")
            elif not has_deposit_100:
                try:
                    latest = get_submission(submission_id)
                    if latest:
                        await send_user_deposit_request_message(context, submission_id, latest)
                except Exception:
                    logger.exception("Failed to send deposit request after IB verification submit")
        elif not has_deposit_100:
            try:
                latest = get_submission(submission_id)
                if latest:
                    await send_user_deposit_request_message(context, submission_id, latest)
            except Exception:
                logger.exception("Failed to send deposit request after verification submit")
        return

    if payload_type == "sidebot_onetime_payment_submit":
        full_name = str(payload.get("full_name") or "").strip()
        phone_number = str(payload.get("phone_number") or "").strip()
        transfer_to = str(payload.get("transfer_to") or "").strip().lower()
        amount_raw = str(payload.get("amount_paid") or "").strip()

        if not full_name or not phone_number or transfer_to not in {"maybank", "tng"} or not amount_raw:
            await message.reply_text("❌ Data pengesahan pembayaran tak lengkap. Sila isi semula.")
            return
        if not amount_raw.isdigit():
            await message.reply_text("❌ Jumlah bayaran mesti nombor sahaja.")
            return

        amount_paid = int(amount_raw)
        if amount_paid <= 0:
            await message.reply_text("❌ Jumlah bayaran mesti lebih dari 0.")
            return

        saved = store_onetime_payment_submission(
            user_id=user.id,
            telegram_username=str(user.username or ""),
            full_name=full_name,
            phone_number=phone_number,
            transfer_to=transfer_to,
            amount_paid=amount_paid,
        )
        submission_id = str(saved.get("submission_id") or "-")

        admin_notified = False
        try:
            admin_notified = await send_submission_to_admin_group(context, saved)
        except Exception:
            logger.exception("Failed to send one-time payment notification to admin group")

        notify_text = (
            "Pengesahan pembayaran anda telah dihantar ke admin."
            if admin_notified
            else "Pengesahan pembayaran direkod, tetapi notifikasi admin belum berjaya dihantar."
        )
        await message.reply_text(
            "✅ Pengesahan pembayaran one-time purchase diterima.\n"
            f"{notify_text}\n"
            f"Submission ID: {submission_id}\n"
            "Sila tunggu semakan admin.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    await message.reply_text("ℹ️ Miniapp demo diterima.", reply_markup=main_menu_keyboard(user.id))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        init_sidebot_storage()
    except sqlite3.Error:
        logger.warning("Sidebot storage init failed, continuing with JSON fallback", exc_info=True)

    app = ApplicationBuilder().token(get_token()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("groupid", group_id))
    app.add_handler(CommandHandler("dbreport", db_report))
    app.add_handler(CommandHandler("dbhealth", db_health))
    app.add_handler(CallbackQueryHandler(handle_tnc_callback, pattern=f"^({TNC_ACCEPT}|{TNC_DECLINE})$"))
    app.add_handler(
        CallbackQueryHandler(
            handle_admin_callback,
            pattern=f"^({CB_BETA_RESET_CONFIRM}|{CB_BETA_RESET_CANCEL}|{CB_VERIF_APPROVE}|{CB_VERIF_PENDING}|{CB_VERIF_REJECT}|{CB_VERIF_REQUEST_DEPOSIT}|{CB_VERIF_REQUEST_PAYMENT_CUSTOM}|{CB_VERIF_REQUEST_CHANGE_IB}|{CB_VERIF_REVOKE_VIP}).*",
        )
    )
    app.add_handler(CallbackQueryHandler(handle_user_deposit_callback, pattern=f"^({CB_USER_DEPOSIT_DONE}|{CB_USER_DEPOSIT_CANCEL}).*"))
    app.add_handler(CallbackQueryHandler(handle_user_ib_callback, pattern=f"^({CB_USER_IB_DONE}|{CB_USER_IB_CANCEL}).*"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(handle_application_error)
    app.run_polling()


if __name__ == "__main__":
    main()
