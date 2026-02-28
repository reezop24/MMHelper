from __future__ import annotations

import unittest

from impulse_engine import ImpulseConfig, analyzeImpulse, detectImpulseAll


def _c(ts: int, o: float, h: float, l: float, c: float) -> dict:
    return {"time": f"2026-02-01 00:{ts:02d}:00", "open": o, "high": h, "low": l, "close": c}


def scenario_impulse_bull() -> list[dict]:
    rows: list[dict] = []
    # warmup candles
    for i in range(10):
        p = 99.5 + (0.25 if i % 2 else -0.25)
        rows.append(_c(i, p - 0.08, p + 0.22, p - 0.22, p + 0.04))
    # base alternating swings
    px = [100.0, 101.4, 100.6, 101.8, 100.9, 102.2, 101.2, 102.5, 101.5, 102.8]
    for i, p in enumerate(px, start=10):
        rows.append(_c(i, p - 0.12, p + 0.32, p - 0.35, p + 0.10))
    # compression before expansion
    base = 102.9
    for j in range(20, 30):
        o = base + (0.06 if j % 2 else -0.06)
        c = base + (-0.04 if j % 2 else 0.04)
        h = max(o, c) + 0.30
        l = min(o, c) - 0.30
        rows.append(_c(j, o, h, l, c))
    # displacement bullish leg
    rows.append(_c(30, 103.0, 104.6, 102.8, 104.3))
    rows.append(_c(31, 104.3, 106.3, 104.1, 106.0))
    rows.append(_c(32, 106.0, 107.8, 105.8, 107.5))
    rows.append(_c(33, 107.5, 108.0, 107.0, 107.6))
    rows.append(_c(34, 107.6, 108.2, 107.2, 108.0))
    return rows


def scenario_correction() -> list[dict]:
    rows: list[dict] = []
    # warmup
    for i in range(12):
        p = 99.8 + (0.18 if i % 2 else -0.18)
        rows.append(_c(i, p - 0.06, p + 0.20, p - 0.20, p + 0.03))
    # warmup + mild bullish impulse (range sederhana)
    seq = [
        (100.0, 100.4, 99.7, 100.2),
        (100.2, 100.7, 99.9, 100.5),
        (100.5, 101.0, 100.2, 100.8),
        (100.8, 101.3, 100.5, 101.1),
        (101.1, 101.6, 100.8, 101.4),
        (101.4, 102.0, 101.1, 101.8),
        (101.8, 102.4, 101.5, 102.1),
        (102.1, 102.8, 101.8, 102.5),
        (102.5, 103.0, 102.2, 102.8),
        (102.8, 103.3, 102.5, 103.1),
        (103.1, 103.6, 102.8, 103.4),
        (103.4, 103.9, 103.1, 103.7),
    ]
    for i, (o, h, l, c) in enumerate(seq, start=len(rows)):
        rows.append(_c(i, o, h, l, c))

    # correction bearish perlahan + overlap tinggi
    tail = [
        (103.7, 103.9, 103.3, 103.5),
        (103.5, 103.7, 103.1, 103.3),
        (103.3, 103.5, 102.9, 103.1),
        (103.1, 103.3, 102.7, 102.9),
        (102.9, 103.1, 102.6, 102.8),
        (102.8, 103.0, 102.5, 102.7),
        (102.7, 102.9, 102.4, 102.6),
        (102.6, 102.8, 102.3, 102.5),
    ]
    for k, (o, h, l, c) in enumerate(tail, start=len(rows)):
        rows.append(_c(k, o, h, l, c))
    return rows


def scenario_compression() -> list[dict]:
    rows: list[dict] = []
    base = 100.0
    for i in range(36):
        drift = (0.015 if i % 2 else -0.015)
        o = base + drift
        c = base - drift * 0.6
        h = max(o, c) + 0.34
        l = min(o, c) - 0.34
        rows.append(_c(i, o, h, l, c))
    return rows


class TestImpulseEngine(unittest.TestCase):
    def test_clear_bull_displacement_is_impulse(self) -> None:
        cfg = ImpulseConfig(swing_lookback=1)
        res = analyzeImpulse("H1", scenario_impulse_bull(), cfg)
        self.assertEqual(res["phase"], "IMPULSE")
        self.assertEqual(res["direction"], "BULL")
        self.assertTrue(res["bos"])
        self.assertGreaterEqual(res["strength_score"], 6)
        self.assertTrue(res["valid_impulse"])

    def test_slow_retrace_is_correction(self) -> None:
        cfg = ImpulseConfig(swing_lookback=1)
        res = analyzeImpulse("M30", scenario_correction(), cfg)
        self.assertEqual(res["phase"], "CORRECTION")
        self.assertEqual(res["direction"], "BEAR")
        self.assertFalse(res["valid_impulse"])

    def test_tight_chop_is_compression(self) -> None:
        cfg = ImpulseConfig(swing_lookback=1)
        res = analyzeImpulse("M15", scenario_compression(), cfg)
        self.assertEqual(res["phase"], "COMPRESSION")
        self.assertIsNone(res["direction"])
        self.assertFalse(res["valid_impulse"])

    def test_detect_all(self) -> None:
        cfg = ImpulseConfig(swing_lookback=1)
        out = detectImpulseAll(
            {
                "H4": scenario_impulse_bull(),
                "H1": scenario_correction(),
                "M30": scenario_compression(),
                "M15": scenario_compression(),
            },
            cfg,
        )
        self.assertEqual(set(out.keys()), {"H4", "H1", "M30", "M15"})


if __name__ == "__main__":
    unittest.main()
