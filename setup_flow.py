"""WebApp setup flow handlers."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from menu import main_menu_keyboard
from storage import save_user_setup_section
from texts import SETUP_SAVED_TEXT
from ui import send_screen


async def handle_setup_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await send_screen(context, message.chat_id, "❌ Eh data tak lepas. Cuba submit lagi sekali.")
        return

    if payload.get("type") != "setup_profile":
        return

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
    )
