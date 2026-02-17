"""Text handlers for MM HELPER."""

import json

from telegram import Update
from telegram.ext import ContextTypes

from menu import (
    MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY,
    MAIN_MENU_BUTTON_ADMIN_PANEL,
    MAIN_MENU_BUTTON_EXTRA,
    MAIN_MENU_BUTTON_MM_SETTING,
    MAIN_MENU_BUTTON_PROJECT_GROW,
    MAIN_MENU_BUTTON_RISK,
    MAIN_MENU_BUTTON_STATISTIC,
    SUBMENU_ADMIN_BUTTON_BETA_RESET,
    SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING,
    SUBMENU_ADMIN_BUTTON_STOP_ALL_NOTIFICATION,
    SUBMENU_ACCOUNT_BUTTON_SUMMARY,
    SUBMENU_ACCOUNT_BUTTON_TABUNG,
    SUBMENU_MM_BUTTON_BACK_MAIN,
    SUBMENU_MM_BUTTON_CORRECTION,
    SUBMENU_MM_BUTTON_SYSTEM_INFO,
    SUBMENU_PROJECT_BUTTON_ACHIEVEMENT,
    SUBMENU_PROJECT_BUTTON_MISSION,
    SUBMENU_PROJECT_BUTTON_MISSION_LOCKED,
    SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL,
    SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS,
    SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED,
    SUBMENU_STAT_BUTTON_MONTHLY_REPORTS,
    SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY,
    SUBMENU_STAT_BUTTON_WEEKLY_REPORTS,
    admin_panel_keyboard,
    account_activity_keyboard,
    is_admin_user,
    main_menu_keyboard,
    mm_helper_setting_keyboard,
    project_grow_keyboard,
    records_reports_keyboard,
)
from settings import (
    get_balance_adjustment_webapp_url,
    get_deposit_activity_webapp_url,
    get_initial_capital_reset_webapp_url,
    get_notification_setting_webapp_url,
    get_project_grow_mission_webapp_url,
    get_set_new_goal_webapp_url,
    get_tabung_update_webapp_url,
    get_tabung_progress_webapp_url,
    get_transaction_history_webapp_url,
    get_trading_activity_webapp_url,
    get_withdrawal_activity_webapp_url,
    get_user_log_webapp_url,
    get_system_info_webapp_url,
)
from storage import (
    get_balance_adjustment_rules,
    can_open_project_grow_mission,
    get_current_balance_usd,
    get_current_profit_usd,
    get_initial_setup_summary,
    get_mission_progress_summary,
    get_monthly_performance_usd,
    get_monthly_profit_loss_usd,
    get_project_grow_goal_summary,
    get_project_grow_mission_state,
    get_project_grow_mission_status_text,
    get_tabung_start_date,
    get_tabung_progress_summary,
    get_tabung_update_state,
    get_transaction_history_records,
    get_tabung_balance_usd,
    get_total_balance_usd,
    get_weekly_performance_usd,
    get_weekly_profit_loss_usd,
    has_tabung_save_today,
    has_reached_daily_target_today,
    has_project_grow_goal,
    has_initial_setup,
    is_project_grow_goal_reached,
    list_registered_user_logs,
    reset_all_data,
    stop_all_notification_settings,
)
from texts import (
    ACCOUNT_ACTIVITY_OPENED_TEXT,
    ACHIEVEMENT_OPENED_TEXT,
    ADMIN_PANEL_OPENED_TEXT,
    CORRECTION_OPENED_TEXT,
    EXTRA_OPENED_TEXT,
    MAIN_MENU_OPENED_TEXT,
    MISSION_OPENED_TEXT,
    MM_HELPER_SETTING_OPENED_TEXT,
    NOTIFICATION_SETTING_OPENED_TEXT,
    PROJECT_GROW_OPENED_TEXT,
    RISK_CALCULATOR_OPENED_TEXT,
    SET_NEW_GOAL_OPENED_TEXT,
    STATISTIC_OPENED_TEXT,
    SYSTEM_INFO_OPENED_TEXT,
    TABUNG_OPENED_TEXT,
    TABUNG_PROGRESS_OPENED_TEXT,
    TRANSACTION_HISTORY_OPENED_TEXT,
    WEEKLY_REPORTS_OPENED_TEXT,
    MONTHLY_REPORTS_OPENED_TEXT,
)
from ui import clear_last_screen, send_screen
from welcome import start


