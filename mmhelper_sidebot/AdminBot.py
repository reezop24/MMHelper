"""Admin side bot scaffold with TnC gate and starter menu."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from texts import DECLINED_TEXT, MAIN_MENU_TEXT, TNC_TEXT

logger = logging.getLogger(__name__)

TNC_ACCEPT = "ADMIN_TNC_ACCEPT"
TNC_DECLINE = "ADMIN_TNC_DECLINE"

MENU_DAFTAR_NEXT_MEMBER = "Daftar NEXT member"
MENU_BELI_EVIDEO26 = "Beli NEXT eVideo26"
MENU_ALL_PRODUCT_PREVIEW = "All Product Preview"


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
    token = (os.getenv("SIDEBOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set SIDEBOT_TOKEN in mmhelper_sidebot/.env")
    return token


def tnc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Setuju & Teruskan", callback_data=TNC_ACCEPT)],
            [InlineKeyboardButton("❌ Batal", callback_data=TNC_DECLINE)],
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(MENU_DAFTAR_NEXT_MEMBER)],
            [KeyboardButton(MENU_BELI_EVIDEO26)],
            [KeyboardButton(MENU_ALL_PRODUCT_PREVIEW)],
        ],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    await message.reply_text(TNC_TEXT, reply_markup=tnc_keyboard())


async def handle_tnc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.data == TNC_ACCEPT:
        await query.message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
        return

    await query.message.reply_text(DECLINED_TEXT)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    app = ApplicationBuilder().token(get_token()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_tnc_callback, pattern=f"^({TNC_ACCEPT}|{TNC_DECLINE})$"))
    app.run_polling()


if __name__ == "__main__":
    main()
