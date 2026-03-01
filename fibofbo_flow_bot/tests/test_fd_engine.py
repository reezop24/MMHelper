from __future__ import annotations

import unittest

from fd_engine import computeExternalSwingFD, computeImpulseFD, evaluateFD, resetFDCache


class TestFDEngine(unittest.TestCase):
    def setUp(self) -> None:
        resetFDCache()

    def test_external_discount(self) -> None:
        out = computeExternalSwingFD(lastSwingLow=100.0, lastSwingHigh=200.0, current_price=110.0)
        self.assertEqual(out["zone"], "DISCOUNT_EXT")
        self.assertAlmostEqual(float(out["ratio"]), 0.10, places=6)

    def test_external_premium(self) -> None:
        out = computeExternalSwingFD(lastSwingLow=100.0, lastSwingHigh=200.0, current_price=180.0)
        self.assertEqual(out["zone"], "PREMIUM_EXT")
        self.assertAlmostEqual(float(out["ratio"]), 0.80, places=6)

    def test_impulse_discount(self) -> None:
        out = computeImpulseFD(impulse_low=120.0, impulse_high=220.0, current_price=130.0)
        self.assertEqual(out["zone"], "DISCOUNT_IMP")
        self.assertAlmostEqual(float(out["ratio"]), 0.10, places=6)

    def test_impulse_extreme(self) -> None:
        out = computeImpulseFD(impulse_low=120.0, impulse_high=220.0, current_price=240.0)
        self.assertEqual(out["zone"], "PREMIUM_IMP")
        self.assertAlmostEqual(float(out["ratio"]), 1.00, places=6)

    def test_swing_invalid_outside_range(self) -> None:
        out = computeExternalSwingFD(lastSwingLow=100.0, lastSwingHigh=200.0, current_price=240.0)
        self.assertFalse(out["valid"])
        self.assertIsNone(out["ratio"])
        self.assertIsNone(out["zone"])

    def test_shift_up_close_based(self) -> None:
        mtf = {
            "mtf_state": {
                "symbol": "XAUUSD",
                "context": {"H4": {"lastSwingLow": {"price": 100.0}, "lastSwingHigh": {"price": 200.0}}},
                "execution": {"M5": {"last_close": 149.0}},
            }
        }
        active = {"active_tf": "H1", "direction": "BULL", "impulse_low": 100.0, "impulse_high": 200.0}
        first = evaluateFD(mtf, active)
        self.assertFalse(first["swing"]["shift_up"])
        self.assertFalse(first["swing"]["shift_down"])
        mtf["mtf_state"]["execution"]["M5"]["last_close"] = 151.0
        second = evaluateFD(mtf, active)
        self.assertTrue(second["swing"]["shift_up"])
        self.assertFalse(second["swing"]["shift_down"])

    def test_shift_down_close_based(self) -> None:
        mtf = {
            "mtf_state": {
                "symbol": "XAUUSD",
                "context": {"H4": {"lastSwingLow": {"price": 100.0}, "lastSwingHigh": {"price": 200.0}}},
                "execution": {"M5": {"last_close": 151.0}},
            }
        }
        active = {"active_tf": "H1", "direction": "BULL", "impulse_low": 100.0, "impulse_high": 200.0}
        first = evaluateFD(mtf, active)
        self.assertFalse(first["swing"]["shift_up"])
        self.assertFalse(first["swing"]["shift_down"])
        mtf["mtf_state"]["execution"]["M5"]["last_close"] = 149.0
        second = evaluateFD(mtf, active)
        self.assertFalse(second["swing"]["shift_up"])
        self.assertTrue(second["swing"]["shift_down"])

    def test_shift_prev_none_false(self) -> None:
        mtf = {
            "mtf_state": {
                "symbol": "XAUUSD",
                "context": {"H4": {"lastSwingLow": {"price": 100.0}, "lastSwingHigh": {"price": 200.0}}},
                "execution": {"M5": {"last_close": 160.0}},
            }
        }
        active = {"active_tf": "H1", "direction": "BULL", "impulse_low": 100.0, "impulse_high": 200.0}
        out = evaluateFD(mtf, active)
        self.assertFalse(out["swing"]["shift_up"])
        self.assertFalse(out["swing"]["shift_down"])

    def test_reaction_low_and_high_flags(self) -> None:
        low = computeExternalSwingFD(lastSwingLow=100.0, lastSwingHigh=200.0, current_price=120.0)
        self.assertTrue(low["reaction_low"])
        self.assertFalse(low["reaction_high"])
        self.assertTrue(low["reaction_zone"])

        high = computeExternalSwingFD(lastSwingLow=100.0, lastSwingHigh=200.0, current_price=180.0)
        self.assertFalse(high["reaction_low"])
        self.assertTrue(high["reaction_high"])
        self.assertTrue(high["reaction_zone"])


if __name__ == "__main__":
    unittest.main()
