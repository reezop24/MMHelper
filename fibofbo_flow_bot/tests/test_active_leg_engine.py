from __future__ import annotations

import unittest

from active_leg_engine import ActiveLegConfig, evaluateActiveLeg


def _tf_state(bias: str, last_close: float, sh: float = 0.0, sl: float = 0.0) -> dict:
    return {
        "bias": bias,
        "last_close": last_close,
        "lastSwingHigh": {"price": sh if sh else last_close},
        "lastSwingLow": {"price": sl if sl else last_close},
    }


def make_mtf(
    h4_bias: str,
    h1_close: float = 100.0,
    m30_close: float = 100.0,
    m15_close: float = 100.0,
    m5_close: float = 100.0,
    h4_phase: str = "EXPANSION",
    direction_ready: bool = True,
    invalidated: bool = False,
) -> dict:
    h4 = _tf_state(h4_bias, h1_close, sh=h1_close + 2.0, sl=h1_close - 2.0)
    h4["phase"] = h4_phase
    h4["invalidated"] = invalidated
    return {
        "mtf_state": {
            "context": {
                "H4": h4,
            },
            "bridge": {
                "H1": _tf_state(h4_bias, h1_close, sh=h1_close + 2.0, sl=h1_close - 2.0),
                "M30": _tf_state(h4_bias, m30_close, sh=m30_close + 1.3, sl=m30_close - 1.3),
            },
            "execution": {
                "M15": _tf_state(h4_bias, m15_close, sh=m15_close + 0.9, sl=m15_close - 0.9),
                "M5": _tf_state(h4_bias, m5_close, sh=m5_close + 0.7, sl=m5_close - 0.7),
            },
        },
        "score_state": {
            "direction_ready": direction_ready,
        },
    }


def make_imp(phase: str, direction: str, atr_ratio: float, rng: float = 6.0, s: int = 100, e: int = 130) -> dict:
    return {
        "phase": phase,
        "direction": direction,
        "atr_ratio": atr_ratio,
        "range": rng,
        "start_index": s,
        "end_index": e,
    }


class TestActiveLegEngine(unittest.TestCase):
    def test_case1_expansion_active(self) -> None:
        mtf = make_mtf("BULL", h1_close=2000, m30_close=1999, m15_close=1998, m5_close=2002)
        imp = {
            "H1": make_imp("IMPULSE", "BULL", 2.4, rng=8.0),
            "M30": make_imp("IMPULSE", "BULL", 2.0),
            "M15": make_imp("IMPULSE", "BULL", 1.9),
        }
        out = evaluateActiveLeg(mtf, imp, ActiveLegConfig())
        self.assertEqual(out["active_tf"], "H1")
        self.assertEqual(out["state"], "EXPANSION_ACTIVE")
        self.assertEqual(out["action"], "WAIT_RETRACE")

    def test_case2_retrace_in_progress(self) -> None:
        mtf = make_mtf("BULL", h1_close=2000, m30_close=1999, m15_close=1996, m5_close=1995)
        imp = {
            "H1": make_imp("IMPULSE", "BULL", 2.1, rng=7.0),
            "M30": make_imp("CORRECTION", "BEAR", 0.9),
            "M15": make_imp("CORRECTION", "BEAR", 0.8),
        }
        out = evaluateActiveLeg(mtf, imp, ActiveLegConfig())
        self.assertEqual(out["active_tf"], "H1")
        self.assertEqual(out["state"], "RETRACE_IN_PROGRESS")
        self.assertEqual(out["action"], "MONITOR_FIBO_ZONE")

    def test_case3_compression_active(self) -> None:
        mtf = make_mtf(
            "BULL",
            h1_close=2000,
            m30_close=2000,
            m15_close=1999,
            m5_close=1999,
            h4_phase="COMPRESSION_IN_TREND",
        )
        imp = {
            "H1": make_imp("CORRECTION", "BULL", 1.0),
            "M30": make_imp("COMPRESSION", "BULL", 0.7),
            "M15": make_imp("CORRECTION", "BEAR", 0.8),
        }
        out = evaluateActiveLeg(mtf, imp, ActiveLegConfig())
        self.assertEqual(out["state"], "COMPRESSION_ACTIVE")
        self.assertEqual(out["action"], "WAIT_BREAKOUT_OR_RETRACE")

    def test_case4_direction_not_ready(self) -> None:
        mtf = make_mtf("RANGE", direction_ready=False)
        imp = {
            "H1": make_imp("IMPULSE", "BULL", 2.2),
            "M30": make_imp("IMPULSE", "BULL", 2.0),
            "M15": make_imp("IMPULSE", "BULL", 1.9),
        }
        out = evaluateActiveLeg(mtf, imp, ActiveLegConfig())
        self.assertEqual(out["state"], "NO_VALID_STRUCTURE")
        self.assertEqual(out["action"], "STANDBY")

    def test_case5_conflict_no_valid(self) -> None:
        mtf = make_mtf("BULL", h1_close=2000, m30_close=1998, m15_close=1998, m5_close=1998)
        imp = {
            "H1": make_imp("IMPULSE", "BEAR", 2.2),
            "M30": make_imp("IMPULSE", "BEAR", 2.0),
            "M15": make_imp("IMPULSE", "BEAR", 1.9),
        }
        out = evaluateActiveLeg(mtf, imp, ActiveLegConfig())
        self.assertEqual(out["state"], "NO_VALID_STRUCTURE")
        self.assertEqual(out["action"], "STANDBY")


if __name__ == "__main__":
    unittest.main()
