from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Candle:
    idx: int
    ts: str
    open: float
    high: float
    low: float
    close: float


def load_candles(db_path: Path, timeframe: str, limit: int) -> list[Candle]:
    """Load candles from chart engine DB (candles table)."""
    tf = str(timeframe or "").strip().lower()
    capped_limit = max(1, int(limit or 1))

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
            (tf, capped_limit),
        ).fetchall()
    finally:
        con.close()

    rows.reverse()
    out: list[Candle] = []
    for i, row in enumerate(rows):
        ts, o, h, l, c = row
        out.append(
            Candle(
                idx=i,
                ts=str(ts),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
            )
        )
    return out


def get_engine_status(db_path: Path, timeframe: str, limit: int = 5) -> dict:
    """Simple status helper for bot commands and debug exports."""
    candles = load_candles(db_path=db_path, timeframe=timeframe, limit=limit)
    if not candles:
        return {
            "status": "NO_DATA",
            "timeframe": str(timeframe or "").lower(),
            "count": 0,
            "latest": None,
        }

    last = candles[-1]
    return {
        "status": "OK",
        "timeframe": str(timeframe or "").lower(),
        "count": len(candles),
        "latest": {
            "ts": last.ts,
            "open": last.open,
            "high": last.high,
            "low": last.low,
            "close": last.close,
        },
    }
