from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class SwingConfig:
    min_post_candles: int = 2
    scope_window: int = 180
    scope_window_by_tf: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.scope_window_by_tf is None:
            self.scope_window_by_tf = {
                "W1": 180,
                "D1": 180,
                "H4": 220,
            }


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
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
    if wd == 5 and mins >= 360:  # Sat >= 06:00
        return True
    if wd == 6:  # Sun
        return True
    if wd == 0 and mins < 420:  # Mon < 07:00
        return True
    return False


def _normalize(candles: list[dict[str, Any]], tf: str, cfg: SwingConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, c in enumerate(candles or []):
        if not isinstance(c, dict):
            continue
        if _is_market_closed_myt(c.get("time")):
            continue
        h = _safe_float(c.get("high"))
        l = _safe_float(c.get("low"))
        o = _safe_float(c.get("open"))
        cl = _safe_float(c.get("close"))
        if h < l:
            h, l = l, h
        rows.append(
            {
                "idx": i,
                "time": c.get("time"),
                "open": o,
                "high": h,
                "low": l,
                "close": cl,
            }
        )
    if not rows:
        return rows
    # Scope control: never scan full history blindly.
    w = int(cfg.scope_window_by_tf.get(tf, cfg.scope_window))
    if w > 0 and len(rows) > w:
        rows = rows[-w:]
    # Never detect on latest candle.
    if len(rows) > 1:
        rows = rows[:-1]
    return rows


def _pivot_highs(rows: list[dict[str, Any]], min_post: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    n = len(rows)
    for i in range(1, max(1, n - (1 + min_post))):
        if rows[i]["high"] > rows[i - 1]["high"] and rows[i]["high"] > rows[i + 1]["high"]:
            out.append({"idx": i, "price": float(rows[i]["high"])})
    return out


def _pivot_lows(rows: list[dict[str, Any]], min_post: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    n = len(rows)
    for i in range(1, max(1, n - (1 + min_post))):
        if rows[i]["low"] < rows[i - 1]["low"] and rows[i]["low"] < rows[i + 1]["low"]:
            out.append({"idx": i, "price": float(rows[i]["low"])})
    return out


def _first_after(items: list[dict[str, Any]], idx: int) -> dict[str, Any] | None:
    for x in items:
        if int(x["idx"]) > idx:
            return x
    return None


def _confirm_down_event(rows: list[dict[str, Any]], p_high: dict[str, Any], piv_lows: list[dict[str, Any]]) -> dict[str, Any] | None:
    pull_low = _first_after(piv_lows, int(p_high["idx"]))
    if pull_low is None:
        return None
    threshold = float(pull_low["price"])
    h_idx = int(p_high["idx"])
    l_idx = int(pull_low["idx"])
    # Need continuation by body close.
    for j in range(l_idx + 1, len(rows)):
        if float(rows[j]["close"]) < threshold:
            ll = min(float(x["low"]) for x in rows[l_idx : j + 1])
            return {
                "type": "DOWN",
                "break_idx": j,
                "anchor_idx": h_idx,
                "swing_high": float(p_high["price"]),
                "swing_low": ll,
            }
    return None


def _confirm_up_event(rows: list[dict[str, Any]], p_low: dict[str, Any], piv_highs: list[dict[str, Any]]) -> dict[str, Any] | None:
    pull_high = _first_after(piv_highs, int(p_low["idx"]))
    if pull_high is None:
        return None
    threshold = float(pull_high["price"])
    l_idx = int(p_low["idx"])
    h_idx = int(pull_high["idx"])
    for j in range(h_idx + 1, len(rows)):
        if float(rows[j]["close"]) > threshold:
            hh = max(float(x["high"]) for x in rows[h_idx : j + 1])
            return {
                "type": "UP",
                "break_idx": j,
                "anchor_idx": l_idx,
                "swing_low": float(p_low["price"]),
                "swing_high": hh,
            }
    return None


def _external_structure(
    rows: list[dict[str, Any]],
    piv_highs: list[dict[str, Any]],
    piv_lows: list[dict[str, Any]],
    tf: str,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for ph in piv_highs:
        ev = _confirm_down_event(rows, ph, piv_lows)
        if ev:
            events.append(ev)
    for pl in piv_lows:
        ev = _confirm_up_event(rows, pl, piv_highs)
        if ev:
            events.append(ev)
    if not events:
        return {
            "trend": "Range",
            "external_swing_high": None,
            "external_swing_low": None,
            "external_active": False,
            "break_idx": None,
        }
    latest_break = max(int(x["break_idx"]) for x in events)
    candidates = [x for x in events if int(x["break_idx"]) == latest_break]
    # For same break candle, prefer earliest anchor (major structure reference).
    last = min(candidates, key=lambda x: int(x.get("anchor_idx") or 0))
    trend = "Uptrend" if last["type"] == "UP" else "Downtrend"
    start = max(0, min(int(last.get("anchor_idx") or 0), len(rows) - 1))
    tf_up = str(tf or "").upper()

    # External range calibration for active cycle visibility.
    lookback = {"W1": 8, "D1": 24, "H4": 24}.get(tf_up, 24)
    seg = rows[-min(len(rows), lookback) :] if rows else []
    if seg:
        ext_high = max(float(x["high"]) for x in seg)
        ext_low = min(float(x["low"]) for x in seg)
    else:
        ext_high = float(last["swing_high"])
        ext_low = float(last["swing_low"])

    return {
        "trend": trend,
        "external_swing_high": ext_high,
        "external_swing_low": ext_low,
        "external_active": True,
        "break_idx": int(last["break_idx"]),
        "anchor_idx": start,
    }


def _internal_structure(rows: list[dict[str, Any]], ext: dict[str, Any], cfg: SwingConfig) -> dict[str, Any]:
    if not ext.get("external_active"):
        return {
            "internal_swing_high": None,
            "internal_swing_low": None,
            "internal_bias": "Neutral",
            "internal_active": False,
        }
    bidx = int(ext.get("break_idx") or 0)
    if bidx >= len(rows) - 3:
        return {
            "internal_swing_high": None,
            "internal_swing_low": None,
            "internal_bias": "Neutral",
            "internal_active": False,
        }
    seg = rows[bidx:]
    piv_highs = _pivot_highs(seg, cfg.min_post_candles)
    piv_lows = _pivot_lows(seg, cfg.min_post_candles)

    events: list[dict[str, Any]] = []
    for ph in piv_highs:
        ev = _confirm_down_event(seg, ph, piv_lows)
        if ev:
            events.append(ev)
    for pl in piv_lows:
        ev = _confirm_up_event(seg, pl, piv_highs)
        if ev:
            events.append(ev)
    if not events:
        return {
            "internal_swing_high": None,
            "internal_swing_low": None,
            "internal_bias": "Neutral",
            "internal_active": False,
        }

    # Use last valid event and keep it within external boundaries.
    last = max(events, key=lambda x: int(x["break_idx"]))
    e_hi = _safe_float(ext.get("external_swing_high"), 0.0)
    e_lo = _safe_float(ext.get("external_swing_low"), 0.0)
    i_hi = float(last["swing_high"])
    i_lo = float(last["swing_low"])

    # Internal must stay inside external range.
    if e_hi and e_lo and not (e_lo <= i_lo <= e_hi and e_lo <= i_hi <= e_hi):
        return {
            "internal_swing_high": None,
            "internal_swing_low": None,
            "internal_bias": "Neutral",
            "internal_active": False,
        }

    bias = "Bullish" if last["type"] == "UP" else "Bearish"
    return {
        "internal_swing_high": i_hi,
        "internal_swing_low": i_lo,
        "internal_bias": bias,
        "internal_active": True,
    }


def analyzeSwing(tf: str, candles: list[dict[str, Any]], config: SwingConfig | None = None) -> dict[str, Any]:
    cfg = config or SwingConfig()
    tf_up = str(tf).upper()
    rows = _normalize(candles, tf_up, cfg)

    base = {
        "timeframe": tf_up,
        "external": {
            "trend": "Range",
            "external_swing_high": None,
            "external_swing_low": None,
            "external_active": False,
        },
        "internal": {
            "internal_swing_high": None,
            "internal_swing_low": None,
            "internal_bias": "Neutral",
            "internal_active": False,
        },
    }

    if len(rows) < 8:
        return base

    piv_highs = _pivot_highs(rows, cfg.min_post_candles)
    piv_lows = _pivot_lows(rows, cfg.min_post_candles)
    ext = _external_structure(rows, piv_highs, piv_lows, tf=tf_up)
    itn = _internal_structure(rows, ext, cfg)

    return {
        "timeframe": tf_up,
        "external": {
            "trend": ext["trend"],
            "external_swing_high": ext["external_swing_high"],
            "external_swing_low": ext["external_swing_low"],
            "external_active": bool(ext["external_active"]),
        },
        "internal": itn,
    }


def detectSwingStructureAll(
    candles_by_tf: dict[str, list[dict[str, Any]]],
    config: SwingConfig | None = None,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for tf in ("W1", "D1", "H4"):
        rows = candles_by_tf.get(tf) or candles_by_tf.get(tf.lower()) or []
        out[tf] = analyzeSwing(tf, rows, config)
    return out


def explainSwing(result: dict[str, Any]) -> str:
    tf = str(result.get("timeframe") or "-")
    ext = result.get("external") if isinstance(result.get("external"), dict) else {}
    itn = result.get("internal") if isinstance(result.get("internal"), dict) else {}

    e_hi = ext.get("external_swing_high")
    e_lo = ext.get("external_swing_low")
    i_hi = itn.get("internal_swing_high")
    i_lo = itn.get("internal_swing_low")
    e_hi_txt = "NONE" if e_hi is None else str(e_hi)
    e_lo_txt = "NONE" if e_lo is None else str(e_lo)
    i_hi_txt = "NONE" if i_hi is None else str(i_hi)
    i_lo_txt = "NONE" if i_lo is None else str(i_lo)

    return "\n".join(
        [
            f"Timeframe: {tf}",
            "",
            "External Structure:",
            f"- Trend: {ext.get('trend', 'Range')}",
            f"- External Swing High: {e_hi_txt}",
            f"- External Swing Low: {e_lo_txt}",
            "",
            "Internal Structure:",
            f"- Internal Swing High: {i_hi_txt}",
            f"- Internal Swing Low: {i_lo_txt}",
            f"- Internal Bias: {itn.get('internal_bias', 'Neutral')}",
        ]
    )
