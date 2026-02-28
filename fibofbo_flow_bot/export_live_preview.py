#!/usr/bin/env python3
"""Export chart-engine candles for clean preview payload (reset baseline)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dbo import get_engine_status, load_candles


def build_payload(candles_db: Path, timeframe: str, limit: int) -> dict:
    candles = load_candles(db_path=candles_db, timeframe=timeframe, limit=limit)
    engine = get_engine_status(db_path=candles_db, timeframe=timeframe, limit=min(limit, 5))

    candle_rows = [
        {
            "time": row.ts,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
        }
        for row in candles
    ]
    return {
        "ok": True,
        "mode": "baseline_chart_engine_only",
        "timeframe": timeframe,
        "candles_count": len(candle_rows),
        "candles": candle_rows,
        "engine": engine,
        "logic": {
            "dbo": {"status": "RESET"},
            "fibo": {"status": "RESET"},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export clean preview JSON from chart engine candles DB.")
    parser.add_argument("--candles-db", default="/root/mmhelper/db/twelve_data_bot/candles.db")
    parser.add_argument("--tf", default="h1")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    tf = str(args.tf).strip().lower()
    out = Path(args.out).resolve() if args.out else (Path(__file__).resolve().parent / f"debug_live_{tf}.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = build_payload(
        candles_db=Path(args.candles_db).resolve(),
        timeframe=tf,
        limit=max(50, int(args.limit)),
    )
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Saved: {out}")
    print(
        "timeframe={} candles={} engine_status={}".format(
            tf,
            payload["candles_count"],
            payload.get("engine", {}).get("status"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