def _build_mm_setting_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    rules = get_balance_adjustment_rules(user_id)
    reset_url = get_initial_capital_reset_webapp_url(
        name=summary["name"],
        initial_capital=summary["initial_capital_usd"],
        current_balance=get_current_balance_usd(user_id),
        saved_date=summary["saved_date"],
        can_reset=True,
    )
    balance_adjustment_url = get_balance_adjustment_webapp_url(
        name=summary["name"],
        current_balance=get_current_balance_usd(user_id),
        saved_date=summary["saved_date"],
        can_adjust=rules["can_adjust"],
        used_this_month=rules["used_this_month"],
        window_open=rules["window_open"],
        window_label=rules["window_label"],
    )
    system_info_url = get_system_info_webapp_url()
    return mm_helper_setting_keyboard(reset_url, balance_adjustment_url, system_info_url)


def _build_admin_panel_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    notification_url = get_notification_setting_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
    )
    user_logs_json = json.dumps(list_registered_user_logs(), ensure_ascii=False, separators=(",", ":"))
    user_log_url = get_user_log_webapp_url(user_logs_json)
    return admin_panel_keyboard(notification_url, user_log_url)


def _build_account_activity_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    current_balance = get_current_balance_usd(user_id)
    current_profit = get_current_profit_usd(user_id)
    total_balance = get_total_balance_usd(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    weekly_performance = get_weekly_performance_usd(user_id)
    monthly_performance = get_monthly_performance_usd(user_id)
    goal_summary = get_project_grow_goal_summary(user_id)
    tabung_update_state = get_tabung_update_state(user_id)
    tabung_start_date = get_tabung_start_date(user_id)
    total_grow_target = max(float(goal_summary["target_balance_usd"]) - float(goal_summary["current_balance_usd"]), 0.0)
    set_goal_grow_target = max(total_grow_target - tabung_balance, 0.0)
    daily_target_reached_today = has_reached_daily_target_today(user_id)
    tabung_saved_today = has_tabung_save_today(user_id)

    set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=get_project_grow_mission_status_text(user_id),
        has_goal=goal_summary["target_balance_usd"] > 0,
        goal_reached=is_project_grow_goal_reached(user_id),
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=set_goal_grow_target,
        target_days=int(goal_summary["target_days"]),
        target_label=goal_summary["target_label"],
        tabung_update_url="",
        goal_baseline_balance_usd=float(goal_summary["current_balance_usd"]),
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=tabung_saved_today,
    )
    tabung_update_url = get_tabung_update_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        current_balance_usd=current_balance,
        tabung_balance_usd=tabung_balance,
        total_balance_usd=total_balance,
        target_balance_usd=float(goal_summary["target_balance_usd"]),
        goal_reached=bool(tabung_update_state["goal_reached"]),
        emergency_left=int(tabung_update_state["emergency_left"]),
        set_new_goal_url=set_new_goal_url,
    )
    set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=get_project_grow_mission_status_text(user_id),
        has_goal=goal_summary["target_balance_usd"] > 0,
        goal_reached=is_project_grow_goal_reached(user_id),
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=set_goal_grow_target,
        target_days=int(goal_summary["target_days"]),
        target_label=goal_summary["target_label"],
        tabung_update_url=tabung_update_url,
        goal_baseline_balance_usd=float(goal_summary["current_balance_usd"]),
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=tabung_saved_today,
    )
    tabung_update_url = get_tabung_update_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        current_balance_usd=current_balance,
        tabung_balance_usd=tabung_balance,
        total_balance_usd=total_balance,
        target_balance_usd=float(goal_summary["target_balance_usd"]),
        goal_reached=bool(tabung_update_state["goal_reached"]),
        emergency_left=int(tabung_update_state["emergency_left"]),
        set_new_goal_url=set_new_goal_url,
    )

    common_kwargs = {
        "name": summary["name"],
        "initial_capital_usd": summary["initial_capital_usd"],
        "current_balance_usd": current_balance,
        "saved_date": summary["saved_date"],
        "tabung_start_date": tabung_start_date,
        "current_profit_usd": current_profit,
        "total_balance_usd": total_balance,
        "tabung_balance_usd": tabung_balance,
        "weekly_performance_usd": weekly_performance,
        "monthly_performance_usd": monthly_performance,
        "target_balance_usd": float(goal_summary["target_balance_usd"]),
        "grow_target_usd": set_goal_grow_target,
        "target_days": int(goal_summary["target_days"]),
        "goal_reached": is_project_grow_goal_reached(user_id),
        "goal_baseline_balance_usd": float(goal_summary["current_balance_usd"]),
        "tabung_update_url": tabung_update_url,
        "daily_target_reached_today": daily_target_reached_today,
        "has_tabung_save_today": tabung_saved_today,
    }

    deposit_url = get_deposit_activity_webapp_url(**common_kwargs)
    withdrawal_url = get_withdrawal_activity_webapp_url(**common_kwargs)
    trading_url = get_trading_activity_webapp_url(**common_kwargs)

    return account_activity_keyboard(
        deposit_activity_url=deposit_url,
        withdrawal_activity_url=withdrawal_url,
        trading_activity_url=trading_url,
        tabung_update_url=tabung_update_url,
    )


