"""Text handlers for MM HELPER."""

from telegram import Update
from telegram.ext import ContextTypes

from storage import reset_all_data
from ui import clear_last_screen
from welcome import start


async def handle_text_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()

    if text == "🧪 BETA RESET":
        reset_all_data()
        await clear_last_screen(context, message.chat_id)
        context.user_data.clear()
        await start(update, context)
