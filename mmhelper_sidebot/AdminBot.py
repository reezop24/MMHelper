"""Admin side bot scaffold with TnC gate and starter menu."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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
CB_VERIF_APPROVE = "VERIF_APPROVE"
CB_VERIF_PENDING = "VERIF_PENDING"
CB_VERIF_REJECT = "VERIF_REJECT"
CB_VERIF_REQUEST_DEPOSIT = "VERIF_REQUEST_DEPOSIT"
CB_VERIF_REQUEST_CHANGE_IB = "VERIF_REQUEST_CHANGE_IB"
CB_VERIF_REVOKE_VIP = "VERIF_REVOKE_VIP"
CB_USER_DEPOSIT_DONE = "USER_DEPOSIT_DONE"
CB_USER_DEPOSIT_CANCEL = "USER_DEPOSIT_CANCEL"
CB_USER_IB_DONE = "USER_IB_DONE"
CB_USER_IB_CANCEL = "USER_IB_CANCEL"

ADMIN_USER_IDS = {627116869}
STATE_PATH = Path(__file__).with_name("sidebot_state.json")
VIP_WHITELIST_PATH = Path(__file__).with_name("sidebot_vip_whitelist.json")

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


def get_admin_group_id() -> int | None:
    raw = (os.getenv("SIDEBOT_ADMIN_GROUP_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def get_amarkets_api_base_url() -> str:
    return (os.getenv("AMARKETS_API_BASE_URL") or "").strip().rstrip("/")


def get_amarkets_api_token() -> str:
    return (os.getenv("AMARKETS_API_TOKEN") or "").strip()


def amarkets_check_is_client(wallet_id: str) -> tuple[bool | None, str]:
    base_url = get_amarkets_api_base_url()
    token = get_amarkets_api_token()
    if not base_url or not token:
        return None, "AMarkets API belum dikonfigurasi"

    endpoint = f"{base_url}/partner/is_client/{quote(wallet_id)}"
    req = Request(
        endpoint,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="ignore").strip()
    except HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except URLError:
        return None, "Connection failed"
    except Exception:
        return None, "Unknown error"

    lowered = raw.lower()
    if lowered in {"true", "1", "yes"}:
        return True, "ok"
    if lowered in {"false", "0", "no"}:
        return False, "ok"

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, "Unexpected response"

    if isinstance(parsed, bool):
        return parsed, "ok"
    if isinstance(parsed, dict):
        for key in ("is_client", "result", "data", "value"):
            value = parsed.get(key)
            if isinstance(value, bool):
                return value, "ok"
            if isinstance(value, str) and value.lower() in {"true", "false"}:
                return value.lower() == "true", "ok"
    return None, "Unexpected response"


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


def load_vip_whitelist() -> dict:
    if not VIP_WHITELIST_PATH.exists():
        return {"vip1": {"users": {}}}
    try:
        data = json.loads(VIP_WHITELIST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"vip1": {"users": {}}}
    if not isinstance(data, dict):
        return {"vip1": {"users": {}}}
    vip1 = data.get("vip1")
    if not isinstance(vip1, dict):
        data["vip1"] = {"users": {}}
    users = data["vip1"].get("users")
    if not isinstance(users, dict):
        data["vip1"]["users"] = {}
    return data


def save_vip_whitelist(data: dict) -> None:
    VIP_WHITELIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_user_to_vip1(item: dict) -> None:
    data = load_vip_whitelist()
    vip_users = data.setdefault("vip1", {}).setdefault("users", {})
    user_id = str(item.get("user_id"))
    vip_users[user_id] = {
        "user_id": item.get("user_id"),
        "telegram_username": item.get("telegram_username") or "",
        "full_name": item.get("full_name") or "",
        "wallet_id": item.get("wallet_id") or "",
        "source_submission_id": item.get("submission_id"),
        "added_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    save_vip_whitelist(data)


def remove_user_from_vip1(user_id: int) -> bool:
    data = load_vip_whitelist()
    vip_users = data.setdefault("vip1", {}).setdefault("users", {})
    removed = vip_users.pop(str(user_id), None)
    save_vip_whitelist(data)
    return removed is not None


def get_required_deposit_amount(registration_flow: str) -> int:
    if registration_flow == "under_ib_reezo":
        return 50
    return 100


def is_valid_wallet_id(wallet_id: str) -> bool:
    return wallet_id.isdigit() and len(wallet_id) == 7


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


def store_verification_submission(
    user_id: int,
    telegram_username: str,
    wallet_id: str,
    has_deposit_100: bool,
    full_name: str,
    phone_number: str,
    registration_flow: str = "new_registration",
    ib_request_submitted: bool | None = None,
) -> dict:
    state = load_state()
    users = state.setdefault("users", {})
    user_obj = users.setdefault(str(user_id), {})
    submissions = state.setdefault("verification_submissions", {})
    if not isinstance(submissions, dict):
        submissions = {}
        state["verification_submissions"] = submissions

    submission_id = f"{user_id}-{int(datetime.now(timezone.utc).timestamp())}"

    deposit_required_usd = get_required_deposit_amount(registration_flow)

    payload = {
        "submission_id": submission_id,
        "user_id": user_id,
        "telegram_username": telegram_username or "",
        "wallet_id": wallet_id,
        "has_deposit_100": bool(has_deposit_100),
        "full_name": full_name,
        "phone_number": phone_number,
        "registration_flow": registration_flow,
        "ib_request_submitted": ib_request_submitted,
        "deposit_required_usd": deposit_required_usd,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "admin_group_message_id": None,
        "user_deposit_prompt_message_id": None,
        "user_ib_prompt_message_id": None,
    }

    user_obj["telegram_username"] = telegram_username or ""
    user_obj["latest_verification"] = payload
    history = user_obj.setdefault("verification_history", [])
    if not isinstance(history, list):
        history = []
        user_obj["verification_history"] = history
    history.append(payload)
    submissions[submission_id] = payload
    save_state(state)
    return payload


def verification_action_keyboard(submission_id: str, registration_flow: str) -> InlineKeyboardMarkup:
    second_row = [InlineKeyboardButton("💸 Request Deposit", callback_data=f"{CB_VERIF_REQUEST_DEPOSIT}:{submission_id}")]
    if registration_flow == "ib_transfer":
        second_row.append(InlineKeyboardButton("🔁 Request Change IB", callback_data=f"{CB_VERIF_REQUEST_CHANGE_IB}:{submission_id}"))
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"{CB_VERIF_APPROVE}:{submission_id}"),
                InlineKeyboardButton("⏳ Pending", callback_data=f"{CB_VERIF_PENDING}:{submission_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"{CB_VERIF_REJECT}:{submission_id}"),
            ],
            second_row,
        ]
    )


def approved_admin_keyboard(submission_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 Revoke User", callback_data=f"{CB_VERIF_REVOKE_VIP}:{submission_id}")],
        ]
    )


def user_deposit_keyboard(submission_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Deposit Selesai", callback_data=f"{CB_USER_DEPOSIT_DONE}:{submission_id}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"{CB_USER_DEPOSIT_CANCEL}:{submission_id}"),
            ]
        ]
    )


def user_ib_request_keyboard(submission_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Change IB Selesai", callback_data=f"{CB_USER_IB_DONE}:{submission_id}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"{CB_USER_IB_CANCEL}:{submission_id}"),
            ]
        ]
    )


def update_submission_status(submission_id: str, status: str, reviewer_id: int) -> dict | None:
    state = load_state()
    submissions = state.setdefault("verification_submissions", {})
    if not isinstance(submissions, dict):
        return None

    item = submissions.get(submission_id)
    if not isinstance(item, dict):
        return None

    item["status"] = status
    item["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    item["reviewed_by"] = reviewer_id

    user_id = item.get("user_id")
    users = state.setdefault("users", {})
    user_obj = users.get(str(user_id), {})
    if isinstance(user_obj, dict):
        latest = user_obj.get("latest_verification")
        if isinstance(latest, dict) and latest.get("submission_id") == submission_id:
            latest["status"] = status
            latest["reviewed_at"] = item["reviewed_at"]
            latest["reviewed_by"] = reviewer_id
        history = user_obj.get("verification_history", [])
        if isinstance(history, list):
            for row in history:
                if isinstance(row, dict) and row.get("submission_id") == submission_id:
                    row["status"] = status
                    row["reviewed_at"] = item["reviewed_at"]
                    row["reviewed_by"] = reviewer_id
                    break

    save_state(state)
    return item


def get_submission(submission_id: str) -> dict | None:
    state = load_state()
    submissions = state.get("verification_submissions", {})
    if not isinstance(submissions, dict):
        return None
    item = submissions.get(submission_id)
    if not isinstance(item, dict):
        return None
    return item


def update_submission_fields(submission_id: str, fields: dict) -> dict | None:
    state = load_state()
    submissions = state.setdefault("verification_submissions", {})
    if not isinstance(submissions, dict):
        return None

    item = submissions.get(submission_id)
    if not isinstance(item, dict):
        return None

    item.update(fields)

    user_id = item.get("user_id")
    users = state.setdefault("users", {})
    user_obj = users.get(str(user_id), {})
    if isinstance(user_obj, dict):
        latest = user_obj.get("latest_verification")
        if isinstance(latest, dict) and latest.get("submission_id") == submission_id:
            latest.update(fields)
        history = user_obj.get("verification_history", [])
        if isinstance(history, list):
            for row in history:
                if isinstance(row, dict) and row.get("submission_id") == submission_id:
                    row.update(fields)
                    break

    save_state(state)
    return item


def render_admin_submission_text(item: dict) -> str:
    raw_status = str(item.get("status") or "pending").lower()
    status_text = {
        "approved": "✅ APPROVED",
        "rejected": "❌ REJECTED",
    }.get(raw_status, raw_status.upper())
    user_id = item.get("user_id")
    username = item.get("telegram_username") or "-"
    username_text = f"@{username}" if username != "-" else "-"
    deposit_text = "Ya" if bool(item.get("has_deposit_100")) else "Belum"
    flow = str(item.get("registration_flow") or "new_registration")
    deposit_required_usd = int(item.get("deposit_required_usd") or get_required_deposit_amount(flow))
    flow_text_map = {
        "new_registration": "Pelanggan Baru",
        "ib_transfer": "Penukaran IB",
        "under_ib_reezo": "Client Under IB Reezo",
    }
    flow_text = flow_text_map.get(flow, flow)
    ib_req = item.get("ib_request_submitted")
    ib_req_text = ""
    if flow == "ib_transfer":
        ib_req_text = f"Submit Request IB: {'Ya' if ib_req else 'Belum'}\n"
    api_check_text = ""
    api_ib_status = item.get("api_is_client_under_ib")
    api_message = str(item.get("api_check_message") or "").strip()
    if api_ib_status is True:
        api_check_text = "API Check (Under IB): ✅ PASS\n"
    elif api_ib_status is False:
        api_check_text = "API Check (Under IB): ❌ FAIL\n"
    elif api_message:
        api_check_text = f"API Check (Under IB): ⚠️ {api_message}\n"
    return (
        "🆕 NEXT Member Verification Submit\n\n"
        f"Flow: {flow_text}\n"
        f"Submission ID: {item.get('submission_id')}\n"
        f"User ID: {user_id}\n"
        f"Username: {username_text}\n"
        f"Nama: {item.get('full_name')}\n"
        f"Wallet ID: {item.get('wallet_id')}\n"
        f"{ib_req_text}"
        f"{api_check_text}"
        f"Deposit Minimum USD{deposit_required_usd}: {deposit_text}\n"
        f"No Telefon: {item.get('phone_number')}\n"
        f"Status: {status_text}"
    )


async def send_submission_to_admin_group(context: ContextTypes.DEFAULT_TYPE, item: dict) -> None:
    admin_group_id = get_admin_group_id()
    if not admin_group_id:
        return
    sent = await context.bot.send_message(
        chat_id=admin_group_id,
        text=render_admin_submission_text(item),
        reply_markup=verification_action_keyboard(str(item.get("submission_id")), str(item.get("registration_flow") or "")),
    )
    update_submission_fields(str(item.get("submission_id")), {"admin_group_message_id": sent.message_id})


async def clear_user_deposit_prompt(context: ContextTypes.DEFAULT_TYPE, item: dict) -> None:
    user_id = item.get("user_id")
    prompt_message_id = item.get("user_deposit_prompt_message_id")
    if not isinstance(user_id, int) or not isinstance(prompt_message_id, int):
        return
    try:
        await context.bot.delete_message(chat_id=user_id, message_id=prompt_message_id)
    except Exception:
        logger.exception("Failed to delete old user deposit prompt message")
    finally:
        update_submission_fields(str(item.get("submission_id")), {"user_deposit_prompt_message_id": None})


async def clear_user_ib_prompt(context: ContextTypes.DEFAULT_TYPE, item: dict) -> None:
    user_id = item.get("user_id")
    prompt_message_id = item.get("user_ib_prompt_message_id")
    if not isinstance(user_id, int) or not isinstance(prompt_message_id, int):
        return
    try:
        await context.bot.delete_message(chat_id=user_id, message_id=prompt_message_id)
    except Exception:
        logger.exception("Failed to delete old user change-IB prompt message")
    finally:
        update_submission_fields(str(item.get("submission_id")), {"user_ib_prompt_message_id": None})


async def clear_user_deposit_prompt_by_submission(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str
) -> None:
    item = get_submission(submission_id)
    if not item:
        return
    await clear_user_deposit_prompt(context, item)


async def clear_user_ib_prompt_by_submission(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str
) -> None:
    item = get_submission(submission_id)
    if not item:
        return
    await clear_user_ib_prompt(context, item)


async def refresh_admin_submission_message(context: ContextTypes.DEFAULT_TYPE, submission_id: str) -> None:
    admin_group_id = get_admin_group_id()
    item = get_submission(submission_id)
    if not admin_group_id or not item:
        return
    old_message_id = item.get("admin_group_message_id")
    if isinstance(old_message_id, int):
        try:
            await context.bot.delete_message(chat_id=admin_group_id, message_id=old_message_id)
        except Exception:
            logger.exception("Failed to delete old admin verification message")
    await send_submission_to_admin_group(context, item)


async def send_user_deposit_request_message(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str, item: dict
) -> None:
    user_id = item.get("user_id")
    if not isinstance(user_id, int):
        return
    deposit_required_usd = int(item.get("deposit_required_usd") or get_required_deposit_amount(str(item.get("registration_flow") or "")))
    await clear_user_deposit_prompt(context, item)
    await clear_user_ib_prompt(context, item)
    sent = await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"Sila buat deposit USD{deposit_required_usd} ke akaun Amarkets ({item.get('wallet_id')}) "
            "untuk melengkapkan proses pendaftaran.\n\n"
            "Tekan butang DEPOSIT SELESAI untuk pengesahan semula."
        ),
        reply_markup=user_deposit_keyboard(submission_id),
    )
    update_submission_fields(submission_id, {"user_deposit_prompt_message_id": sent.message_id})


async def send_user_change_ib_request_message(
    context: ContextTypes.DEFAULT_TYPE, submission_id: str, item: dict
) -> None:
    user_id = item.get("user_id")
    if not isinstance(user_id, int):
        return
    await clear_user_ib_prompt(context, item)
    await clear_user_deposit_prompt(context, item)
    sent = await context.bot.send_message(
        chat_id=user_id,
        text=(
            "Sila submit request penukaran IB di dashboard AMarkets terlebih dahulu.\n\n"
            "Tekan butang CHANGE IB SELESAI untuk pengesahan semula."
        ),
        reply_markup=user_ib_request_keyboard(submission_id),
    )
    update_submission_fields(submission_id, {"user_ib_prompt_message_id": sent.message_id})


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
        return

    if ":" in str(query.data):
        action, submission_id = str(query.data).split(":", 1)
        action_status_map = {
            CB_VERIF_APPROVE: "approved",
            CB_VERIF_PENDING: "pending",
            CB_VERIF_REJECT: "rejected",
        }
        if action == CB_VERIF_REQUEST_DEPOSIT:
            item = update_submission_fields(
                submission_id=submission_id,
                fields={
                    "status": "request_deposit",
                    "has_deposit_100": False,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": query.from_user.id,
                },
            )
            if not item:
                await query.message.reply_text("❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            user_id = item.get("user_id")
            if isinstance(user_id, int):
                try:
                    await send_user_deposit_request_message(context, submission_id, item)
                except Exception:
                    logger.exception("Failed to notify user for deposit request")
            await refresh_admin_submission_message(context, submission_id)
            await query.message.reply_text(f"✅ Request deposit dihantar kepada user untuk submission {submission_id}.")
            return

        if action == CB_VERIF_REQUEST_CHANGE_IB:
            item = update_submission_fields(
                submission_id=submission_id,
                fields={
                    "status": "request_change_ib",
                    "ib_request_submitted": False,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": query.from_user.id,
                },
            )
            if not item:
                await query.message.reply_text("❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            user_id = item.get("user_id")
            if isinstance(user_id, int):
                try:
                    await send_user_change_ib_request_message(context, submission_id, item)
                except Exception:
                    logger.exception("Failed to notify user for change-IB request")
            await refresh_admin_submission_message(context, submission_id)
            await query.message.reply_text(f"✅ Request change IB dihantar kepada user untuk submission {submission_id}.")
            return

        if action == CB_VERIF_REVOKE_VIP:
            item = get_submission(submission_id)
            if not item:
                await query.message.reply_text("❌ Rekod submission tak jumpa atau dah dipadam.")
                return
            user_id = item.get("user_id")
            if not isinstance(user_id, int):
                await query.message.reply_text("❌ User ID tak sah.")
                return
            remove_user_from_vip1(user_id)
            update_submission_fields(
                submission_id=submission_id,
                fields={
                    "status": "revoked",
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": query.from_user.id,
                },
            )
            await clear_user_deposit_prompt_by_submission(context, submission_id)
            await clear_user_ib_prompt_by_submission(context, submission_id)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "Akses NEXT Member anda telah ditarik semula oleh admin.\n"
                        "Sila hubungi admin untuk maklumat lanjut."
                    ),
                )
            except Exception:
                logger.exception("Failed to notify user after revoke")
            item = get_submission(submission_id)
            if item:
                await query.message.edit_text(render_admin_submission_text(item), reply_markup=approved_admin_keyboard(submission_id))
            return

        status = action_status_map.get(action)
        if not status:
            return

        updated = update_submission_status(submission_id=submission_id, status=status, reviewer_id=query.from_user.id)
        if not updated:
            await query.message.reply_text("❌ Rekod submission tak jumpa atau dah dipadam.")
            return

        target_user_id = updated.get("user_id")
        if isinstance(target_user_id, int):
            await clear_user_deposit_prompt_by_submission(context, submission_id)
            await clear_user_ib_prompt_by_submission(context, submission_id)
            try:
                if status == "rejected":
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            "Permohonan akses NEXT Member anda tidak diluluskan.\n"
                            "Sila buat pendaftaran baru."
                        ),
                    )
                elif status == "pending":
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            "Permohonan anda sedang disemak semula.\n"
                            "Sila tunggu maklum balas seterusnya daripada admin."
                        ),
                    )
                elif status == "approved":
                    add_user_to_vip1(updated)
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            "Tahniah! Anda kini boleh menikmati semua keistimewaan/privilege NEXT Member."
                        ),
                    )
            except Exception:
                logger.exception("Failed to send status update to user")

        status_label = {
            "approved": "✅ APPROVED",
            "pending": "PENDING",
            "rejected": "❌ REJECTED",
        }.get(status, status.upper())
        if status == "approved":
            refreshed = get_submission(submission_id)
            if refreshed:
                await query.message.edit_text(
                    render_admin_submission_text(refreshed),
                    reply_markup=approved_admin_keyboard(submission_id),
                )
            return

        if status == "rejected":
            refreshed = get_submission(submission_id)
            if refreshed:
                await query.message.edit_text(render_admin_submission_text(refreshed))
            return

        await refresh_admin_submission_message(context, submission_id)
        await query.message.reply_text(f"✅ Status submission {submission_id} ditetapkan kepada {status_label}.")
        return


async def handle_user_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if ":" not in str(query.data):
        return

    action, submission_id = str(query.data).split(":", 1)
    item = get_submission(submission_id)
    if not item:
        await query.message.reply_text("❌ Rekod submission tak jumpa.")
        return

    user_id = item.get("user_id")
    if query.from_user.id != user_id:
        await query.message.reply_text("❌ Butang ini bukan untuk anda.")
        return

    if action == CB_USER_DEPOSIT_CANCEL:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_deposit_prompt_message_id": None})
        await query.message.reply_text("Baik, status deposit anda kekal belum selesai.")
        return

    if action == CB_USER_DEPOSIT_DONE:
        updated = update_submission_fields(
            submission_id=submission_id,
            fields={
                "has_deposit_100": True,
                "status": "pending",
                "deposit_completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not updated:
            await query.message.reply_text("❌ Rekod submission tak jumpa.")
            return
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_deposit_prompt_message_id": None})
        await refresh_admin_submission_message(context, submission_id)
        await query.message.reply_text(
            "✅ Deposit selesai direkod.\n"
            "Permohonan anda dihantar semula kepada admin untuk semakan."
        )
        return


async def handle_user_ib_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if ":" not in str(query.data):
        return

    action, submission_id = str(query.data).split(":", 1)
    item = get_submission(submission_id)
    if not item:
        await query.message.reply_text("❌ Rekod submission tak jumpa.")
        return

    user_id = item.get("user_id")
    if query.from_user.id != user_id:
        await query.message.reply_text("❌ Butang ini bukan untuk anda.")
        return

    if action == CB_USER_IB_CANCEL:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_ib_prompt_message_id": None})
        await query.message.reply_text("Baik, status submit request penukaran IB anda kekal belum selesai.")
        return

    if action == CB_USER_IB_DONE:
        updated = update_submission_fields(
            submission_id=submission_id,
            fields={
                "ib_request_submitted": True,
                "status": "pending",
                "ib_request_completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not updated:
            await query.message.reply_text("❌ Rekod submission tak jumpa.")
            return
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        update_submission_fields(submission_id, {"user_ib_prompt_message_id": None})
        await refresh_admin_submission_message(context, submission_id)
        await query.message.reply_text(
            "✅ Request penukaran IB selesai direkod.\n"
            "Permohonan anda dihantar semula kepada admin untuk semakan."
        )
        return


async def group_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat:
        return
    if not is_admin_user(user.id):
        await message.reply_text("❌ Akses ditolak.")
        return
    await message.reply_text(
        "📌 Group/Chat Info\n"
        f"- chat_id: {chat.id}\n"
        f"- type: {chat.type}\n\n"
        "Salin chat_id ini dan letak dalam `.env`:\n"
        "SIDEBOT_ADMIN_GROUP_ID=<chat_id>",
    )


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

    if not has_tnc_accepted(user.id):
        await message.reply_text(
            "❌ Akses menu dikunci sehingga anda setuju TnC. Tekan /start untuk teruskan.",
            reply_markup=ReplyKeyboardRemove(),
        )
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

    if payload_type == "sidebot_verification_submit":
        registration_flow = str(payload.get("registration_flow") or "new_registration").strip() or "new_registration"
        ib_request_raw = payload.get("ib_request_submitted", None)
        ib_request_submitted = None
        if registration_flow == "ib_transfer":
            if isinstance(ib_request_raw, bool):
                ib_request_submitted = ib_request_raw

        wallet_id = str(payload.get("wallet_id") or "").strip()
        full_name = str(payload.get("full_name") or "").strip()
        phone_number = str(payload.get("phone_number") or "").strip()
        has_deposit_100 = bool(payload.get("has_deposit_100"))

        if not wallet_id or not full_name or not phone_number:
            await message.reply_text("❌ Data pengesahan tak lengkap. Sila isi semula dalam miniapp.")
            return
        if not is_valid_wallet_id(wallet_id):
            await message.reply_text("❌ AMarkets Wallet ID mesti tepat 7 angka.")
            return
        if registration_flow == "ib_transfer" and ib_request_submitted is None:
            await message.reply_text("❌ Status submit request penukaran IB belum dipilih. Sila isi semula.")
            return

        saved = store_verification_submission(
            user_id=user.id,
            telegram_username=str(user.username or ""),
            wallet_id=wallet_id,
            has_deposit_100=has_deposit_100,
            full_name=full_name,
            phone_number=phone_number,
            registration_flow=registration_flow,
            ib_request_submitted=ib_request_submitted,
        )
        api_is_client_under_ib = None
        api_check_message = ""
        if registration_flow in {"ib_transfer", "under_ib_reezo"}:
            api_is_client_under_ib, api_check_message = amarkets_check_is_client(wallet_id)
            update_submission_fields(
                submission_id=str(saved.get("submission_id")),
                fields={
                    "api_checked_at": datetime.now(timezone.utc).isoformat(),
                    "api_is_client_under_ib": api_is_client_under_ib,
                    "api_check_message": api_check_message,
                },
            )
            saved = get_submission(str(saved.get("submission_id"))) or saved

        deposit_required_usd = get_required_deposit_amount(registration_flow)
        deposit_text = "Ya" if has_deposit_100 else "Belum"
        submission_id = str(saved.get("submission_id") or "-")

        try:
            await send_submission_to_admin_group(context, saved)
        except Exception:
            logger.exception("Failed to send verification notification to admin group")

        await message.reply_text(
            "✅ Pengesahan diterima.\n"
            "Permohonan anda telah direkod dan dihantar ke admin.\n"
            "Sila tunggu approval.\n\n"
            f"Submission ID: {submission_id}\n"
            f"Wallet ID: {wallet_id}\n"
            f"Deposit Minimum USD{deposit_required_usd}: {deposit_text}\n"
            f"Nama: {full_name}\n"
            f"Telefon: {phone_number}",
            reply_markup=main_menu_keyboard(user.id),
        )
        if registration_flow == "ib_transfer":
            if not ib_request_submitted:
                try:
                    latest = get_submission(submission_id)
                    if latest:
                        await send_user_change_ib_request_message(context, submission_id, latest)
                except Exception:
                    logger.exception("Failed to send change-IB request after IB verification submit")
            elif not has_deposit_100:
                try:
                    latest = get_submission(submission_id)
                    if latest:
                        await send_user_deposit_request_message(context, submission_id, latest)
                except Exception:
                    logger.exception("Failed to send deposit request after IB verification submit")
        elif not has_deposit_100:
            try:
                latest = get_submission(submission_id)
                if latest:
                    await send_user_deposit_request_message(context, submission_id, latest)
            except Exception:
                logger.exception("Failed to send deposit request after verification submit")
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
    app.add_handler(CommandHandler("groupid", group_id))
    app.add_handler(CallbackQueryHandler(handle_tnc_callback, pattern=f"^({TNC_ACCEPT}|{TNC_DECLINE})$"))
    app.add_handler(
        CallbackQueryHandler(
            handle_admin_callback,
            pattern=f"^({CB_BETA_RESET_CONFIRM}|{CB_BETA_RESET_CANCEL}|{CB_VERIF_APPROVE}|{CB_VERIF_PENDING}|{CB_VERIF_REJECT}|{CB_VERIF_REQUEST_DEPOSIT}|{CB_VERIF_REQUEST_CHANGE_IB}|{CB_VERIF_REVOKE_VIP}).*",
        )
    )
    app.add_handler(CallbackQueryHandler(handle_user_deposit_callback, pattern=f"^({CB_USER_DEPOSIT_DONE}|{CB_USER_DEPOSIT_CANCEL}).*"))
    app.add_handler(CallbackQueryHandler(handle_user_ib_callback, pattern=f"^({CB_USER_IB_DONE}|{CB_USER_IB_CANCEL}).*"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
