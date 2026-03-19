"""Simple NEXT event bot with reply-keyboard main menu."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MENU_BOOTCAMP = "Bootcamp"
MENU_SEMINAR = "Seminar"
MENU_WEBINAR = "Webinar"
MENU_TRADE_TALK = "Trade Talk"
MENU_WEBINAR_FULLFLOW = "Webinar FULLFLOW (April)"
MENU_SERIES_1 = "SIRI 1 (7 & 8 April 2026)"
MENU_SERIES_2 = "SIRI 2 (22 & 23 April 2026)"
MENU_SERIES_3 = "SIRI 3 (14 & 15 May 2026)"
MENU_ZOOM_LINK = "ZOOM Link"
MENU_PDF_EBOOK = "PDF/eBook bahan rujukan belajar"
MENU_RECORDINGS = "Video rakaman"
MENU_EXTRA_VIDEOS = "Video bantuan tambahan"
MENU_BACK = "⬅️ Back"
MENU_HOME = "🏠 Home"
MENU_ADMIN_PANEL = "⚠️ Admin Panel ⚠️"
MENU_UPDATE_ZOOM = "Update link zoom"
MENU_NOTIFICATION_SENDER = "Notification sender"

BOOTCAMP_PLACEHOLDER = "Tiada Bootcamp aktif buat masa ini"
SEMINAR_PLACEHOLDER = "Tiada Seminar aktif buat masa ini"
TRADE_TALK_PLACEHOLDER = "Tiada Trade Talk aktif buat masa ini"
SERIES_PLACEHOLDER = "Maklumat siri ini akan diumumkan kemudian."
CONTENT_PLACEHOLDER = "Kandungan masih belum dikemaskini , kami akan menghantar notifikasi apabila kandungan sudah tersedia"
ZOOM_PLACEHOLDER = "Link hanya akan tersedia 30 - 120 minit sebelum sesi bermula"
FULL_ACCESS_REQUIRED_TEXT = "Akses untuk kandungan ini hanya diberikan kepada peserta webinar yang layak bagi siri ini."
RECORDING_ONLY_TEXT = "Akaun anda untuk siri ini hanya mempunyai akses rakaman. ZOOM Link, PDF/eBook dan video bantuan tambahan tidak tersedia."

LEVEL_MAIN = "main"
LEVEL_WEBINAR = "webinar"
LEVEL_WEBINAR_FULLFLOW = "webinar_fullflow"
LEVEL_SERIES_DETAIL = "series_detail"
LEVEL_SERIES_CONTENT = "series_content"
LEVEL_RECORDINGS = "recordings"
LEVEL_ADMIN = "admin"

SERIES_SESSION_LABELS = {
    MENU_SERIES_1: ("Sesi 1 (7 April 2026)", "Sesi 2 (8 April 2026)"),
    MENU_SERIES_2: ("Sesi 1 (22 April 2026)", "Sesi 2 (23 April 2026)"),
    MENU_SERIES_3: ("Sesi 1 (14 May 2026)", "Sesi 2 (15 May 2026)"),
}
SERIES_NUMBER_BY_LABEL = {
    MENU_SERIES_1: "1",
    MENU_SERIES_2: "2",
    MENU_SERIES_3: "3",
}
DEFAULT_SHARED_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "mmhelper_shared.db"
NEXT_EVENT_ZOOM_STATE_KEY = "next_event_zoom_state"


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
    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set BOT_TOKEN in NEXT_Event_BOT/.env")
    return token


def get_superuser_id() -> int | None:
    raw = (os.getenv("SUPERUSER_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid SUPERUSER_ID: %s", raw)
        return None


def get_shared_db_path() -> Path:
    raw = (os.getenv("SIDEBOT_SHARED_DB_PATH") or os.getenv("MMHELPER_SHARED_DB_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_SHARED_DB_PATH


def get_current_webinar_campaign() -> str:
    raw = str(os.getenv("SIDEBOT_WEBINAR_CAMPAIGN") or "webinar_april").strip().lower()
    return raw or "webinar_april"


def _connect_shared_db() -> sqlite3.Connection:
    conn = sqlite3.connect(get_shared_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_kv_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sidebot_kv_state (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        )
        """
    )


