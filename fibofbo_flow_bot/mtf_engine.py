from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


TF_ORDER = ["W1", "D1", "H4", "H1", "M30", "M15", "M5"]


@dataclass
class SessionWindow:
    name: str
    start_minute: int
    end_minute: int

    def contains(self, minute_of_day: int) -> bool:
        if self.start_minute <= self.end_minute:
            return self.start_minute <= minute_of_day <= self.end_minute
        return minute_of_day >= self.start_minute or minute_of_day <= self.end_minute


@dataclass
class MTFConfig:
    swing_lookback: int = 2
    trend_swings_n: int = 4
    near_session_end_minutes: int = 45
    score_min: int = 7
    daily_conflict_mode: str = "soft"  # strict|soft
    weekly_conflict_mode: str = "soft"  # ignore|soft
    soft_conflict_points: int = 1
    score_weights: dict[str, int] = field(
        default_factory=lambda: {
            "h4": 3,
            "daily": 2,
            "weekly": 1,
            "bridge": 2,
            "execution": 1,
            "session": 1,
        }
    )
    # MYT sessions (minutes from 00:00).
    sessions: list[SessionWindow] = field(
        default_factory=lambda: [
            SessionWindow("ASIA", 7 * 60, 14 * 60 + 59),
            SessionWindow("LONDON", 15 * 60, 20 * 60 + 59),
            SessionWindow("NEW_YORK", 21 * 60, 5 * 60 + 59),
        ]
    )


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows or []):
        if not isinstance(row, dict):
            continue
        o = _to_float(row.get("open"))
        h = _to_float(row.get("high"))
        l = _to_float(row.get("low"))
        c = _to_float(row.get("close"))
        ts = str(row.get("ts") or row.get("time") or "")
        if h == 0.0 and l == 0.0 and o == 0.0 and c == 0.0:
            continue
        out.append({"idx": idx, "ts": ts, "open": o, "high": h, "low": l, "close": c})
    return out


def _detect_swings(candles: list[dict[str, Any]], lookback: int) -> list[dict[str, Any]]:
    swings: list[dict[str, Any]] = []
    if len(candles) < (lookback * 2 + 1):
        return swings

    for i in range(lookback, len(candles) - lookback):
        center = candles[i]
        left = candles[i - lookback : i]
        right = candles[i + 1 : i + lookback + 1]
        others = left + right
        if not others:
            continue

        is_high = all(center["high"] > x["high"] for x in others)
        is_low = all(center["low"] < x["low"] for x in others)

        if is_high:
            swings.append({"idx": i, "ts": center["ts"], "kind": "H", "price": center["high"]})
        elif is_low:
            swings.append({"idx": i, "ts": center["ts"], "kind": "L", "price": center["low"]})

    # compress same-kind contiguous picks
    compressed: list[dict[str, Any]] = []
    for s in swings:
        if not compressed:
            compressed.append(s)
            continue
        prev = compressed[-1]
        if prev["kind"] != s["kind"]:
            compressed.append(s)
            continue
        if s["kind"] == "H" and s["price"] > prev["price"]:
            compressed[-1] = s
        if s["kind"] == "L" and s["price"] < prev["price"]:
            compressed[-1] = s
    return compressed


def _last_bos(candles: list[dict[str, Any]], swings: list[dict[str, Any]]) -> str:
    if len(swings) < 3:
        return "NONE"
    highs = [s for s in swings if s["kind"] == "H"]
    lows = [s for s in swings if s["kind"] == "L"]
    if not highs or not lows:
        return "NONE"

    ref_high = highs[-1]["price"]
    ref_low = lows[-1]["price"]
    up_idx = -1
    dn_idx = -1
    for i, c in enumerate(candles):
        close = c["close"]
        if close > ref_high:
            up_idx = i
        if close < ref_low:
            dn_idx = i
    if up_idx < 0 and dn_idx < 0:
        # Fallback for synthetic/early market states:
        # infer BOS direction from last swing progression.
        if len(highs) >= 2 and len(lows) >= 2:
            if highs[-1]["price"] > highs[-2]["price"] and lows[-1]["price"] > lows[-2]["price"]:
                return "UP"
            if highs[-1]["price"] < highs[-2]["price"] and lows[-1]["price"] < lows[-2]["price"]:
                return "DOWN"
        return "NONE"
    if up_idx > dn_idx:
        return "UP"
    if dn_idx > up_idx:
        return "DOWN"
    return "NONE"