def _build_account_summary_text(user_id: int) -> str:
    summary = get_initial_setup_summary(user_id)
    current_balance = get_current_balance_usd(user_id)
    current_profit = get_current_profit_usd(user_id)
    total_balance = get_total_balance_usd(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    weekly = get_weekly_profit_loss_usd(user_id)
    monthly = get_monthly_profit_loss_usd(user_id)
    tabung_start = get_tabung_start_date(user_id)

    goal = get_project_grow_goal_summary(user_id)
    mission_state = get_project_grow_mission_state(user_id)
    mission = get_mission_progress_summary(user_id)
    target_capital = float(goal.get("target_balance_usd") or 0)
    grow_target_total = max(target_capital - float(goal.get("current_balance_usd") or 0), 0.0)
    grow_target = max(grow_target_total - tabung_balance, 0.0)
    target_label = goal.get("target_label") or "-"

    def _usd(v: float) -> str:
        return f"{v:.2f}"

    lines = [
        "*Account Summary*",
        "",
        "*Account*",
        f"- Name: {summary['name']}",
        f"- Tarikh mula akaun: {summary['saved_date']}",
        f"- Tarikh mula tabung: {tabung_start}",
        f"- Initial Balance: USD {_usd(summary['initial_capital_usd'])}",
        f"- Current Balance: USD {_usd(current_balance)}",
        f"- Current Profit: USD {_usd(current_profit)}",
        f"- Capital: USD {_usd(total_balance)}",
        f"- Tabung Balance: USD {_usd(tabung_balance)}",
        f"- Weekly P/L: USD {_usd(weekly)}",
        f"- Monthly P/L: USD {_usd(monthly)}",
        "",
        "*Project Grow*",
        f"- Mission: {'Active' if mission_state['active'] else 'Inactive'}",
    ]

    if target_capital > 0:
        lines.extend(
            [
                f"- Target Capital: USD {_usd(target_capital)}",
                f"- Grow Target: USD {_usd(grow_target)}",
                f"- Tempoh Target: {target_label}",
            ]
        )
    else:
        lines.append("- Target Capital: belum diset")

    if mission_state["active"]:
        lines.extend(
            [
                "",
                "*Mission Progress*",
                f"- Mission Mode: {mission['mode_level']}",
                f"- Mission Status: {mission['progress_count']}",
                mission["mission_1"],
                mission["mission_2"],
                mission["mission_3"],
                mission["mission_4"],
            ]
        )

    return "\n".join(lines)


def _build_records_reports_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    tx_history_url = get_transaction_history_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        records_7d=get_transaction_history_records(user_id, days=7, limit=100),
        records_30d=get_transaction_history_records(user_id, days=30, limit=100),
    )
    return records_reports_keyboard(tx_history_url)


