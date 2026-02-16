"""Main menu UI for MM HELPER."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

MAIN_MENU_BUTTON_MM_SETTING = "⚙️ MM Helper setting"
MAIN_MENU_BUTTON_RISK = "🧮 Risk Calculator"
MAIN_MENU_BUTTON_TRANSACTION = "💳 Transaction"
MAIN_MENU_BUTTON_PROJECT_GROW = "📈 Project Grow"
MAIN_MENU_BUTTON_STATISTIC = "📊 Statistic"
MAIN_MENU_BUTTON_EXTRA = "🧰 Extra"
MAIN_MENU_BUTTON_BETA_RESET = "🧪 BETA RESET"

SUBMENU_MM_BUTTON_INITIAL_CAPITAL_RESET = "💸 Initial Capital Reset"
SUBMENU_MM_BUTTON_CORRECTION = "🛠️ Correction"
SUBMENU_MM_BUTTON_SYSTEM_INFO = "ℹ️ System Info"
SUBMENU_MM_BUTTON_BACK_MAIN = "⬅️ Back to Main Menu"

MAIN_MENU_ROWS = [
    [MAIN_MENU_BUTTON_MM_SETTING, MAIN_MENU_BUTTON_RISK],
    [MAIN_MENU_BUTTON_TRANSACTION, MAIN_MENU_BUTTON_PROJECT_GROW],
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