def _phase_from_bias(candles: list[dict[str, Any]], bias: str, last_high: dict[str, Any] | None, last_low: dict[str, Any] | None) -> str:
    if not candles or bias not in {"BULL", "BEAR"}:
        return "UNKNOWN"
    if not last_high or not last_low:
        return "UNKNOWN"
    close = candles[-1]["close"]

    hi = float(last_high["price"])
    lo = float(last_low["price"])
    span = max(hi - lo, 1e-9)

    if bias == "BULL":
        retrace = (hi - close) / span
        return "PULLBACK" if retrace > 0.22 else "EXPANSION"
    retrace = (close - lo) / span
    return "PULLBACK" if retrace > 0.22 else "EXPANSION"


def analyze_tf(tf: str, candles_raw: list[dict[str, Any]], cfg: MTFConfig) -> dict[str, Any]:
    candles = _norm_candles(candles_raw)
    swings = _detect_swings(candles, cfg.swing_lookback)
    highs = [s for s in swings if s["kind"] == "H"]
    lows = [s for s in swings if s["kind"] == "L"]

    last_high = highs[-1] if highs else None
    last_low = lows[-1] if lows else None
    last_bos = _last_bos(candles, swings)

    bias = "RANGE"
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1]["price"] > highs[-2]["price"]
        hl = lows[-1]["price"] > lows[-2]["price"]
        ll = lows[-1]["price"] < lows[-2]["price"]
        lh = highs[-1]["price"] < highs[-2]["price"]

        if hh and hl:
            bias = "BULL"
            if last_bos == "NONE":
                last_bos = "UP"
        elif ll and lh:
            bias = "BEAR"
            if last_bos == "NONE":
                last_bos = "DOWN"

    if len(swings) < max(cfg.trend_swings_n, 4):
        bias = "RANGE"

    phase = _phase_from_bias(candles, bias, last_high, last_low)
    return {
        "tf": tf,
        "bias": bias,
        "lastBOS": last_bos,
        "lastSwingHigh": last_high,
        "lastSwingLow": last_low,
        "phase": phase,
        "swings": swings,
        "candles_count": len(candles),
        "last_close": candles[-1]["close"] if candles else None,
    }


def _to_myt(now_ts: datetime | str | int | float) -> datetime:
    tz = timezone(timedelta(hours=8))
    if isinstance(now_ts, datetime):
        if now_ts.tzinfo is None:
            return now_ts.replace(tzinfo=tz)
        return now_ts.astimezone(tz)
    if isinstance(now_ts, (int, float)):
        return datetime.fromtimestamp(float(now_ts), tz=tz)
    text = str(now_ts).strip()
    if not text:
        return datetime.now(tz)
    text = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _session_state(now_ts: datetime | str | int | float, cfg: MTFConfig, open_position_session: str | None = None) -> dict[str, Any]:
    now = _to_myt(now_ts)
    minute = now.hour * 60 + now.minute

    picked: SessionWindow | None = None
    for s in cfg.sessions:
        if s.contains(minute):
            picked = s
            break

    if picked is None:
        return {
            "session": "NONE",
            "active": False,
            "minutes_left": 0,
            "near_end": True,
            "can_trade": False,
            "must_close": False,
            "session_exit": bool(open_position_session),
            "notes": ["No active trading session"],
        }

    end = picked.end_minute
    if picked.start_minute <= picked.end_minute:
        minutes_left = max(0, end - minute)
    else:
        if minute <= end:
            minutes_left = end - minute
        else:
            minutes_left = (24 * 60 - minute) + end

    near_end = minutes_left <= cfg.near_session_end_minutes
    session_exit = bool(open_position_session and open_position_session != picked.name)
    return {
        "session": picked.name,
        "active": True,
        "minutes_left": minutes_left,
        "near_end": near_end,
        "can_trade": not near_end,
        "must_close": near_end,
        "session_exit": session_exit,
        "notes": [
            (
                "Position crossed session -> force close(session_exit)"
                if session_exit
                else "Session OK"
            )
        ],
    }


