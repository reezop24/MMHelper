"""Main menu UI for MM HELPER."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from settings import get_risk_calculator_webapp_url

ADMIN_USER_IDS = {627116869}

MAIN_MENU_BUTTON_MM_SETTING = "⚙️ MM Helper Setting"
MAIN_MENU_BUTTON_RISK = "🧮 Risk Calculator"
MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY = "📒 Account Activity"
MAIN_MENU_BUTTON_PROJECT_GROW = "📈 Project Grow"
MAIN_MENU_BUTTON_STATISTIC = "📊 Records & Reports"
MAIN_MENU_BUTTON_EXTRA = "🧰 Extra"
MAIN_MENU_BUTTON_ADMIN_PANEL = "🛡️ Admin Panel"

SUBMENU_MM_BUTTON_INITIAL_CAPITAL_RESET = "💸 Initial Capital Reset"
SUBMENU_MM_BUTTON_CORRECTION = "⚖️ Balance Adjustment"
SUBMENU_MM_BUTTON_SYSTEM_INFO = "ℹ️ System Info"
SUBMENU_MM_BUTTON_BACK_MAIN = "⬅️ Back to Main Menu"

SUBMENU_ACCOUNT_BUTTON_DEPOSIT_ACTIVITY = "💵 Update Deposit Activitiy"
SUBMENU_ACCOUNT_BUTTON_WITHDRAWAL_ACTIVITY = "💸 Update Withdrawal Activity"
SUBMENU_ACCOUNT_BUTTON_TRADING_ACTIVITY = "📉 Update Trading Activity"
SUBMENU_ACCOUNT_BUTTON_TABUNG = "🏦 Update Tabung"
SUBMENU_ACCOUNT_BUTTON_SUMMARY = "🧾 Account Summary"

SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL = "🎯 Set New Goal"
SUBMENU_PROJECT_BUTTON_MISSION = "🧭 Mission"
SUBMENU_PROJECT_BUTTON_MISSION_LOCKED = "🔒 Mission"
SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS = "🏦 Tabung Progress"
SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED = "🔒 Tabung Progress"
SUBMENU_PROJECT_BUTTON_ACHIEVEMENT = "🏆 Achievement"

SUBMENU_ADMIN_BUTTON_BETA_RESET = "🧪 BETA RESET"
SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING = "🔔 Notification Setting"

SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY = "🧾 Transaction History"
SUBMENU_STAT_BUTTON_WEEKLY_REPORTS = "📆 Weekly Reports"
SUBMENU_STAT_BUTTON_MONTHLY_REPORTS = "🗓️ Monthly Reports"

BASE_MAIN_MENU_ROWS = [
    [MAIN_MENU_BUTTON_MM_SETTING, MAIN_MENU_BUTTON_RISK],
    [MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY, MAIN_MENU_BUTTON_PROJECT_GROW],
    [MAIN_MENU_BUTTON_STATISTIC, MAIN_MENU_BUTTON_EXTRA],
]


def is_admin_user(user_id: int | None) -> bool:
    return user_id in ADMIN_USER_IDS


def main_menu_keyboard(user_id: int | None = None) -> ReplyKeyboardMarkup:
    rows = [
        [
            MAIN_MENU_BUTTON_MM_SETTING,
            KeyboardButton(
                MAIN_MENU_BUTTON_RISK,
                web_app=WebAppInfo(url=get_risk_calculator_webapp_url()),
            ),
        ],
        [MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY, MAIN_MENU_BUTTON_PROJECT_GROW],
        [MAIN_MENU_BUTTON_STATISTIC, MAIN_MENU_BUTTON_EXTRA],
    ]
    if is_admin_user(user_id):
        rows.append([MAIN_MENU_BUTTON_ADMIN_PANEL])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def mm_helper_setting_keyboard(initial_capital_reset_url: str, balance_adjustment_url: str) -> ReplyKeyboardMarkup:
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
            SUBMENU_MM_BUTTON_SYSTEM_INFO,
        ],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def account_activity_keyboard(
    deposit_activity_url: str,
    withdrawal_activity_url: str,
    trading_activity_url: str,
    tabung_update_url: str,
) -> ReplyKeyboardMarkup:
    rows = [
        [SUBMENU_ACCOUNT_BUTTON_SUMMARY],
        [
            KeyboardButton(
                SUBMENU_ACCOUNT_BUTTON_TRADING_ACTIVITY,
                web_app=WebAppInfo(url=trading_activity_url),
            )
        ],
        [
            KeyboardButton(
                SUBMENU_ACCOUNT_BUTTON_DEPOSIT_ACTIVITY,
                web_app=WebAppInfo(url=deposit_activity_url),
            )
        ],
        [
            KeyboardButton(
                SUBMENU_ACCOUNT_BUTTON_WITHDRAWAL_ACTIVITY,
                web_app=WebAppInfo(url=withdrawal_activity_url),
            )
        ],
        [KeyboardButton(SUBMENU_ACCOUNT_BUTTON_TABUNG, web_app=WebAppInfo(url=tabung_update_url))],
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


def admin_panel_keyboard(notification_setting_url: str) -> ReplyKeyboardMarkup:
    rows = [
        [SUBMENU_ADMIN_BUTTON_BETA_RESET],
        [
            KeyboardButton(
                SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING,
                web_app=WebAppInfo(url=notification_setting_url),
            )
        ],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def records_reports_keyboard(transaction_history_url: str) -> ReplyKeyboardMarkup:
    rows = [
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
