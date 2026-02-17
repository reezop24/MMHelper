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

from menu import main_menu_keyboard
from settings import get_setup_webapp_url
from storage import has_initial_setup, has_tnc_accepted, save_tnc_acceptance
from texts import DECLINED_TEXT, RETURNING_USER_TEXT, TNC_TEXT, WHY_MM_HELPER_TEXT
from ui import send_screen

TNC_ACCEPT = "TNC_ACCEPT"
TNC_DECLINE = "TNC_DECLINE"


def _tnc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Agree & Continue", callback_data=TNC_ACCEPT)],
            [InlineKeyboardButton("❌ Decline", callback_data=TNC_DECLINE)],
        ]
    )


def _initial_setup_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "🚀 Initial Setup",
                    web_app=WebAppInfo(url=get_setup_webapp_url()),
                )
            ]
        ],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    if has_initial_setup(user.id):
        await send_screen(
            context,
            chat.id,
            RETURNING_USER_TEXT,
            reply_markup=main_menu_keyboard(user.id),
            parse_mode="Markdown",
        )
        return

    if has_tnc_accepted(user.id):
        await send_screen(
            context,
            chat.id,
            WHY_MM_HELPER_TEXT,
            reply_markup=_initial_setup_keyboard(),
        )
        return

    await send_screen(
        context,
        chat.id,
        TNC_TEXT,
        reply_markup=_tnc_keyboard(),
    )


async def handle_tnc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.data == TNC_ACCEPT:
        context.user_data["tnc_accepted"] = True
        telegram_name = (update.effective_user.full_name or "").strip() if update.effective_user else ""
        save_tnc_acceptance(
            user_id=query.from_user.id,
            telegram_name=telegram_name or str(query.from_user.id),
            accepted=True,
            telegram_username=(query.from_user.username or "").strip(),
        )
        try:
            await query.message.delete()
        except Exception:
            pass
        await send_screen(
            context,
            query.message.chat_id,
            WHY_MM_HELPER_TEXT,
            reply_markup=_initial_setup_keyboard(),
        )
        return

    context.user_data["tnc_accepted"] = False
    telegram_name = (update.effective_user.full_name or "").strip() if update.effective_user else ""
    save_tnc_acceptance(
        user_id=query.from_user.id,
        telegram_name=telegram_name or str(query.from_user.id),
        accepted=False,
        telegram_username=(query.from_user.username or "").strip(),
    )
    try:
        await query.message.delete()
    except Exception:
        pass
    await send_screen(context, query.message.chat_id, DECLINED_TEXT)
