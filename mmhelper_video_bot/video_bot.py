"""Standalone video bot for NEXT eVideo26 and strategy videos."""

from __future__ import annotations

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
from video_catalog import LEVEL_LABELS, VIDEO_CATALOG

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


def main() -> None:
    token = get_token()
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("groupid", groupid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Video bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
