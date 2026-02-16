"""Main entry point for MM HELPER Telegram bot."""

import os
from pathlib import Path

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers import handle_text_actions
from setup_flow import handle_setup_webapp
from welcome import TNC_ACCEPT, TNC_DECLINE, handle_tnc_callback, start


def load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_bot_token() -> str:
    load_local_env()
    token = os.getenv("MMHELPER_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set MMHELPER_BOT_TOKEN (or BOT_TOKEN) before running the bot.")
    return token


def main() -> None:
    app = ApplicationBuilder().token(get_bot_token()).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_tnc_callback, pattern=f"^({TNC_ACCEPT}|{TNC_DECLINE})$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_setup_webapp))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_actions))

    app.run_polling()


if __name__ == "__main__":
    main()