def _build_project_grow_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    goal_summary = get_project_grow_goal_summary(user_id)
    mission_state = get_project_grow_mission_state(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    current_balance = get_current_balance_usd(user_id)
    mission_status = get_project_grow_mission_status_text(user_id)
    tabung_start_date = get_tabung_start_date(user_id)
    tabung_progress = get_tabung_progress_summary(user_id)
    grow_target_usd = tabung_progress["grow_target_usd"]
    total_balance = get_total_balance_usd(user_id)
    goal_reached = is_project_grow_goal_reached(user_id)
    tabung_state = get_tabung_update_state(user_id)
    daily_target_reached_today = has_reached_daily_target_today(user_id)
    tabung_saved_today = has_tabung_save_today(user_id)
    mission_url = get_project_grow_mission_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
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
    provisional_set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        has_goal=goal_summary["target_balance_usd"] > 0,
        goal_reached=goal_reached,
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=grow_target_usd,
        target_days=int(goal_summary["target_days"]),
        target_label=goal_summary["target_label"],
        tabung_update_url="",
        goal_baseline_balance_usd=float(goal_summary["current_balance_usd"]),
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=tabung_saved_today,
    )
    tabung_update_url = get_tabung_update_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        current_balance_usd=current_balance,
        tabung_balance_usd=tabung_balance,
        total_balance_usd=total_balance,
        target_balance_usd=float(goal_summary["target_balance_usd"]),
        goal_reached=goal_reached,
        emergency_left=int(tabung_state["emergency_left"]),
        set_new_goal_url=provisional_set_new_goal_url,
    )
    set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        has_goal=goal_summary["target_balance_usd"] > 0,
        goal_reached=goal_reached,
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=grow_target_usd,
        target_days=int(goal_summary["target_days"]),
        target_label=goal_summary["target_label"],
        tabung_update_url=tabung_update_url,
        goal_baseline_balance_usd=float(goal_summary["current_balance_usd"]),
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=tabung_saved_today,
    )
    tabung_progress_url = get_tabung_progress_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        tabung_balance_usd=tabung_progress["tabung_balance_usd"],
        grow_target_usd=tabung_progress["grow_target_usd"],
        days_left=tabung_progress["days_left"],
        days_left_label=tabung_progress["days_left_label"],
        grow_progress_pct=tabung_progress["grow_progress_pct"],
        weekly_grow_usd=tabung_progress["weekly_grow_usd"],
        monthly_grow_usd=tabung_progress["monthly_grow_usd"],
    )
    return project_grow_keyboard(
        set_new_goal_url=set_new_goal_url,
        mission_url=mission_url,
        can_open_mission=can_open_project_grow_mission(user_id),
        tabung_progress_url=tabung_progress_url,
        can_open_tabung_progress=has_project_grow_goal(user_id),
    )


async def handle_text_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not message.text or not user:
        return

    text = message.text.strip()

    if not has_initial_setup(user.id):
        await start(update, context)
        return

    if text == MAIN_MENU_BUTTON_ADMIN_PANEL:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        await send_screen(
            context,
            message.chat_id,
            ADMIN_PANEL_OPENED_TEXT,
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ADMIN_BUTTON_BETA_RESET:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        reset_all_data()
        await clear_last_screen(context, message.chat_id)
        context.user_data.clear()
        await start(update, context)
        return

    if text == SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        await send_screen(
            context,
            message.chat_id,
            NOTIFICATION_SETTING_OPENED_TEXT,
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ADMIN_BUTTON_STOP_ALL_NOTIFICATION:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        ok = stop_all_notification_settings(user.id)
        if not ok:
            await send_screen(
                context,
                message.chat_id,
                "❌ Gagal stop notification. Cuba lagi.",
                reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            )
            return

        await send_screen(
            context,
            message.chat_id,
            "✅ Semua notification dah dihentikan. User takkan terima mesej lagi sehingga admin set notification baru.",
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        )
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
            reply_markup=main_menu_keyboard(user.id),
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
            reply_markup=_build_records_reports_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_EXTRA:
        await send_screen(
            context,
            message.chat_id,
            EXTRA_OPENED_TEXT,
            reply_markup=main_menu_keyboard(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_MM_BUTTON_BACK_MAIN:
        await send_screen(
            context,
            message.chat_id,
            MAIN_MENU_OPENED_TEXT,
            reply_markup=main_menu_keyboard(user.id),
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

    if text == SUBMENU_ACCOUNT_BUTTON_SUMMARY:
        await send_screen(
            context,
            message.chat_id,
            _build_account_summary_text(user.id),
            reply_markup=_build_account_activity_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY:
        await send_screen(
            context,
            message.chat_id,
            TRANSACTION_HISTORY_OPENED_TEXT,
            reply_markup=_build_records_reports_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_STAT_BUTTON_WEEKLY_REPORTS:
        await send_screen(
            context,
            message.chat_id,
            WEEKLY_REPORTS_OPENED_TEXT,
            reply_markup=_build_records_reports_keyboard_for_user(user.id),
        )
        return

    if text == SUBMENU_STAT_BUTTON_MONTHLY_REPORTS:
        await send_screen(
            context,
            message.chat_id,
            MONTHLY_REPORTS_OPENED_TEXT,
            reply_markup=_build_records_reports_keyboard_for_user(user.id),
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
            "Mission masih locked. Pastikan balance tabung minimum USD 20.",
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

    if text == SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED:
        await send_screen(
            context,
            message.chat_id,
            "Tabung Progress masih locked. Set New Goal dulu baru boleh buka.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
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
