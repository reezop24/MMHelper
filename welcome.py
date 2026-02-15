"""Welcome/T&C flow for MM HELPER."""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ContextTypes

from settings import get_setup_webapp_url
from texts import TNC_TEXT, DECLINED_TEXT, WHY_MM_HELPER_TEXT

TNC_ACCEPT = "TNC_ACCEPT"
TNC_DECLINE = "TNC_DECLINE"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Setuju & Teruskan", callback_data=TNC_ACCEPT)],
            [InlineKeyboardButton("🚪 Tidak Setuju", callback_data=TNC_DECLINE)],
        ]
    )

    await update.effective_message.reply_text(
        TNC_TEXT,
        reply_markup=keyboard,
    )


async def handle_tnc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.data == TNC_ACCEPT:
        context.user_data["tnc_accepted"] = True
        setup_keyboard = ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton(
                        "🚀 Mula Setup",
                        web_app=WebAppInfo(url=get_setup_webapp_url()),
                    )
                ]
            ],
            resize_keyboard=True,
        )
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=WHY_MM_HELPER_TEXT,
            reply_markup=setup_keyboard,
        )
        return

    context.user_data["tnc_accepted"] = False
    await query.edit_message_text(DECLINED_TEXT)
