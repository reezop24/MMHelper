"""Screen lifecycle helpers for MM HELPER."""

from __future__ import annotations

from telegram import ReplyMarkup
from telegram.ext import ContextTypes


async def clear_last_screen(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    last_msg_id = context.user_data.pop("last_screen_message_id", None)
    if not last_msg_id:
        return

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
    except Exception:
        pass


async def send_screen(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup: ReplyMarkup | None = None,
) -> None:
    await clear_last_screen(context, chat_id)
    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    context.user_data["last_screen_message_id"] = sent.message_id
