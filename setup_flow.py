"""WebApp setup flow handlers."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from menu import main_menu_keyboard, project_grow_keyboard
from settings import get_project_grow_mission_webapp_url, get_set_new_goal_webapp_url
from storage import (
    add_deposit_activity,
    add_trading_activity_update,
    add_withdrawal_activity,
    apply_project_grow_unlock_to_tabung,
    apply_initial_capital_reset,
    can_open_project_grow_mission,
    can_reset_initial_capital,
    get_capital_usd,
    get_current_balance_usd,
    get_current_profit_usd,
    get_initial_setup_summary,
    get_project_grow_goal_summary,
    get_project_grow_mission_state,
    get_project_grow_mission_status_text,
    get_tabung_balance_usd,
    get_tabung_start_date,
    reset_project_grow_goal,
    reset_project_grow_mission,
    save_user_setup_section,
    start_project_grow_mission,
)
from texts import (
    DEPOSIT_ACTIVITY_SAVED_TEXT,
    INITIAL_CAPITAL_RESET_SUCCESS_TEXT,
    PROJECT_GROW_OPENED_TEXT,
    MISSION_RESET_TEXT,
    MISSION_STARTED_TEXT,
    SET_NEW_GOAL_RESET_TEXT,
    SET_NEW_GOAL_SAVED_TEXT,
    SETUP_SAVED_TEXT,
    TRADING_ACTIVITY_SAVED_TEXT,
    WITHDRAWAL_ACTIVITY_SAVED_TEXT,
)
from ui import send_screen


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


async def _handle_initial_setup(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    name = (payload.get("name") or "").strip()
    if not name:
        await send_screen(context, message.chat_id, "❌ Nama kosong lagi. Isi dulu bro.")
        return

    try:
        initial_capital = float(payload.get("initial_capital_usd"))
        risk_per_trade = float(payload.get("risk_per_trade_pct"))
        max_daily_loss = float(payload.get("max_daily_loss_pct"))
        daily_profit_target = float(payload.get("daily_profit_target_pct"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Nombor ada yang pelik. Check balik input.")
        return

    if initial_capital <= 0:
        await send_screen(context, message.chat_id, "❌ Modal kena lebih dari 0, baru game start.")
        return

    numeric_values = [risk_per_trade, max_daily_loss, daily_profit_target]
    if any(v <= 0 for v in numeric_values):
        await send_screen(context, message.chat_id, "❌ Value % kena lebih dari 0 boss.")
        return

    telegram_name = (update.effective_user.full_name or "").strip() or str(update.effective_user.id)

    save_user_setup_section(
        user_id=update.effective_user.id,
        telegram_name=telegram_name,
        section="initial_setup",
        payload={
            "name": name,
            "initial_capital_usd": initial_capital,
            "risk_per_trade_pct": risk_per_trade,
            "max_daily_loss_pct": max_daily_loss,
            "daily_profit_target_pct": daily_profit_target,
        },
    )

    await send_screen(
        context,
        message.chat_id,
        SETUP_SAVED_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def _handle_initial_capital_reset(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    if not can_reset_initial_capital(user_id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Reset tak dibenarkan sebab dah ada rekod transaksi.",
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        new_initial_capital = float(payload.get("new_initial_capital_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Nilai baru modal tak sah.")
        return

    ok = apply_initial_capital_reset(user_id, new_initial_capital)
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Reset gagal. Cuba semula dari menu.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        INITIAL_CAPITAL_RESET_SUCCESS_TEXT,
        reply_markup=main_menu_keyboard(),
    )


async def _handle_withdrawal_activity(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    reason = (payload.get("reason") or "").strip()
    if not reason:
        await send_screen(context, message.chat_id, "❌ Pilih reason dulu bro.")
        return

    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Jumlah withdraw tak sah.")
        return

    ok = add_withdrawal_activity(
        user_id=user_id,
        reason=reason,
        amount_usd=amount_usd,
        current_profit_usd=get_current_profit_usd(user_id),
    )
    if not ok:
        await send_screen(context, message.chat_id, "❌ Gagal simpan withdrawal activity.")
        return

    await send_screen(
        context,
        message.chat_id,
        WITHDRAWAL_ACTIVITY_SAVED_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def _handle_deposit_activity(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    reason = (payload.get("reason") or "").strip()
    if not reason:
        await send_screen(context, message.chat_id, "❌ Pilih reason dulu bro.")
        return

    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Jumlah deposit tak sah.")
        return

    ok = add_deposit_activity(
        user_id=user_id,
        reason=reason,
        amount_usd=amount_usd,
        current_profit_usd=get_current_profit_usd(user_id),
    )
    if not ok:
        await send_screen(context, message.chat_id, "❌ Gagal simpan deposit activity.")
        return

    await send_screen(
        context,
        message.chat_id,
        DEPOSIT_ACTIVITY_SAVED_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def _handle_trading_activity_update(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    mode = (payload.get("mode") or "").strip().lower()

    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Jumlah update tak sah.")
        return

    ok = add_trading_activity_update(
        user_id=user_id,
        mode=mode,
        amount_usd=amount_usd,
    )
    if not ok:
        await send_screen(context, message.chat_id, "❌ Gagal simpan trading activity.")
        return

    await send_screen(
        context,
        message.chat_id,
        TRADING_ACTIVITY_SAVED_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def _handle_set_new_goal(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    try:
        target_balance_usd = float(payload.get("target_balance_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Isi target account yang valid dulu bro.")
        return

    if target_balance_usd <= 0:
        await send_screen(context, message.chat_id, "❌ Target account kena lebih dari 0.")
        return

    target_days_raw = str(payload.get("target_days") or "").strip()
    target_label = (payload.get("target_label") or "").strip()

    if target_days_raw not in {"30", "90", "180"}:
        await send_screen(context, message.chat_id, "❌ Tempoh target tak sah.")
        return

    try:
        unlock_amount_usd = float(payload.get("unlock_amount_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Nilai unlock mission/tabung tak sah.")
        return

    if unlock_amount_usd < 10:
        await send_screen(context, message.chat_id, "❌ Nilai unlock minimum USD 10.")
        return

    current_balance = get_current_balance_usd(user.id)
    minimum_target = current_balance + 100.0
    if target_balance_usd < minimum_target:
        await send_screen(
            context,
            message.chat_id,
            f"❌ Target minimum kena USD {minimum_target:.2f} (baki semasa + 100).",
        )
        return

    target_days = int(target_days_raw)
    if not target_label:
        if target_days == 90:
            target_label = "3 bulan"
        elif target_days == 180:
            target_label = "6 bulan"
        else:
            target_label = "30 hari"

    telegram_name = (user.full_name or "").strip() or str(user.id)
    save_user_setup_section(
        user_id=user.id,
        telegram_name=telegram_name,
        section="project_grow_goal",
        payload={
            "target_balance_usd": float(target_balance_usd),
            "unlock_amount_usd": float(unlock_amount_usd),
            "minimum_target_usd": float(minimum_target),
            "current_balance_usd": float(current_balance),
            "target_days": target_days,
            "target_label": target_label,
        },
    )
    apply_project_grow_unlock_to_tabung(user.id, unlock_amount_usd)

    await send_screen(
        context,
        message.chat_id,
        SET_NEW_GOAL_SAVED_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def _handle_project_grow_mission_start(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    if not can_open_project_grow_mission(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Mission tak boleh start lagi. Pastikan goal dah set dan tabung minimum USD 10.",
            reply_markup=main_menu_keyboard(),
        )
        return

    mode = (payload.get("mode") or "").strip().lower()
    ok = start_project_grow_mission(user.id, mode)
    if not ok:
        await send_screen(context, message.chat_id, "❌ Mission gagal diaktifkan. Cuba lagi.")
        return

    await send_screen(
        context,
        message.chat_id,
        MISSION_STARTED_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def _handle_project_grow_mission_reset(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    confirm_reset = str(payload.get("confirm_reset") or "0").strip()
    if confirm_reset != "1":
        await send_screen(context, message.chat_id, "❌ Reset mission dibatalkan.")
        return

    ok = reset_project_grow_mission(user.id)
    if not ok:
        await send_screen(context, message.chat_id, "❌ Mission belum aktif atau reset gagal.")
        return

    await send_screen(
        context,
        message.chat_id,
        MISSION_RESET_TEXT,
        reply_markup=_build_project_grow_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def _handle_project_grow_goal_reset(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    confirm_reset = str(payload.get("confirm_reset") or "0").strip()
    if confirm_reset != "1":
        await send_screen(context, message.chat_id, "❌ Reset goal dibatalkan.")
        return

    ok = reset_project_grow_goal(user.id)
    if not ok:
        await send_screen(context, message.chat_id, "❌ Goal belum ada atau reset gagal.")
        return

    await send_screen(
        context,
        message.chat_id,
        SET_NEW_GOAL_RESET_TEXT,
        reply_markup=_build_project_grow_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def _handle_project_grow_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    await send_screen(
        context,
        message.chat_id,
        PROJECT_GROW_OPENED_TEXT,
        reply_markup=_build_project_grow_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def handle_setup_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await send_screen(context, message.chat_id, "❌ Eh data tak lepas. Cuba submit lagi sekali.")
        return

    payload_type = payload.get("type")
    if payload_type == "setup_profile":
        await _handle_initial_setup(payload, update, context)
        return

    if payload_type == "initial_capital_reset":
        await _handle_initial_capital_reset(payload, update, context)
        return

    if payload_type == "withdrawal_activity":
        await _handle_withdrawal_activity(payload, update, context)
        return

    if payload_type == "deposit_activity":
        await _handle_deposit_activity(payload, update, context)
        return

    if payload_type == "trading_activity_update":
        await _handle_trading_activity_update(payload, update, context)
        return

    if payload_type == "set_new_goal":
        await _handle_set_new_goal(payload, update, context)
        return

    if payload_type == "project_grow_mission_start":
        await _handle_project_grow_mission_start(payload, update, context)
        return

    if payload_type == "project_grow_mission_reset":
        await _handle_project_grow_mission_reset(payload, update, context)
        return

    if payload_type == "project_grow_goal_reset":
        await _handle_project_grow_goal_reset(payload, update, context)
        return

    if payload_type == "project_grow_back_to_menu":
        await _handle_project_grow_back_to_menu(update, context)
        return

    await send_screen(
        context,
        message.chat_id,
        "❌ Jenis data tak dikenali. Sila buka semula menu dan cuba lagi.",
        reply_markup=main_menu_keyboard(),
    )