def _bridge_state(h4_bias: str, h1: dict[str, Any], m30: dict[str, Any]) -> dict[str, Any]:
    notes: list[str] = []
    if h4_bias not in {"BULL", "BEAR"}:
        return {
            "bridge_ok": False,
            "bridge_bias": "RANGE",
            "minorBOSAligned": False,
            "conflict": False,
            "notes": ["H4 not directional"],
        }

    want_bos = "UP" if h4_bias == "BULL" else "DOWN"
    aligned_candidates = []
    for x in (h1, m30):
        if x.get("bias") == h4_bias:
            aligned_candidates.append(x)

    minor_bos_aligned = any(x.get("lastBOS") == want_bos for x in aligned_candidates)
    weak_ok = bool(aligned_candidates)

    conflict = any(
        x.get("bias") in {"BULL", "BEAR"} and x.get("bias") != h4_bias
        for x in (h1, m30)
    )

    if minor_bos_aligned:
        notes.append(f"minor BOS {want_bos} aligned on bridge")
    elif weak_ok:
        notes.append("bridge bias aligns but BOS not strong yet")
    else:
        notes.append("bridge not aligned")

    if conflict:
        notes.append("bridge conflict detected")

    bridge_bias = h1.get("bias") if h1.get("bias") in {"BULL", "BEAR"} else m30.get("bias", "RANGE")
    return {
        "bridge_ok": bool(minor_bos_aligned or weak_ok),
        "bridge_bias": bridge_bias if bridge_bias in {"BULL", "BEAR"} else "RANGE",
        "minorBOSAligned": bool(minor_bos_aligned),
        "conflict": bool(conflict),
        "notes": notes,
    }


def _execution_state(h4_bias: str, m15: dict[str, Any], m5: dict[str, Any]) -> dict[str, Any]:
    exec_bias = m15.get("bias") if m15.get("bias") in {"BULL", "BEAR"} else m5.get("bias", "RANGE")
    exec_align = h4_bias in {"BULL", "BEAR"} and exec_bias == h4_bias
    notes = []
    if exec_align:
        notes.append("M15/M5 aligned with H4")
    else:
        notes.append("Execution layer not aligned")
    return {
        "exec_align": bool(exec_align),
        "exec_bias": exec_bias if exec_bias in {"BULL", "BEAR"} else "RANGE",
        "exec_notes": notes,
    }


def evaluateMTF(
    symbol: str,
    candlesByTF: dict[str, list[dict[str, Any]]],
    nowTimestamp: datetime | str | int | float,
    config: MTFConfig | None = None,
    open_position_session: str | None = None,
) -> dict[str, Any]:
    cfg = config or MTFConfig()

    tf_states: dict[str, dict[str, Any]] = {}
    for tf in TF_ORDER:
        tf_states[tf] = analyze_tf(tf=tf, candles_raw=candlesByTF.get(tf, []), cfg=cfg)

    h4 = tf_states["H4"]
    d1 = tf_states["D1"]
    w1 = tf_states["W1"]
    h1 = tf_states["H1"]
    m30 = tf_states["M30"]
    m15 = tf_states["M15"]
    m5 = tf_states["M5"]

    session = _session_state(nowTimestamp, cfg, open_position_session=open_position_session)
    bridge = _bridge_state(h4.get("bias", "RANGE"), h1, m30)
    execution = _execution_state(h4.get("bias", "RANGE"), m15, m5)

    w = cfg.score_weights
    breakdown = {"h4": 0, "daily": 0, "weekly": 0, "bridge": 0, "execution": 0, "session": 0}
    conflicts: list[str] = []
    notes: list[str] = []

    h4_bias = h4.get("bias")
    if h4_bias in {"BULL", "BEAR"}:
        breakdown["h4"] = int(w.get("h4", 3))
    else:
        notes.append("H4 not directional")

    d1_bias = d1.get("bias")
    if h4_bias in {"BULL", "BEAR"} and d1_bias == h4_bias:
        breakdown["daily"] = int(w.get("daily", 2))
    elif d1_bias in {"BULL", "BEAR"} and h4_bias in {"BULL", "BEAR"} and d1_bias != h4_bias:
        conflicts.append("D1_vs_H4")
        if cfg.daily_conflict_mode == "soft":
            breakdown["daily"] = min(int(w.get("daily", 2)), int(cfg.soft_conflict_points))
        else:
            breakdown["daily"] = 0

    w1_bias = w1.get("bias")
    if h4_bias in {"BULL", "BEAR"} and w1_bias == h4_bias:
        breakdown["weekly"] = int(w.get("weekly", 1))
    elif w1_bias in {"BULL", "BEAR"} and h4_bias in {"BULL", "BEAR"} and w1_bias != h4_bias:
        conflicts.append("W1_vs_H4")
        if cfg.weekly_conflict_mode == "soft":
            breakdown["weekly"] = min(int(w.get("weekly", 1)), int(cfg.soft_conflict_points))
        else:
            breakdown["weekly"] = 0

    if bridge.get("bridge_ok") and bridge.get("minorBOSAligned"):
        breakdown["bridge"] = int(w.get("bridge", 2))
    elif bridge.get("bridge_ok"):
        breakdown["bridge"] = 1
        notes.append("Bridge OK but weak")
    else:
        breakdown["bridge"] = 0
        conflicts.append("Bridge_fail")

    if execution.get("exec_align"):
        breakdown["execution"] = int(w.get("execution", 1))
    else:
        breakdown["execution"] = 0
        conflicts.append("Exec_conflict")

    if session.get("active") and session.get("can_trade"):
        breakdown["session"] = int(w.get("session", 1))
    else:
        breakdown["session"] = 0
        if session.get("near_end"):
            conflicts.append("Session_near_end")

    score = int(sum(breakdown.values()))

    hard_reject_reason = None
    if h4_bias == "RANGE":
        hard_reject_reason = "H4_RANGE"
    elif not bridge.get("bridge_ok"):
        hard_reject_reason = "BRIDGE_FAIL"
    elif not session.get("can_trade"):
        hard_reject_reason = "SESSION_CONSTRAINT"

    trade_ready = (
        score >= cfg.score_min
        and h4_bias in {"BULL", "BEAR"}
        and bool(bridge.get("bridge_ok"))
        and bool(session.get("can_trade"))
    )

    mtf_state = {
        "symbol": symbol,
        "context": {"W1": w1, "D1": d1, "H4": h4},
        "bridge": {"H1": h1, "M30": m30, "state": bridge},
        "execution": {"M15": m15, "M5": m5, "state": execution},
        "session": session,
    }
    score_state = {
        "score": score,
        "trade_ready": bool(trade_ready),
        "hard_reject_reason": hard_reject_reason,
        "breakdown": breakdown,
        "conflicts": conflicts,
        "notes": notes,
    }
    return {
        "mtf_state": mtf_state,
        "score_state": score_state,
    }


