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
    SUBMENU_ACCOUNT_BUTTON_TABUNG,
    SUBMENU_MM_BUTTON_BACK_MAIN,
    SUBMENU_MM_BUTTON_CORRECTION,
    SUBMENU_MM_BUTTON_SYSTEM_INFO,
    SUBMENU_PROJECT_BUTTON_ACHIEVEMENT,
    SUBMENU_PROJECT_BUTTON_MISSION,
    SUBMENU_PROJECT_BUTTON_MISSION_LOCKED,
    SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL,
    SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS,
    account_activity_keyboard,
    main_menu_keyboard,
    mm_helper_setting_keyboard,
    project_grow_keyboard,
)
from settings import (
    get_deposit_activity_webapp_url,
    get_initial_capital_reset_webapp_url,
    get_project_grow_mission_webapp_url,
    get_set_new_goal_webapp_url,
    get_trading_activity_webapp_url,
    get_withdrawal_activity_webapp_url,
)
from storage import (
    can_open_project_grow_mission,
    can_reset_initial_capital,
    get_capital_usd,
    get_current_balance_usd,
    get_current_profit_usd,
    get_initial_setup_summary,
    get_monthly_performance_usd,
    get_project_grow_goal_summary,
    get_project_grow_mission_state,
    get_project_grow_mission_status_text,
    get_tabung_start_date,
    get_tabung_balance_usd,
    get_total_balance_usd,
    get_weekly_performance_usd,
    reset_all_data,
)
from texts import (
    ACCOUNT_ACTIVITY_OPENED_TEXT,
    ACHIEVEMENT_OPENED_TEXT,
    CORRECTION_OPENED_TEXT,
    EXTRA_OPENED_TEXT,
    MAIN_MENU_OPENED_TEXT,
    MISSION_OPENED_TEXT,
    MM_HELPER_SETTING_OPENED_TEXT,
    PROJECT_GROW_OPENED_TEXT,
    RISK_CALCULATOR_OPENED_TEXT,
    SET_NEW_GOAL_OPENED_TEXT,
    STATISTIC_OPENED_TEXT,
    SYSTEM_INFO_OPENED_TEXT,
    TABUNG_OPENED_TEXT,
    TABUNG_PROGRESS_OPENED_TEXT,
)
from ui import clear_last_screen, send_screen
from welcome import start


def _build_mm_setting_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    reset_url = get_initial_capital_reset_webapp_url(
        name=summary["name"],
        initial_capital=summary["initial_capital_usd"],
        current_balance=get_current_balance_usd(user_id),
        saved_date=summary["saved_date"],
        can_reset=can_reset_initial_capital(user_id),
    )
    return mm_helper_setting_keyboard(reset_url)


def _build_account_activity_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    current_balance = get_current_balance_usd(user_id)
    current_profit = get_current_profit_usd(user_id)
    total_balance = get_total_balance_usd(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    capital = get_capital_usd(user_id)
    weekly_performance = get_weekly_performance_usd(user_id)
    monthly_performance = get_monthly_performance_usd(user_id)

    common_kwargs = {
        "name": summary["name"],
        "initial_capital_usd": summary["initial_capital_usd"],
        "current_balance_usd": current_balance,
        "saved_date": summary["saved_date"],
        "current_profit_usd": current_profit,
        "total_balance_usd": total_balance,
        "tabung_balance_usd": tabung_balance,
        "capital_usd": capital,
        "weekly_performance_usd": weekly_performance,
        "monthly_performance_usd": monthly_performance,
    }

    deposit_url = get_deposit_activity_webapp_url(**common_kwargs)
    withdrawal_url = get_withdrawal_activity_webapp_url(**common_kwargs)
    trading_url = get_trading_activity_webapp_url(**common_kwargs)

    return account_activity_keyboard(
        deposit_activity_url=deposit_url,
        withdrawal_activity_url=withdrawal_url,
        trading_activity_url=trading_url,
    )


def _build_project_grow_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    goal_summary = get_project_grow_goal_summary(user_id)
    mission_state = get_project_grow_mission_state(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    current_balance = get_current_balance_usd(user_id)
    mission_status = get_project_grow_mission_status_text(user_id)
    tabung_start_date = get_tabung_start_date(user_id)
    grow_target_usd = max(float(goal_summary["target_balance_usd"]) - current_balance, 0.0)
    mission_url = get_project_grow_mission_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        capital_usd=get_capital_usd(user_id),
        saved_date=summary["saved_date"],
        target_balance_usd=goal_summary["target_balance_usd"],
        target_days=goal_summary["target_days"],
        target_label=goal_summary["target_label"],
        tabung_balance_usd=tabung_balance,
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        mission_active=mission_state["active"],
        mission_mode=mission_state["mode"],
        mission_started_date=mission_state["started_date"],
    )
    set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        capital_usd=get_capital_usd(user_id),
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        has_goal=goal_summary["target_balance_usd"] > 0,
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=grow_target_usd,
        target_label=goal_summary["target_label"],
    )
    return project_grow_keyboard(
        set_new_goal_url=set_new_goal_url,
        mission_url=mission_url,
        can_open_mission=can_open_project_grow_mission(user_id),
    )


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
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
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

    if text == SUBMENU_ACCOUNT_BUTTON_TABUNG:
        await send_screen(
            context,
            message.chat_id,
            TABUNG_OPENED_TEXT,
            reply_markup=_build_account_activity_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL:
        await send_screen(
            context,
            message.chat_id,
            SET_NEW_GOAL_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_MISSION:
        await send_screen(
            context,
            message.chat_id,
            MISSION_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_MISSION_LOCKED:
        await send_screen(
            context,
            message.chat_id,
            "Mission masih locked. Syarat: kena ada Set New Goal dan balance tabung minimum USD 10.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS:
        await send_screen(
            context,
            message.chat_id,
            TABUNG_PROGRESS_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_ACHIEVEMENT:
        await send_screen(
            context,
            message.chat_id,
            ACHIEVEMENT_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return
