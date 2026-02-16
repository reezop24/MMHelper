"""Text handlers for MM HELPER."""

from telegram import Update
from telegram.ext import ContextTypes

from texts import BETA_RESET_DONE_TEXT
from storage import reset_all_data
from welcome import start
from ui import clear_last_screen


async def handle_text_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()

    if text == "🧪 BETA RESET":
        reset_all_data()
        await clear_last_screen(context, message.chat_id)
        context.user_data.clear()
        await message.reply_text(BETA_RESET_DONE_TEXT)
        await start(update, context)