def _read_kv_json(conn: sqlite3.Connection, key: str, default: dict) -> dict:
    _ensure_kv_table(conn)
    row = conn.execute("SELECT value_json FROM sidebot_kv_state WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    raw = str(row["value_json"] or "").strip()
    if not raw:
        return default
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return default
    return data if isinstance(data, dict) else default


def _write_kv_json(conn: sqlite3.Connection, key: str, value: dict) -> None:
    _ensure_kv_table(conn)
    conn.execute(
        "INSERT OR REPLACE INTO sidebot_kv_state (key, value_json) VALUES (?, ?)",
        (key, json.dumps(value, ensure_ascii=False)),
    )


def _read_vip_whitelist() -> dict:
    out: dict = {"vip1": {"users": {}}, "vip2": {"users": {}}, "vip3": {"users": {}}}
    try:
        with _connect_shared_db() as conn:
            rows = conn.execute(
                """
                SELECT tier, user_id, status
                FROM vip_whitelist
                """
            ).fetchall()
    except sqlite3.Error:
        logger.warning("Failed to read vip whitelist for NEXT event bot", exc_info=True)
        return out
    for row in rows:
        tier = str(row["tier"] or "").strip().lower()
        user_id = str(row["user_id"] or "").strip()
        status = str(row["status"] or "active").strip().lower()
        if tier not in {"vip1", "vip2", "vip3"} or not user_id or status != "active":
            continue
        out.setdefault(tier, {"users": {}}).setdefault("users", {})[user_id] = {
            "user_id": user_id,
            "status": status,
        }
    return out


def _read_webinar_access_state() -> dict:
    default = {"campaigns": {}}
    try:
        with _connect_shared_db() as conn:
            data = _read_kv_json(conn, "webinar_access_state", default)
    except sqlite3.Error:
        logger.warning("Failed to read webinar access state for NEXT event bot", exc_info=True)
        return default
    return data if isinstance(data, dict) else default


def _read_zoom_state() -> dict:
    default = {"campaigns": {}}
    try:
        with _connect_shared_db() as conn:
            return _read_kv_json(conn, NEXT_EVENT_ZOOM_STATE_KEY, default)
    except sqlite3.Error:
        logger.warning("Failed to read zoom state for NEXT event bot", exc_info=True)
        return default


def _write_zoom_state(data: dict) -> None:
    with _connect_shared_db() as conn:
        _write_kv_json(conn, NEXT_EVENT_ZOOM_STATE_KEY, data)


def get_zoom_update_webapp_url() -> str:
    base = (os.getenv("NEXT_EVENT_ADMIN_WEBAPP_URL") or os.getenv("NEXT_EVENT_WEBAPP_URL") or "").strip()
    if not base.lower().startswith("https://"):
        return ""
    if base.endswith("/"):
        built = f"{base}zoom-update.html"
    elif base.endswith(".html"):
        built = f"{base.rsplit('/', 1)[0]}/zoom-update.html"
    else:
        built = f"{base}/zoom-update.html"
    sep = "&" if "?" in built else "?"
    payload = _zoom_entries_payload()
    return f"{built}{sep}{urlencode({'campaign': get_current_webinar_campaign(), 'zoom_entries_payload': payload})}"


def get_zoom_entry(campaign: str, series_number: str, session_number: str) -> dict | None:
    data = _read_zoom_state()
    campaigns = data.get("campaigns")
    if not isinstance(campaigns, dict):
        return None
    campaign_row = campaigns.get(str(campaign))
    if not isinstance(campaign_row, dict):
        return None
    series = campaign_row.get("series")
    if not isinstance(series, dict):
        return None
    series_row = series.get(str(series_number))
    if not isinstance(series_row, dict):
        return None
    sessions = series_row.get("sessions")
    if not isinstance(sessions, dict):
        return None
    session_row = sessions.get(str(session_number))
    return session_row if isinstance(session_row, dict) else None


def _zoom_entries_payload() -> str:
    out: dict[str, object] = {"campaign": get_current_webinar_campaign(), "entries": []}
    data = _read_zoom_state()
    campaigns = data.get("campaigns")
    if not isinstance(campaigns, dict):
        return json.dumps(out, ensure_ascii=False)
    campaign_row = campaigns.get(get_current_webinar_campaign())
    if not isinstance(campaign_row, dict):
        return json.dumps(out, ensure_ascii=False)
    series = campaign_row.get("series")
    if not isinstance(series, dict):
        return json.dumps(out, ensure_ascii=False)
    entries: list[dict[str, str]] = []
    for series_number, series_row in series.items():
        if not isinstance(series_row, dict):
            continue
        sessions = series_row.get("sessions")
        if not isinstance(sessions, dict):
            continue
        for session_number, session_row in sessions.items():
            if not isinstance(session_row, dict):
                continue
            entries.append(
                {
                    "series": str(series_number),
                    "session": str(session_number),
                    "start_at": str(session_row.get("start_at") or ""),
                    "link": str(session_row.get("link") or ""),
                    "message": str(session_row.get("message") or ""),
                    "status": str(session_row.get("status") or "active"),
                }
            )
    entries.sort(key=lambda row: (row.get("series", ""), row.get("session", "")))
    out["entries"] = entries
    return json.dumps(out, ensure_ascii=False)


def get_series_access_level(user_id: int, series_number: str) -> str:
    if user_id and user_id == get_superuser_id():
        return "full"
    user_key = str(user_id)
    whitelist = _read_vip_whitelist()
    vip2_users = whitelist.get("vip2", {}).get("users", {})
    vip3_users = whitelist.get("vip3", {}).get("users", {})
    if isinstance(vip2_users, dict) and user_key in vip2_users:
        return "full"
    if isinstance(vip3_users, dict) and user_key in vip3_users:
        return "full" if str(series_number) == "1" else "recording_only"

    data = _read_webinar_access_state()
    campaigns = data.get("campaigns")
    if not isinstance(campaigns, dict):
        return "none"
    campaign = campaigns.get(get_current_webinar_campaign())
    if not isinstance(campaign, dict):
        return "none"
    series = campaign.get("series")
    if not isinstance(series, dict):
        return "none"
    series_row = series.get(str(series_number))
    if not isinstance(series_row, dict):
        return "none"
    users = series_row.get("users")
    if isinstance(users, dict) and user_key in users:
        return "full"
    return "none"


def selected_series_number_from_context(context: ContextTypes.DEFAULT_TYPE) -> str:
    selected_series_label = str(context.user_data.get("selected_series_label") or "")
    return SERIES_NUMBER_BY_LABEL.get(selected_series_label, "")


def get_full_access_user_ids_for_series(campaign: str, series_number: str) -> set[int]:
    out: set[int] = set()
    superuser_id = get_superuser_id()
    if isinstance(superuser_id, int):
        out.add(superuser_id)

    whitelist = _read_vip_whitelist()
    vip2_users = whitelist.get("vip2", {}).get("users", {})
    vip3_users = whitelist.get("vip3", {}).get("users", {})
    if isinstance(vip2_users, dict):
        for user_id in vip2_users:
            if str(user_id).isdigit():
                out.add(int(user_id))
    if str(series_number) == "1" and isinstance(vip3_users, dict):
        for user_id in vip3_users:
            if str(user_id).isdigit():
                out.add(int(user_id))

    access_state = _read_webinar_access_state()
    campaigns = access_state.get("campaigns")
    if not isinstance(campaigns, dict):
        return out
    campaign_row = campaigns.get(str(campaign))
    if not isinstance(campaign_row, dict):
        return out
    series = campaign_row.get("series")
    if not isinstance(series, dict):
        return out
    series_row = series.get(str(series_number))
    if not isinstance(series_row, dict):
        return out
    users = series_row.get("users")
    if isinstance(users, dict):
        for user_id in users:
            if str(user_id).isdigit():
                out.add(int(user_id))
    return out


def build_main_menu(user_id: int | None = None) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(MENU_BOOTCAMP)],
        [KeyboardButton(MENU_SEMINAR)],
        [KeyboardButton(MENU_WEBINAR)],
        [KeyboardButton(MENU_TRADE_TALK)],
    ]
    if user_id is not None and user_id == get_superuser_id():
        keyboard.append([KeyboardButton(MENU_ADMIN_PANEL)])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


