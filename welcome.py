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
from settings import get_risk_calculator_webapp_url, get_setup_webapp_url
from storage import get_initial_setup_summary, has_initial_setup
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
        summary = get_initial_setup_summary(user.id)
        risk_url = get_risk_calculator_webapp_url(
            name=summary["name"],
            saved_date=summary["saved_date"],
        )
        await send_screen(
            context,
            chat.id,
            RETURNING_USER_TEXT,
            reply_markup=main_menu_keyboard(user.id, risk_calculator_url=risk_url),
            parse_mode="Markdown",
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
    try:
        await query.message.delete()
    except Exception:
        pass
    await send_screen(context, query.message.chat_id, DECLINED_TEXT)
