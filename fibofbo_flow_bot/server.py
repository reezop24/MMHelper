#!/usr/bin/env python3
"""Telegram bot scaffold for FiboFBO Flow."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from dbo import detect_dbo, find_pivots, load_candles


LOGGER = logging.getLogger("fibofbo_flow_bot")
BASE_DIR = Path(__file__).resolve().parent


def load_local_env() -> None:
    env_path = BASE_DIR / ".env"
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


def get_env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def read_latest_signal(signal_file: Path) -> dict[str, Any] | None:
    if not signal_file.exists():
        return None
    try:
        loaded = json.loads(signal_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "FiboFBO Flow bot online.\n"
        "Commands:\n"
        "/ping - health check\n"
        "/signal - latest feeder signal\n"
        "/dbo [tf] - DBO setup/trigger check (cth: /dbo m5)\n"
        "/dbochart - buka chart viewer miniapp"
    )
    await update.effective_message.reply_text(msg)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("pong")


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    signal_file = Path(context.application.bot_data["signal_file"])
    payload = read_latest_signal(signal_file)
    if payload is None:
        await update.effective_message.reply_text(
            f"Signal belum ada atau fail tak valid.\nPath: {signal_file}"
        )
        return

    signal = str(payload.get("signal") or "UNKNOWN")
    symbol = str(payload.get("symbol") or "N/A")
    tf = str(payload.get("timeframe") or "N/A")
    as_of = str(payload.get("as_of") or payload.get("updated_at") or "N/A")
    reason = str(payload.get("reason") or "-")

    lines = [
        "FiboFBO Flow Signal",
        f"symbol: {symbol}",
        f"timeframe: {tf}",
        f"signal: {signal}",
        f"as_of: {as_of}",
        f"reason: {reason}",
    ]
    await update.effective_message.reply_text("\n".join(lines))


async def cmd_dbo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    default_tf = str(context.application.bot_data["dbo_default_tf"])
    tf = default_tf
    if context.args:
        tf = str(context.args[0]).strip().lower()

    valid_tfs = {"m5", "m15", "m30", "h1", "h4"}
    if tf not in valid_tfs:
        await update.effective_message.reply_text(
            f"TF tak sah: {tf}\nGunakan: {', '.join(sorted(valid_tfs))}"
        )
        return

    db_path = Path(context.application.bot_data["candles_db"])
    lookback = int(context.application.bot_data["dbo_lookback"])

    candles = load_candles(db_path=db_path, timeframe=tf, limit=lookback)
    pivots = find_pivots(candles=candles, swing_window=2)
    result = detect_dbo(candles=candles, pivots=pivots)

    if result.get("status") == "NO_SETUP":
        await update.effective_message.reply_text(
            f"DBO {tf.upper()}: NO_SETUP\ncandles={len(candles)} pivots={len(pivots)}"
        )
        return

    points = result.get("points") or {}
    ls = points.get("left_shoulder", {})
    hd = points.get("head", {})
    rs = points.get("right_shoulder", {})
    lines = [
        f"DBO {tf.upper()}",
        f"status: {result.get('status')}",
        f"side: {result.get('side')}",
        f"pattern: {result.get('pattern')}",
        f"trigger_level: {float(result.get('trigger_level', 0.0)):.2f}",
        f"latest_close: {float(result.get('latest_close', 0.0)):.2f}",
        f"LS: {ls.get('ts', '-')}, {float(ls.get('price', 0.0)):.2f}",
        f"Head: {hd.get('ts', '-')}, {float(hd.get('price', 0.0)):.2f}",
        f"RS: {rs.get('ts', '-')}, {float(rs.get('price', 0.0)):.2f}",
    ]
    await update.effective_message.reply_text("\n".join(lines))


async def cmd_dbochart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = str(context.application.bot_data["dbo_chart_url"])
    await update.effective_message.reply_text(f"DBO chart viewer:\n{url}")


def main() -> None:
    load_local_env()
    log_level = get_env("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot_token = get_env("FIBOFBO_FLOW_BOT_TOKEN") or get_env("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Set FIBOFBO_FLOW_BOT_TOKEN in fibofbo_flow_bot/.env")

    signal_file = Path(
        get_env("FIBOFBO_FLOW_SIGNAL_FILE", "/root/mmhelper/db/twelve_data_bot/latest_signal.json")
    ).resolve()
    candles_db = Path(get_env("FIBOFBO_FLOW_CANDLES_DB", "/root/mmhelper/db/twelve_data_bot/candles.db")).resolve()
    dbo_default_tf = get_env("FIBOFBO_FLOW_DBO_TF", "m5").lower()
    dbo_lookback = int(get_env("FIBOFBO_FLOW_DBO_LOOKBACK", "600"))
    dbo_chart_url = get_env("FIBOFBO_FLOW_DBO_CHART_URL", "https://mm-helper.vercel.app/dbo-viewer.html")

    app = ApplicationBuilder().token(bot_token).build()
    app.bot_data["signal_file"] = str(signal_file)
    app.bot_data["candles_db"] = str(candles_db)
    app.bot_data["dbo_default_tf"] = dbo_default_tf
    app.bot_data["dbo_lookback"] = dbo_lookback
    app.bot_data["dbo_chart_url"] = dbo_chart_url
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("dbo", cmd_dbo))
    app.add_handler(CommandHandler("dbochart", cmd_dbochart))

    LOGGER.info(
        "Starting FiboFBO Flow bot (signal_file=%s candles_db=%s dbo_default_tf=%s)",
        signal_file,
        candles_db,
        dbo_default_tf,
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
