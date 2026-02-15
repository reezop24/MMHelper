"""WebApp setup flow handlers."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from storage import save_user_setup
from texts import SETUP_SAVED_TEXT


async def handle_setup_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.reply_text("❌ Data setup tak sah. Cuba submit semula.")
        return

    if payload.get("type") != "setup_profile":
        return

    name = (payload.get("name") or "").strip()
    if not name:
        await message.reply_text("❌ Nama wajib diisi.")
        return

    try:
        initial_capital = float(payload.get("initial_capital_usd"))
        risk_per_trade = float(payload.get("risk_per_trade_pct"))
        max_daily_loss = float(payload.get("max_daily_loss_pct"))
        daily_profit_target = float(payload.get("daily_profit_target_pct"))
    except (TypeError, ValueError):
        await message.reply_text("❌ Nilai angka tak sah. Sila semak semula borang setup.")
        return

    if initial_capital <= 0:
        await message.reply_text("❌ Modal permulaan mesti lebih besar dari 0.")
        return

    numeric_values = [risk_per_trade, max_daily_loss, daily_profit_target]
    if any(v <= 0 for v in numeric_values):
        await message.reply_text("❌ Nilai peratus mesti lebih besar dari 0.")
        return

    save_user_setup(
        update.effective_user.id,
        {
            "name": name,
            "initial_capital_usd": initial_capital,
            "risk_per_trade_pct": risk_per_trade,
            "max_daily_loss_pct": max_daily_loss,
            "daily_profit_target_pct": daily_profit_target,
        },
    )

    await message.reply_text(SETUP_SAVED_TEXT)
