"""Main menu UI for MM HELPER."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from settings import get_activity_hub_webapp_url, get_risk_calculator_webapp_url

ADMIN_USER_IDS = {627116869}

MAIN_MENU_BUTTON_MM_SETTING = "⚙️ MM Helper Setting"
MAIN_MENU_BUTTON_RISK = "🧮 Risk Calculator"
MAIN_MENU_BUTTON_PROJECT_GROW = "📈 Project Grow"
MAIN_MENU_BUTTON_STATISTIC = "📊 Records & Reports"
MAIN_MENU_BUTTON_EXTRA = "🧰 Extra"
MAIN_MENU_BUTTON_ADMIN_PANEL = "🛡️ Admin Panel"
MAIN_MENU_BUTTON_ACTIVITY_HUB = "🧭 Activity Hub"

SUBMENU_MM_BUTTON_INITIAL_CAPITAL_RESET = "♻️ Reset All Setting"
SUBMENU_MM_BUTTON_CORRECTION = "⚖️ Balance Adjustment"
SUBMENU_MM_BUTTON_SYSTEM_INFO = "ℹ️ System Info"
SUBMENU_MM_BUTTON_BACK_MAIN = "⬅️ Back to Main Menu"

SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL = "🎯 Set New Goal"
SUBMENU_PROJECT_BUTTON_MISSION = "🧭 Mission"
SUBMENU_PROJECT_BUTTON_MISSION_LOCKED = "🔒 Mission"
SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS = "🏦 Tabung Progress"
SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED = "🔒 Tabung Progress"
SUBMENU_PROJECT_BUTTON_ACHIEVEMENT = "🏆 Achievement"

SUBMENU_ADMIN_BUTTON_BETA_RESET = "🧪 BETA RESET"
SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING = "🔔 Notification Setting"
SUBMENU_ADMIN_BUTTON_DATE_OVERRIDE = "🗓️ Date Override"
SUBMENU_ADMIN_BUTTON_USER_LOG = "👥 User Log"
SUBMENU_ADMIN_BUTTON_STOP_ALL_NOTIFICATION = "⛔ Stop All Notification"

SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY = "🧾 Transaction History"
SUBMENU_STAT_BUTTON_ACCOUNT_SUMMARY = "🧾 Account Summary"
SUBMENU_STAT_BUTTON_WEEKLY_REPORTS = "📆 Weekly Reports"
SUBMENU_STAT_BUTTON_MONTHLY_REPORTS = "🗓️ Monthly Reports"

def is_admin_user(user_id: int | None) -> bool:
    return user_id in ADMIN_USER_IDS


def main_menu_keyboard(user_id: int | None = None) -> ReplyKeyboardMarkup:
    risk_url = get_risk_calculator_webapp_url()
    activity_hub_url = ""
    if user_id is not None:
        try:
            from storage import (
                get_current_balance_usd,
                get_initial_setup_summary,
                get_monthly_performance_usd,
                get_project_grow_goal_summary,
                get_tabung_balance_usd,
                get_tabung_update_state,
                get_weekly_performance_usd,
                is_project_grow_goal_reached,
            )

            current_balance = get_current_balance_usd(user_id)
            goal = get_project_grow_goal_summary(user_id)
            summary = get_initial_setup_summary(user_id)
            target_days = int(goal.get("target_days") or 0)
            target_balance = float(goal.get("target_balance_usd") or 0.0)
            baseline_balance = float(goal.get("current_balance_usd") or 0.0)
            tabung_balance = float(get_tabung_balance_usd(user_id) or 0.0)
            total_grow_target = max(target_balance - baseline_balance, 0.0)
            remaining_grow_target = max(total_grow_target - tabung_balance, 0.0)
            risk_url = get_risk_calculator_webapp_url(
                current_balance_usd=current_balance,
                target_days=target_days,
                grow_target_usd=remaining_grow_target,
            )
            tabung_state = get_tabung_update_state(user_id)
            activity_hub_url = get_activity_hub_webapp_url(
                name=summary["name"],
                current_balance_usd=current_balance,
                saved_date=summary["saved_date"],
                tabung_balance_usd=tabung_balance,
                weekly_performance_usd=get_weekly_performance_usd(user_id),
                monthly_performance_usd=get_monthly_performance_usd(user_id),
                emergency_left=int(tabung_state.get("emergency_left") or 0),
                target_balance_usd=target_balance,
                grow_target_usd=remaining_grow_target,
                target_days=target_days,
                goal_reached=is_project_grow_goal_reached(user_id),
            )
        except Exception:
            risk_url = get_risk_calculator_webapp_url()
            activity_hub_url = ""

    activity_hub_button: KeyboardButton | str
    if activity_hub_url:
        activity_hub_button = KeyboardButton(
            MAIN_MENU_BUTTON_ACTIVITY_HUB,
            web_app=WebAppInfo(url=activity_hub_url),
        )
    else:
        activity_hub_button = MAIN_MENU_BUTTON_ACTIVITY_HUB

    rows = [
        [
            activity_hub_button,
            MAIN_MENU_BUTTON_PROJECT_GROW,
        ],
        [
            MAIN_MENU_BUTTON_STATISTIC,
            KeyboardButton(
                MAIN_MENU_BUTTON_RISK,
                web_app=WebAppInfo(url=risk_url),
            ),
        ],
        [MAIN_MENU_BUTTON_EXTRA, MAIN_MENU_BUTTON_MM_SETTING],
    ]
    if is_admin_user(user_id):
        rows.append([MAIN_MENU_BUTTON_ADMIN_PANEL])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def mm_helper_setting_keyboard(
    initial_capital_reset_url: str,
    balance_adjustment_url: str,
    system_info_url: str,
) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                SUBMENU_MM_BUTTON_INITIAL_CAPITAL_RESET,
                web_app=WebAppInfo(url=initial_capital_reset_url),
            )
        ],
        [
            KeyboardButton(
                SUBMENU_MM_BUTTON_CORRECTION,
                web_app=WebAppInfo(url=balance_adjustment_url),
            ),
            KeyboardButton(
                SUBMENU_MM_BUTTON_SYSTEM_INFO,
                web_app=WebAppInfo(url=system_info_url),
            ),
        ],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def project_grow_keyboard(
    set_new_goal_url: str,
    mission_url: str,
    can_open_mission: bool,
    tabung_progress_url: str,
    can_open_tabung_progress: bool,
) -> ReplyKeyboardMarkup:
    mission_button: KeyboardButton | str
    if can_open_mission:
        mission_button = KeyboardButton(
            SUBMENU_PROJECT_BUTTON_MISSION,
            web_app=WebAppInfo(url=mission_url),
        )
    else:
        mission_button = SUBMENU_PROJECT_BUTTON_MISSION_LOCKED

    tabung_progress_button: KeyboardButton | str
    if can_open_tabung_progress:
        tabung_progress_button = KeyboardButton(
            SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS,
            web_app=WebAppInfo(url=tabung_progress_url),
        )
    else:
        tabung_progress_button = SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED

    rows = [
        [
            KeyboardButton(
                SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL,
                web_app=WebAppInfo(url=set_new_goal_url),
            ),
            mission_button,
        ],
        [tabung_progress_button, SUBMENU_PROJECT_BUTTON_ACHIEVEMENT],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard(notification_setting_url: str, date_override_url: str, user_log_url: str) -> ReplyKeyboardMarkup:
    rows = [
        [SUBMENU_ADMIN_BUTTON_BETA_RESET],
        [SUBMENU_ADMIN_BUTTON_STOP_ALL_NOTIFICATION],
        [
            KeyboardButton(
                SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING,
                web_app=WebAppInfo(url=notification_setting_url),
            )
        ],
        [
            KeyboardButton(
                SUBMENU_ADMIN_BUTTON_DATE_OVERRIDE,
                web_app=WebAppInfo(url=date_override_url),
            )
        ],
        [
            KeyboardButton(
                SUBMENU_ADMIN_BUTTON_USER_LOG,
                web_app=WebAppInfo(url=user_log_url),
            )
        ],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def records_reports_keyboard(account_summary_url: str, transaction_history_url: str) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                SUBMENU_STAT_BUTTON_ACCOUNT_SUMMARY,
                web_app=WebAppInfo(url=account_summary_url),
            )
        ],
        [
            KeyboardButton(
                SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY,
                web_app=WebAppInfo(url=transaction_history_url),
            )
        ],
        [SUBMENU_STAT_BUTTON_WEEKLY_REPORTS],
        [SUBMENU_STAT_BUTTON_MONTHLY_REPORTS],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