def build_webinar_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(MENU_WEBINAR_FULLFLOW)],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_webinar_series_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(MENU_SERIES_1)],
            [KeyboardButton(MENU_SERIES_2)],
            [KeyboardButton(MENU_SERIES_3)],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_series_content_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(MENU_ZOOM_LINK)],
            [KeyboardButton(MENU_PDF_EBOOK)],
            [KeyboardButton(MENU_RECORDINGS)],
            [KeyboardButton(MENU_EXTRA_VIDEOS)],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_recordings_menu(session_1_label: str, session_2_label: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(session_1_label)],
            [KeyboardButton(session_2_label)],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_admin_menu() -> ReplyKeyboardMarkup:
    zoom_update_url = get_zoom_update_webapp_url()
    if zoom_update_url:
        zoom_button = KeyboardButton(MENU_UPDATE_ZOOM, web_app=WebAppInfo(url=zoom_update_url))
    else:
        zoom_button = KeyboardButton(MENU_UPDATE_ZOOM)
    return ReplyKeyboardMarkup(
        keyboard=[
            [zoom_button],
            [KeyboardButton(MENU_NOTIFICATION_SENDER)],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


async def show_main_menu(update: Update, text: str) -> None:
    message = update.effective_message
    if not message:
        return
    user_id = update.effective_user.id if update.effective_user else None
    await message.reply_text(text, reply_markup=build_main_menu(user_id))


async def show_webinar_menu(update: Update, text: str) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(text, reply_markup=build_webinar_menu())


async def show_webinar_series_menu(update: Update, text: str) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(text, reply_markup=build_webinar_series_menu())


async def show_series_content_menu(update: Update, text: str) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(text, reply_markup=build_series_content_menu())


async def show_recordings_menu(update: Update, text: str, session_1_label: str, session_2_label: str) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(text, reply_markup=build_recordings_menu(session_1_label, session_2_label))


async def show_admin_menu(update: Update, text: str) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(text, reply_markup=build_admin_menu())


def build_zoom_series_text(series_number: str) -> str:
    campaign = get_current_webinar_campaign()
    session_rows: list[str] = []
    for session_number in ("1", "2"):
        row = get_zoom_entry(campaign, series_number, session_number)
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "active").strip().lower()
        if status == "revoked":
            continue
        session_label = f"Sesi {session_number}"
        start_at = str(row.get("start_at") or "").strip()
        link = str(row.get("link") or "").strip()
        message_text = str(row.get("message") or "").strip()
        parts = [f"{session_label}"]
        if start_at:
            parts.append(f"Mula: {start_at}")
        if status == "finished":
            parts.append("Sesi tersebut telah tamat.")
        elif link:
            parts.append(f"Link: {link}")
        if message_text:
            parts.append(message_text)
        session_rows.append("\n".join(parts))
    if not session_rows:
        return ZOOM_PLACEHOLDER
    return "\n\n".join(session_rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["menu_level"] = LEVEL_MAIN
    await show_main_menu(update, "Sila pilih menu utama:")


async def menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    selected_series_label = str(context.user_data.get("selected_series_label") or "")
    session_1_label, session_2_label = SERIES_SESSION_LABELS.get(
        selected_series_label,
        ("Sesi 1", "Sesi 2"),
    )
    selected_series_number = selected_series_number_from_context(context)
    current_user_id = update.effective_user.id if update.effective_user else 0
    access_level = get_series_access_level(current_user_id, selected_series_number) if selected_series_number else "none"
    if text == MENU_HOME:
        context.user_data["menu_level"] = LEVEL_MAIN
        await show_main_menu(update, "Kembali ke menu utama.")
        return

    if text == MENU_BOOTCAMP:
        context.user_data["menu_level"] = LEVEL_MAIN
        await show_main_menu(update, BOOTCAMP_PLACEHOLDER)
        return

    if text == MENU_SEMINAR:
        context.user_data["menu_level"] = LEVEL_MAIN
        await show_main_menu(update, SEMINAR_PLACEHOLDER)
        return

    if text == MENU_TRADE_TALK:
        context.user_data["menu_level"] = LEVEL_MAIN
        await show_main_menu(update, TRADE_TALK_PLACEHOLDER)
        return

    if text == MENU_WEBINAR:
        context.user_data["menu_level"] = LEVEL_WEBINAR
        await show_webinar_menu(update, "Sila pilih webinar yang tersedia:")
        return

    if text == MENU_BACK:
        menu_level = str(context.user_data.get("menu_level") or LEVEL_MAIN)
        if menu_level == LEVEL_SERIES_DETAIL:
            context.user_data["menu_level"] = LEVEL_WEBINAR_FULLFLOW
            await show_webinar_series_menu(update, "Kembali ke pilihan siri Webinar FULLFLOW (April):")
            return
        if menu_level == LEVEL_RECORDINGS:
            context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
            await show_series_content_menu(update, f"{selected_series_label or 'Siri dipilih'}\n\nKembali ke kandungan siri yang dipilih:")
            return
        if menu_level == LEVEL_SERIES_CONTENT:
            context.user_data["menu_level"] = LEVEL_WEBINAR_FULLFLOW
            await show_webinar_series_menu(update, "Kembali ke pilihan siri Webinar FULLFLOW (April):")
            return
        if menu_level == LEVEL_WEBINAR_FULLFLOW:
            context.user_data["menu_level"] = LEVEL_WEBINAR
            await show_webinar_menu(update, "Kembali ke senarai webinar:")
            return
        if menu_level == LEVEL_ADMIN:
            context.user_data["menu_level"] = LEVEL_MAIN
            await show_main_menu(update, "Kembali ke menu utama.")
            return
        context.user_data["menu_level"] = LEVEL_MAIN
        await show_main_menu(update, "Kembali ke menu utama.")
        return

    if text == MENU_WEBINAR_FULLFLOW:
        context.user_data["menu_level"] = LEVEL_WEBINAR_FULLFLOW
        await show_webinar_series_menu(update, "Sila pilih siri Webinar FULLFLOW (April):")
        return

    if text in {MENU_SERIES_1, MENU_SERIES_2, MENU_SERIES_3}:
        context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
        context.user_data["selected_series_label"] = text
        await show_series_content_menu(update, f"{text}\n\nSila pilih kandungan yang tersedia:")
        return

    if text == MENU_PDF_EBOOK:
        context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
        if access_level != "full":
            deny_text = RECORDING_ONLY_TEXT if access_level == "recording_only" else FULL_ACCESS_REQUIRED_TEXT
            await show_series_content_menu(update, deny_text)
            return
        await show_series_content_menu(update, CONTENT_PLACEHOLDER)
        return

    if text == MENU_ZOOM_LINK:
        context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
        if access_level != "full":
            deny_text = RECORDING_ONLY_TEXT if access_level == "recording_only" else FULL_ACCESS_REQUIRED_TEXT
            await show_series_content_menu(update, deny_text)
            return
        await show_series_content_menu(update, build_zoom_series_text(selected_series_number))
        return

    if text == MENU_EXTRA_VIDEOS:
        context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
        if access_level != "full":
            deny_text = RECORDING_ONLY_TEXT if access_level == "recording_only" else FULL_ACCESS_REQUIRED_TEXT
            await show_series_content_menu(update, deny_text)
            return
        await show_series_content_menu(update, CONTENT_PLACEHOLDER)
        return

    if text == MENU_RECORDINGS:
        context.user_data["menu_level"] = LEVEL_RECORDINGS
        if access_level not in {"full", "recording_only"}:
            await show_series_content_menu(update, "Akses rakaman untuk siri ini belum tersedia pada akaun anda.")
            context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
            return
        await show_recordings_menu(update, "Sila pilih sesi rakaman:", session_1_label, session_2_label)
        return

    if text in {session_1_label, session_2_label}:
        context.user_data["menu_level"] = LEVEL_RECORDINGS
        if access_level not in {"full", "recording_only"}:
            await show_series_content_menu(update, "Akses rakaman untuk siri ini belum tersedia pada akaun anda.")
            context.user_data["menu_level"] = LEVEL_SERIES_CONTENT
            return
        await show_recordings_menu(update, CONTENT_PLACEHOLDER, session_1_label, session_2_label)
        return

    if text == MENU_UPDATE_ZOOM:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != get_superuser_id():
            await show_main_menu(update, "Sila gunakan menu yang disediakan.")
            return
        context.user_data["menu_level"] = LEVEL_ADMIN
        if get_zoom_update_webapp_url():
            await show_admin_menu(update, "Buka miniapp untuk kemaskini Zoom Link.")
        else:
            await show_admin_menu(update, "Miniapp Zoom Link belum dikonfigurasi. Set `NEXT_EVENT_ADMIN_WEBAPP_URL` dalam .env dulu.")
        return

    if text == MENU_NOTIFICATION_SENDER:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != get_superuser_id():
            await show_main_menu(update, "Sila gunakan menu yang disediakan.")
            return
        context.user_data["menu_level"] = LEVEL_ADMIN
        await show_admin_menu(update, "Notification sender belum dibuka lagi.")
        return

    if text == MENU_ADMIN_PANEL:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != get_superuser_id():
            await show_main_menu(update, "Sila gunakan menu yang disediakan.")
            return
        context.user_data["menu_level"] = LEVEL_ADMIN
        await show_admin_menu(update, "Admin panel aktif.")
        return

    if text == "/home":
        context.user_data["menu_level"] = LEVEL_MAIN
        await show_main_menu(update, "Kembali ke menu utama.")
        return

    await show_main_menu(update, "Sila gunakan menu yang disediakan.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    user_id = update.effective_user.id if update.effective_user else None
    superuser_id = get_superuser_id()
    if superuser_id is None or user_id != superuser_id:
        await message.reply_text("Akses admin tidak dibenarkan.")
        return
    context.user_data["menu_level"] = LEVEL_ADMIN
    await show_admin_menu(update, "Admin panel aktif.")


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.web_app_data:
        return
    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.reply_text("❌ Data miniapp tak sah.", reply_markup=build_admin_menu())
        return
    if not isinstance(payload, dict):
        await message.reply_text("❌ Data miniapp tak sah.", reply_markup=build_admin_menu())
        return

    payload_type = str(payload.get("type") or "")
    if payload_type not in {
        "next_event_admin_zoom_submit",
        "next_event_admin_zoom_revoke",
        "next_event_admin_zoom_finish",
    }:
        await message.reply_text("ℹ️ Miniapp event diterima.", reply_markup=build_admin_menu())
        return

    if user.id != get_superuser_id():
        await message.reply_text("❌ Akses admin tidak dibenarkan.")
        return

    campaign = str(payload.get("campaign") or get_current_webinar_campaign()).strip().lower()
    series_number = str(payload.get("series") or "").strip()
    session_number = str(payload.get("session") or "").strip()

    if not campaign:
        await message.reply_text("❌ Campaign webinar tak sah.", reply_markup=build_admin_menu())
        return
    if series_number not in {"1", "2", "3"}:
        await message.reply_text("❌ Siri webinar tak sah.", reply_markup=build_admin_menu())
        return
    if session_number not in {"1", "2"}:
        await message.reply_text("❌ Sesi webinar tak sah.", reply_markup=build_admin_menu())
        return
    data = _read_zoom_state()
    campaigns = data.setdefault("campaigns", {})
    if not isinstance(campaigns, dict):
        campaigns = {}
        data["campaigns"] = campaigns
    campaign_row = campaigns.setdefault(campaign, {})
    if not isinstance(campaign_row, dict):
        campaign_row = {}
        campaigns[campaign] = campaign_row
    series = campaign_row.setdefault("series", {})
    if not isinstance(series, dict):
        series = {}
        campaign_row["series"] = series
    series_row = series.setdefault(series_number, {})
    if not isinstance(series_row, dict):
        series_row = {}
        series[series_number] = series_row
    sessions = series_row.setdefault("sessions", {})
    if not isinstance(sessions, dict):
        sessions = {}
        series_row["sessions"] = sessions

    if payload_type == "next_event_admin_zoom_submit":
        start_at = str(payload.get("start_at") or "").strip()
        link = str(payload.get("link") or "").strip()
        message_text = str(payload.get("message") or "").strip()
        if not start_at or not link:
            await message.reply_text("❌ Masa mula sesi dan link wajib diisi.", reply_markup=build_admin_menu())
            return
        sessions[session_number] = {
            "start_at": start_at,
            "link": link,
            "message": message_text,
            "status": "active",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": int(user.id),
        }
    else:
        existing = sessions.get(session_number)
        if not isinstance(existing, dict):
            await message.reply_text("❌ Rekod Zoom Link untuk siri/sesi ini belum wujud.", reply_markup=build_admin_menu())
            return
        if payload_type == "next_event_admin_zoom_revoke":
            existing["status"] = "revoked"
        elif payload_type == "next_event_admin_zoom_finish":
            existing["status"] = "finished"
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        existing["updated_by"] = int(user.id)
        sessions[session_number] = existing

    try:
        _write_zoom_state(data)
    except sqlite3.Error:
        logger.exception("Failed to write zoom state")
        await message.reply_text("❌ Gagal simpan Zoom Link.", reply_markup=build_admin_menu())
        return

    if payload_type == "next_event_admin_zoom_submit":
        start_at = str(payload.get("start_at") or "").strip()
        link = str(payload.get("link") or "").strip()
        message_text = str(payload.get("message") or "").strip()
        notify_ids = get_full_access_user_ids_for_series(campaign, series_number)
        notify_text = (
            f"📡 Update Webinar FULLFLOW ({campaign})\n\n"
            f"Siri: SIRI {series_number}\n"
            f"Sesi: Sesi {session_number}\n"
            f"Masa mula: {start_at}\n"
            f"Link: {link}\n"
            f"{message_text}".strip()
        )
        sent_count = 0
        for target_user_id in sorted(notify_ids):
            try:
                await context.bot.send_message(chat_id=target_user_id, text=notify_text)
                sent_count += 1
            except Exception:
                logger.exception("Failed sending zoom notification user_id=%s", target_user_id)

        await message.reply_text(
            f"✅ Zoom Link berjaya disimpan.\nCampaign: {campaign}\nSiri: SIRI {series_number}\nSesi: Sesi {session_number}\nNotifikasi dihantar kepada {sent_count} user.",
            reply_markup=build_admin_menu(),
        )
        return

    if payload_type == "next_event_admin_zoom_revoke":
        await message.reply_text(
            f"✅ Zoom Link untuk SIRI {series_number}, Sesi {session_number} telah direvoke.",
            reply_markup=build_admin_menu(),
        )
        return

    if payload_type == "next_event_admin_zoom_finish":
        await message.reply_text(
            f"✅ Sesi {session_number} untuk SIRI {series_number} ditandakan tamat.",
            reply_markup=build_admin_menu(),
        )


def main() -> None:
    application = ApplicationBuilder().token(get_token()).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
