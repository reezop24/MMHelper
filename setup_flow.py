"""WebApp setup flow handlers."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from menu import (
    is_admin_user,
    main_menu_keyboard,
)
from handlers import (
    _build_account_activity_keyboard_for_user,
    _build_admin_panel_keyboard_for_user,
    _build_mm_setting_keyboard_for_user,
    _build_project_grow_keyboard_for_user,
    _build_records_reports_keyboard_for_user,
)
from storage import (
    add_deposit_activity,
    add_trading_activity_update,
    add_withdrawal_activity,
    apply_balance_adjustment,
    apply_project_grow_unlock_to_tabung,
    apply_initial_capital_reset,
    apply_tabung_update_action,
    can_open_project_grow_mission,
    can_reset_initial_capital,
    get_current_balance_usd,
    get_current_profit_usd,
    get_tabung_balance_usd,
    get_total_balance_usd,
    get_weekly_performance_usd,
    is_daily_target_hit_now,
    has_initial_setup,
    has_tnc_accepted,
    reset_project_grow_goal,
    reset_project_grow_mission,
    save_notification_settings,
    save_user_setup_section,
    start_project_grow_mission,
)
from texts import (
    ACCOUNT_ACTIVITY_OPENED_TEXT,
    INITIAL_CAPITAL_RESET_SUCCESS_TEXT,
    MAIN_MENU_OPENED_TEXT,
    MM_HELPER_SETTING_OPENED_TEXT,
    NOTIFICATION_SETTING_SAVED_TEXT,
    PROJECT_GROW_OPENED_TEXT,
    STATISTIC_OPENED_TEXT,
    MISSION_RESET_TEXT,
    MISSION_STARTED_TEXT,
    SET_NEW_GOAL_RESET_TEXT,
)
from ui import send_screen


def _usd(value: float) -> str:
    return f"USD {float(value):.2f}"


def _trading_days_for_target_days(target_days: int) -> int:
    mapping = {30: 22, 90: 66, 180: 132}
    return mapping.get(int(target_days), 0)


def _build_setup_recommendation(initial_capital: float, target_balance_usd: float, target_days: int) -> dict:
    trading_days = _trading_days_for_target_days(target_days)
    if trading_days <= 0 or initial_capital <= 0:
        return {
            "trading_days": 0,
            "daily_target_usd": 0.0,
            "daily_target_pct": 0.0,
            "daily_risk_usd": 0.0,
            "daily_risk_pct": 0.0,
            "per_setup_risk_usd": 0.0,
            "per_setup_risk_pct": 0.0,
            "setups_per_day": 2,
            "assumption": "22 trading days per month (Mon-Fri)",
        }

    grow_target_usd = max(float(target_balance_usd) - float(initial_capital), 0.0)
    daily_target_usd = grow_target_usd / float(trading_days)
    daily_target_pct = (daily_target_usd / float(initial_capital)) * 100.0
    daily_risk_pct = daily_target_pct
    daily_risk_usd = (float(initial_capital) * daily_risk_pct) / 100.0
    per_setup_risk_pct = daily_risk_pct / 2.0
    per_setup_risk_usd = daily_risk_usd / 2.0

    return {
        "trading_days": int(trading_days),
        "daily_target_usd": float(daily_target_usd),
        "daily_target_pct": float(daily_target_pct),
        "daily_risk_usd": float(daily_risk_usd),
        "daily_risk_pct": float(daily_risk_pct),
        "per_setup_risk_usd": float(per_setup_risk_usd),
        "per_setup_risk_pct": float(per_setup_risk_pct),
        "setups_per_day": 2,
        "assumption": "22 trading days per month (Mon-Fri)",
    }


def _weekly_pl_line(user_id: int) -> str:
    weekly_pl = float(get_weekly_performance_usd(user_id))
    if weekly_pl > 0:
        return f"Lepas aku kira-kira, minggu ni kau tengah untung **{_usd(weekly_pl)}**."
    if weekly_pl < 0:
        return f"Lepas aku kira-kira, minggu ni kau tengah rugi **{_usd(abs(weekly_pl))}**."
    return "Lepas aku kira-kira, minggu ni P/L kau masih **USD 0.00**."


def _build_deposit_saved_text(user_id: int, amount_usd: float) -> str:
    return (
        "Ok, aku dah update deposit kau ✅\n\n"
        f"Kau baru je tambah **{_usd(amount_usd)}**.\n"
        "Duit ni masuk ke account trading kau.\n\n"
        f"Current Balance kau sekarang dah ada **{_usd(get_current_balance_usd(user_id))}**.\n"
        f"{_weekly_pl_line(user_id)}\n\n"
        f"Baki tabung sekarang: **{_usd(get_tabung_balance_usd(user_id))}**."
    )


def _build_withdrawal_saved_text(user_id: int, amount_usd: float) -> str:
    return (
        "Ok, aku dah update withdrawal kau ✅\n\n"
        f"Kau baru je keluarkan **{_usd(amount_usd)}**.\n"
        "Duit ni keluar dari account trading kau.\n\n"
        f"Current Balance kau sekarang jadi **{_usd(get_current_balance_usd(user_id))}**.\n"
        f"{_weekly_pl_line(user_id)}\n\n"
        f"Baki tabung sekarang: **{_usd(get_tabung_balance_usd(user_id))}**."
    )


def _build_trading_saved_text(user_id: int, mode: str, amount_usd: float) -> str:
    mode_label = "profit" if mode == "profit" else "loss"
    return (
        "Ok, aku dah update trading kau ✅\n\n"
        f"Trade latest kau: **{mode_label.upper()} {_usd(amount_usd)}**.\n"
        f"{_weekly_pl_line(user_id)}\n\n"
        f"Current Balance sekarang: **{_usd(get_current_balance_usd(user_id))}**.\n"
        f"Baki tabung sekarang: **{_usd(get_tabung_balance_usd(user_id))}**."
    )


def _build_trading_daily_target_hit_text(user_id: int, mode: str, amount_usd: float) -> str:
    mode_label = "profit" if mode == "profit" else "loss"
    return (
        "Update trading dah masuk ✅\n\n"
        f"Trade latest kau: **{mode_label.upper()} {_usd(amount_usd)}**.\n"
        f"{_weekly_pl_line(user_id)}\n\n"
        "Daily target kau untuk hari ni dah *REACH* bro.\n"
        "Nasihat kawan: stop trade dulu hari ni, lock result, sambung esok kepala fresh.\n\n"
        f"Current Balance: **{_usd(get_current_balance_usd(user_id))}**\n"
        f"Tabung Balance: **{_usd(get_tabung_balance_usd(user_id))}**"
    )


def _build_tabung_saved_text(user_id: int, action: str, amount_usd: float) -> str:
    current_balance = _usd(get_current_balance_usd(user_id))
    tabung_balance = _usd(get_tabung_balance_usd(user_id))
    total_balance = _usd(get_total_balance_usd(user_id))
    if action == "save":
        return (
            "Nice, simpanan tabung kau dah masuk ✅\n\n"
            f"Kau baru simpan **{_usd(amount_usd)}** ke tabung.\n"
            "Jumlah ni diambil terus dari Current Balance kau.\n\n"
            f"Current Balance sekarang: **{current_balance}**\n"
            f"Tabung Balance sekarang: **{tabung_balance}**\n"
            f"Capital sekarang: **{total_balance}**"
        )
    if action == "emergency_withdrawal":
        return (
            "Emergency withdrawal dah direkod ✅\n\n"
            f"Kau keluarkan **{_usd(amount_usd)}** dari tabung.\n"
            "Aku ingatkan je, guna mode ni bila betul-betul perlu.\n\n"
            f"Current Balance kekal: **{current_balance}**\n"
            f"Tabung Balance sekarang: **{tabung_balance}**\n"
            f"Capital sekarang: **{total_balance}**"
        )
    if action == "goal_to_current":
        return (
            "Withdrawal goal ke Current Balance berjaya ✅\n\n"
            f"Kau pindahkan **{_usd(amount_usd)}** dari tabung ke Current Balance.\n\n"
            f"Current Balance sekarang: **{current_balance}**\n"
            f"Tabung Balance sekarang: **{tabung_balance}**\n"
            f"Capital sekarang: **{total_balance}**"
        )
    return (
        "Withdrawal goal terus berjaya ✅\n\n"
        f"Kau keluarkan **{_usd(amount_usd)}** terus dari tabung.\n\n"
        f"Current Balance kekal: **{current_balance}**\n"
        f"Tabung Balance sekarang: **{tabung_balance}**\n"
        f"Capital sekarang: **{total_balance}**"
    )


def _build_goal_recommendation_text(initial_capital: float, target_balance_usd: float, target_days: int) -> str:
    recommendation = _build_setup_recommendation(initial_capital, target_balance_usd, target_days)
    if recommendation["trading_days"] <= 0:
        return "Cadangan plan belum dapat dikira. Semak semula tempoh target."
    return (
        "Rujukan plan harian (kiraan guna 22 hari trading sebulan, Isnin-Jumaat):\n"
        f"- Daily target: **{recommendation['daily_target_pct']:.2f}%** "
        f"(**{_usd(recommendation['daily_target_usd'])}**)\n"
        f"- Risk maksimum sehari: **{recommendation['daily_risk_pct']:.2f}%** "
        f"(**{_usd(recommendation['daily_risk_usd'])}**)\n"
        f"- Risk per setup (2 setup/hari): **{recommendation['per_setup_risk_pct']:.2f}%** "
        f"(**{_usd(recommendation['per_setup_risk_usd'])}**)"
    )


def _build_initial_setup_saved_text(
    user_id: int,
    name: str,
    initial_capital: float,
    target_balance_usd: float,
    target_days: int,
    target_label: str,
) -> str:
    recommendation_text = _build_goal_recommendation_text(initial_capital, target_balance_usd, target_days)
    return (
        "Initial setup berjaya disimpan ✅\n\n"
        f"Nama: **{name}**\n"
        f"Modal permulaan: **{_usd(initial_capital)}**\n"
        f"Goal: **{_usd(target_balance_usd)}** ({target_label})\n\n"
        f"{recommendation_text}\n\n"
        f"Current Balance sekarang: **{_usd(get_current_balance_usd(user_id))}**."
    )


def _build_set_new_goal_saved_text(
    user_id: int,
    target_balance_usd: float,
    unlock_amount_usd: float,
    target_label: str,
    target_days: int,
    base_balance_usd: float,
) -> str:
    if unlock_amount_usd >= 10:
        unlock_line = f"Kau unlock mission dengan simpanan awal tabung: **{_usd(unlock_amount_usd)}**."
    else:
        unlock_line = "Mission belum unlock lagi (minimum unlock mission USD 10). Tabung masih boleh guna seperti biasa."
    recommendation_text = _build_goal_recommendation_text(base_balance_usd, target_balance_usd, target_days)
    return (
        "Set New Goal berjaya disimpan ✅\n\n"
        f"Target capital baru kau: **{_usd(target_balance_usd)}** ({target_label}).\n"
        f"{unlock_line}\n\n"
        f"{recommendation_text}\n\n"
        f"Current Balance sekarang: **{_usd(get_current_balance_usd(user_id))}**.\n"
        f"Baki tabung sekarang: **{_usd(get_tabung_balance_usd(user_id))}**.\n"
        f"{_weekly_pl_line(user_id)}"
    )


async def _handle_initial_setup(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    if has_initial_setup(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Akaun kau dah didaftarkan. Initial setup tak perlu diulang.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    if not has_tnc_accepted(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Sila accept T&C dulu melalui /start sebelum buat initial setup.",
        )
        return

    name = (payload.get("name") or "").strip()
    if not name:
        await send_screen(context, message.chat_id, "❌ Nama kosong lagi. Isi dulu bro.")
        return

    try:
        initial_capital = float(payload.get("initial_capital_usd"))
        target_balance_usd = float(payload.get("target_balance_usd"))
    except (TypeError, ValueError):
        await send_screen(context, message.chat_id, "❌ Nombor ada yang pelik. Check balik input.")
        return

    if initial_capital <= 0:
        await send_screen(context, message.chat_id, "❌ Modal kena lebih dari 0, baru game start.")
        return

    minimum_target = initial_capital + 100.0
    if target_balance_usd < minimum_target:
        await send_screen(
            context,
            message.chat_id,
            f"❌ Target Capital minimum ialah USD {minimum_target:.2f} (modal + 100).",
        )
        return

    target_days_raw = str(payload.get("target_days") or "").strip()
    target_label = str(payload.get("target_label") or "").strip()
    if target_days_raw not in {"30", "90", "180"}:
        await send_screen(context, message.chat_id, "❌ Tempoh target tak sah.")
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
        section="initial_setup",
        payload={
            "name": name,
            "initial_capital_usd": initial_capital,
            # Kept as defaults for compatibility with existing mission logic.
            "risk_per_trade_pct": 1.0,
            "max_daily_loss_pct": 5.0,
            "daily_profit_target_pct": 2.0,
        },
    )

    save_user_setup_section(
        user_id=user.id,
        telegram_name=telegram_name,
        section="project_grow_goal",
        payload={
            "target_balance_usd": float(target_balance_usd),
            "unlock_amount_usd": 0.0,
            "minimum_target_usd": float(minimum_target),
            "current_balance_usd": float(initial_capital),
            "target_days": target_days,
            "target_label": target_label,
        },
    )

    recommendation_data = _build_setup_recommendation(initial_capital, target_balance_usd, target_days)
    recommendation_data["save_mode"] = "with_recommendation"
    recommendation_data["initial_capital_usd"] = float(initial_capital)
    recommendation_data["target_balance_usd"] = float(target_balance_usd)
    recommendation_data["target_days"] = int(target_days)
    recommendation_data["target_label"] = target_label
    save_user_setup_section(
        user_id=user.id,
        telegram_name=telegram_name,
        section="setup_recommendation",
        payload=recommendation_data,
    )

    await send_screen(
        context,
        message.chat_id,
        _build_initial_setup_saved_text(
            user_id=user.id,
            name=name,
            initial_capital=initial_capital,
            target_balance_usd=target_balance_usd,
            target_days=target_days,
            target_label=target_label,
        ),
        reply_markup=main_menu_keyboard(update.effective_user.id),
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
            reply_markup=_build_mm_setting_keyboard_for_user(user_id),
        )
        return

    try:
        new_initial_capital = float(payload.get("new_initial_capital_usd"))
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Nilai baru modal tak sah.",
            reply_markup=_build_mm_setting_keyboard_for_user(user_id),
        )
        return

    ok = apply_initial_capital_reset(user_id, new_initial_capital)
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Reset gagal. Cuba semula dari menu.",
            reply_markup=_build_mm_setting_keyboard_for_user(user_id),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        INITIAL_CAPITAL_RESET_SUCCESS_TEXT,
        reply_markup=_build_mm_setting_keyboard_for_user(user_id),
    )


async def _handle_balance_adjustment(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    mode = str(payload.get("mode") or "").strip().lower()
    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Nilai balance adjustment tak sah.",
            reply_markup=_build_mm_setting_keyboard_for_user(user_id),
        )
        return

    ok, status_text = apply_balance_adjustment(user_id, mode, amount_usd)
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            f"❌ {status_text}",
            reply_markup=_build_mm_setting_keyboard_for_user(user_id),
        )
        return

    current_balance = get_current_balance_usd(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    direction = "Tambah" if mode == "add" else "Tolak"
    sign = "+" if mode == "add" else "-"
    confirmation = (
        "Balance Adjustment berjaya disimpan ✅\n\n"
        f"{direction} balance: {sign}USD {amount_usd:.2f}\n"
        f"Current Balance sekarang: USD {current_balance:.2f}\n"
        f"Baki tabung sekarang: USD {tabung_balance:.2f}"
    )
    await send_screen(
        context,
        message.chat_id,
        confirmation,
        reply_markup=_build_mm_setting_keyboard_for_user(user_id),
    )


async def _handle_withdrawal_activity(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    reason = (payload.get("reason") or "").strip()
    if not reason:
        await send_screen(
            context,
            message.chat_id,
            "❌ Pilih reason dulu bro.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Jumlah withdraw tak sah.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    ok = add_withdrawal_activity(
        user_id=user_id,
        reason=reason,
        amount_usd=amount_usd,
        current_profit_usd=get_current_profit_usd(user_id),
    )
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Gagal simpan withdrawal activity.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        _build_withdrawal_saved_text(user_id, amount_usd),
        reply_markup=_build_account_activity_keyboard_for_user(user_id),
        parse_mode="Markdown",
    )


async def _handle_deposit_activity(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    reason = (payload.get("reason") or "").strip()
    if not reason:
        await send_screen(
            context,
            message.chat_id,
            "❌ Pilih reason dulu bro.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Jumlah deposit tak sah.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    ok = add_deposit_activity(
        user_id=user_id,
        reason=reason,
        amount_usd=amount_usd,
        current_profit_usd=get_current_profit_usd(user_id),
    )
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Gagal simpan deposit activity.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        _build_deposit_saved_text(user_id, amount_usd),
        reply_markup=_build_account_activity_keyboard_for_user(user_id),
        parse_mode="Markdown",
    )


async def _handle_trading_activity_update(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    mode = (payload.get("mode") or "").strip().lower()

    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Jumlah update tak sah.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    ok = add_trading_activity_update(
        user_id=user_id,
        mode=mode,
        amount_usd=amount_usd,
    )
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Gagal simpan trading activity.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    if is_daily_target_hit_now(user_id):
        response_text = _build_trading_daily_target_hit_text(user_id, mode, amount_usd)
    else:
        response_text = _build_trading_saved_text(user_id, mode, amount_usd)

    await send_screen(
        context,
        message.chat_id,
        response_text,
        reply_markup=_build_account_activity_keyboard_for_user(user_id),
        parse_mode="Markdown",
    )


async def _handle_tabung_update_action(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id

    action = str(payload.get("action") or "").strip().lower()
    try:
        amount_usd = float(payload.get("amount_usd"))
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Jumlah tabung tak sah.",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    ok, status = apply_tabung_update_action(user_id, action, amount_usd)
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            f"❌ {status}",
            reply_markup=_build_account_activity_keyboard_for_user(user_id),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        _build_tabung_saved_text(user_id, action, amount_usd),
        reply_markup=_build_account_activity_keyboard_for_user(user_id),
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
        await send_screen(
            context,
            message.chat_id,
            "❌ Isi target account yang valid dulu bro.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    if target_balance_usd <= 0:
        await send_screen(
            context,
            message.chat_id,
            "❌ Target account kena lebih dari 0.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    target_days_raw = str(payload.get("target_days") or "").strip()
    target_label = (payload.get("target_label") or "").strip()

    if target_days_raw not in {"30", "90", "180"}:
        await send_screen(
            context,
            message.chat_id,
            "❌ Tempoh target tak sah.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    try:
        unlock_amount_usd = float(payload.get("unlock_amount_usd") or 0.0)
    except (TypeError, ValueError):
        await send_screen(
            context,
            message.chat_id,
            "❌ Nilai unlock mission tak sah.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    if unlock_amount_usd < 0:
        await send_screen(
            context,
            message.chat_id,
            "❌ Nilai unlock mission tak boleh negatif.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    current_balance = get_current_balance_usd(user.id)
    if unlock_amount_usd > current_balance:
        await send_screen(
            context,
            message.chat_id,
            f"❌ Unlock tak boleh lebih dari Current Balance kau sekarang ({current_balance:.2f}).",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    minimum_target = current_balance + 100.0
    if target_balance_usd < minimum_target:
        await send_screen(
            context,
            message.chat_id,
            f"❌ Target minimum kena USD {minimum_target:.2f} (current balance + 100).",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
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
    if unlock_amount_usd >= 10:
        apply_project_grow_unlock_to_tabung(user.id, unlock_amount_usd)

    await send_screen(
        context,
        message.chat_id,
        _build_set_new_goal_saved_text(
            user_id=user.id,
            target_balance_usd=target_balance_usd,
            unlock_amount_usd=unlock_amount_usd,
            target_label=target_label,
            target_days=target_days,
            base_balance_usd=current_balance,
        ),
        reply_markup=_build_project_grow_keyboard_for_user(user.id),
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
            "❌ Mission tak boleh start lagi. Pastikan balance tabung minimum USD 20.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    mode = (payload.get("mode") or "").strip().lower()
    ok = start_project_grow_mission(user.id, mode)
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Mission gagal diaktifkan. Cuba lagi.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        MISSION_STARTED_TEXT,
        reply_markup=_build_project_grow_keyboard_for_user(user.id),
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


async def _handle_account_activity_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    await send_screen(
        context,
        message.chat_id,
        ACCOUNT_ACTIVITY_OPENED_TEXT,
        reply_markup=_build_account_activity_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def _handle_mm_setting_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    await send_screen(
        context,
        message.chat_id,
        MM_HELPER_SETTING_OPENED_TEXT,
        reply_markup=_build_mm_setting_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def _handle_admin_panel_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

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
        "Admin Panel _dibuka_.",
        reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def _handle_records_reports_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    await send_screen(
        context,
        message.chat_id,
        STATISTIC_OPENED_TEXT,
        reply_markup=_build_records_reports_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def _handle_risk_calculator_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    await send_screen(
        context,
        message.chat_id,
        MAIN_MENU_OPENED_TEXT,
        reply_markup=main_menu_keyboard(user.id),
        parse_mode="Markdown",
    )


async def _handle_notification_settings_save(payload: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not user:
        return

    if not is_admin_user(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Akses ditolak.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    ok = save_notification_settings(user.id, payload)
    if not ok:
        await send_screen(
            context,
            message.chat_id,
            "❌ Gagal simpan notification setting. Semak input dan cuba lagi.",
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        )
        return

    await send_screen(
        context,
        message.chat_id,
        NOTIFICATION_SETTING_SAVED_TEXT,
        reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        parse_mode="Markdown",
    )


async def handle_setup_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return
    user = update.effective_user
    if not user:
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await send_screen(context, message.chat_id, "❌ Eh data tak lepas. Cuba submit lagi sekali.")
        return

    payload_type = payload.get("type")

    if payload_type != "setup_profile" and not has_initial_setup(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Akaun belum siap daftar. Guna /start dan lengkapkan T&C + Initial Setup dulu.",
        )
        return

    if payload_type == "setup_profile" and has_initial_setup(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Initial setup dah lengkap. Teruskan guna menu utama.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    if payload_type == "setup_profile" and not has_tnc_accepted(user.id):
        await send_screen(
            context,
            message.chat_id,
            "❌ Sila accept T&C dulu melalui /start.",
        )
        return

    if payload_type == "setup_profile":
        await _handle_initial_setup(payload, update, context)
        return

    if payload_type == "initial_capital_reset":
        await _handle_initial_capital_reset(payload, update, context)
        return

    if payload_type == "balance_adjustment":
        await _handle_balance_adjustment(payload, update, context)
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

    if payload_type == "tabung_update_action":
        await _handle_tabung_update_action(payload, update, context)
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

    if payload_type == "account_activity_back_to_menu":
        await _handle_account_activity_back_to_menu(update, context)
        return

    if payload_type == "mm_setting_back_to_menu":
        await _handle_mm_setting_back_to_menu(update, context)
        return

    if payload_type == "admin_panel_back_to_menu":
        await _handle_admin_panel_back_to_menu(update, context)
        return

    if payload_type == "records_reports_back_to_menu":
        await _handle_records_reports_back_to_menu(update, context)
        return

    if payload_type == "risk_calculator_back_to_menu":
        await _handle_risk_calculator_back_to_menu(update, context)
        return

    if payload_type == "notification_settings_save":
        await _handle_notification_settings_save(payload, update, context)
        return

    await send_screen(
        context,
        message.chat_id,
        "❌ Jenis data tak dikenali. Sila buka semula menu dan cuba lagi.",
        reply_markup=main_menu_keyboard(update.effective_user.id if update.effective_user else None),
    )
