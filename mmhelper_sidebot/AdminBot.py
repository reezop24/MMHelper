"""Admin side bot scaffold with TnC gate and starter menu."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from texts import (
    ADMIN_PANEL_TEXT,
    BETA_RESET_DONE_TEXT,
    BETA_RESET_PROMPT_TEXT,
    DECLINED_TEXT,
    MAIN_MENU_TEXT,
    TNC_TEXT,
)

logger = logging.getLogger(__name__)

TNC_ACCEPT = "ADMIN_TNC_ACCEPT"
TNC_DECLINE = "ADMIN_TNC_DECLINE"
CB_BETA_RESET_CONFIRM = "ADMIN_BETA_RESET_CONFIRM"
CB_BETA_RESET_CANCEL = "ADMIN_BETA_RESET_CANCEL"

ADMIN_USER_IDS = {627116869}
STATE_PATH = Path(__file__).with_name("sidebot_state.json")

MENU_DAFTAR_NEXT_MEMBER = "Daftar NEXT member"
MENU_BELI_EVIDEO26 = "Beli NEXT eVideo26"
MENU_ALL_PRODUCT_PREVIEW = "All Product Preview"
MENU_ADMIN_PANEL = "Admin Panel"
MENU_BETA_RESET = "🧪 BETA RESET"
MENU_BACK_MAIN = "⬅️ Back to Main Menu"


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


def get_token() -> str:
    load_local_env()
    token = (os.getenv("SIDEBOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set SIDEBOT_TOKEN in mmhelper_sidebot/.env")
    return token


def get_register_next_webapp_url() -> str:
    url = (os.getenv("SIDEBOT_REGISTER_WEBAPP_URL") or "").strip()
    if not url.lower().startswith("https://"):
        return ""
    return url


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"users": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": {}}
    if not isinstance(data, dict):
        return {"users": {}}
    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    return data


def save_state(data: dict) -> None:
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def has_tnc_accepted(user_id: int) -> bool:
    state = load_state()
    users = state.get("users", {})
    user_obj = users.get(str(user_id), {})
    if not isinstance(user_obj, dict):
        return False
    return bool(user_obj.get("tnc_accepted"))


def mark_tnc_accepted(user_id: int, accepted: bool) -> None:
    state = load_state()
    users = state.setdefault("users", {})
    user_obj = users.setdefault(str(user_id), {})
    user_obj["tnc_accepted"] = bool(accepted)
    save_state(state)


def is_admin_user(user_id: int | None) -> bool:
    return user_id in ADMIN_USER_IDS


def reset_all_data() -> None:
    save_state({"users": {}})


def tnc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Setuju & Teruskan", callback_data=TNC_ACCEPT)],
            [InlineKeyboardButton("❌ Batal", callback_data=TNC_DECLINE)],
        ]
    )


def main_menu_keyboard(user_id: int | None) -> ReplyKeyboardMarkup:
    register_url = get_register_next_webapp_url()
    if register_url:
        register_button = KeyboardButton(MENU_DAFTAR_NEXT_MEMBER, web_app=WebAppInfo(url=register_url))
    else:
        register_button = KeyboardButton(MENU_DAFTAR_NEXT_MEMBER)

    rows = [
        [register_button],
        [KeyboardButton(MENU_BELI_EVIDEO26)],
        [KeyboardButton(MENU_ALL_PRODUCT_PREVIEW)],
    ]
    if is_admin_user(user_id):
        rows.append([KeyboardButton(MENU_ADMIN_PANEL)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(MENU_BETA_RESET)],
            [KeyboardButton(MENU_BACK_MAIN)],
        ],
        resize_keyboard=True,
    )


def beta_reset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirm BETA RESET", callback_data=CB_BETA_RESET_CONFIRM)],
            [InlineKeyboardButton("❌ Batal", callback_data=CB_BETA_RESET_CANCEL)],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    if has_tnc_accepted(user.id):
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
        return

    await message.reply_text("Sila baca dan setuju TnC dulu.", reply_markup=ReplyKeyboardRemove())
    await message.reply_text(TNC_TEXT, reply_markup=tnc_keyboard())


async def handle_tnc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    if query.data == TNC_ACCEPT:
        mark_tnc_accepted(query.from_user.id, True)
        await query.message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(query.from_user.id))
        return

    mark_tnc_accepted(query.from_user.id, False)
    await query.message.reply_text(DECLINED_TEXT)


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if not is_admin_user(query.from_user.id):
        await query.message.reply_text("❌ Akses ditolak.")
        return

    if query.data == CB_BETA_RESET_CANCEL:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text("BETA RESET dibatalkan.", reply_markup=admin_panel_keyboard())
        return

    if query.data == CB_BETA_RESET_CONFIRM:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        reset_all_data()
        await query.message.reply_text(BETA_RESET_DONE_TEXT)
        await query.message.reply_text("Sila baca dan setuju TnC dulu.", reply_markup=ReplyKeyboardRemove())
        await query.message.reply_text(TNC_TEXT, reply_markup=tnc_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.text:
        return

    text = message.text.strip()

    if not has_tnc_accepted(user.id):
        await message.reply_text(
            "❌ Akses menu dikunci sehingga anda setuju TnC. Tekan /start untuk teruskan.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if text == MENU_ADMIN_PANEL:
        if not is_admin_user(user.id):
            await message.reply_text("❌ Akses ditolak.", reply_markup=main_menu_keyboard(user.id))
            return
        await message.reply_text(ADMIN_PANEL_TEXT, reply_markup=admin_panel_keyboard())
        return

    if text == MENU_DAFTAR_NEXT_MEMBER:
        if get_register_next_webapp_url():
            await message.reply_text("Buka miniapp melalui butang web app pada menu.")
            return
        await message.reply_text("Miniapp URL belum diset. Isi SIDEBOT_REGISTER_WEBAPP_URL dalam .env dulu.")
        return

    if text == MENU_BETA_RESET:
        if not is_admin_user(user.id):
            await message.reply_text("❌ Akses ditolak.", reply_markup=main_menu_keyboard(user.id))
            return
        await message.reply_text("Mode pengesahan reset diaktifkan.", reply_markup=ReplyKeyboardRemove())
        await message.reply_text(BETA_RESET_PROMPT_TEXT, reply_markup=beta_reset_keyboard())
        return

    if text == MENU_BACK_MAIN:
        await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
        return


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not message.web_app_data or not user:
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.reply_text("❌ Data miniapp tak sah. Cuba buka semula.")
        return

    payload_type = str(payload.get("type") or "").strip()
    if payload_type == "sidebot_back_to_main_menu":
        if has_tnc_accepted(user.id):
            await message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user.id))
            return
        await message.reply_text("Sila baca dan setuju TnC dulu.", reply_markup=ReplyKeyboardRemove())
        await message.reply_text(TNC_TEXT, reply_markup=tnc_keyboard())
        return

    if payload_type == "next_member_request_type":
        choice = str(payload.get("choice") or "").strip()
        labels = {
            "new_registration_amarkets": "Pendaftaran baru AMarkets",
            "ib_transfer_existing_amarkets": "Penukaran IB (Pelanggan sedia ada AMarkets)",
            "client_under_ib_reezo": "Client AMarkets under IB Reezo",
        }
        selected = labels.get(choice) or "Pilihan tidak dikenali"
        await message.reply_text(
            f"✅ Pilihan diterima: {selected}\n\nFlow seterusnya akan kita sambung dalam step berikutnya.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    await message.reply_text("ℹ️ Miniapp demo diterima.", reply_markup=main_menu_keyboard(user.id))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    app = ApplicationBuilder().token(get_token()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_tnc_callback, pattern=f"^({TNC_ACCEPT}|{TNC_DECLINE})$"))
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=f"^({CB_BETA_RESET_CONFIRM}|{CB_BETA_RESET_CANCEL})$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
