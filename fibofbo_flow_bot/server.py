#!/usr/bin/env python3
"""FiboFBO Flow bot (reset baseline: chart engine feeder only)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from active_leg_engine import ActiveLegConfig, evaluateActiveLeg, explainActiveLeg
from dbo import get_engine_status, load_candles
from fd_engine import evaluateFD
from impulse_engine import ImpulseConfig, detectImpulseAll, explainImpulse
from mtf_engine import MTFConfig, evaluateMTF, explainMTF
from retrace_engine import RetraceConfig, evaluateRetrace, explainRetrace
from swing_engine import detectSwingStructureAll, explainSwing
from unified_state import buildCompactSummary, buildUnifiedState


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


def _safe_env_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_ts_utc(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    s = raw.replace(" ", "T")
    if s.endswith("Z"):
        s = f"{s[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_market_closed_myt(ts: Any) -> bool:
    dt = _parse_ts_utc(ts)
    if dt is None:
        return False
    myt = dt.astimezone(timezone(timedelta(hours=8)))
    wd = myt.weekday()  # Mon=0 ... Sun=6
    mins = myt.hour * 60 + myt.minute
    if wd == 5 and mins >= 360:
        return True
    if wd == 6:
        return True
    if wd == 0 and mins < 420:
        return True
    return False


def _load_tf_candles(db_path: Path, timeframe: str, limit: int = 320) -> list[dict[str, Any]]:
    rows = load_candles(db_path=db_path, timeframe=timeframe, limit=limit)
    payload = [
        {"time": r.ts, "open": r.open, "high": r.high, "low": r.low, "close": r.close}
        for r in rows
    ]
    if timeframe in {"w1", "mn1"}:
        return payload
    return [r for r in payload if not _is_market_closed_myt(r.get("time"))]


def _fd_block_lines(title: str, block: dict[str, Any]) -> list[str]:
    b = block if isinstance(block, dict) else {}
    valid = bool(b.get("valid", True))
    if not valid:
        return [
            f"{title}:",
            "FD: invalid (price outside range)",
        ]
    ratio = b.get("ratio")
    ratio_txt = f"{float(ratio):.4f}" if isinstance(ratio, (int, float)) else "-"
    levels = b.get("levels") if isinstance(b.get("levels"), dict) else {}

    def _lvl(name: str) -> str:
        v = levels.get(name)
        return f"{float(v):.2f}" if isinstance(v, (int, float)) else "-"

    return [
        f"{title}:",
        f"ratio={ratio_txt}",
        f"side={b.get('side') or '-'}",
        f"zone={b.get('zone') or '-'}",
        f"reaction_zone={bool(b.get('reaction_zone'))}",
        f"shift_up={bool(b.get('shift_up'))}",
        f"shift_down={bool(b.get('shift_down'))}",
        f"L25={_lvl('L25')}",
        f"L50={_lvl('L50')}",
        f"L75={_lvl('L75')}",
    ]


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
        "/impulse - run impulse phase sensor (H4/H1/M30/M15)\n"
        "/activeleg - evaluate active leg decision layer\n"
        "/retrace - evaluate retrace context + readiness state\n"
        "/fd - evaluate FD positioning (external + impulse)\n"
        "/swing - evaluate wick-based swing structure (W1/D1/H4)\n"
        "/state - unified state snapshot\n"
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
    candle_rows = _load_tf_candles(db_path=db_path, timeframe=tf, limit=limit)
    if not candle_rows:
        await update.effective_message.reply_text(f"Tiada candle untuk TF {tf.upper()}.")
        return

    lines = [f"{tf.upper()} candles (last {len(candle_rows)}):"]
    for row in candle_rows[-min(len(candle_rows), 8):]:
        lines.append(
            f"{row.get('time')} | O:{float(row.get('open', 0.0)):.2f} H:{float(row.get('high', 0.0)):.2f} "
            f"L:{float(row.get('low', 0.0)):.2f} C:{float(row.get('close', 0.0)):.2f}"
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
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
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
        candles_by_tf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf,
        nowTimestamp=datetime.now(timezone.utc),
        config=cfg,
    )
    await update.effective_message.reply_text(explainMTF(result))


async def cmd_impulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])
    cfg = ImpulseConfig(
        swing_lookback=int(context.application.bot_data["impulse_swing_lookback"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    tf_map = {
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
    }
    candles_by_tf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map.items():
        candles_by_tf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    out = detectImpulseAll(candles_by_tf, cfg)
    blocks = ["XAUUSD Impulse Sensor"]
    for tf in ("H4", "H1", "M30", "M15"):
        blocks.append("")
        blocks.append(explainImpulse(out.get(tf, {})))
    await update.effective_message.reply_text("\n".join(blocks))


async def cmd_activeleg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])

    mtf_cfg = MTFConfig(
        score_min=int(context.application.bot_data["mtf_score_min"]),
        near_session_end_minutes=int(context.application.bot_data["mtf_near_end_min"]),
        daily_conflict_mode=str(context.application.bot_data["mtf_daily_conflict_mode"]),
        weekly_conflict_mode=str(context.application.bot_data["mtf_weekly_conflict_mode"]),
        swing_lookback=int(context.application.bot_data["mtf_swing_lookback"]),
        trend_swings_n=int(context.application.bot_data["mtf_trend_swings_n"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    impulse_cfg = ImpulseConfig(
        swing_lookback=int(context.application.bot_data["impulse_swing_lookback"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    active_cfg = ActiveLegConfig(
        h1_overextension_mult=_safe_env_float(context.application.bot_data["activeleg_h1_overext"], 1.2),
        m30_overextension_mult=_safe_env_float(context.application.bot_data["activeleg_m30_overext"], 1.5),
    )

    tf_map_mtf = {
        "W1": "w1",
        "D1": "d1",
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
    }
    candles_by_tf_mtf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map_mtf.items():
        candles_by_tf_mtf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    mtf_result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf_mtf,
        nowTimestamp=datetime.now(timezone.utc),
        config=mtf_cfg,
    )
    impulse_result = detectImpulseAll(
        {
            "H4": candles_by_tf_mtf["H4"],
            "H1": candles_by_tf_mtf["H1"],
            "M30": candles_by_tf_mtf["M30"],
            "M15": candles_by_tf_mtf["M15"],
        },
        impulse_cfg,
    )
    active_leg = evaluateActiveLeg(mtf_result, impulse_result, active_cfg)

    lines = [
        "XAUUSD Active Leg Check",
        "",
        explainActiveLeg(active_leg),
        "",
        "Phase Snapshot:",
    ]
    for tf in ("H4", "H1", "M30", "M15"):
        x = impulse_result.get(tf, {})
        lines.append(
            f"{tf}: {x.get('phase', '-')}/{x.get('direction', '-')}"
            f" (atr_ratio={float(x.get('atr_ratio', 0.0)):.2f})"
        )
    await update.effective_message.reply_text("\n".join(lines))


async def cmd_retrace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])

    mtf_cfg = MTFConfig(
        score_min=int(context.application.bot_data["mtf_score_min"]),
        near_session_end_minutes=int(context.application.bot_data["mtf_near_end_min"]),
        daily_conflict_mode=str(context.application.bot_data["mtf_daily_conflict_mode"]),
        weekly_conflict_mode=str(context.application.bot_data["mtf_weekly_conflict_mode"]),
        swing_lookback=int(context.application.bot_data["mtf_swing_lookback"]),
        trend_swings_n=int(context.application.bot_data["mtf_trend_swings_n"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    impulse_cfg = ImpulseConfig(
        swing_lookback=int(context.application.bot_data["impulse_swing_lookback"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    active_cfg = ActiveLegConfig(
        h1_overextension_mult=_safe_env_float(context.application.bot_data["activeleg_h1_overext"], 1.2),
        m30_overextension_mult=_safe_env_float(context.application.bot_data["activeleg_m30_overext"], 1.5),
    )
    retrace_cfg = RetraceConfig(
        enable_sweep=bool(context.application.bot_data["retrace_enable_sweep"]),
        sweep_ready_direct=bool(context.application.bot_data["retrace_sweep_ready_direct"]),
        sweep_require_micro_confirm=bool(context.application.bot_data["retrace_sweep_require_micro_confirm"]),
        sweep_max_reclaim_candles=int(context.application.bot_data["retrace_sweep_max_reclaim_candles"]),
        sweep_trigger_ratio=_safe_env_float(context.application.bot_data["retrace_sweep_trigger_ratio"], 0.9),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )

    tf_map_mtf = {
        "W1": "w1",
        "D1": "d1",
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
    }
    candles_by_tf_mtf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map_mtf.items():
        candles_by_tf_mtf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    mtf_result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf_mtf,
        nowTimestamp=datetime.now(timezone.utc),
        config=mtf_cfg,
    )
    impulse_result = detectImpulseAll(
        {
            "H4": candles_by_tf_mtf["H4"],
            "H1": candles_by_tf_mtf["H1"],
            "M30": candles_by_tf_mtf["M30"],
            "M15": candles_by_tf_mtf["M15"],
        },
        impulse_cfg,
    )
    active_leg = evaluateActiveLeg(mtf_result, impulse_result, active_cfg)
    retrace = evaluateRetrace(
        active_leg_result=active_leg,
        impulse_result=impulse_result,
        candlesByTF={
            "H4": candles_by_tf_mtf["H4"],
            "H1": candles_by_tf_mtf["H1"],
            "M30": candles_by_tf_mtf["M30"],
            "M15": candles_by_tf_mtf["M15"],
            "M5": candles_by_tf_mtf["M5"],
        },
        config=retrace_cfg,
    )

    lines = [
        "XAUUSD Retrace Check",
        "",
        explainActiveLeg(active_leg),
        "",
        explainRetrace(retrace),
    ]
    notes = [str(x) for x in (retrace.get("notes") or []) if str(x).strip()]
    if notes:
        lines.extend(["", "Notes:"] + [f"- {n}" for n in notes[:6]])
    await update.effective_message.reply_text("\n".join(lines))


async def cmd_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])

    mtf_cfg = MTFConfig(
        score_min=int(context.application.bot_data["mtf_score_min"]),
        near_session_end_minutes=int(context.application.bot_data["mtf_near_end_min"]),
        daily_conflict_mode=str(context.application.bot_data["mtf_daily_conflict_mode"]),
        weekly_conflict_mode=str(context.application.bot_data["mtf_weekly_conflict_mode"]),
        swing_lookback=int(context.application.bot_data["mtf_swing_lookback"]),
        trend_swings_n=int(context.application.bot_data["mtf_trend_swings_n"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    impulse_cfg = ImpulseConfig(
        swing_lookback=int(context.application.bot_data["impulse_swing_lookback"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )
    active_cfg = ActiveLegConfig(
        h1_overextension_mult=_safe_env_float(context.application.bot_data["activeleg_h1_overext"], 1.2),
        m30_overextension_mult=_safe_env_float(context.application.bot_data["activeleg_m30_overext"], 1.5),
    )
    retrace_cfg = RetraceConfig(
        enable_sweep=bool(context.application.bot_data["retrace_enable_sweep"]),
        sweep_ready_direct=bool(context.application.bot_data["retrace_sweep_ready_direct"]),
        sweep_require_micro_confirm=bool(context.application.bot_data["retrace_sweep_require_micro_confirm"]),
        sweep_max_reclaim_candles=int(context.application.bot_data["retrace_sweep_max_reclaim_candles"]),
        sweep_trigger_ratio=_safe_env_float(context.application.bot_data["retrace_sweep_trigger_ratio"], 0.9),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=_safe_env_float(context.application.bot_data["anomaly_range_multiplier"], 4.0),
        anomaly_wick_multiplier=_safe_env_float(context.application.bot_data["anomaly_wick_multiplier"], 2.0),
        anomaly_micro_range_ratio=_safe_env_float(context.application.bot_data["anomaly_micro_range_ratio"], 0.25),
    )

    tf_map_mtf = {
        "W1": "w1",
        "D1": "d1",
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
    }
    candles_by_tf_mtf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map_mtf.items():
        candles_by_tf_mtf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    mtf_result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf_mtf,
        nowTimestamp=datetime.now(timezone.utc),
        config=mtf_cfg,
    )
    impulse_result = detectImpulseAll(
        {
            "H4": candles_by_tf_mtf["H4"],
            "H1": candles_by_tf_mtf["H1"],
            "M30": candles_by_tf_mtf["M30"],
            "M15": candles_by_tf_mtf["M15"],
        },
        impulse_cfg,
    )
    active_leg = evaluateActiveLeg(mtf_result, impulse_result, active_cfg)
    retrace = evaluateRetrace(
        active_leg_result=active_leg,
        impulse_result=impulse_result,
        candlesByTF={
            "H4": candles_by_tf_mtf["H4"],
            "H1": candles_by_tf_mtf["H1"],
            "M30": candles_by_tf_mtf["M30"],
            "M15": candles_by_tf_mtf["M15"],
            "M5": candles_by_tf_mtf["M5"],
        },
        config=retrace_cfg,
    )

    candle_index = len(candles_by_tf_mtf.get("M5", [])) - 1
    timestamp = (
        str(candles_by_tf_mtf.get("M5", [])[-1].get("time"))
        if candles_by_tf_mtf.get("M5")
        else datetime.now(timezone.utc).isoformat()
    )
    state = buildUnifiedState(
        candle_index=candle_index,
        timestamp=timestamp,
        mtf_result=mtf_result,
        impulse_result=impulse_result,
        active_leg_result=active_leg,
        retrace_result=retrace,
    )

    summary = buildCompactSummary(state)
    await update.effective_message.reply_text(
        "\n".join(
            [
                "XAUUSD Unified State",
                summary,
                "",
                f"TradeReady={state['summary'].get('trade_ready')} | MTFScore={state['summary'].get('mtf_score')}",
                f"Bias={state['summary'].get('bias')} | ActiveTF={state['summary'].get('active_tf')}",
                f"Leg={state['summary'].get('leg_state')} | Action={state['summary'].get('leg_action')}",
                f"Retrace={state['summary'].get('retrace_status')}/{state['summary'].get('retrace_depth')}",
                f"ReadyForSetup={state['summary'].get('ready_for_setup')}",
                "",
                *_fd_block_lines("External", (state.get("fd") or {}).get("swing") or {}),
                "",
                *_fd_block_lines("Impulse", (state.get("fd") or {}).get("impulse") or {}),
            ]
        )
    )


async def cmd_fd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])
    mtf_cfg = MTFConfig(
        score_min=int(context.application.bot_data["mtf_score_min"]),
        near_session_end_minutes=int(context.application.bot_data["mtf_near_end_min"]),
        daily_conflict_mode=str(context.application.bot_data["mtf_daily_conflict_mode"]),
        weekly_conflict_mode=str(context.application.bot_data["mtf_weekly_conflict_mode"]),
        swing_lookback=int(context.application.bot_data["mtf_swing_lookback"]),
        trend_swings_n=int(context.application.bot_data["mtf_trend_swings_n"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=float(context.application.bot_data["anomaly_range_multiplier"]),
        anomaly_wick_multiplier=float(context.application.bot_data["anomaly_wick_multiplier"]),
        anomaly_micro_range_ratio=float(context.application.bot_data["anomaly_micro_range_ratio"]),
    )
    impulse_cfg = ImpulseConfig(
        swing_lookback=int(context.application.bot_data["impulse_swing_lookback"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=float(context.application.bot_data["anomaly_range_multiplier"]),
        anomaly_wick_multiplier=float(context.application.bot_data["anomaly_wick_multiplier"]),
        anomaly_micro_range_ratio=float(context.application.bot_data["anomaly_micro_range_ratio"]),
    )
    active_cfg = ActiveLegConfig(
        h1_overextension_mult=float(context.application.bot_data["activeleg_h1_overext"]),
        m30_overextension_mult=float(context.application.bot_data["activeleg_m30_overext"]),
        anomaly_filter_enabled=bool(context.application.bot_data["anomaly_filter_enabled"]),
        anomaly_range_multiplier=float(context.application.bot_data["anomaly_range_multiplier"]),
        anomaly_wick_multiplier=float(context.application.bot_data["anomaly_wick_multiplier"]),
        anomaly_micro_range_ratio=float(context.application.bot_data["anomaly_micro_range_ratio"]),
    )

    tf_map_mtf = {
        "W1": "w1",
        "D1": "d1",
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
    }
    candles_by_tf_mtf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map_mtf.items():
        candles_by_tf_mtf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    mtf_result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf_mtf,
        nowTimestamp=datetime.now(timezone.utc),
        config=mtf_cfg,
    )
    impulse_result = detectImpulseAll(
        {
            "H4": candles_by_tf_mtf["H4"],
            "H1": candles_by_tf_mtf["H1"],
            "M30": candles_by_tf_mtf["M30"],
            "M15": candles_by_tf_mtf["M15"],
        },
        impulse_cfg,
    )
    active_leg = evaluateActiveLeg(mtf_result, impulse_result, active_cfg)
    fd = evaluateFD(mtf_result, active_leg)

    ext = (fd.get("swing") or fd.get("external") or {}) if isinstance(fd, dict) else {}
    imp = (fd.get("impulse") or {}) if isinstance(fd, dict) else {}

    await update.effective_message.reply_text(
        "\n".join(
            [
                "XAUUSD FD Positioning",
                "",
                *_fd_block_lines("External", ext),
                "",
                *_fd_block_lines("Impulse", imp),
            ]
        )
    )


async def cmd_swing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = Path(context.application.bot_data["candles_db"])
    tf_map = {"W1": "w1", "D1": "d1", "H4": "h4"}
    candles_by_tf: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map.items():
        candles_by_tf[tf] = _load_tf_candles(db_path=db_path, timeframe=tf_key, limit=320)

    swing = detectSwingStructureAll(candles_by_tf)
    lines = ["XAUUSD Swing Structure", ""]
    for tf in ("W1", "D1", "H4"):
        lines.append(explainSwing(swing.get(tf) or {"tf": tf}))
        lines.append("")
    await update.effective_message.reply_text("\n".join(lines).rstrip())


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
    impulse_swing_lookback = max(1, int(get_env("FIBOFBO_FLOW_IMPULSE_SWING_LOOKBACK", "2")))
    activeleg_h1_overext = _safe_env_float(get_env("FIBOFBO_FLOW_ACTIVELEG_H1_OVEREXT", "1.2"), 1.2)
    activeleg_m30_overext = _safe_env_float(get_env("FIBOFBO_FLOW_ACTIVELEG_M30_OVEREXT", "1.5"), 1.5)
    retrace_enable_sweep = get_env("FIBOFBO_FLOW_RETRACE_ENABLE_SWEEP", "1").lower() in {"1", "true", "yes", "on"}
    retrace_sweep_ready_direct = get_env("FIBOFBO_FLOW_RETRACE_SWEEP_READY_DIRECT", "1").lower() in {"1", "true", "yes", "on"}
    retrace_sweep_require_micro_confirm = get_env("FIBOFBO_FLOW_RETRACE_SWEEP_REQUIRE_MICRO_CONFIRM", "1").lower() in {"1", "true", "yes", "on"}
    retrace_sweep_max_reclaim_candles = max(
        1, int(get_env("FIBOFBO_FLOW_RETRACE_SWEEP_MAX_RECLAIM_CANDLES", "3"))
    )
    retrace_sweep_trigger_ratio = _safe_env_float(
        get_env("FIBOFBO_FLOW_RETRACE_SWEEP_TRIGGER_RATIO", "0.9"), 0.9
    )
    anomaly_filter_enabled = get_env("FIBOFBO_FLOW_ANOMALY_FILTER_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
    anomaly_range_multiplier = _safe_env_float(get_env("FIBOFBO_FLOW_ANOMALY_RANGE_MULTIPLIER", "4.0"), 4.0)
    anomaly_wick_multiplier = _safe_env_float(get_env("FIBOFBO_FLOW_ANOMALY_WICK_MULTIPLIER", "2.0"), 2.0)
    anomaly_micro_range_ratio = _safe_env_float(get_env("FIBOFBO_FLOW_ANOMALY_MICRO_RANGE_RATIO", "0.25"), 0.25)

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
    app.bot_data["impulse_swing_lookback"] = impulse_swing_lookback
    app.bot_data["activeleg_h1_overext"] = activeleg_h1_overext
    app.bot_data["activeleg_m30_overext"] = activeleg_m30_overext
    app.bot_data["retrace_enable_sweep"] = retrace_enable_sweep
    app.bot_data["retrace_sweep_ready_direct"] = retrace_sweep_ready_direct
    app.bot_data["retrace_sweep_require_micro_confirm"] = retrace_sweep_require_micro_confirm
    app.bot_data["retrace_sweep_max_reclaim_candles"] = retrace_sweep_max_reclaim_candles
    app.bot_data["retrace_sweep_trigger_ratio"] = retrace_sweep_trigger_ratio
    app.bot_data["anomaly_filter_enabled"] = anomaly_filter_enabled
    app.bot_data["anomaly_range_multiplier"] = anomaly_range_multiplier
    app.bot_data["anomaly_wick_multiplier"] = anomaly_wick_multiplier
    app.bot_data["anomaly_micro_range_ratio"] = anomaly_micro_range_ratio

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("engine", cmd_engine))
    app.add_handler(CommandHandler("candles", cmd_candles))
    app.add_handler(CommandHandler("dbo", cmd_dbo))
    app.add_handler(CommandHandler("mtf", cmd_mtf))
    app.add_handler(CommandHandler("impulse", cmd_impulse))
    app.add_handler(CommandHandler("activeleg", cmd_activeleg))
    app.add_handler(CommandHandler("retrace", cmd_retrace))
    app.add_handler(CommandHandler("fd", cmd_fd))
    app.add_handler(CommandHandler("swing", cmd_swing))
    app.add_handler(CommandHandler("state", cmd_state))
    app.add_handler(CommandHandler("unified", cmd_state))

    LOGGER.info(
        "Starting FiboFBO Flow baseline bot (signal_file=%s candles_db=%s default_tf=%s)",
        signal_file,
        candles_db,
        default_tf,
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
