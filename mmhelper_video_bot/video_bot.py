"""Standalone video bot for NEXT eVideo26 and strategy videos."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from texts import (
    COMING_SOON_FIBO,
    COMING_SOON_INTRADAY,
    EVIDEO_MENU_TEXT,
    MAIN_MENU_TEXT,
)
from video_catalog import LEVEL_LABELS, LEVEL_TOPICS, VIDEO_CATALOG

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MENU_EVIDEO = "🎬 NEXT eVideo26 Full Silibus"
MENU_INTRADAY = "📈 Intraday Strategy (coming soon)"
MENU_FIBO = "🧩 Fibo Extension Custom Strategy (coming soon)"
MENU_MMHELPER = "🤖 MM Helper"
MENU_ADMIN = "📝 Daftar NEXT"
MENU_ADMIN_PANEL = "🔒 Admin Panel"
MENU_ADMIN_PUSH = "📣 Push Notification"
MENU_ADMIN_DELETE = "🗑️ Delete Video"
MENU_ADMIN_VIDEO_STATUS = "🧷 Video Status"
MENU_ADMIN_BACK = "⬅️ Back to Main Menu"
MENU_ADMIN_DELETE_CONFIRM = "✅ Confirm Delete All"
MENU_ADMIN_DELETE_CANCEL = "❌ Cancel"

MENU_LEVEL_BASIC = "🟢 Basic"
MENU_LEVEL_INTERMEDIATE = "🟠 Intermediate"
MENU_LEVEL_ADVANCED = "🔴 Advanced"
MENU_BACK_MAIN = "⬅️ Back to Main Menu"
MENU_TOPIC_PREV = "⏮️ << Prev Topic"
MENU_TOPIC_NEXT = "⏭️ Next Topic >>"
MENU_TOPIC_PICK = "📚 Pilih Topik"
MENU_TOPIC_MAIN = "🏠 Main Menu"

SENT_VIDEO_LOG_PATH = Path(__file__).with_name("sent_video_log.json")
KNOWN_USERS_PATH = Path(__file__).with_name("known_users.json")
SCHEDULED_NOTIFICATIONS_PATH = Path(__file__).with_name("scheduled_notifications.json")
AUTO_DELETE_NOTICES_PATH = Path(__file__).with_name("auto_delete_notices.json")
VIDEO_STATUS_PATH = Path(__file__).with_name("video_status.json")
SAVED_VIDEOS_PATH = Path(__file__).with_name("saved_videos.json")
DEFAULT_VIP_WHITELIST_PATH = Path(__file__).resolve().parent.parent / "mmhelper_sidebot" / "sidebot_vip_whitelist.json"
DEFAULT_SHARED_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "mmhelper_shared.db"
VIDEO_STATE_TABLE = "video_bot_kv_state"
VIDEO_STATUS_KEY = "video_status_overrides"
VIDEO_SENT_LOG_KEY = "video_sent_log"
VIDEO_KNOWN_USERS_KEY = "video_known_users"
VIDEO_SCHEDULED_KEY = "video_scheduled_notifications"
VIDEO_AUTO_DELETE_KEY = "video_auto_delete_notices"
VIDEO_SAVED_VIDEOS_KEY = "video_saved_videos"
SIDEBOT_STATE_TABLE = "sidebot_kv_state"
VIDEO_HAPPY_HOUR_RULES_KEY = "video_happy_hour_rules"
VIDEO_HAPPY_HOUR_RUNTIME_KEY = "video_happy_hour_runtime"
SAVE_LATER_MAX = 2
VIP2_SUBSCRIPTION_DAYS = 45
HAPPY_HOUR_FREE_PICK_LIMIT = 2
HAPPY_HOUR_DELETE_AFTER_SECONDS = 30 * 60


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


def get_token() -> str:
    load_local_env()
    token = (os.getenv("VIDEO_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set VIDEO_BOT_TOKEN in mmhelper_video_bot/.env")
    return token


def get_video_db_group_id() -> int | None:
    raw = (os.getenv("VIDEO_DB_GROUP_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def get_evideo_webapp_url() -> str:
    url = (os.getenv("VIDEO_EVIDEO_WEBAPP_URL") or "").strip()
    if not url.lower().startswith("https://"):
        return ""
    # Ignore template/placeholder values so bot menu still works.
    if "<" in url or ">" in url or " " in url:
        return ""
    return url


def get_push_webapp_url() -> str:
    explicit = (os.getenv("VIDEO_PUSH_WEBAPP_URL") or "").strip()
    if explicit.lower().startswith("https://") and "<" not in explicit and ">" not in explicit and " " not in explicit:
        return explicit

    base = get_evideo_webapp_url()
    if not base:
        return ""
    if base.endswith("/"):
        return f"{base}push-notification.html"
    if base.endswith(".html"):
        prefix = base.rsplit("/", 1)[0]
        return f"{prefix}/push-notification.html"
    return f"{base}/push-notification.html"


def get_video_status_webapp_url() -> str:
    explicit = (os.getenv("VIDEO_STATUS_WEBAPP_URL") or "").strip()
    if explicit.lower().startswith("https://") and "<" not in explicit and ">" not in explicit and " " not in explicit:
        return explicit

    base = get_evideo_webapp_url()
    if not base:
        return ""
    if base.endswith("/"):
        return f"{base}video-status.html"
    if base.endswith(".html"):
        prefix = base.rsplit("/", 1)[0]
        return f"{prefix}/video-status.html"
    return f"{base}/video-status.html"


def get_daftar_next_webapp_url() -> str:
    explicit = (os.getenv("VIDEO_DAFTAR_WEBAPP_URL") or "").strip()
    if explicit.lower().startswith("https://") and "<" not in explicit and ">" not in explicit and " " not in explicit:
        base = explicit
    else:
        root = get_evideo_webapp_url()
        if not root:
            return ""
        if root.endswith("/"):
            base = f"{root}daftar-next.html"
        elif root.endswith(".html"):
            prefix = root.rsplit("/", 1)[0]
            base = f"{prefix}/daftar-next.html"
        else:
            base = f"{root}/daftar-next.html"

    admin_bot_url = (os.getenv("VIDEO_ADMIN_BOT_URL") or "").strip()
    if not admin_bot_url:
        return base
    if not admin_bot_url.startswith("https://t.me/"):
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}admin_bot_url={quote(admin_bot_url, safe='')}"


def get_mmhelper_bot_url() -> str:
    raw = (os.getenv("VIDEO_MMHELPER_BOT_URL") or "").strip()
    if raw.startswith("https://t.me/"):
        return raw
    return ""


def get_bot_timezone() -> ZoneInfo:
    raw = (os.getenv("VIDEO_BOT_TIMEZONE") or "Asia/Kuala_Lumpur").strip()
    try:
        return ZoneInfo(raw)
    except Exception:
        return ZoneInfo("UTC")


def get_vip_whitelist_path() -> Path:
    raw = (os.getenv("VIDEO_VIP_WHITELIST_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_VIP_WHITELIST_PATH


def get_shared_db_path() -> Path:
    raw = (
        (os.getenv("VIDEO_SHARED_DB_PATH") or "")
        or (os.getenv("MMHELPER_SHARED_DB_PATH") or "")
    ).strip()
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_SHARED_DB_PATH


def _connect_shared_db() -> sqlite3.Connection:
    db_path = get_shared_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_video_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {VIDEO_STATE_TABLE} (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _read_state_json_from_db(key: str) -> object | None:
    try:
        with _connect_shared_db() as con:
            _ensure_video_state_table(con)
            row = con.execute(
                f"SELECT value_json FROM {VIDEO_STATE_TABLE} WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            raw = str(row["value_json"] or "").strip()
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
    except sqlite3.Error:
        logger.warning("Video state DB read failed key=%s", key, exc_info=True)
        return None


def _write_state_json_to_db(key: str, value: object) -> None:
    try:
        with _connect_shared_db() as con:
            _ensure_video_state_table(con)
            con.execute(
                f"""
                INSERT OR REPLACE INTO {VIDEO_STATE_TABLE} (key, value_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.Error:
        logger.warning("Video state DB write failed key=%s", key, exc_info=True)


def _read_sidebot_state_json(key: str) -> object | None:
    try:
        with _connect_shared_db() as con:
            row = con.execute(
                f"SELECT value_json FROM {SIDEBOT_STATE_TABLE} WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            raw = str(row["value_json"] or "").strip()
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
    except sqlite3.Error:
        return None


def _bootstrap_state_key_from_file(conn: sqlite3.Connection, key: str, path: Path, default: object) -> None:
    existing = conn.execute(
        f"SELECT 1 FROM {VIDEO_STATE_TABLE} WHERE key = ? LIMIT 1",
        (key,),
    ).fetchone()
    if existing is not None:
        return
    value: object = default
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            value = loaded
        except (OSError, json.JSONDecodeError):
            value = default
    conn.execute(
        f"""
        INSERT OR REPLACE INTO {VIDEO_STATE_TABLE} (key, value_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), datetime.now(timezone.utc).isoformat()),
    )


def init_video_storage() -> None:
    with _connect_shared_db() as con:
        _ensure_video_state_table(con)
        _bootstrap_state_key_from_file(con, VIDEO_STATUS_KEY, VIDEO_STATUS_PATH, {})
        _bootstrap_state_key_from_file(con, VIDEO_SENT_LOG_KEY, SENT_VIDEO_LOG_PATH, [])
        _bootstrap_state_key_from_file(con, VIDEO_KNOWN_USERS_KEY, KNOWN_USERS_PATH, [])
        _bootstrap_state_key_from_file(con, VIDEO_SCHEDULED_KEY, SCHEDULED_NOTIFICATIONS_PATH, [])
        _bootstrap_state_key_from_file(con, VIDEO_AUTO_DELETE_KEY, AUTO_DELETE_NOTICES_PATH, {})
        _bootstrap_state_key_from_file(
            con,
            VIDEO_HAPPY_HOUR_RUNTIME_KEY,
            Path("__video_happy_hour_runtime_bootstrap__.json"),
            {"sessions": {}},
        )


def _parse_iso_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _vip2_days(value: object) -> int:
    try:
        days = int(value or VIP2_SUBSCRIPTION_DAYS)
    except (TypeError, ValueError):
        days = VIP2_SUBSCRIPTION_DAYS
    if days <= 0:
        days = VIP2_SUBSCRIPTION_DAYS
    return days


def _is_vip2_active_from_added_at(added_at: str, subscription_days: object = None) -> bool:
    approved_at = _parse_iso_datetime(added_at)
    if approved_at is None:
        return False
    expires_at = approved_at + timedelta(days=_vip2_days(subscription_days))
    return datetime.now(timezone.utc) < expires_at


def _is_tier_row_active(tier: str, status: str, added_at: str, subscription_days: object = None) -> bool:
    normalized_status = str(status or "active").strip().lower()
    if normalized_status not in {"", "active"}:
        return False
    tier_key = str(tier or "").strip().lower()
    if tier_key == "vip2":
        return _is_vip2_active_from_added_at(added_at, subscription_days=subscription_days)
    return True


def _has_tier_access_db(user_id: int, tiers: tuple[str, ...]) -> bool:
    db_path = get_shared_db_path()
    if not db_path.exists():
        return False
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in tiers)
        rows = con.execute(
            f"""
            SELECT tier, added_at, subscription_days, status
            FROM vip_whitelist
            WHERE user_id = ?
              AND tier IN ({placeholders})
            """,
            (str(user_id), *tiers),
        ).fetchall()
        for row in rows:
            if _is_tier_row_active(
                tier=str(row["tier"] or ""),
                status=str(row["status"] or "active"),
                added_at=str(row["added_at"] or ""),
                subscription_days=row["subscription_days"],
            ):
                return True
        return False
    except sqlite3.Error:
        logger.warning("VIP shared DB read failed; fallback JSON whitelist", exc_info=True)
        return False
    finally:
        con.close()


def _load_vip_whitelist_data() -> dict:
    path = get_vip_whitelist_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def has_next_topic_access(user_id: int | None) -> bool:
    if not isinstance(user_id, int):
        return False
    if is_super_user_id(user_id):
        return True
    # Admin always has access.
    if get_admin_user_id() == user_id:
        return True

    if _has_tier_access_db(user_id, ("vip2", "vip3")):
        return True

    data = _load_vip_whitelist_data()
    user_key = str(user_id)
    for tier in ("vip2", "vip3"):
        tier_obj = data.get(tier)
        if not isinstance(tier_obj, dict):
            continue
        users = tier_obj.get("users")
        if not isinstance(users, dict):
            continue
        row = users.get(user_key)
        if isinstance(row, dict):
            if _is_tier_row_active(
                tier=tier,
                status=str(row.get("status") or "active"),
                added_at=str(row.get("added_at") or ""),
                subscription_days=row.get("subscription_days"),
            ):
                return True
    return False


def has_save_later_access(user_id: int | None) -> bool:
    if not isinstance(user_id, int):
        return False
    if is_super_user_id(user_id):
        return True
    if _has_tier_access_db(user_id, ("vip2", "vip3")):
        return True

    data = _load_vip_whitelist_data()
    user_key = str(user_id)
    for tier in ("vip2", "vip3"):
        tier_obj = data.get(tier)
        if not isinstance(tier_obj, dict):
            continue
        users = tier_obj.get("users")
        if not isinstance(users, dict):
            continue
        row = users.get(user_key)
        if isinstance(row, dict):
            if _is_tier_row_active(
                tier=tier,
                status=str(row.get("status") or "active"),
                added_at=str(row.get("added_at") or ""),
                subscription_days=row.get("subscription_days"),
            ):
                return True
    return False


def parse_local_schedule_to_epoch(date_value: str, time_value: str) -> int:
    date_value = str(date_value or "").strip()
    time_value = str(time_value or "").strip()
    dt = datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")
    tz = get_bot_timezone()
    localized = dt.replace(tzinfo=tz)
    return int(localized.timestamp())


def get_admin_user_id() -> int | None:
    raw = (os.getenv("VIDEO_ADMIN_USER_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def get_super_user_ids() -> set[int]:
    raw = (os.getenv("VIDEO_SUPER_USER_IDS") or "").strip()
    out: set[int] = set()
    if not raw:
        return out
    for part in raw.split(","):
        token = str(part).strip()
        if not token:
            continue
        try:
            out.add(int(token))
        except ValueError:
            continue
    return out


def is_super_user_id(user_id: int | None) -> bool:
    if not isinstance(user_id, int):
        return False
    return int(user_id) in get_super_user_ids()


def is_admin_user(update: Update) -> bool:
    admin_id = get_admin_user_id()
    user = update.effective_user
    if admin_id is None or not user:
        return False
    return int(user.id) == int(admin_id)


def _topic_message_ids_payload() -> str:
    payload: dict[str, dict[str, int]] = {}
    for level, topics in LEVEL_TOPICS.items():
        level_map: dict[str, int] = {}
        for row in topics:
            topic_no = int(row.get("topic_no") or 0)
            if topic_no <= 0:
                continue
            level_map[str(topic_no)] = int(row.get("message_id") or 0)
        payload[level] = level_map
    return json.dumps(payload, separators=(",", ":"))


def _load_video_status_overrides() -> dict[str, dict[str, dict[str, str]]]:
    raw = _read_state_json_from_db(VIDEO_STATUS_KEY)
    if raw is None:
        if not VIDEO_STATUS_PATH.exists():
            raw = {}
        else:
            try:
                raw = json.loads(VIDEO_STATUS_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
        _write_state_json_to_db(VIDEO_STATUS_KEY, raw)
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, dict[str, str]]] = {}
    for level, topics in raw.items():
        if not isinstance(topics, dict):
            continue
        level_key = str(level).strip().lower()
        level_map: dict[str, dict[str, str]] = {}
        for topic_no, data in topics.items():
            if not isinstance(data, dict):
                continue
            status = str(data.get("status") or "").strip().lower()
            if status not in {"coming_soon", "available_on", "online"}:
                continue
            row: dict[str, str] = {"status": status}
            available_on = str(data.get("available_on") or "").strip()
            if available_on:
                row["available_on"] = available_on
            level_map[str(topic_no)] = row
        if level_map:
            result[level_key] = level_map
    return result


def _save_video_status_overrides(data: dict[str, dict[str, dict[str, str]]]) -> None:
    _write_state_json_to_db(VIDEO_STATUS_KEY, data)
    try:
        VIDEO_STATUS_PATH.write_text(
            json.dumps(data, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write video status overrides")


def _upsert_video_status(level: str, topic_no: int, status: str, available_on: str) -> None:
    all_data = _load_video_status_overrides()
    level_key = str(level).strip().lower()
    topic_key = str(int(topic_no))
    if level_key not in all_data:
        all_data[level_key] = {}
    row: dict[str, str] = {"status": status}
    if status == "available_on" and available_on:
        row["available_on"] = available_on
    all_data[level_key][topic_key] = row
    _save_video_status_overrides(all_data)


def _video_status_payload() -> str:
    data = _load_video_status_overrides()
    return json.dumps(data, separators=(",", ":"))


def get_evideo_webapp_url_with_topic_ids(user_id: int | None = None) -> str:
    base = get_evideo_webapp_url()
    if not base:
        return ""
    encoded_payload = quote(_topic_message_ids_payload(), safe="")
    encoded_status = quote(_video_status_payload(), safe="")
    next_access = "1" if has_next_topic_access(user_id) else "0"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}topic_ids={encoded_payload}&video_status={encoded_status}&next_access={next_access}"


def main_menu_keyboard(show_admin_panel: bool = False, user_id: int | None = None) -> ReplyKeyboardMarkup:
    evideo_url = get_evideo_webapp_url_with_topic_ids(user_id)
    if evideo_url:
        evideo_button = KeyboardButton(MENU_EVIDEO, web_app=WebAppInfo(url=evideo_url))
    else:
        evideo_button = KeyboardButton(MENU_EVIDEO)
    daftar_url = get_daftar_next_webapp_url()
    if daftar_url:
        daftar_button = KeyboardButton(MENU_ADMIN, web_app=WebAppInfo(url=daftar_url))
    else:
        daftar_button = KeyboardButton(MENU_ADMIN)
    rows = [
        [evideo_button],
        [KeyboardButton(MENU_INTRADAY)],
        [KeyboardButton(MENU_FIBO)],
        [KeyboardButton(MENU_MMHELPER), daftar_button],
    ]
    if show_admin_panel:
        rows.append([KeyboardButton(MENU_ADMIN_PANEL)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    push_url = get_push_webapp_url()
    status_url = get_video_status_webapp_url()
    if push_url:
        push_button = KeyboardButton(MENU_ADMIN_PUSH, web_app=WebAppInfo(url=push_url))
    else:
        push_button = KeyboardButton(MENU_ADMIN_PUSH)
    if status_url:
        status_button = KeyboardButton(MENU_ADMIN_VIDEO_STATUS, web_app=WebAppInfo(url=status_url))
    else:
        status_button = KeyboardButton(MENU_ADMIN_VIDEO_STATUS)
    rows = [
        [push_button],
        [status_button],
        [KeyboardButton(MENU_ADMIN_DELETE)],
        [KeyboardButton(MENU_ADMIN_BACK)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_delete_confirm_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(MENU_ADMIN_DELETE_CONFIRM)],
        [KeyboardButton(MENU_ADMIN_DELETE_CANCEL)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def level_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(MENU_LEVEL_BASIC), KeyboardButton(MENU_LEVEL_INTERMEDIATE)],
        [KeyboardButton(MENU_LEVEL_ADVANCED)],
        [KeyboardButton(MENU_BACK_MAIN)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def topic_navigation_keyboard(user_id: int | None = None) -> ReplyKeyboardMarkup:
    evideo_url = get_evideo_webapp_url_with_topic_ids(user_id)
    if evideo_url:
        pick_button = KeyboardButton(MENU_TOPIC_PICK, web_app=WebAppInfo(url=evideo_url))
    else:
        pick_button = KeyboardButton(MENU_TOPIC_PICK)
    rows = [
        [KeyboardButton(MENU_TOPIC_PREV), KeyboardButton(MENU_TOPIC_NEXT)],
        [pick_button],
        [KeyboardButton(MENU_TOPIC_MAIN)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def vip_locked_keyboard() -> ReplyKeyboardMarkup:
    daftar_url = get_daftar_next_webapp_url()
    if daftar_url:
        daftar_button = KeyboardButton(MENU_ADMIN, web_app=WebAppInfo(url=daftar_url))
    else:
        daftar_button = KeyboardButton(MENU_ADMIN)
    rows = [
        [daftar_button],
        [KeyboardButton(MENU_TOPIC_MAIN)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def _message_link(group_id: int, message_id: int) -> str:
    # Telegram deep-link format for private supergroup messages.
    group_text = str(group_id)
    if group_text.startswith("-100"):
        group_text = group_text[4:]
    elif group_text.startswith("-"):
        group_text = group_text[1:]
    return f"https://t.me/c/{group_text}/{message_id}"


def _load_sent_video_log() -> list[dict[str, int]]:
    raw = _read_state_json_from_db(VIDEO_SENT_LOG_KEY)
    if raw is None:
        if not SENT_VIDEO_LOG_PATH.exists():
            raw = []
        else:
            try:
                raw = json.loads(SENT_VIDEO_LOG_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = []
        _write_state_json_to_db(VIDEO_SENT_LOG_KEY, raw)
    if not isinstance(raw, list):
        return []
    items: list[dict[str, int]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            chat_id = int(row.get("chat_id"))
            message_id = int(row.get("message_id"))
            sent_at = int(row.get("sent_at") or 0)
        except (TypeError, ValueError):
            continue
        if message_id <= 0:
            continue
        items.append({"chat_id": chat_id, "message_id": message_id, "sent_at": sent_at})
    return items


def _save_sent_video_log(items: list[dict[str, int]]) -> None:
    _write_state_json_to_db(VIDEO_SENT_LOG_KEY, items)
    try:
        SENT_VIDEO_LOG_PATH.write_text(
            json.dumps(items, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write sent video log")


def _add_sent_video_log(chat_id: int, message_id: int) -> None:
    items = _load_sent_video_log()
    items.append({
        "chat_id": int(chat_id),
        "message_id": int(message_id),
        "sent_at": int(time.time()),
    })
    _save_sent_video_log(items)


def _remove_sent_video_log_entry(chat_id: int, message_id: int) -> None:
    items = _load_sent_video_log()
    kept = [
        row for row in items
        if not (int(row.get("chat_id", 0)) == int(chat_id) and int(row.get("message_id", 0)) == int(message_id))
    ]
    if len(kept) != len(items):
        _save_sent_video_log(kept)


def _is_tracked_video_message(chat_id: int, message_id: int) -> bool:
    items = _load_sent_video_log()
    for row in items:
        if int(row.get("chat_id", 0)) == int(chat_id) and int(row.get("message_id", 0)) == int(message_id):
            return True
    return False


async def _delete_all_tracked_videos(context: ContextTypes.DEFAULT_TYPE) -> tuple[int, int, int]:
    items = _load_sent_video_log()
    total = len(items)
    if total == 0:
        return (0, 0, 0)

    deleted = 0
    failed = 0
    seen: set[tuple[int, int]] = set()
    for row in items:
        chat_id = int(row.get("chat_id", 0))
        message_id = int(row.get("message_id", 0))
        key = (chat_id, message_id)
        if key in seen:
            continue
        seen.add(key)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            deleted += 1
        except Exception:
            failed += 1
            logger.exception("Failed to delete tracked video chat_id=%s message_id=%s", chat_id, message_id)

    # Clear log after one bulk cleanup cycle.
    _save_sent_video_log([])
    return (total, deleted, failed)


def _load_int_list(path: Path) -> list[int]:
    key = VIDEO_KNOWN_USERS_KEY if path == KNOWN_USERS_PATH else ""
    raw: object | None = _read_state_json_from_db(key) if key else None
    if raw is None:
        if not path.exists():
            raw = []
        else:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = []
        if key:
            _write_state_json_to_db(key, raw)
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    for row in raw:
        try:
            out.append(int(row))
        except (TypeError, ValueError):
            continue
    return out


def _save_int_list(path: Path, items: list[int]) -> None:
    unique = sorted(set(int(x) for x in items))
    if path == KNOWN_USERS_PATH:
        _write_state_json_to_db(VIDEO_KNOWN_USERS_KEY, unique)
    try:
        path.write_text(json.dumps(unique, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    except OSError:
        logger.exception("Failed to write %s", path.name)


def _register_known_user_from_update(update: Update) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return
    if str(chat.type) != "private":
        return
    chat_id = int(chat.id)
    users = _load_int_list(KNOWN_USERS_PATH)
    if chat_id in users:
        return
    users.append(chat_id)
    _save_int_list(KNOWN_USERS_PATH, users)


def _load_saved_videos_map() -> dict[str, list[dict[str, int | str]]]:
    raw = _read_state_json_from_db(VIDEO_SAVED_VIDEOS_KEY)
    if raw is None:
        if not SAVED_VIDEOS_PATH.exists():
            raw = {}
        else:
            try:
                raw = json.loads(SAVED_VIDEOS_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
        _write_state_json_to_db(VIDEO_SAVED_VIDEOS_KEY, raw)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[dict[str, int | str]]] = {}
    for user_key, items in raw.items():
        if not isinstance(items, list):
            continue
        cleaned: list[dict[str, int | str]] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            try:
                chat_id = int(row.get("chat_id") or 0)
                message_id = int(row.get("message_id") or 0)
                topic_no = int(row.get("topic_no") or 0)
                saved_at = int(row.get("saved_at") or 0)
            except (TypeError, ValueError):
                continue
            level = str(row.get("level") or "").strip().lower()
            if chat_id == 0 or message_id <= 0:
                continue
            cleaned.append(
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "level": level,
                    "topic_no": topic_no,
                    "saved_at": saved_at,
                }
            )
        out[str(user_key)] = cleaned
    return out


def _save_saved_videos_map(data: dict[str, list[dict[str, int | str]]]) -> None:
    _write_state_json_to_db(VIDEO_SAVED_VIDEOS_KEY, data)
    try:
        SAVED_VIDEOS_PATH.write_text(
            json.dumps(data, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write saved videos")


def _get_saved_videos_for_user(user_id: int) -> list[dict[str, int | str]]:
    data = _load_saved_videos_map()
    rows = data.get(str(int(user_id)))
    if not isinstance(rows, list):
        return []
    return list(rows)


def _set_saved_videos_for_user(user_id: int, rows: list[dict[str, int | str]]) -> None:
    data = _load_saved_videos_map()
    data[str(int(user_id))] = list(rows)
    _save_saved_videos_map(data)


def _is_saved_video_for_user(user_id: int | None, chat_id: int, message_id: int) -> bool:
    if not isinstance(user_id, int):
        return False
    rows = _get_saved_videos_for_user(user_id)
    for row in rows:
        if int(row.get("chat_id") or 0) == int(chat_id) and int(row.get("message_id") or 0) == int(message_id):
            return True
    return False


def _load_scheduled_notifications() -> list[dict]:
    raw = _read_state_json_from_db(VIDEO_SCHEDULED_KEY)
    if raw is None:
        if not SCHEDULED_NOTIFICATIONS_PATH.exists():
            raw = []
        else:
            try:
                raw = json.loads(SCHEDULED_NOTIFICATIONS_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = []
        _write_state_json_to_db(VIDEO_SCHEDULED_KEY, raw)
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _save_scheduled_notifications(rows: list[dict]) -> None:
    _write_state_json_to_db(VIDEO_SCHEDULED_KEY, rows)
    try:
        SCHEDULED_NOTIFICATIONS_PATH.write_text(
            json.dumps(rows, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write scheduled notifications")


def _create_scheduled_notification(message: str, send_at_epoch: int, auto_delete: bool, created_by: int) -> dict:
    rows = _load_scheduled_notifications()
    next_id = 1
    if rows:
        next_id = max(int(r.get("id") or 0) for r in rows) + 1
    row = {
        "id": next_id,
        "message": str(message),
        "send_at": int(send_at_epoch),
        "auto_delete": bool(auto_delete),
        "created_by": int(created_by),
        "status": "pending",
        "created_at": int(time.time()),
    }
    rows.append(row)
    _save_scheduled_notifications(rows)
    return row


def _load_auto_delete_notices() -> dict[str, list[int]]:
    raw = _read_state_json_from_db(VIDEO_AUTO_DELETE_KEY)
    if raw is None:
        if not AUTO_DELETE_NOTICES_PATH.exists():
            raw = {}
        else:
            try:
                raw = json.loads(AUTO_DELETE_NOTICES_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
        _write_state_json_to_db(VIDEO_AUTO_DELETE_KEY, raw)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[int]] = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            continue
        cleaned: list[int] = []
        for item in v:
            try:
                cleaned.append(int(item))
            except (TypeError, ValueError):
                continue
        out[str(k)] = cleaned
    return out


def _save_auto_delete_notices(data: dict[str, list[int]]) -> None:
    normalized: dict[str, list[int]] = {}
    for k, v in data.items():
        normalized[str(k)] = sorted(set(int(x) for x in v))
    _write_state_json_to_db(VIDEO_AUTO_DELETE_KEY, normalized)
    try:
        AUTO_DELETE_NOTICES_PATH.write_text(
            json.dumps(normalized, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write auto-delete notices")


def _append_auto_delete_notice(chat_id: int, message_id: int) -> None:
    data = _load_auto_delete_notices()
    key = str(int(chat_id))
    lst = data.get(key, [])
    lst.append(int(message_id))
    data[key] = lst
    _save_auto_delete_notices(data)


def _pop_auto_delete_notices(chat_id: int) -> list[int]:
    data = _load_auto_delete_notices()
    key = str(int(chat_id))
    items = data.pop(key, [])
    _save_auto_delete_notices(data)
    return [int(x) for x in items]


async def _purge_auto_delete_notices_for_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    message_ids = _pop_auto_delete_notices(chat_id)
    for mid in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            # Ignore failures (message too old/deleted/etc).
            pass


async def scheduled_notification_worker(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = int(time.time())
    rows = _load_scheduled_notifications()
    if not rows:
        return

    users = _load_int_list(KNOWN_USERS_PATH)
    updated = False
    for row in rows:
        if str(row.get("status") or "") != "pending":
            continue
        send_at = int(row.get("send_at") or 0)
        if send_at <= 0 or send_at > now:
            continue

        message = str(row.get("message") or "").strip()
        auto_delete = bool(row.get("auto_delete"))
        sent_count = 0
        fail_count = 0

        for chat_id in users:
            try:
                sent = await context.bot.send_message(chat_id=chat_id, text=message)
                sent_count += 1
                if auto_delete:
                    _append_auto_delete_notice(chat_id, int(sent.message_id))
            except Exception:
                fail_count += 1

        row["status"] = "sent"
        row["sent_at"] = now
        row["sent_count"] = sent_count
        row["fail_count"] = fail_count
        updated = True

    if updated:
        _save_scheduled_notifications(rows)


async def happy_hour_worker(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = int(time.time())
    entries = _load_happy_hour_entries()
    if not entries:
        return

    runtime = _load_happy_hour_runtime()
    sessions = runtime.setdefault("sessions", {})
    changed = False

    # Delete any Happy Hour video past delete deadline.
    for session in sessions.values():
        if not isinstance(session, dict):
            continue
        users = session.get("users")
        if not isinstance(users, dict):
            continue
        for user_row in users.values():
            if not isinstance(user_row, dict):
                continue
            deliveries = user_row.get("deliveries")
            if not isinstance(deliveries, list):
                continue
            for item in deliveries:
                if not isinstance(item, dict):
                    continue
                if int(item.get("deleted") or 0) == 1:
                    continue
                delete_at = int(item.get("delete_at") or 0)
                if delete_at <= 0 or delete_at > now:
                    continue
                chat_id = int(item.get("chat_id") or 0)
                message_id = int(item.get("message_id") or 0)
                if chat_id == 0 or message_id <= 0:
                    item["deleted"] = 1
                    changed = True
                    continue
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except Exception:
                    pass
                _remove_sent_video_log_entry(chat_id, message_id)
                item["deleted"] = 1
                item["deleted_at"] = now
                changed = True

    if changed:
        _save_happy_hour_runtime(runtime)


def build_level_text(level_key: str, group_id: int | None) -> str:
    label = LEVEL_LABELS.get(level_key, level_key.title())
    level_topics = LEVEL_TOPICS.get(level_key, [])
    if level_topics:
        lines = [f"📂 {label} ({len(level_topics)} topik)\n"]
        for row in level_topics:
            topic_no = int(row.get("topic_no") or 0)
            topic_title = str(row.get("topic_title") or f"Topik {topic_no}")
            mid = int(row.get("message_id") or 0)
            status = "✅" if mid > 0 else "⚠️"
            lines.append(f"{status} Topik {topic_no}: {topic_title}")
        lines.append("\nPilih topik melalui miniapp untuk hantar video.")
        return "\n".join(lines)

    videos = VIDEO_CATALOG.get(level_key, [])
    if not videos:
        return f"📂 {label}\n\nBelum ada video lagi."
    if group_id is None:
        return (
            f"📂 {label}\n\n"
            "Group ID belum diset. Isi VIDEO_DB_GROUP_ID dalam .env dahulu."
        )
    lines = [f"📂 {label} ({len(videos)} video)\n"]
    for idx, row in enumerate(videos, start=1):
        title = str(row.get("title") or f"Video {idx}")
        message_id = int(row.get("message_id") or 0)
        if message_id <= 0:
            lines.append(f"{idx}. {title} (message_id belum set)")
            continue
        lines.append(f"{idx}. {title}\n   {_message_link(group_id, message_id)}")
    return "\n".join(lines)


def _find_level_topic(level: str, topic_no: int) -> dict | None:
    topics = LEVEL_TOPICS.get(level, [])
    for row in topics:
        if int(row.get("topic_no") or 0) == int(topic_no):
            return row
    return None


def _is_free_user(user_id: int | None) -> bool:
    if not isinstance(user_id, int):
        return False
    return not has_next_topic_access(user_id)


def _topic_key(level: str, topic_no: int) -> str:
    return f"{str(level).strip().lower()}:{int(topic_no)}"


def _topic_title(level: str, topic_no: int) -> str:
    row = _find_level_topic(level, topic_no)
    if isinstance(row, dict):
        title = str(row.get("topic_title") or "").strip()
        if title:
            return title
    return f"Topik {int(topic_no)}"


def _load_happy_hour_runtime() -> dict:
    raw = _read_state_json_from_db(VIDEO_HAPPY_HOUR_RUNTIME_KEY)
    if not isinstance(raw, dict):
        return {"sessions": {}}
    sessions = raw.get("sessions")
    if not isinstance(sessions, dict):
        return {"sessions": {}}
    return {"sessions": sessions}


def _save_happy_hour_runtime(data: dict) -> None:
    sessions = data.get("sessions")
    normalized = {"sessions": sessions if isinstance(sessions, dict) else {}}
    _write_state_json_to_db(VIDEO_HAPPY_HOUR_RUNTIME_KEY, normalized)


def _normalize_happy_hour_entry(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    entry_id = str(raw.get("id") or "").strip()
    if not entry_id:
        return None
    start_at = _parse_iso_datetime(str(raw.get("start_at_utc") or ""))
    end_at = _parse_iso_datetime(str(raw.get("end_at_utc") or ""))
    if start_at is None or end_at is None or end_at <= start_at:
        return None
    videos_raw = raw.get("videos")
    if not isinstance(videos_raw, list):
        return None

    videos: list[dict[str, object]] = []
    video_keys: set[str] = set()
    for row in videos_raw:
        if not isinstance(row, dict):
            continue
        level = str(row.get("level") or "").strip().lower()
        if level not in LEVEL_TOPICS:
            continue
        try:
            topic_no = int(row.get("topic_no") or 0)
        except (TypeError, ValueError):
            continue
        if topic_no < 1 or topic_no > len(LEVEL_TOPICS.get(level, [])):
            continue
        title = str(row.get("title") or "").strip() or _topic_title(level, topic_no)
        videos.append({"level": level, "topic_no": topic_no, "title": title})
        video_keys.add(_topic_key(level, topic_no))
    if not videos:
        return None

    notify_raw = raw.get("notify_user", True)
    if isinstance(notify_raw, bool):
        notify_user = notify_raw
    else:
        notify_user = str(notify_raw).strip().lower() in {"1", "true", "yes", "on"}

    return {
        "id": entry_id,
        "start_ts": int(start_at.timestamp()),
        "end_ts": int(end_at.timestamp()),
        "start_at": start_at,
        "end_at": end_at,
        "notify_user": bool(notify_user),
        "videos": videos,
        "video_keys": video_keys,
    }


def _load_happy_hour_entries() -> list[dict]:
    # Source of truth is sidebot saved schedules.
    data = _read_sidebot_state_json(VIDEO_HAPPY_HOUR_RULES_KEY)
    if not isinstance(data, dict):
        return []
    rows = data.get("entries")
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    for row in rows:
        entry = _normalize_happy_hour_entry(row)
        if entry is not None:
            out.append(entry)
    return out


def _find_active_happy_hour(level: str, topic_no: int, now_ts: int | None = None) -> dict | None:
    now = int(time.time()) if now_ts is None else int(now_ts)
    needle = _topic_key(level, topic_no)
    active: list[dict] = []
    for entry in _load_happy_hour_entries():
        if needle not in entry.get("video_keys", set()):
            continue
        start_ts = int(entry.get("start_ts") or 0)
        end_ts = int(entry.get("end_ts") or 0)
        if start_ts <= now < end_ts:
            active.append(entry)
    if not active:
        return None
    active.sort(key=lambda x: int(x.get("start_ts") or 0), reverse=True)
    return active[0]


def _get_happy_hour_pick_count(runtime: dict, session_id: str, user_id: int, level: str, topic_no: int) -> int:
    sessions = runtime.get("sessions")
    if not isinstance(sessions, dict):
        return 0
    session = sessions.get(str(session_id))
    if not isinstance(session, dict):
        return 0
    users = session.get("users")
    if not isinstance(users, dict):
        return 0
    user_row = users.get(str(int(user_id)))
    if not isinstance(user_row, dict):
        return 0
    counts = user_row.get("topic_counts")
    if not isinstance(counts, dict):
        return 0
    try:
        return int(counts.get(_topic_key(level, topic_no)) or 0)
    except (TypeError, ValueError):
        return 0


def _record_happy_hour_delivery(
    runtime: dict,
    session_id: str,
    user_id: int,
    level: str,
    topic_no: int,
    chat_id: int,
    message_id: int,
    delete_at: int,
) -> int:
    sessions = runtime.setdefault("sessions", {})
    session = sessions.setdefault(str(session_id), {})
    users = session.setdefault("users", {})
    user_row = users.setdefault(str(int(user_id)), {})
    counts = user_row.setdefault("topic_counts", {})
    topic_key = _topic_key(level, topic_no)
    try:
        next_count = int(counts.get(topic_key) or 0) + 1
    except (TypeError, ValueError):
        next_count = 1
    counts[topic_key] = int(next_count)
    deliveries = user_row.setdefault("deliveries", [])
    deliveries.append(
        {
            "chat_id": int(chat_id),
            "message_id": int(message_id),
            "delete_at": int(delete_at),
            "deleted": 0,
        }
    )
    return int(next_count)


def _build_happy_hour_user_message(entry: dict) -> str:
    tz = get_bot_timezone()
    start_at = entry.get("start_at")
    end_at = entry.get("end_at")
    if not isinstance(start_at, datetime):
        start_text = "-"
    else:
        start_text = start_at.astimezone(tz).strftime("%Y-%m-%d %H:%M %Z")
    if not isinstance(end_at, datetime):
        end_text = "-"
    else:
        end_text = end_at.astimezone(tz).strftime("%Y-%m-%d %H:%M %Z")

    lines = []
    for row in entry.get("videos", []):
        if not isinstance(row, dict):
            continue
        level = str(row.get("level") or "").strip().lower()
        topic_no = int(row.get("topic_no") or 0)
        if level not in LEVEL_TOPICS or topic_no <= 0:
            continue
        title = str(row.get("title") or "").strip() or _topic_title(level, topic_no)
        lines.append(f"{LEVEL_LABELS.get(level, level.title())}\nTopik {topic_no}\n{title}")
    selected_text = "\n\n".join(lines) if lines else "-"

    return (
        "Happy Hour akan diaktifkan pada\n\n"
        f"{start_text}\n\n"
        "Anda kini boleh menonton video/topik dibawah secara percuma dalam tempoh Happy Hour yang ditetapkan.\n\n"
        f"{selected_text}\n\n"
        "Video akan automatik terpadam dalam tempoh 30 minit selepas anda pilih atau selepas tamat tempoh Happy Hour.\n\n"
        "Setiap video Happy Hour hanya boleh dipilih maksima 2 kali sahaja dalam tempoh Happy Hour berlangsung.\n\n"
        f"Waktu tamat Happy Hour: {end_text}"
    )


def save_later_keyboard(message_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="⏸️ Sambung nanti", callback_data=f"save_later|{int(message_id)}")]]
    )


async def _save_video_for_user_with_quota(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    chat_id: int,
    message_id: int,
    level: str,
    topic_no: int,
) -> tuple[int, int, bool]:
    rows = _get_saved_videos_for_user(user_id)
    before = len(rows)

    for row in rows:
        if int(row.get("chat_id") or 0) == int(chat_id) and int(row.get("message_id") or 0) == int(message_id):
            return (before, before, False)

    rows.append(
        {
            "chat_id": int(chat_id),
            "message_id": int(message_id),
            "level": str(level),
            "topic_no": int(topic_no),
            "saved_at": int(time.time()),
        }
    )

    replaced = False
    while len(rows) > SAVE_LATER_MAX:
        old = rows.pop(0)
        old_chat_id = int(old.get("chat_id") or 0)
        old_message_id = int(old.get("message_id") or 0)
        if old_chat_id and old_message_id > 0:
            try:
                await context.bot.delete_message(chat_id=old_chat_id, message_id=old_message_id)
            except Exception:
                logger.exception(
                    "Failed to delete old saved video chat_id=%s message_id=%s",
                    old_chat_id,
                    old_message_id,
                )
            _remove_sent_video_log_entry(old_chat_id, old_message_id)
        replaced = True

    _set_saved_videos_for_user(user_id, rows)
    return (before, len(rows), replaced)


async def _send_topic_video(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    level: str,
    topic_no: int,
    user_id: int | None = None,
) -> None:
    topic = _find_level_topic(level, topic_no)
    if not topic:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Topik tak dijumpai.",
            reply_markup=topic_navigation_keyboard(user_id),
        )
        return

    topic_is_next_only = bool(topic.get("next_only"))
    has_next_access = has_next_topic_access(user_id)
    happy_hour_entry: dict | None = None
    if topic_is_next_only and not has_next_access and _is_free_user(user_id):
        happy_hour_entry = _find_active_happy_hour(level, topic_no)

    if topic_is_next_only and not has_next_access and happy_hour_entry is None:
        context.user_data["last_topic_level"] = level
        context.user_data["last_topic_no"] = topic_no
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🔒 Topik ini khas untuk NEXT access.\n"
                "Sila daftar NEXT untuk unlock kandungan NEXTexclusive."
            ),
            reply_markup=vip_locked_keyboard(),
        )
        return

    if happy_hour_entry is not None and isinstance(user_id, int):
        runtime = _load_happy_hour_runtime()
        current_count = _get_happy_hour_pick_count(runtime, str(happy_hour_entry.get("id") or ""), user_id, level, topic_no)
        if current_count >= HAPPY_HOUR_FREE_PICK_LIMIT:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⚠️ Kuota Happy Hour untuk topik ini telah habis.\n"
                    f"Maksimum pilihan: {HAPPY_HOUR_FREE_PICK_LIMIT} kali bagi setiap topik dalam sesi ini."
                ),
                reply_markup=topic_navigation_keyboard(user_id),
            )
            return

    group_id = get_video_db_group_id()
    if group_id is None:
        await context.bot.send_message(
            chat_id=chat_id,
            text="VIDEO_DB_GROUP_ID belum diset dalam .env.",
            reply_markup=topic_navigation_keyboard(user_id),
        )
        return

    message_id = int(topic.get("message_id") or 0)
    topic_title = str(topic.get("topic_title") or f"Topik {topic_no}")
    if message_id <= 0:
        context.user_data["last_topic_level"] = level
        context.user_data["last_topic_no"] = topic_no
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Video ini belum tersedia, akan dikemaskini kemudian.",
            reply_markup=topic_navigation_keyboard(user_id),
        )
        return

    try:
        protect_content = not is_super_user_id(user_id)
        sent_video = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=group_id,
            message_id=message_id,
            protect_content=protect_content,
        )
    except Exception:
        logger.exception("Failed to copy topic video level=%s topic=%s", level, topic_no)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Gagal tarik video Topik {topic_no}. Semak message_id/group id.",
            reply_markup=topic_navigation_keyboard(user_id),
        )
        return

    # Keep video until user chooses another topic.
    # Old video is removed only after a new one is sent successfully.
    old_video_message_id = int(context.user_data.get("last_video_message_id") or 0)
    old_video_chat_id = int(context.user_data.get("last_video_chat_id") or 0)
    if (
        old_video_message_id > 0
        and old_video_chat_id == chat_id
        and old_video_message_id != int(sent_video.message_id)
        and not _is_saved_video_for_user(user_id, old_video_chat_id, old_video_message_id)
    ):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_video_message_id)
            _remove_sent_video_log_entry(old_video_chat_id, old_video_message_id)
        except Exception:
            logger.exception("Failed to delete previous topic video message_id=%s", old_video_message_id)

    context.user_data["last_video_message_id"] = int(sent_video.message_id)
    context.user_data["last_video_chat_id"] = int(chat_id)
    context.user_data["last_topic_level"] = level
    context.user_data["last_topic_no"] = topic_no
    _add_sent_video_log(chat_id, int(sent_video.message_id))
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Topik {topic_no}: {topic_title}",
        reply_markup=topic_navigation_keyboard(user_id),
    )

    if happy_hour_entry is not None and isinstance(user_id, int):
        now_ts = int(time.time())
        end_ts = int(happy_hour_entry.get("end_ts") or now_ts)
        delete_at = min(now_ts + HAPPY_HOUR_DELETE_AFTER_SECONDS, end_ts)
        runtime = _load_happy_hour_runtime()
        after_count = _record_happy_hour_delivery(
            runtime=runtime,
            session_id=str(happy_hour_entry.get("id") or ""),
            user_id=user_id,
            level=level,
            topic_no=topic_no,
            chat_id=chat_id,
            message_id=int(sent_video.message_id),
            delete_at=delete_at,
        )
        _save_happy_hour_runtime(runtime)
        if bool(happy_hour_entry.get("notify_user", True)):
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{_build_happy_hour_user_message(happy_hour_entry)}\n\n"
                    f"Penggunaan topik ini untuk sesi semasa: {after_count}/{HAPPY_HOUR_FREE_PICK_LIMIT}"
                ),
                reply_markup=topic_navigation_keyboard(user_id),
            )

    if has_save_later_access(user_id):
        await context.bot.send_message(
            chat_id=chat_id,
            text="Jika nak sambung kemudian, tekan butang di bawah.",
            reply_markup=save_later_keyboard(int(sent_video.message_id)),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    _register_known_user_from_update(update)
    await _purge_auto_delete_notices_for_chat(context, message.chat_id)
    user_id = update.effective_user.id if update.effective_user else None
    await message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
    )


async def groupid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return
    _register_known_user_from_update(update)
    await _purge_auto_delete_notices_for_chat(context, message.chat_id)
    await message.reply_text(
        f"chat_id: `{chat.id}`\nchat_type: `{chat.type}`",
        parse_mode="Markdown",
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return
    _register_known_user_from_update(update)
    await _purge_auto_delete_notices_for_chat(context, message.chat_id)
    user_id = update.effective_user.id if update.effective_user else None
    text = message.text.strip()
    lowered = text.lower()

    if lowered in {"groupid", "/groupid"}:
        await groupid(update, context)
        return

    if text == MENU_TOPIC_MAIN:
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return
    if text == MENU_TOPIC_PICK:
        if not bool(context.user_data.get("topic_session_active")):
            await message.reply_text(
                "Sila buka miniapp eVideo dulu dan pilih topik.",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
            )
            return
        await message.reply_text(EVIDEO_MENU_TEXT, reply_markup=level_menu_keyboard())
        return
    if text in {MENU_TOPIC_PREV, MENU_TOPIC_NEXT}:
        if not bool(context.user_data.get("topic_session_active")):
            await message.reply_text(
                "Sila pilih topik melalui miniapp terlebih dahulu.",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
            )
            return
        level = str(context.user_data.get("last_topic_level") or "basic")
        current_topic = int(context.user_data.get("last_topic_no") or 0)
        if current_topic <= 0:
            await message.reply_text(
                "Belum ada topik dipilih. Pilih topik dulu dari miniapp.",
                reply_markup=topic_navigation_keyboard(user_id),
            )
            return
        next_topic = current_topic - 1 if text == MENU_TOPIC_PREV else current_topic + 1
        level_topics = LEVEL_TOPICS.get(level, [])
        if next_topic < 1 or next_topic > len(level_topics):
            await message.reply_text(
                "Tiada topik lagi untuk arah ini.",
                reply_markup=topic_navigation_keyboard(user_id),
            )
            return
        await _send_topic_video(context, message.chat_id, level, next_topic, user_id=user_id)
        return

    if text == MENU_EVIDEO:
        await message.reply_text(EVIDEO_MENU_TEXT, reply_markup=level_menu_keyboard())
        return
    if text == MENU_INTRADAY:
        await message.reply_text(
            COMING_SOON_INTRADAY,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return
    if text == MENU_FIBO:
        await message.reply_text(
            COMING_SOON_FIBO,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return
    if text == MENU_MMHELPER:
        mmhelper_url = get_mmhelper_bot_url()
        if not mmhelper_url:
            await message.reply_text(
                "Link MM Helper belum diset (VIDEO_MMHELPER_BOT_URL).",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
            )
            return
        await message.reply_text(
            "Tekan butang di bawah untuk buka MM Helper.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Buka MM Helper", url=mmhelper_url)]]
            ),
        )
        return
    if text == MENU_ADMIN:
        daftar_url = get_daftar_next_webapp_url()
        if not daftar_url:
            await message.reply_text(
                "Daftar NEXT miniapp URL belum diset.",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
            )
            return
        await message.reply_text(
            "Sila buka miniapp Daftar NEXT untuk teruskan pendaftaran.",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return
    if text == MENU_ADMIN_PANEL:
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return
        context.user_data["pending_admin_delete_all"] = False
        await message.reply_text("🔒 Admin Panel", reply_markup=admin_panel_keyboard())
        return
    if text == MENU_ADMIN_PUSH:
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return
        push_url = get_push_webapp_url()
        if not push_url:
            await message.reply_text(
                "Push miniapp URL belum diset. Isi VIDEO_PUSH_WEBAPP_URL atau pastikan VIDEO_EVIDEO_WEBAPP_URL sah.",
                reply_markup=admin_panel_keyboard(),
            )
            return
        await message.reply_text(
            "📣 Buka miniapp Push Notification dan submit jadual.",
            reply_markup=admin_panel_keyboard(),
        )
        return
    if text == MENU_ADMIN_VIDEO_STATUS:
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return
        status_url = get_video_status_webapp_url()
        if not status_url:
            await message.reply_text(
                "Video Status miniapp URL belum diset. Isi VIDEO_STATUS_WEBAPP_URL atau pastikan VIDEO_EVIDEO_WEBAPP_URL sah.",
                reply_markup=admin_panel_keyboard(),
            )
            return
        await message.reply_text(
            "🧷 Buka miniapp Video Status dan submit perubahan.",
            reply_markup=admin_panel_keyboard(),
        )
        return
    if text == MENU_ADMIN_DELETE:
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return
        context.user_data["pending_admin_delete_all"] = True
        await message.reply_text(
            "⚠️ Anda pasti nak delete semua video yang pernah bot hantar?\n\nTindakan ini cuba padam semua rekod tracked video.",
            reply_markup=admin_delete_confirm_keyboard(),
        )
        return
    if text == MENU_ADMIN_DELETE_CONFIRM:
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return
        if not bool(context.user_data.get("pending_admin_delete_all")):
            await message.reply_text(
                "Tiada proses delete aktif.",
                reply_markup=admin_panel_keyboard(),
            )
            return
        context.user_data["pending_admin_delete_all"] = False
        total, deleted, failed = await _delete_all_tracked_videos(context)
        await message.reply_text(
            f"🗑️ Selesai delete video.\nTotal tracked: {total}\nDeleted: {deleted}\nGagal: {failed}",
            reply_markup=admin_panel_keyboard(),
        )
        return
    if text == MENU_ADMIN_DELETE_CANCEL:
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return
        context.user_data["pending_admin_delete_all"] = False
        await message.reply_text(
            "Delete dibatalkan.",
            reply_markup=admin_panel_keyboard(),
            parse_mode="HTML",
        )
        return
    if text == MENU_BACK_MAIN:
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return
    if text == MENU_ADMIN_BACK:
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return

    level_map = {
        MENU_LEVEL_BASIC: "basic",
        MENU_LEVEL_INTERMEDIATE: "intermediate",
        MENU_LEVEL_ADVANCED: "advanced",
    }
    if text in level_map:
        group_id = get_video_db_group_id()
        level_text = build_level_text(level_map[text], group_id)
        await message.reply_text(
            level_text,
            reply_markup=level_menu_keyboard(),
            disable_web_page_preview=True,
        )
        return

    await message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
    )


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return
    _register_known_user_from_update(update)
    await _purge_auto_delete_notices_for_chat(context, message.chat_id)
    user_id = update.effective_user.id if update.effective_user else None
    raw = str(message.web_app_data.data or "").strip()
    if not raw:
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.reply_text(
            "Data miniapp tak sah.",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return

    if not isinstance(payload, dict):
        await message.reply_text(
            "Data miniapp tak sah.",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return

    payload_type = str(payload.get("type") or "").strip().lower()
    if payload_type == "video_bot_back_to_main_menu":
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
        )
        return

    if payload_type == "video_topic_pick":
        level = str(payload.get("level") or "").strip().lower()
        topic = str(payload.get("topic") or "").strip()
        title = str(payload.get("title") or "").strip()
        try:
            topic_no = int(topic)
        except ValueError:
            topic_no = 0
        if not level or topic_no <= 0:
            await message.reply_text(
                "Pilihan topik tak sah.",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
            )
            return
        context.user_data["topic_session_active"] = True
        await _send_topic_video(context, message.chat_id, level, topic_no, user_id=user_id)
        return

    if payload_type == "push_notification_schedule":
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return

        body = str(payload.get("message") or "").strip()
        date_value = str(payload.get("date") or "").strip()
        time_value = str(payload.get("time") or "").strip()
        auto_delete = bool(payload.get("auto_delete"))

        if not body:
            await message.reply_text(
                "Mesej kosong. Isi mesej dahulu.",
                reply_markup=admin_panel_keyboard(),
            )
            return
        if len(body) > 3500:
            await message.reply_text(
                "Mesej terlalu panjang (max 3500 aksara).",
                reply_markup=admin_panel_keyboard(),
            )
            return

        try:
            send_at_epoch = parse_local_schedule_to_epoch(date_value, time_value)
        except ValueError:
            await message.reply_text(
                "Format tarikh/masa tak sah.",
                reply_markup=admin_panel_keyboard(),
            )
            return

        now = int(time.time())
        if send_at_epoch < now - 60:
            await message.reply_text(
                "Tarikh/masa telah lepas. Sila pilih masa akan datang.",
                reply_markup=admin_panel_keyboard(),
            )
            return

        created_by = int(update.effective_user.id) if update.effective_user else 0
        row = _create_scheduled_notification(
            message=body,
            send_at_epoch=send_at_epoch,
            auto_delete=auto_delete,
            created_by=created_by,
        )
        tz = get_bot_timezone()
        human_time = datetime.fromtimestamp(send_at_epoch, tz).strftime("%Y-%m-%d %H:%M %Z")
        auto_text = "ON" if auto_delete else "OFF"
        await message.reply_text(
            f"✅ Push notification dijadualkan.\nID: {row['id']}\nMasa: {human_time}\nAuto delete: {auto_text}",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if payload_type == "video_status_update":
        if not is_admin_user(update):
            await message.reply_text(
                "Akses ditolak.",
                reply_markup=main_menu_keyboard(show_admin_panel=False),
            )
            return

        level = str(payload.get("level") or "").strip().lower()
        status = str(payload.get("status") or "").strip().lower()
        available_on = str(payload.get("available_on") or "").strip()
        topic_raw = str(payload.get("topic_no") or "").strip()

        try:
            topic_no = int(topic_raw)
        except ValueError:
            topic_no = 0

        if level not in LEVEL_TOPICS:
            await message.reply_text("Level tak sah.", reply_markup=admin_panel_keyboard())
            return
        if topic_no < 1 or topic_no > len(LEVEL_TOPICS.get(level, [])):
            await message.reply_text("Topik tak sah.", reply_markup=admin_panel_keyboard())
            return
        if status not in {"coming_soon", "available_on", "online"}:
            await message.reply_text("Status tak sah.", reply_markup=admin_panel_keyboard())
            return
        if status == "available_on":
            try:
                datetime.strptime(available_on, "%Y-%m-%d")
            except ValueError:
                await message.reply_text(
                    "Tarikh available_on tak sah (format: YYYY-MM-DD).",
                    reply_markup=admin_panel_keyboard(),
                )
                return
        else:
            available_on = ""

        _upsert_video_status(level=level, topic_no=topic_no, status=status, available_on=available_on)
        status_text = status.replace("_", " ")
        if status == "online":
            status_text = "online 🟢"
        if status == "available_on":
            status_text = f"available on: {available_on}"
        status_message = (
            f"✅ Status dikemaskini.\n"
            f"Level: {level.title()}\n"
            f"Topik: {topic_no}\n"
            f"Status: {status_text}"
        )

        sent_count = 0
        fail_count = 0
        known_users = _load_int_list(KNOWN_USERS_PATH)
        source_chat_id = int(message.chat_id) if message.chat_id is not None else 0
        for chat_id in known_users:
            if source_chat_id > 0 and int(chat_id) == source_chat_id:
                continue
            try:
                await context.bot.send_message(chat_id=int(chat_id), text=status_message)
                sent_count += 1
            except Exception:
                fail_count += 1

        await message.reply_text(
            f"{status_message}\n\nBroadcast user: {sent_count} berjaya, {fail_count} gagal.",
            reply_markup=admin_panel_keyboard(),
        )
        return

    await message.reply_text(
        "Action miniapp diterima.",
        reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update), user_id=user_id),
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat
    if not query or not user or not chat:
        return

    data = str(query.data or "")
    if not data.startswith("save_later|"):
        return

    parts = data.split("|", 1)
    if len(parts) != 2:
        await query.answer("Data tak sah.", show_alert=True)
        return

    try:
        message_id = int(parts[1])
    except ValueError:
        await query.answer("Message ID tak sah.", show_alert=True)
        return

    user_id = int(user.id)
    chat_id = int(chat.id)
    if not has_save_later_access(user_id):
        await query.answer("Fungsi ini hanya untuk VIP2/VIP3.", show_alert=True)
        return

    if not _is_tracked_video_message(chat_id, message_id):
        await query.answer("Video ini tak lagi available untuk simpan.", show_alert=True)
        return

    if _is_saved_video_for_user(user_id, chat_id, message_id):
        current = len(_get_saved_videos_for_user(user_id))
        await query.answer("Video ini dah disimpan.", show_alert=False)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ Video ini sudah dalam simpanan sambung nanti.\n"
                f"Kuota simpanan: {current}/{SAVE_LATER_MAX}\n"
                f"Maksimum simpanan: {SAVE_LATER_MAX}"
            ),
        )
        return

    level = str(context.user_data.get("last_topic_level") or "")
    topic_no = int(context.user_data.get("last_topic_no") or 0)
    _, after, replaced = await _save_video_for_user_with_quota(
        context=context,
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        level=level,
        topic_no=topic_no,
    )

    await query.answer("Disimpan untuk sambung nanti.", show_alert=False)
    if replaced:
        extra = "Kuota penuh, simpanan paling lama telah diganti."
    else:
        extra = "Video disimpan untuk sambung nanti."
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ {extra}\n"
            f"Kuota simpanan: {after}/{SAVE_LATER_MAX}\n"
            f"Maksimum simpanan: {SAVE_LATER_MAX}"
        ),
    )


def main() -> None:
    token = get_token()
    try:
        init_video_storage()
    except sqlite3.Error:
        logger.warning("Video state storage init failed, continuing with file fallback", exc_info=True)
    app = ApplicationBuilder().token(token).build()
    if app.job_queue is not None:
        app.job_queue.run_repeating(scheduled_notification_worker, interval=10, first=5)
        app.job_queue.run_repeating(happy_hour_worker, interval=15, first=8)
    else:
        logger.warning("Job queue unavailable; scheduled workers disabled.")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("groupid", groupid))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_callback_query, pattern=r"^save_later\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Video bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
