from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PivotType = Literal["H", "L"]


@dataclass
class Candle:
    idx: int
    ts: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class Pivot:
    idx: int
    ts: str
    kind: PivotType
    price: float


def load_candles(db_path: Path, timeframe: str, limit: int) -> list[Candle]:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            SELECT ts, open, high, low, close
            FROM candles
            WHERE timeframe = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (timeframe, limit),
        ).fetchall()
    finally:
        con.close()

    rows.reverse()
    out: list[Candle] = []
    for i, row in enumerate(rows):
        ts, o, h, l, c = row
        out.append(Candle(idx=i, ts=str(ts), open=float(o), high=float(h), low=float(l), close=float(c)))
    return out


def find_pivots(candles: list[Candle], swing_window: int = 2) -> list[Pivot]:
    if len(candles) < (swing_window * 2 + 1):
        return []

    pivots: list[Pivot] = []
    for i in range(swing_window, len(candles) - swing_window):
        center = candles[i]
        chunk = candles[i - swing_window : i + swing_window + 1]
        highs = [x.high for x in chunk]
        lows = [x.low for x in chunk]

        if center.high == max(highs):
            pivots.append(Pivot(idx=i, ts=center.ts, kind="H", price=center.high))
        if center.low == min(lows):
            pivots.append(Pivot(idx=i, ts=center.ts, kind="L", price=center.low))

    pivots.sort(key=lambda p: p.idx)
    return _compress_same_kind(pivots)


def _compress_same_kind(pivots: list[Pivot]) -> list[Pivot]:
    if not pivots:
        return []
    out = [pivots[0]]
    for p in pivots[1:]:
        last = out[-1]
        if p.kind != last.kind:
            out.append(p)
            continue
        if p.kind == "H" and p.price > last.price:
            out[-1] = p
        elif p.kind == "L" and p.price < last.price:
            out[-1] = p
    return out


def detect_dbo(
    candles: list[Candle],
    pivots: list[Pivot],
    shoulder_tolerance_pct: float = 0.003,
) -> dict:
    if not candles or len(pivots) < 5:
        return {"status": "NO_SETUP"}

    latest_close = candles[-1].close
    best: dict | None = None

    for i in range(4, len(pivots)):
        seq = pivots[i - 4 : i + 1]
        kinds = "".join(x.kind for x in seq)

        # Bullish structure: L-H-L-H-L (inverse HNS / bullish QM)
        if kinds == "LHLHL":
            ls, _, head, right_high, rs = seq
            if not (head.price < ls.price and head.price < rs.price):
                continue

            near_equal = abs(rs.price - ls.price) / max(ls.price, 1e-9) <= shoulder_tolerance_pct
            qm_shape = rs.price > ls.price * (1 + shoulder_tolerance_pct)
            if not (near_equal or qm_shape):
                continue

            trigger_level = right_high.price
            triggered = latest_close > trigger_level
            pattern = "INV_HNS" if near_equal else "QM_BULL"
            candidate = {
                "status": "TRIGGERED" if triggered else "ARMED",
                "side": "BUY",
                "pattern": pattern,
                "trigger_level": trigger_level,
                "latest_close": latest_close,
                "points": {
                    "left_shoulder": {"ts": ls.ts, "price": ls.price},
                    "head": {"ts": head.ts, "price": head.price},
                    "right_shoulder": {"ts": rs.ts, "price": rs.price},
                },
            }
            best = candidate

        # Bearish structure: H-L-H-L-H (HNS / bearish QM)
        if kinds == "HLHLH":
            ls, _, head, right_low, rs = seq
            if not (head.price > ls.price and head.price > rs.price):
                continue

            near_equal = abs(rs.price - ls.price) / max(ls.price, 1e-9) <= shoulder_tolerance_pct
            qm_shape = rs.price < ls.price * (1 - shoulder_tolerance_pct)
            if not (near_equal or qm_shape):
                continue

            trigger_level = right_low.price
            triggered = latest_close < trigger_level
            pattern = "HNS" if near_equal else "QM_BEAR"
            candidate = {
                "status": "TRIGGERED" if triggered else "ARMED",
                "side": "SELL",
                "pattern": pattern,
                "trigger_level": trigger_level,
                "latest_close": latest_close,
                "points": {
                    "left_shoulder": {"ts": ls.ts, "price": ls.price},
                    "head": {"ts": head.ts, "price": head.price},
                    "right_shoulder": {"ts": rs.ts, "price": rs.price},
                },
            }
            best = candidate

    if best is None:
        return {"status": "NO_SETUP"}
    return best
