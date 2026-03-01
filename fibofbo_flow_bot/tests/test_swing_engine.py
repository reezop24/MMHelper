from __future__ import annotations

import unittest

from swing_engine import SwingConfig, analyzeSwing


def _c(ts: int, h: float, l: float) -> dict:
    return {"time": f"2026-02-01 00:{ts:02d}:00", "open": (h + l) / 2, "high": h, "low": l, "close": (h + l) / 2}


def scenario_uptrend() -> list[dict]:
    # Creates rising pivot highs + rising pivot lows.
    return [
        _c(0, 10.0, 8.0),
        _c(1, 11.0, 8.8),
        _c(2, 10.4, 8.5),
        _c(3, 12.2, 9.4),
        _c(4, 11.5, 9.0),
        _c(5, 13.5, 10.0),
        _c(6, 12.8, 9.6),
        _c(7, 14.2, 10.8),
        _c(8, 13.6, 10.2),
        _c(9, 15.0, 11.5),
        _c(10, 14.4, 11.0),
    ]


def scenario_downtrend() -> list[dict]:
    # Creates lower pivot highs + lower pivot lows.
    return [
        _c(0, 20.0, 18.0), _c(1, 19.2, 17.2), _c(2, 19.6, 17.6),
        _c(3, 18.8, 16.8), _c(4, 19.0, 17.0), _c(5, 18.2, 16.1),
        _c(6, 18.4, 16.3), _c(7, 17.6, 15.5), _c(8, 17.9, 15.9),
    ]


def scenario_range() -> list[dict]:
    # Mixed pivots, no clear HH+HL / LL+LH pair.
    return [
        _c(0, 30.0, 28.0), _c(1, 31.0, 29.0), _c(2, 30.5, 28.9),
        _c(3, 31.2, 29.1), _c(4, 30.8, 29.3), _c(5, 31.1, 29.2),
        _c(6, 30.9, 29.1), _c(7, 31.0, 29.0), _c(8, 30.7, 29.2),
    ]


class TestSwingEngine(unittest.TestCase):
    def test_uptrend_floor_ceiling(self) -> None:
        out = analyzeSwing("H4", scenario_uptrend(), SwingConfig(recent_window=30))
        self.assertEqual(out["regime"], "UPTREND")
        self.assertEqual(out["direction"], "BULL")
        self.assertIsNotNone(out["swing_high"])
        self.assertIsNotNone(out["swing_low"])
        self.assertGreater(float(out["swing_high"]), float(out["swing_low"]))

    def test_downtrend_floor_ceiling(self) -> None:
        out = analyzeSwing("D1", scenario_downtrend(), SwingConfig(recent_window=30))
        self.assertEqual(out["regime"], "DOWNTREND")
        self.assertEqual(out["direction"], "BEAR")
        self.assertIsNotNone(out["swing_high"])
        self.assertIsNotNone(out["swing_low"])
        self.assertGreater(float(out["swing_high"]), float(out["swing_low"]))

    def test_range_structure(self) -> None:
        out = analyzeSwing("W1", scenario_range(), SwingConfig(recent_window=30))
        self.assertEqual(out["regime"], "RANGE")
        self.assertEqual(out["direction"], "RANGE")
        self.assertIsNotNone(out["swing_high"])
        self.assertIsNotNone(out["swing_low"])

    def test_no_external_dependencies(self) -> None:
        # Guard: engine should still operate with simple candles only.
        rows = [_c(i, 10 + i * 0.1, 9 + i * 0.05) for i in range(12)]
        out = analyzeSwing("H4", rows, SwingConfig())
        self.assertIn(out["regime"], {"UPTREND", "DOWNTREND", "RANGE"})


if __name__ == "__main__":
    unittest.main()
