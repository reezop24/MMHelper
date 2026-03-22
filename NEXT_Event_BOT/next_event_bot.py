"""Simple NEXT event bot with reply-keyboard main menu."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
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
MENU_USER_STATUS = "User Status"

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
NEXT_EVENT_NOTIFICATION_STATE_KEY = "next_event_notification_state"
NEXT_EVENT_ACTIVATION_STATE_KEY = "next_event_activation_state"
MY_TZ = ZoneInfo("Asia/Kuala_Lumpur")


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


def get_admin_bot_url() -> str:
    url = (
        os.getenv("NEXT_EVENT_ADMIN_BOT_URL")
        or os.getenv("SIDEBOT_ADMIN_BOT_URL")
        or "https://t.me/ReezoAdmin_Bot"
    )
    url = str(url or "").strip()
    return url if url.startswith("https://t.me/") else ""


def get_admin_group_id() -> int | None:
    raw = (os.getenv("SIDEBOT_ADMIN_GROUP_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


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


def _read_notification_state() -> dict:
    default = {"jobs": []}
    try:
        with _connect_shared_db() as conn:
            return _read_kv_json(conn, NEXT_EVENT_NOTIFICATION_STATE_KEY, default)
    except sqlite3.Error:
        logger.warning("Failed to read notification state for NEXT event bot", exc_info=True)
        return default


def _write_notification_state(data: dict) -> None:
    with _connect_shared_db() as conn:
        _write_kv_json(conn, NEXT_EVENT_NOTIFICATION_STATE_KEY, data)


def _read_activation_state() -> dict:
    default = {"campaigns": {}}
    try:
        with _connect_shared_db() as conn:
            return _read_kv_json(conn, NEXT_EVENT_ACTIVATION_STATE_KEY, default)
    except sqlite3.Error:
        logger.warning("Failed to read activation state for NEXT event bot", exc_info=True)
        return default


def _write_activation_state(data: dict) -> None:
    with _connect_shared_db() as conn:
        _write_kv_json(conn, NEXT_EVENT_ACTIVATION_STATE_KEY, data)


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


def get_notification_sender_webapp_url() -> str:
    base = (os.getenv("NEXT_EVENT_ADMIN_WEBAPP_URL") or os.getenv("NEXT_EVENT_WEBAPP_URL") or "").strip()
    if not base.lower().startswith("https://"):
        return ""
    if base.endswith("/"):
        built = f"{base}notification-sender.html"
    elif base.endswith(".html"):
        built = f"{base.rsplit('/', 1)[0]}/notification-sender.html"
    else:
        built = f"{base}/notification-sender.html"
    sep = "&" if "?" in built else "?"
    return f"{built}{sep}{urlencode({'campaign': get_current_webinar_campaign()})}"


def get_user_status_webapp_url() -> str:
    base = (os.getenv("NEXT_EVENT_ADMIN_WEBAPP_URL") or os.getenv("NEXT_EVENT_WEBAPP_URL") or "").strip()
    if not base.lower().startswith("https://"):
        return ""
    if base.endswith("/"):
        built = f"{base}user-status.html"
    elif base.endswith(".html"):
        built = f"{base.rsplit('/', 1)[0]}/user-status.html"
    else:
        built = f"{base}/user-status.html"
    sep = "&" if "?" in built else "?"
    return f"{built}{sep}{urlencode({'campaign': get_current_webinar_campaign(), 'user_status_payload': _user_status_payload()})}"


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


def get_vip2_user_ids() -> set[int]:
    out: set[int] = set()
    vip2_users = _read_vip_whitelist().get("vip2", {}).get("users", {})
    if isinstance(vip2_users, dict):
        for user_id in vip2_users:
            if str(user_id).isdigit():
                out.add(int(user_id))
    return out


def get_vip3_user_ids() -> set[int]:
    out: set[int] = set()
    vip3_users = _read_vip_whitelist().get("vip3", {}).get("users", {})
    if isinstance(vip3_users, dict):
        for user_id in vip3_users:
            if str(user_id).isdigit():
                out.add(int(user_id))
    return out


def get_webinar_whitelist_user_ids(campaign: str, series_number: str) -> set[int]:
    out: set[int] = set()
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


def _display_name_for_user_id(user_id: str, vip_whitelist: dict, webinar_state: dict, campaign: str) -> str:
    if isinstance(vip_whitelist.get("vip2", {}), dict):
        row = vip_whitelist.get("vip2", {}).get("users", {}).get(user_id)
        if isinstance(row, dict) and str(row.get("full_name") or "").strip():
            return str(row.get("full_name") or "").strip()
    if isinstance(vip_whitelist.get("vip3", {}), dict):
        row = vip_whitelist.get("vip3", {}).get("users", {}).get(user_id)
        if isinstance(row, dict) and str(row.get("full_name") or "").strip():
            return str(row.get("full_name") or "").strip()
    campaigns = webinar_state.get("campaigns")
    if isinstance(campaigns, dict):
        campaign_row = campaigns.get(campaign)
        if isinstance(campaign_row, dict):
            series = campaign_row.get("series")
            if isinstance(series, dict):
                for series_row in series.values():
                    if not isinstance(series_row, dict):
                        continue
                    users = series_row.get("users")
                    if not isinstance(users, dict):
                        continue
                    row = users.get(user_id)
                    if isinstance(row, dict) and str(row.get("full_name") or "").strip():
                        return str(row.get("full_name") or "").strip()
    return "-"


def _user_status_payload() -> str:
    campaign = get_current_webinar_campaign()
    out: dict[str, object] = {
        "campaign": campaign,
        "webinars": {
            "fullflow": {
                "1": [],
                "2": [],
                "3": [],
            }
        },
    }
    vip_whitelist = _read_vip_whitelist()
    webinar_state = _read_webinar_access_state()

    vip2_users = vip_whitelist.get("vip2", {}).get("users", {}) if isinstance(vip_whitelist.get("vip2"), dict) else {}
    vip3_users = vip_whitelist.get("vip3", {}).get("users", {}) if isinstance(vip_whitelist.get("vip3"), dict) else {}
    webinars = out["webinars"]["fullflow"]  # type: ignore[index]

    for user_id in sorted(vip2_users.keys()) if isinstance(vip2_users, dict) else []:
        name = _display_name_for_user_id(str(user_id), vip_whitelist, webinar_state, campaign)
        for series_number in ("1", "2", "3"):
            webinars[series_number].append({"user_id": str(user_id), "name": name, "category": "NEXTexclusive member"})  # type: ignore[index]

    for user_id in sorted(vip3_users.keys()) if isinstance(vip3_users, dict) else []:
        name = _display_name_for_user_id(str(user_id), vip_whitelist, webinar_state, campaign)
        webinars["1"].append({"user_id": str(user_id), "name": name, "category": "NEXTeVideo26 subscriber"})  # type: ignore[index]
        webinars["2"].append({"user_id": str(user_id), "name": name, "category": "NEXTeVideo26 subscriber (recording)"})  # type: ignore[index]
        webinars["3"].append({"user_id": str(user_id), "name": name, "category": "NEXTeVideo26 subscriber (recording)"})  # type: ignore[index]

    campaigns = webinar_state.get("campaigns")
    if isinstance(campaigns, dict):
        campaign_row = campaigns.get(campaign)
        if isinstance(campaign_row, dict):
            series = campaign_row.get("series")
            if isinstance(series, dict):
                for series_number in ("1", "2", "3"):
                    series_row = series.get(series_number)
                    if not isinstance(series_row, dict):
                        continue
                    users = series_row.get("users")
                    if not isinstance(users, dict):
                        continue
                    for user_id, row in users.items():
                        name = "-"
                        if isinstance(row, dict) and str(row.get("full_name") or "").strip():
                            name = str(row.get("full_name") or "").strip()
                        webinars[series_number].append({"user_id": str(user_id), "name": name, "category": "Peserta"})  # type: ignore[index]

    for series_number in ("1", "2", "3"):
        seen: set[str] = set()
        unique_rows: list[dict[str, str]] = []
        rows = webinars[series_number]  # type: ignore[index]
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = f"{row.get('user_id')}|{row.get('category')}"
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(row)
        webinars[series_number] = unique_rows  # type: ignore[index]

    return json.dumps(out, ensure_ascii=False)


async def maybe_log_event_activation(context: ContextTypes.DEFAULT_TYPE, user_id: int, role_label: str) -> None:
    admin_group_id = get_admin_group_id()
    if not admin_group_id:
        return
    campaign = get_current_webinar_campaign()
    state = _read_activation_state()
    campaigns = state.setdefault("campaigns", {})
    if not isinstance(campaigns, dict):
        campaigns = {}
        state["campaigns"] = campaigns
    campaign_row = campaigns.setdefault(campaign, {})
    if not isinstance(campaign_row, dict):
        campaign_row = {}
        campaigns[campaign] = campaign_row
    users = campaign_row.setdefault("users", {})
    if not isinstance(users, dict):
        users = {}
        campaign_row["users"] = users
    user_key = str(user_id)
    if user_key in users:
        return
    users[user_key] = {
        "role": role_label,
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _write_activation_state(state)
    except sqlite3.Error:
        logger.exception("Failed to persist event activation state")
    try:
        await context.bot.send_message(
            chat_id=admin_group_id,
            text=(
                "✅ NEXT Event Bot Activation\n\n"
                f"Campaign: {campaign}\n"
                f"User ID: {user_id}\n"
                f"Kategori: {role_label}\n"
                "Status: User telah tekan Start dalam NEXT Event Bot"
            ),
        )
    except Exception:
        logger.exception("Failed sending event activation notification to admin group")


def resolve_notification_recipients(
    *,
    target_mode: str,
    target_value: str,
    campaign: str,
    event_kind: str = "",
    event_name: str = "",
    series_number: str = "",
) -> set[int]:
    mode = str(target_mode or "").strip().lower()
    value = str(target_value or "").strip().lower()
    series = str(series_number or "").strip()
    if mode == "group":
        if value == "next":
            return get_vip2_user_ids()
        if value == "evideo":
            return get_vip3_user_ids()
        if value in {"webinar_s1", "webinar_s2", "webinar_s3"}:
            return get_webinar_whitelist_user_ids(campaign, value[-1])
        return set()
    if mode == "event":
        if str(event_kind or "").strip().lower() != "webinar":
            return set()
        if str(event_name or "").strip().lower() != "fullflow":
            return set()
        if series not in {"1", "2", "3"}:
            return set()
        return get_full_access_user_ids_for_series(campaign, series)
    return set()


def _notification_target_label(
    *,
    target_mode: str,
    target_value: str,
    campaign: str,
    event_kind: str = "",
    event_name: str = "",
    series_number: str = "",
) -> str:
    mode = str(target_mode or "").strip().lower()
    value = str(target_value or "").strip().lower()
    if mode == "group":
        labels = {
            "next": "NEXTexclusive",
            "evideo": "NEXTeVideo",
            "webinar_s1": f"{campaign} SIRI 1",
            "webinar_s2": f"{campaign} SIRI 2",
            "webinar_s3": f"{campaign} SIRI 3",
        }
        return labels.get(value, value or "group")
    if mode == "event":
        if str(event_kind or "").strip().lower() == "webinar" and str(event_name or "").strip().lower() == "fullflow":
            return f"Webinar FULLFLOW SIRI {series_number}"
        return f"{event_kind} {event_name}".strip()
    return "target"


def _parse_custom_schedule_utc(date_value: str, time_value: str) -> str:
    raw_date = str(date_value or "").strip()
    raw_time = str(time_value or "").strip()
    if not raw_date or not raw_time:
        raise ValueError("Missing date or time")
    naive = datetime.fromisoformat(f"{raw_date}T{raw_time}")
    local_dt = naive.replace(tzinfo=MY_TZ)
    return local_dt.astimezone(timezone.utc).isoformat()


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
    notification_sender_url = get_notification_sender_webapp_url()
    if notification_sender_url:
        notification_button = KeyboardButton(MENU_NOTIFICATION_SENDER, web_app=WebAppInfo(url=notification_sender_url))
    else:
        notification_button = KeyboardButton(MENU_NOTIFICATION_SENDER)
    user_status_url = get_user_status_webapp_url()
    if user_status_url:
        user_status_button = KeyboardButton(MENU_USER_STATUS, web_app=WebAppInfo(url=user_status_url))
    else:
        user_status_button = KeyboardButton(MENU_USER_STATUS)
    return ReplyKeyboardMarkup(
        keyboard=[
            [zoom_button],
            [notification_button],
            [user_status_button],
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


async def send_notification_message(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    recipient_ids: set[int],
    message_text: str,
) -> int:
    sent_count = 0
    for target_user_id in sorted(recipient_ids):
        try:
            await context.bot.send_message(chat_id=target_user_id, text=message_text)
            sent_count += 1
        except Exception:
            logger.exception("Failed sending notification user_id=%s", target_user_id)
    return sent_count


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


def _series_access_label(access_level: str) -> str:
    level = str(access_level or "none").strip().lower()
    if level == "full":
        return "Akses Penuh"
    if level == "recording_only":
        return "Rakaman Sahaja"
    return "Tiada Akses"


def build_start_welcome_text(user_id: int | None) -> str:
    campaign = get_current_webinar_campaign()
    if not isinstance(user_id, int):
        return (
            "Selamat datang ke NEXT Event Bot.\n\n"
            f"Campaign semasa: {campaign}\n"
            "Bot ini digunakan untuk akses webinar, Zoom link, bahan rujukan, dan rakaman mengikut kelayakan akaun anda."
        )

    if user_id == get_superuser_id():
        role_line = "Kategori akaun anda: SUPERUSER"
    else:
        whitelist = _read_vip_whitelist()
        vip2_users = whitelist.get("vip2", {}).get("users", {})
        vip3_users = whitelist.get("vip3", {}).get("users", {})
        if isinstance(vip2_users, dict) and str(user_id) in vip2_users:
            role_line = "Kategori akaun anda: NEXTexclusive member"
        elif isinstance(vip3_users, dict) and str(user_id) in vip3_users:
            role_line = "Kategori akaun anda: NEXTeVideo26 subscriber"
        else:
            has_any_series_access = any(
                get_series_access_level(user_id, series_number) != "none"
                for series_number in ("1", "2", "3")
            )
            role_line = (
                "Kategori akaun anda: Peserta"
                if has_any_series_access
                else "Kategori akaun anda: Free User / User Biasa"
            )

    s1 = get_series_access_level(user_id, "1")
    s2 = get_series_access_level(user_id, "2")
    s3 = get_series_access_level(user_id, "3")

    lines = [
        "Selamat datang ke NEXT Event Bot.",
        "",
        f"Campaign semasa: {campaign}",
        role_line,
        "",
        "Ringkasan akses anda:",
        f"SIRI 1: {_series_access_label(s1)}",
        f"SIRI 2: {_series_access_label(s2)}",
        f"SIRI 3: {_series_access_label(s3)}",
        "",
        "Akses kandungan dalam bot ini bergantung pada kategori akaun dan whitelist webinar anda.",
    ]
    if s1 == s2 == s3 == "none":
        lines.extend(
            [
                "",
                "Akaun anda belum mempunyai akses webinar buat masa ini.",
                "Anda boleh pergi ke bot admin untuk mendaftar webinar.",
                "Jika anda telah diluluskan untuk webinar, sila pastikan anda menggunakan akaun Telegram yang sama.",
            ]
        )
    return "\n".join(lines)


def is_free_user(user_id: int | None) -> bool:
    if not isinstance(user_id, int):
        return False
    return all(get_series_access_level(user_id, series_number) == "none" for series_number in ("1", "2", "3"))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["menu_level"] = LEVEL_MAIN
    user_id = update.effective_user.id if update.effective_user else None
    if isinstance(user_id, int):
        whitelist = _read_vip_whitelist()
        vip2_users = whitelist.get("vip2", {}).get("users", {})
        vip3_users = whitelist.get("vip3", {}).get("users", {})
        if isinstance(vip2_users, dict) and str(user_id) in vip2_users:
            await maybe_log_event_activation(context, user_id, "NEXTexclusive member")
        elif isinstance(vip3_users, dict) and str(user_id) in vip3_users:
            await maybe_log_event_activation(context, user_id, "NEXTeVideo26 subscriber")
    await show_main_menu(update, build_start_welcome_text(user_id))
    message = update.effective_message
    if not message or not is_free_user(user_id):
        return
    admin_bot_url = get_admin_bot_url()
    if not admin_bot_url:
        return
    await message.reply_text(
        "Tekan butang di bawah untuk buka bot admin dan mendaftar webinar.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Buka Bot Admin", url=admin_bot_url)]]
        ),
    )


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
        if get_notification_sender_webapp_url():
            await show_admin_menu(update, "Buka miniapp untuk Notification sender.")
        else:
            await show_admin_menu(update, "Miniapp Notification sender belum dikonfigurasi. Set `NEXT_EVENT_ADMIN_WEBAPP_URL` dalam .env dulu.")
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
        "next_event_admin_zoom_delete",
        "next_event_admin_notification_submit",
    }:
        await message.reply_text("ℹ️ Miniapp event diterima.", reply_markup=build_admin_menu())
        return

    if user.id != get_superuser_id():
        await message.reply_text("❌ Akses admin tidak dibenarkan.")
        return

    if payload_type == "next_event_admin_notification_submit":
        campaign = str(payload.get("campaign") or get_current_webinar_campaign()).strip().lower()
        target_mode = str(payload.get("target_mode") or "").strip().lower()
        target_value = str(payload.get("target_value") or "").strip().lower()
        event_kind = str(payload.get("event_kind") or "").strip().lower()
        event_name = str(payload.get("event_name") or "").strip().lower()
        series_number = str(payload.get("series") or "").strip()
        delivery_mode = str(payload.get("delivery_mode") or "immediately").strip().lower()
        message_text = str(payload.get("message") or "").strip()
        custom_date = str(payload.get("custom_date") or "").strip()
        custom_time = str(payload.get("custom_time") or "").strip()
        if target_mode not in {"group", "event"}:
            await message.reply_text("❌ Target mode tak sah.", reply_markup=build_admin_menu())
            return
        if not message_text:
            await message.reply_text("❌ Mesej notifikasi wajib diisi.", reply_markup=build_admin_menu())
            return
        if target_mode == "event":
            if event_kind != "webinar":
                await message.reply_text("❌ Event ini belum disokong lagi. Buat masa ini hanya Webinar.", reply_markup=build_admin_menu())
                return
            if event_name != "fullflow":
                await message.reply_text("❌ Webinar ini belum disokong lagi.", reply_markup=build_admin_menu())
                return
            if series_number not in {"1", "2", "3"}:
                await message.reply_text("❌ Siri webinar tak sah.", reply_markup=build_admin_menu())
                return
        elif target_value not in {"next", "evideo", "webinar_s1", "webinar_s2", "webinar_s3"}:
            await message.reply_text("❌ Group target tak sah.", reply_markup=build_admin_menu())
            return

        recipient_ids = resolve_notification_recipients(
            target_mode=target_mode,
            target_value=target_value,
            campaign=campaign,
            event_kind=event_kind,
            event_name=event_name,
            series_number=series_number,
        )
        target_label = _notification_target_label(
            target_mode=target_mode,
            target_value=target_value,
            campaign=campaign,
            event_kind=event_kind,
            event_name=event_name,
            series_number=series_number,
        )
        if delivery_mode == "custom":
            try:
                scheduled_for = _parse_custom_schedule_utc(custom_date, custom_time)
            except ValueError:
                await message.reply_text("❌ Tarikh atau masa custom tak sah.", reply_markup=build_admin_menu())
                return
            state = _read_notification_state()
            jobs = state.setdefault("jobs", [])
            if not isinstance(jobs, list):
                jobs = []
                state["jobs"] = jobs
            jobs.append(
                {
                    "job_id": f"notif_{int(datetime.now(timezone.utc).timestamp())}_{user.id}",
                    "campaign": campaign,
                    "target_mode": target_mode,
                    "target_value": target_value,
                    "event_kind": event_kind,
                    "event_name": event_name,
                    "series": series_number,
                    "message": message_text,
                    "scheduled_for": scheduled_for,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "created_by": int(user.id),
                }
            )
            try:
                _write_notification_state(state)
            except sqlite3.Error:
                logger.exception("Failed to save scheduled notification")
                await message.reply_text("❌ Gagal simpan jadual notifikasi.", reply_markup=build_admin_menu())
                return
            await message.reply_text(
                f"✅ Notifikasi dijadualkan.\nTarget: {target_label}\nCampaign: {campaign}\nMasa hantar: {scheduled_for}\nJumlah penerima: {len(recipient_ids)}",
                reply_markup=build_admin_menu(),
            )
            return

        sent_count = await send_notification_message(
            context,
            recipient_ids=recipient_ids,
            message_text=message_text,
        )
        await message.reply_text(
            f"✅ Notifikasi dihantar segera.\nTarget: {target_label}\nCampaign: {campaign}\nJumlah penerima berjaya: {sent_count}",
            reply_markup=build_admin_menu(),
        )
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
        elif payload_type == "next_event_admin_zoom_delete":
            sessions.pop(session_number, None)
            if not sessions:
                series_row.pop("sessions", None)
            if not series_row:
                series.pop(series_number, None)
            if not series:
                campaign_row.pop("series", None)
            if not campaign_row:
                campaigns.pop(campaign, None)
        if payload_type != "next_event_admin_zoom_delete":
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
        return

    if payload_type == "next_event_admin_zoom_delete":
        await message.reply_text(
            f"✅ Rekod Zoom Link untuk SIRI {series_number}, Sesi {session_number} telah dipadam.",
            reply_markup=build_admin_menu(),
        )


async def notification_schedule_worker(context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _read_notification_state()
    jobs = state.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        return
    now_utc = datetime.now(timezone.utc)
    changed = False
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if str(job.get("status") or "") != "pending":
            continue
        scheduled_for_raw = str(job.get("scheduled_for") or "").strip()
        if not scheduled_for_raw:
            continue
        try:
            scheduled_for = datetime.fromisoformat(scheduled_for_raw)
        except ValueError:
            job["status"] = "failed"
            job["error"] = "invalid_schedule"
            changed = True
            continue
        if scheduled_for.tzinfo is None:
            scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
        if scheduled_for > now_utc:
            continue
        recipient_set = resolve_notification_recipients(
            target_mode=str(job.get("target_mode") or ""),
            target_value=str(job.get("target_value") or ""),
            campaign=str(job.get("campaign") or get_current_webinar_campaign()),
            event_kind=str(job.get("event_kind") or ""),
            event_name=str(job.get("event_name") or ""),
            series_number=str(job.get("series") or ""),
        )
        sent_count = await send_notification_message(
            context,
            recipient_ids=recipient_set,
            message_text=str(job.get("message") or "").strip(),
        )
        job["status"] = "sent"
        job["sent_at"] = now_utc.isoformat()
        job["sent_count"] = sent_count
        changed = True
    if changed:
        try:
            _write_notification_state(state)
        except sqlite3.Error:
            logger.exception("Failed to persist notification schedule state")


def main() -> None:
    application = ApplicationBuilder().token(get_token()).build()
    if application.job_queue:
        application.job_queue.run_repeating(notification_schedule_worker, interval=60, first=15)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
