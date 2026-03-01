from __future__ import annotations

from typing import Any


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _true_range(curr: dict[str, Any], prev_close: float | None) -> float:
    h = _to_float(curr.get("high"))
    l = _to_float(curr.get("low"))
    if prev_close is None:
        return max(h - l, 0.0)
    return max(h - l, abs(h - prev_close), abs(l - prev_close))


def _rolling_atr(candles: list[dict[str, Any]], period: int) -> list[float]:
    out: list[float] = []
    trs: list[float] = []
    prev_close: float | None = None
    for c in candles:
        tr = _true_range(c, prev_close)
        trs.append(tr)
        prev_close = _to_float(c.get("close"))
        if len(trs) < period:
            out.append(sum(trs) / max(1, len(trs)))
        else:
            out.append(sum(trs[-period:]) / period)
    return out


def analyzeCandleQualityWithConfig(
    candles: list[dict[str, Any]],
    atr_period: int = 14,
    enabled: bool = True,
    range_multiplier: float = 4.0,
    wick_multiplier: float = 2.0,
    micro_range_ratio: float = 0.25,
) -> list[dict[str, Any]]:
    rows = [dict(c) for c in (candles or []) if isinstance(c, dict)]
    if not rows:
        return []

    atrs = _rolling_atr(rows, max(2, int(atr_period)))
    avg_atr = sum(atrs) / max(1, len(atrs))
    avg_body = sum(abs(_to_float(c.get("close")) - _to_float(c.get("open"))) for c in rows) / max(1, len(rows))

    for i, c in enumerate(rows):
        o = _to_float(c.get("open"))
        h = _to_float(c.get("high"))
        l = _to_float(c.get("low"))
        cl = _to_float(c.get("close"))
        body = abs(cl - o)
        rng = max(h - l, 0.0)
        upper = max(0.0, h - max(o, cl))
        lower = max(0.0, min(o, cl) - l)
        max_wick = max(upper, lower)
        atr_ref = max(atrs[i], avg_atr, 1e-9)

        range_spike = rng > (range_multiplier * atr_ref)
        wick_dom = (max_wick > (wick_multiplier * max(body, 1e-9))) and (rng > (2.0 * atr_ref))
        micro_liq = (rng < (micro_range_ratio * atr_ref)) and (body <= max(avg_body * 0.2, 1e-9))

        c["is_anomaly"] = bool(enabled and (range_spike or wick_dom or micro_liq))
    return rows


def analyzeCandleQuality(candles: list, atr_period: int = 14) -> list:
    return analyzeCandleQualityWithConfig(candles, atr_period=atr_period)

