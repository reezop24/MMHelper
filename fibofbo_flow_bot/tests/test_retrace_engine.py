from __future__ import annotations

import unittest

from retrace_engine import RetraceConfig, evaluateRetrace


def mk_candles(closes: list[float]) -> list[dict]:
    rows: list[dict] = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = prev
        h = max(o, c) + 0.4
        l = min(o, c) - 0.4
        rows.append({"time": f"2026-02-01 00:{i:02d}:00", "open": o, "high": h, "low": l, "close": c})
        prev = c
    return rows


class TestRetraceEngine(unittest.TestCase):
    def test_normal_retrace_progress(self) -> None:
        h1 = mk_candles([100, 102, 104, 106, 108, 110, 109, 108, 106])
        active = {
            "active_tf": "H1",
            "direction": "BULL",
            "leg_start_index": 0,
            "leg_end_index": 5,
            "atr_ratio": 3.2,
        }
        imp = {
            "H1": {"phase": "IMPULSE", "direction": "BULL", "bos": True},
            "M15": {"phase": "CORRECTION", "direction": "BEAR", "bos": False},
        }
        out = evaluateRetrace(active, imp, {"H1": h1}, RetraceConfig())
        self.assertEqual(out["depth_type"], "NORMAL")
        self.assertEqual(out["status"], "STRONG_RETRACE")
        self.assertTrue(out["ready_for_setup"])

    def test_invalidated_on_opposite_bos(self) -> None:
        h1 = mk_candles([100, 102, 104, 106, 108, 110, 106, 103, 99, 98])
        active = {
            "active_tf": "H1",
            "direction": "BULL",
            "leg_start_index": 0,
            "leg_end_index": 5,
            "atr_ratio": 2.8,
        }
        imp = {"H1": {"phase": "CORRECTION", "direction": "BEAR", "bos": False}}
        out = evaluateRetrace(active, imp, {"H1": h1}, RetraceConfig())
        self.assertFalse(out["structure_intact"])
        self.assertEqual(out["status"], "INVALIDATED")

    def test_sweep_confirmed_ready(self) -> None:
        # Bull leg, deep sweep below start low then reclaim quickly.
        h1 = mk_candles([100, 103, 106, 109, 112, 115, 111, 107, 99, 101, 104])
        active = {
            "active_tf": "H1",
            "direction": "BULL",
            "leg_start_index": 0,
            "leg_end_index": 5,
            "atr_ratio": 3.5,
        }
        imp = {
            "H1": {"phase": "CORRECTION", "direction": "BEAR", "bos": False},
            "M15": {"phase": "IMPULSE", "direction": "BULL", "bos": True, "notes": ["Displacement: YES"]},
        }
        cfg = RetraceConfig(
            enable_sweep=True,
            sweep_ready_direct=True,
            sweep_require_micro_confirm=True,
            sweep_max_reclaim_candles=3,
            sweep_trigger_ratio=0.9,
        )
        out = evaluateRetrace(active, imp, {"H1": h1}, cfg)
        self.assertTrue(out["sweep_detected"])
        self.assertEqual(out["status"], "SWEEP_CONFIRMED")
        self.assertTrue(out["ready_for_setup"])

    def test_micro_retrace_early_not_rejected(self) -> None:
        h1 = mk_candles([100, 103, 106, 109, 112, 115, 114.9, 114.8, 114.7])
        active = {
            "active_tf": "H1",
            "direction": "BULL",
            "leg_start_index": 0,
            "leg_end_index": 5,
            "atr_ratio": 3.5,
        }
        imp = {
            "H1": {"phase": "IMPULSE", "direction": "BULL", "bos": True},
            "M15": {"phase": "CORRECTION", "direction": "BEAR", "bos": False},
        }
        out = evaluateRetrace(active, imp, {"H1": h1}, RetraceConfig())
        self.assertEqual(out["depth_type"], "MICRO")
        self.assertEqual(out["status"], "EARLY_RETRACE")
        self.assertFalse(out["ready_for_setup"])

    def test_anomaly_breach_does_not_trigger_sweep(self) -> None:
        # Build normal climb then one anomaly spike down below start, immediate reclaim.
        h1 = mk_candles([100, 103, 106, 109, 112, 115, 114, 113, 112, 111, 110, 109, 108, 107])
        # inject anomaly wick candle after leg end
        h1.append(
            {
                "time": "2026-02-01 00:14:00",
                "open": 107.0,
                "high": 107.2,
                "low": 92.0,
                "close": 107.05,
            }
        )
        h1.append(
            {
                "time": "2026-02-01 00:15:00",
                "open": 107.05,
                "high": 109.0,
                "low": 106.9,
                "close": 108.5,
            }
        )

        active = {
            "active_tf": "H1",
            "direction": "BULL",
            "leg_start_index": 0,
            "leg_end_index": 5,
            "atr_ratio": 3.0,
        }
        imp = {
            "H1": {"phase": "CORRECTION", "direction": "BEAR", "bos": False},
            "M15": {"phase": "IMPULSE", "direction": "BULL", "bos": True, "notes": ["Displacement: YES"]},
        }
        cfg = RetraceConfig(
            enable_sweep=True,
            sweep_ready_direct=True,
            sweep_require_micro_confirm=True,
            sweep_max_reclaim_candles=3,
            sweep_trigger_ratio=0.9,
        )
        out = evaluateRetrace(active, imp, {"H1": h1}, cfg)
        self.assertFalse(out["sweep_detected"])


if __name__ == "__main__":
    unittest.main()
