"""Standalone video bot for NEXT eVideo26 and strategy videos."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from texts import (
    COMING_SOON_FIBO,
    COMING_SOON_INTRADAY,
    EVIDEO_MENU_TEXT,
    MAIN_MENU_TEXT,
)
from video_catalog import BASIC_TOPICS, LEVEL_LABELS, VIDEO_CATALOG

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MENU_EVIDEO = "🎬 NEXT eVideo26 Full Silibus"
MENU_INTRADAY = "📈 Intraday Strategy"
MENU_FIBO = "🧩 Fibo Extension Custom Strategy"

MENU_LEVEL_BASIC = "🟢 Basic"
MENU_LEVEL_INTERMEDIATE = "🟠 Intermediate"
MENU_LEVEL_ADVANCED = "🔴 Advanced"
MENU_BACK_MAIN = "⬅️ Back to Main Menu"
MENU_TOPIC_PREV = "⏮️ << Prev Topic"
MENU_TOPIC_NEXT = "⏭️ Next Topic >>"
MENU_TOPIC_PICK = "📚 Pilih Topik"
MENU_TOPIC_MAIN = "🏠 Main Menu"


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


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    evideo_url = get_evideo_webapp_url()
    if evideo_url:
        evideo_button = KeyboardButton(MENU_EVIDEO, web_app=WebAppInfo(url=evideo_url))
    else:
        evideo_button = KeyboardButton(MENU_EVIDEO)
    rows = [
        [evideo_button],
        [KeyboardButton(MENU_INTRADAY)],
        [KeyboardButton(MENU_FIBO)],
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
    rows = [
        [KeyboardButton(MENU_TOPIC_PREV), KeyboardButton(MENU_TOPIC_NEXT)],
        [KeyboardButton(MENU_TOPIC_PICK)],
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


def build_level_text(level_key: str, group_id: int | None) -> str:
    label = LEVEL_LABELS.get(level_key, level_key.title())
    if level_key == "basic":
        lines = [f"📂 {label} ({len(BASIC_TOPICS)} topik)\n"]
        for row in BASIC_TOPICS:
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


def _find_basic_topic(topic_no: int) -> dict | None:
    for row in BASIC_TOPICS:
        if int(row.get("topic_no") or 0) == int(topic_no):
            return row
    return None


async def _send_topic_video(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    level: str,
    topic_no: int,
) -> None:
    if level != "basic":
        await context.bot.send_message(
            chat_id=chat_id,
            text="Level ini belum disambung untuk penghantaran video.",
            reply_markup=topic_navigation_keyboard(),
        )
        return

    topic = _find_basic_topic(topic_no)
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
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Message ID untuk Topik {topic_no} belum diisi.",
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
        except Exception:
            logger.exception("Failed to delete previous topic video message_id=%s", old_video_message_id)

    context.user_data["last_video_message_id"] = int(sent_video.message_id)
    context.user_data["last_video_chat_id"] = int(chat_id)
    context.user_data["last_topic_level"] = level
    context.user_data["last_topic_no"] = topic_no
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Topik {topic_no}: {topic_title}",
        reply_markup=topic_navigation_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())


async def groupid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return
    await message.reply_text(
        f"chat_id: `{chat.id}`\nchat_type: `{chat.type}`",
        parse_mode="Markdown",
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return
    text = message.text.strip()
    lowered = text.lower()

    if lowered in {"groupid", "/groupid"}:
        await groupid(update, context)
        return

    if text == MENU_TOPIC_MAIN:
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
        return
    if text == MENU_TOPIC_PICK:
        await message.reply_text(EVIDEO_MENU_TEXT, reply_markup=level_menu_keyboard())
        return
    if text in {MENU_TOPIC_PREV, MENU_TOPIC_NEXT}:
        level = str(context.user_data.get("last_topic_level") or "basic")
        current_topic = int(context.user_data.get("last_topic_no") or 0)
        if current_topic <= 0:
            await message.reply_text(
                "Belum ada topik dipilih. Pilih topik dulu dari miniapp.",
                reply_markup=topic_navigation_keyboard(),
            )
            return
        next_topic = current_topic - 1 if text == MENU_TOPIC_PREV else current_topic + 1
        if next_topic < 1 or next_topic > len(BASIC_TOPICS):
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
        await message.reply_text(COMING_SOON_INTRADAY, reply_markup=main_menu_keyboard())
        return
    if text == MENU_FIBO:
        await message.reply_text(COMING_SOON_FIBO, reply_markup=main_menu_keyboard())
        return
    if text == MENU_BACK_MAIN:
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
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

    await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return
    raw = str(message.web_app_data.data or "").strip()
    if not raw:
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.reply_text("Data miniapp tak sah.", reply_markup=main_menu_keyboard())
        return

    if not isinstance(payload, dict):
        await message.reply_text("Data miniapp tak sah.", reply_markup=main_menu_keyboard())
        return

    payload_type = str(payload.get("type") or "").strip().lower()
    if payload_type == "video_bot_back_to_main_menu":
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
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
            await message.reply_text("Pilihan topik tak sah.", reply_markup=main_menu_keyboard())
            return
        await _send_topic_video(context, message.chat_id, level, topic_no)
        return

    await message.reply_text("Action miniapp diterima.", reply_markup=main_menu_keyboard())


def main() -> None:
    token = get_token()
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("groupid", groupid))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Video bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
