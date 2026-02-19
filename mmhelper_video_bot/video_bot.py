"""Standalone video bot for NEXT eVideo26 and strategy videos."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

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
MENU_ADMIN = "🛠️ Admin"
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


def get_bot_timezone() -> ZoneInfo:
    raw = (os.getenv("VIDEO_BOT_TIMEZONE") or "Asia/Kuala_Lumpur").strip()
    try:
        return ZoneInfo(raw)
    except Exception:
        return ZoneInfo("UTC")


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
    if not VIDEO_STATUS_PATH.exists():
        return {}
    try:
        raw = json.loads(VIDEO_STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
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


def get_evideo_webapp_url_with_topic_ids() -> str:
    base = get_evideo_webapp_url()
    if not base:
        return ""
    encoded_payload = quote(_topic_message_ids_payload(), safe="")
    encoded_status = quote(_video_status_payload(), safe="")
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}topic_ids={encoded_payload}&video_status={encoded_status}"


def main_menu_keyboard(show_admin_panel: bool = False) -> ReplyKeyboardMarkup:
    evideo_url = get_evideo_webapp_url_with_topic_ids()
    if evideo_url:
        evideo_button = KeyboardButton(MENU_EVIDEO, web_app=WebAppInfo(url=evideo_url))
    else:
        evideo_button = KeyboardButton(MENU_EVIDEO)
    rows = [
        [evideo_button],
        [KeyboardButton(MENU_INTRADAY)],
        [KeyboardButton(MENU_FIBO)],
        [KeyboardButton(MENU_MMHELPER), KeyboardButton(MENU_ADMIN)],
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


def topic_navigation_keyboard() -> ReplyKeyboardMarkup:
    evideo_url = get_evideo_webapp_url_with_topic_ids()
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


def _message_link(group_id: int, message_id: int) -> str:
    # Telegram deep-link format for private supergroup messages.
    group_text = str(group_id)
    if group_text.startswith("-100"):
        group_text = group_text[4:]
    elif group_text.startswith("-"):
        group_text = group_text[1:]
    return f"https://t.me/c/{group_text}/{message_id}"


def _load_sent_video_log() -> list[dict[str, int]]:
    if not SENT_VIDEO_LOG_PATH.exists():
        return []
    try:
        raw = json.loads(SENT_VIDEO_LOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
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
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
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


def _load_scheduled_notifications() -> list[dict]:
    if not SCHEDULED_NOTIFICATIONS_PATH.exists():
        return []
    try:
        raw = json.loads(SCHEDULED_NOTIFICATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _save_scheduled_notifications(rows: list[dict]) -> None:
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
    if not AUTO_DELETE_NOTICES_PATH.exists():
        return {}
    try:
        raw = json.loads(AUTO_DELETE_NOTICES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
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


async def _send_topic_video(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    level: str,
    topic_no: int,
) -> None:
    topic = _find_level_topic(level, topic_no)
    if not topic:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Topik tak dijumpai.",
            reply_markup=topic_navigation_keyboard(),
        )
        return

    group_id = get_video_db_group_id()
    if group_id is None:
        await context.bot.send_message(
            chat_id=chat_id,
            text="VIDEO_DB_GROUP_ID belum diset dalam .env.",
            reply_markup=topic_navigation_keyboard(),
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
            reply_markup=topic_navigation_keyboard(),
        )
        return

    try:
        sent_video = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=group_id,
            message_id=message_id,
            protect_content=True,
        )
    except Exception:
        logger.exception("Failed to copy topic video level=%s topic=%s", level, topic_no)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Gagal tarik video Topik {topic_no}. Semak message_id/group id.",
            reply_markup=topic_navigation_keyboard(),
        )
        return

    # Keep video until user chooses another topic.
    # Old video is removed only after a new one is sent successfully.
    old_video_message_id = int(context.user_data.get("last_video_message_id") or 0)
    old_video_chat_id = int(context.user_data.get("last_video_chat_id") or 0)
    if old_video_message_id > 0 and old_video_chat_id == chat_id and old_video_message_id != int(sent_video.message_id):
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
        reply_markup=topic_navigation_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    _register_known_user_from_update(update)
    await _purge_auto_delete_notices_for_chat(context, message.chat_id)
    await message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
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
    text = message.text.strip()
    lowered = text.lower()

    if lowered in {"groupid", "/groupid"}:
        await groupid(update, context)
        return

    if text == MENU_TOPIC_MAIN:
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
        )
        return
    if text == MENU_TOPIC_PICK:
        if not bool(context.user_data.get("topic_session_active")):
            await message.reply_text(
                "Sila buka miniapp eVideo dulu dan pilih topik.",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
            )
            return
        await message.reply_text(EVIDEO_MENU_TEXT, reply_markup=level_menu_keyboard())
        return
    if text in {MENU_TOPIC_PREV, MENU_TOPIC_NEXT}:
        if not bool(context.user_data.get("topic_session_active")):
            await message.reply_text(
                "Sila pilih topik melalui miniapp terlebih dahulu.",
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
            )
            return
        level = str(context.user_data.get("last_topic_level") or "basic")
        current_topic = int(context.user_data.get("last_topic_no") or 0)
        if current_topic <= 0:
            await message.reply_text(
                "Belum ada topik dipilih. Pilih topik dulu dari miniapp.",
                reply_markup=topic_navigation_keyboard(),
            )
            return
        next_topic = current_topic - 1 if text == MENU_TOPIC_PREV else current_topic + 1
        level_topics = LEVEL_TOPICS.get(level, [])
        if next_topic < 1 or next_topic > len(level_topics):
            await message.reply_text(
                "Tiada topik lagi untuk arah ini.",
                reply_markup=topic_navigation_keyboard(),
            )
            return
        await _send_topic_video(context, message.chat_id, level, next_topic)
        return

    if text == MENU_EVIDEO:
        await message.reply_text(EVIDEO_MENU_TEXT, reply_markup=level_menu_keyboard())
        return
    if text == MENU_INTRADAY:
        await message.reply_text(
            COMING_SOON_INTRADAY,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
        )
        return
    if text == MENU_FIBO:
        await message.reply_text(
            COMING_SOON_FIBO,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
        )
        return
    if text == MENU_MMHELPER:
        await message.reply_text(
            "🤖 MM Helper <i>(coming soon)</i>",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
            parse_mode="HTML",
        )
        return
    if text == MENU_ADMIN:
        await message.reply_text(
            "🛠️ Admin <i>(coming soon)</i>",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
            parse_mode="HTML",
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
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
        )
        return
    if text == MENU_ADMIN_BACK:
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
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
        reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
    )


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return
    _register_known_user_from_update(update)
    await _purge_auto_delete_notices_for_chat(context, message.chat_id)
    raw = str(message.web_app_data.data or "").strip()
    if not raw:
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.reply_text(
            "Data miniapp tak sah.",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
        )
        return

    if not isinstance(payload, dict):
        await message.reply_text(
            "Data miniapp tak sah.",
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
        )
        return

    payload_type = str(payload.get("type") or "").strip().lower()
    if payload_type == "video_bot_back_to_main_menu":
        await message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
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
                reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
            )
            return
        context.user_data["topic_session_active"] = True
        await _send_topic_video(context, message.chat_id, level, topic_no)
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
        await message.reply_text(
            f"✅ Status dikemaskini.\nLevel: {level.title()}\nTopik: {topic_no}\nStatus: {status_text}",
            reply_markup=admin_panel_keyboard(),
        )
        return

    await message.reply_text(
        "Action miniapp diterima.",
        reply_markup=main_menu_keyboard(show_admin_panel=is_admin_user(update)),
    )


def main() -> None:
    token = get_token()
    app = ApplicationBuilder().token(token).build()
    if app.job_queue is not None:
        app.job_queue.run_repeating(scheduled_notification_worker, interval=10, first=5)
    else:
        logger.warning("Job queue unavailable; scheduled notifications disabled.")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("groupid", groupid))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Video bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
