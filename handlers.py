"""Text handlers for MM HELPER."""

from telegram import Update
from telegram.ext import ContextTypes

from menu import (
    MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY,
    MAIN_MENU_BUTTON_BETA_RESET,
    MAIN_MENU_BUTTON_EXTRA,
    MAIN_MENU_BUTTON_MM_SETTING,
    MAIN_MENU_BUTTON_PROJECT_GROW,
    MAIN_MENU_BUTTON_RISK,
    MAIN_MENU_BUTTON_STATISTIC,
    SUBMENU_ACCOUNT_BUTTON_DEPOSIT_ACTIVITY,
    SUBMENU_ACCOUNT_BUTTON_TABUNG,
    SUBMENU_ACCOUNT_BUTTON_TRADING_ACTIVITY,
    SUBMENU_MM_BUTTON_BACK_MAIN,
    SUBMENU_MM_BUTTON_CORRECTION,
    SUBMENU_MM_BUTTON_SYSTEM_INFO,
    account_activity_keyboard,
    main_menu_keyboard,
    mm_helper_setting_keyboard,
)
from settings import (
    get_initial_capital_reset_webapp_url,
    get_withdrawal_activity_webapp_url,
)
from storage import (
    can_reset_initial_capital,
    get_current_profit_usd,
    get_initial_setup_summary,
    reset_all_data,
)
from texts import (
    ACCOUNT_ACTIVITY_OPENED_TEXT,
    CORRECTION_OPENED_TEXT,
    DEPOSIT_ACTIVITY_OPENED_TEXT,
    EXTRA_OPENED_TEXT,
    MAIN_MENU_OPENED_TEXT,
    MM_HELPER_SETTING_OPENED_TEXT,
    PROJECT_GROW_OPENED_TEXT,
    RISK_CALCULATOR_OPENED_TEXT,
    STATISTIC_OPENED_TEXT,
    SYSTEM_INFO_OPENED_TEXT,
    TABUNG_OPENED_TEXT,
    TRADING_ACTIVITY_OPENED_TEXT,
)
from ui import clear_last_screen, send_screen
from welcome import start


def _build_mm_setting_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    reset_url = get_initial_capital_reset_webapp_url(
        name=summary["name"],
        initial_capital=summary["initial_capital_usd"],
        saved_date=summary["saved_date"],
        can_reset=can_reset_initial_capital(user_id),
    )
    return mm_helper_setting_keyboard(reset_url)


def _build_account_activity_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    withdrawal_url = get_withdrawal_activity_webapp_url(
        name=summary["name"],
        initial_capital_usd=summary["initial_capital_usd"],
        saved_date=summary["saved_date"],
        current_profit_usd=get_current_profit_usd(user_id),
    )
    return account_activity_keyboard(withdrawal_url)


async def handle_text_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not message.text or not user:
        return

    text = message.text.strip()

    if text == MAIN_MENU_BUTTON_BETA_RESET:
        reset_all_data()
        await clear_last_screen(context, message.chat_id)
        context.user_data.clear()
        await start(update, context)
        return

    if text == MAIN_MENU_BUTTON_MM_SETTING:
        await send_screen(
            context,
            message.chat_id,
            MM_HELPER_SETTING_OPENED_TEXT,
            reply_markup=_build_mm_setting_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY:
        await send_screen(
            context,
            message.chat_id,
            ACCOUNT_ACTIVITY_OPENED_TEXT,
            reply_markup=_build_account_activity_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_RISK:
        await send_screen(
            context,
            message.chat_id,
            RISK_CALCULATOR_OPENED_TEXT,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_PROJECT_GROW:
        await send_screen(
            context,
            message.chat_id,
            PROJECT_GROW_OPENED_TEXT,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_STATISTIC:
        await send_screen(
            context,
            message.chat_id,
            STATISTIC_OPENED_TEXT,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_EXTRA:
        await send_screen(
            context,
            message.chat_id,
            EXTRA_OPENED_TEXT,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_MM_BUTTON_BACK_MAIN:
        await send_screen(
            context,
            message.chat_id,
            MAIN_MENU_OPENED_TEXT,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_MM_BUTTON_CORRECTION:
        await send_screen(
            context,
            message.chat_id,
            CORRECTION_OPENED_TEXT,
            reply_markup=_build_mm_setting_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_MM_BUTTON_SYSTEM_INFO:
        await send_screen(
            context,
            message.chat_id,
            SYSTEM_INFO_OPENED_TEXT,
            reply_markup=_build_mm_setting_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ACCOUNT_BUTTON_DEPOSIT_ACTIVITY:
        await send_screen(
            context,
            message.chat_id,
            DEPOSIT_ACTIVITY_OPENED_TEXT,
            reply_markup=_build_account_activity_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ACCOUNT_BUTTON_TRADING_ACTIVITY:
        await send_screen(
            context,
            message.chat_id,
            TRADING_ACTIVITY_OPENED_TEXT,
            reply_markup=_build_account_activity_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ACCOUNT_BUTTON_TABUNG:
        await send_screen(
            context,
            message.chat_id,
            TABUNG_OPENED_TEXT,
            reply_markup=_build_account_activity_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return
