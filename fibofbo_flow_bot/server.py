#!/usr/bin/env python3
"""FiboFBO Flow bot (reset baseline: chart engine feeder only)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from dbo import get_engine_status, load_candles
from mtf_engine import MTFConfig, evaluateMTF, explainMTF


LOGGER = logging.getLogger("fibofbo_flow_bot")
BASE_DIR = Path(__file__).resolve().parent
VALID_TFS = {"m5", "m15", "m30", "h1", "h4", "d1", "w1", "mn1"}


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
        "FiboFBO Flow baseline aktif (logic reset).\n"
        "Commands:\n"
        "/ping - health check\n"
        "/signal - latest feeder signal\n"
        "/engine [tf] - status chart engine (cth: /engine h1)\n"
        "/candles [tf] [limit] - preview candle terakhir\n"
        "/mtf - run MTF Bias + Scoring check\n"
        "/dbo - status reset logic"
    )
    await update.effective_message.reply_text(msg)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("pong")


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    signal_file = Path(context.application.bot_data["signal_file"])
    payload = read_latest_signal(signal_file)
    if payload is None:
        await update.effective_message.reply_text(
            f"Signal belum ada atau fail tak valid.\\nPath: {signal_file}"
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


async def cmd_engine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tf = str(context.application.bot_data["default_tf"])
    if context.args:
        tf = str(context.args[0]).strip().lower()
    if tf not in VALID_TFS:
        await update.effective_message.reply_text(
            f"TF tak sah: {tf}\\nGunakan: {', '.join(sorted(VALID_TFS))}"
        )
        return

    db_path = Path(context.application.bot_data["candles_db"])
    status = get_engine_status(db_path=db_path, timeframe=tf, limit=5)
    if status.get("status") != "OK":
        await update.effective_message.reply_text(
            f"Engine {tf.upper()}: NO_DATA\\nDB: {db_path}"
        )
        return

    latest = status.get("latest") or {}
    lines = [
        f"Engine {tf.upper()} status: OK",
        f"count(last5): {status.get('count')}",
        f"latest_ts: {latest.get('ts', '-')}",
        (
            "latest_ohlc: "
            f"O={float(latest.get('open', 0.0)):.2f} "
            f"H={float(latest.get('high', 0.0)):.2f} "
            f"L={float(latest.get('low', 0.0)):.2f} "
            f"C={float(latest.get('close', 0.0)):.2f}"
        ),
    ]
    await update.effective_message.reply_text("\n".join(lines))


async def cmd_candles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tf = str(context.application.bot_data["default_tf"])
    limit = 10
    if context.args:
        tf = str(context.args[0]).strip().lower()
    if len(context.args) > 1:
        try:
            limit = int(context.args[1])
        except ValueError:
            limit = 10
    limit = max(1, min(limit, 30))

    if tf not in VALID_TFS:
        await update.effective_message.reply_text(
            f"TF tak sah: {tf}\\nGunakan: {', '.join(sorted(VALID_TFS))}"
        )
        return

    db_path = Path(context.application.bot_data["candles_db"])
    candles = load_candles(db_path=db_path, timeframe=tf, limit=limit)
    if not candles:
        await update.effective_message.reply_text(f"Tiada candle untuk TF {tf.upper()}.")
        return

    lines = [f"{tf.upper()} candles (last {len(candles)}):"]
    for row in candles[-min(len(candles), 8):]:
        lines.append(
            f"{row.ts} | O:{row.open:.2f} H:{row.high:.2f} L:{row.low:.2f} C:{row.close:.2f}"
        )
    await update.effective_message.reply_text("\n".join(lines))


async def cmd_dbo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Logic DBO/FE lama dah dipadam (reset baseline).\n"
        "Sekarang bot hanya feeder chart-engine."
    )


async def cmd_mtf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])
    cfg = MTFConfig(
        score_min=int(context.application.bot_data["mtf_score_min"]),
        near_session_end_minutes=int(context.application.bot_data["mtf_near_end_min"]),
        daily_conflict_mode=str(context.application.bot_data["mtf_daily_conflict_mode"]),
        weekly_conflict_mode=str(context.application.bot_data["mtf_weekly_conflict_mode"]),
        swing_lookback=int(context.application.bot_data["mtf_swing_lookback"]),
        trend_swings_n=int(context.application.bot_data["mtf_trend_swings_n"]),
    )
    tf_map = {
        "W1": "w1",
        "D1": "d1",
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
    }
    candles_by_tf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map.items():
        rows = load_candles(db_path=db_path, timeframe=tf_key, limit=320)
        candles_by_tf[tf] = [
            {
                "time": r.ts,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
            }
            for r in rows
        ]

    result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf,
        nowTimestamp=datetime.now(timezone.utc),
        config=cfg,
    )
    await update.effective_message.reply_text(explainMTF(result))


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
    candles_db = Path(
        get_env("FIBOFBO_FLOW_CANDLES_DB", "/root/mmhelper/db/twelve_data_bot/candles.db")
    ).resolve()
    default_tf = get_env("FIBOFBO_FLOW_DEFAULT_TF", "h1").lower()
    if default_tf not in VALID_TFS:
        default_tf = "h1"
    mtf_score_min = max(1, min(int(get_env("FIBOFBO_FLOW_MTF_SCORE_MIN", "7")), 10))
    mtf_near_end_min = max(1, int(get_env("FIBOFBO_FLOW_MTF_NEAR_END_MIN", "45")))
    mtf_daily_conflict_mode = get_env("FIBOFBO_FLOW_DAILY_CONFLICT_MODE", "soft").lower()
    mtf_weekly_conflict_mode = get_env("FIBOFBO_FLOW_WEEKLY_CONFLICT_MODE", "soft").lower()
    if mtf_daily_conflict_mode not in {"soft", "strict"}:
        mtf_daily_conflict_mode = "soft"
    if mtf_weekly_conflict_mode not in {"soft", "ignore"}:
        mtf_weekly_conflict_mode = "soft"
    mtf_swing_lookback = max(1, int(get_env("FIBOFBO_FLOW_MTF_SWING_LOOKBACK", "2")))
    mtf_trend_swings_n = max(3, int(get_env("FIBOFBO_FLOW_MTF_TREND_SWINGS_N", "4")))

    app = ApplicationBuilder().token(bot_token).build()
    app.bot_data["signal_file"] = str(signal_file)
    app.bot_data["candles_db"] = str(candles_db)
    app.bot_data["default_tf"] = default_tf
    app.bot_data["mtf_score_min"] = mtf_score_min
    app.bot_data["mtf_near_end_min"] = mtf_near_end_min
    app.bot_data["mtf_daily_conflict_mode"] = mtf_daily_conflict_mode
    app.bot_data["mtf_weekly_conflict_mode"] = mtf_weekly_conflict_mode
    app.bot_data["mtf_swing_lookback"] = mtf_swing_lookback
    app.bot_data["mtf_trend_swings_n"] = mtf_trend_swings_n

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("engine", cmd_engine))
    app.add_handler(CommandHandler("candles", cmd_candles))
    app.add_handler(CommandHandler("dbo", cmd_dbo))
    app.add_handler(CommandHandler("mtf", cmd_mtf))

    LOGGER.info(
        "Starting FiboFBO Flow baseline bot (signal_file=%s candles_db=%s default_tf=%s)",
        signal_file,
        candles_db,
        default_tf,
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