def explainMTF(result: dict[str, Any]) -> str:
    mtf = (result or {}).get("mtf_state", {})
    score_state = (result or {}).get("score_state", {})
    context = mtf.get("context", {})
    bridge = (mtf.get("bridge", {}) or {}).get("state", {})
    execution = (mtf.get("execution", {}) or {}).get("state", {})
    session = mtf.get("session", {})
    b = score_state.get("breakdown", {})

    session_name = str(session.get("session") or "NONE")
    mins = int(session.get("minutes_left") or 0)
    hh = mins // 60
    mm = mins % 60
    ses_flag = "✅" if session.get("can_trade") else "⚠️"

    w1 = context.get("W1", {})
    d1 = context.get("D1", {})
    h4 = context.get("H4", {})

    lines = [
        f"{str(mtf.get('symbol') or 'SYMBOL')} MTF CHECK",
        f"Session: {session_name} (time left {hh}h {mm}m) {ses_flag}",
        f"W1: {w1.get('bias', 'RANGE')} (+{int(b.get('weekly', 0))})",
        f"D1: {d1.get('bias', 'RANGE')} (+{int(b.get('daily', 0))})",
        f"H4: {h4.get('bias', 'RANGE')} ({h4.get('phase', 'UNKNOWN')}) (+{int(b.get('h4', 0))})",
        (
            "Bridge (H1/M30): "
            f"{'OK' if bridge.get('bridge_ok') else 'FAIL'} "
            f"({'minor BOS aligned' if bridge.get('minorBOSAligned') else 'weak/no BOS'}) "
            f"(+{int(b.get('bridge', 0))})"
        ),
        (
            f"Exec (M15/M5): {'aligned' if execution.get('exec_align') else 'not aligned'} "
            f"(+{int(b.get('execution', 0))})"
        ),
    ]

    total = int(score_state.get("score") or 0)
    ready = bool(score_state.get("trade_ready"))
    lines.append(f"TOTAL: {total}/10 => {'TRADE READY ✅' if ready else 'NOT READY ❌'}")

    conflicts = score_state.get("conflicts") or []
    if conflicts:
        lines.append("Conflicts: " + ", ".join(str(x) for x in conflicts))
    else:
        lines.append("Conflicts: none")

    reason = score_state.get("hard_reject_reason")
    if reason:
        lines.append(f"Reject reason: {reason}")

    return "\n".join(lines)
