"""Main menu UI for MM HELPER."""

from telegram import ReplyKeyboardMarkup

MAIN_MENU_ROWS = [
    ["MM Helper setting", "Risk Calculator"],
    ["Transaction", "Project Grow"],
    ["Statistic", "Extra"],
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(MAIN_MENU_ROWS, resize_keyboard=True)
