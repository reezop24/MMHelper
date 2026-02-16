"""Screen lifecycle helpers for MM HELPER."""

from __future__ import annotations

from typing import Any

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
    reply_markup: Any = None,
    parse_mode: str | None = None,
) -> None:
    old_msg_id = context.user_data.get("last_screen_message_id")

    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    context.user_data["last_screen_message_id"] = sent.message_id

    if old_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
        except Exception:
            pass
