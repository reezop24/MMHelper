from __future__ import annotations

import unittest
from datetime import datetime

from mtf_engine import MTFConfig, evaluateMTF


def candles_from_points(points: list[float], start_idx: int = 0) -> list[dict]:
    out: list[dict] = []
    for i, p in enumerate(points, start=1):
        # Keep candle body compact around the pivot price so fractal swings
        # are represented by the sequence itself.
        o = p - 0.05 if (i % 2 == 0) else p + 0.05
        c = p
        h = p + 0.30
        l = p - 0.30
        out.append(
            {
                "time": f"2026-02-{(start_idx + i):02d} 00:00:00",
                "open": o,
                "high": h,
                "low": l,
                "close": c,
            }
        )
    return out


def make_bullish_points(start: float = 100.0) -> list[float]:
    return [
        start,
        start + 4,
        start + 1.5,
        start + 7,
        start + 3,
        start + 10,
        start + 6,
        start + 13,
        start + 8,
        start + 15,
        start + 10,
        start + 17,
        start + 12,
        start + 20,
    ]


def make_bearish_points(start: float = 120.0) -> list[float]:
    return [
        start,
        start - 4,
        start - 1.5,
        start - 7,
        start - 3,
        start - 10,
        start - 6,
        start - 13,
        start - 8,
        start - 15,
        start - 10,
        start - 17,
        start - 12,
        start - 20,
    ]


def make_range_points(center: float = 100.0) -> list[float]:
    return [
        center,
        center + 3,
        center - 3,
        center + 2.8,
        center - 2.7,
        center + 3.1,
        center - 3.0,
        center + 2.9,
        center - 2.8,
        center + 3.0,
        center - 2.9,
        center + 2.7,
        center - 2.8,
        center + 2.9,
    ]


def build_dataset(w1: list[float], d1: list[float], h4: list[float], h1: list[float], m30: list[float], m15: list[float], m5: list[float]) -> dict:
    return {
        "W1": candles_from_points(w1),
        "D1": candles_from_points(d1),
        "H4": candles_from_points(h4),
        "H1": candles_from_points(h1),
        "M30": candles_from_points(m30),
        "M15": candles_from_points(m15),
        "M5": candles_from_points(m5),
    }


class TestMTFEngine(unittest.TestCase):
    def test_perfect_alignment_ready(self) -> None:
        data = build_dataset(
            make_bullish_points(1800),
            make_bullish_points(1900),
            make_bullish_points(2000),
            make_bullish_points(2050),
            make_bullish_points(2060),
            make_bullish_points(2070),
            make_bullish_points(2075),
        )
        cfg = MTFConfig(
            score_min=7,
            daily_conflict_mode="soft",
            weekly_conflict_mode="soft",
            swing_lookback=1,
            trend_swings_n=3,
        )
        res = evaluateMTF("XAUUSD", data, datetime(2026, 2, 23, 16, 30), cfg)
        self.assertGreaterEqual(res["score_state"]["score"], 8)
        self.assertTrue(res["score_state"]["trade_ready"])

    def test_h4_bull_daily_bear_conflict_soft(self) -> None:
        data = build_dataset(
            make_bullish_points(1800),
            make_bearish_points(2100),
            make_bullish_points(2000),
            make_bullish_points(2050),
            make_bullish_points(2060),
            make_bullish_points(2070),
            make_bullish_points(2075),
        )
        cfg = MTFConfig(
            score_min=7,
            daily_conflict_mode="soft",
            weekly_conflict_mode="soft",
            swing_lookback=1,
            trend_swings_n=3,
        )
        res = evaluateMTF("XAUUSD", data, datetime(2026, 2, 23, 16, 30), cfg)
        self.assertIn("D1_vs_H4", res["score_state"]["conflicts"])
        self.assertGreaterEqual(res["score_state"]["score"], 7)

    def test_h4_range_hard_reject(self) -> None:
        data = build_dataset(
            make_bullish_points(1800),
            make_bullish_points(1900),
            make_range_points(2000),
            make_bullish_points(2050),
            make_bullish_points(2060),
            make_bullish_points(2070),
            make_bullish_points(2075),
        )
        cfg = MTFConfig(score_min=7, swing_lookback=1, trend_swings_n=3)
        res = evaluateMTF("XAUUSD", data, datetime(2026, 2, 23, 16, 30), cfg)
        self.assertFalse(res["score_state"]["trade_ready"])
        self.assertEqual(res["score_state"]["hard_reject_reason"], "H4_RANGE")


if __name__ == "__main__":
    unittest.main()
