"""Main menu UI for MM HELPER."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

MAIN_MENU_BUTTON_MM_SETTING = "⚙️ MM Helper Setting"
MAIN_MENU_BUTTON_RISK = "🧮 Risk Calculator"
MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY = "📒 Account Activity"
MAIN_MENU_BUTTON_PROJECT_GROW = "📈 Project Grow"
MAIN_MENU_BUTTON_STATISTIC = "📊 Statistic"
MAIN_MENU_BUTTON_EXTRA = "🧰 Extra"
MAIN_MENU_BUTTON_BETA_RESET = "🧪 BETA RESET"

SUBMENU_MM_BUTTON_INITIAL_CAPITAL_RESET = "💸 Initial Capital Reset"
SUBMENU_MM_BUTTON_CORRECTION = "🛠️ Correction"
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
SUBMENU_PROJECT_BUTTON_ACHIEVEMENT = "🏆 Achievement"

MAIN_MENU_ROWS = [
    [MAIN_MENU_BUTTON_MM_SETTING, MAIN_MENU_BUTTON_RISK],
    [MAIN_MENU_BUTTON_ACCOUNT_ACTIVITY, MAIN_MENU_BUTTON_PROJECT_GROW],
    [MAIN_MENU_BUTTON_STATISTIC, MAIN_MENU_BUTTON_EXTRA],
    [MAIN_MENU_BUTTON_BETA_RESET],
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(MAIN_MENU_ROWS, resize_keyboard=True)


def mm_helper_setting_keyboard(initial_capital_reset_url: str) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                SUBMENU_MM_BUTTON_INITIAL_CAPITAL_RESET,
                web_app=WebAppInfo(url=initial_capital_reset_url),
            )
        ],
        [SUBMENU_MM_BUTTON_CORRECTION, SUBMENU_MM_BUTTON_SYSTEM_INFO],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def account_activity_keyboard(
    deposit_activity_url: str,
    withdrawal_activity_url: str,
    trading_activity_url: str,
) -> ReplyKeyboardMarkup:
    rows = [
        [SUBMENU_ACCOUNT_BUTTON_SUMMARY],
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
        [
            KeyboardButton(
                SUBMENU_ACCOUNT_BUTTON_TRADING_ACTIVITY,
                web_app=WebAppInfo(url=trading_activity_url),
            )
        ],
        [SUBMENU_ACCOUNT_BUTTON_TABUNG],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def project_grow_keyboard(
    set_new_goal_url: str,
    mission_url: str,
    can_open_mission: bool,
) -> ReplyKeyboardMarkup:
    mission_button: KeyboardButton | str
    if can_open_mission:
        mission_button = KeyboardButton(
            SUBMENU_PROJECT_BUTTON_MISSION,
            web_app=WebAppInfo(url=mission_url),
        )
    else:
        mission_button = SUBMENU_PROJECT_BUTTON_MISSION_LOCKED

    rows = [
        [
            KeyboardButton(
                SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL,
                web_app=WebAppInfo(url=set_new_goal_url),
            ),
            mission_button,
        ],
        [SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS, SUBMENU_PROJECT_BUTTON_ACHIEVEMENT],
        [SUBMENU_MM_BUTTON_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
