from __future__ import annotations

import unittest

from unified_state import buildCompactSummary, buildUnifiedState


class TestUnifiedState(unittest.TestCase):
    def test_build_unified_state_full(self) -> None:
        mtf_result = {
            "mtf_state": {"context": {"H4": {"bias": "BULL"}}},
            "score_state": {"score": 8, "trade_ready": True},
        }
        impulse_result = {"H4": {"phase": "IMPULSE", "direction": "BULL"}}
        active_leg_result = {
            "active_tf": "H1",
            "direction": "BULL",
            "state": "EXPANSION_ACTIVE",
            "action": "WAIT_RETRACE",
        }
        retrace_result = {
            "status": "RETRACE_IN_PROGRESS",
            "depth_type": "MICRO",
            "ready_for_setup": False,
        }

        out = buildUnifiedState(
            candle_index=145,
            timestamp="2026-02-28T18:20:00Z",
            mtf_result=mtf_result,
            impulse_result=impulse_result,
            active_leg_result=active_leg_result,
            retrace_result=retrace_result,
        )

        self.assertEqual(set(out.keys()), {"candle_index", "timestamp", "summary", "mtf", "impulse", "active", "retrace", "fd"})
        self.assertEqual(out["summary"]["bias"], "BULL")
        self.assertEqual(out["summary"]["mtf_score"], 8)
        self.assertTrue(out["summary"]["trade_ready"])
        self.assertEqual(out["summary"]["active_tf"], "H1")
        self.assertEqual(out["summary"]["direction"], "BULL")
        self.assertEqual(out["summary"]["leg_state"], "EXPANSION_ACTIVE")
        self.assertEqual(out["summary"]["leg_action"], "WAIT_RETRACE")
        self.assertEqual(out["summary"]["retrace_status"], "RETRACE_IN_PROGRESS")
        self.assertEqual(out["summary"]["retrace_depth"], "MICRO")
        self.assertFalse(out["summary"]["ready_for_setup"])
        self.assertIn("swing", out["fd"])
        self.assertIn("impulse", out["fd"])
        self.assertIn("confluence", out["fd"])

        compact = buildCompactSummary(out)
        self.assertEqual(
            compact,
            "[145] H4=BULL | Score=8 | Active=H1/EXPANSION_ACTIVE | Retrace=MICRO | Ready=False",
        )

    def test_build_unified_state_missing_keys(self) -> None:
        out = buildUnifiedState(
            candle_index=1,
            timestamp="t",
            mtf_result={},
            impulse_result={},
            active_leg_result={},
            retrace_result={},
        )

        self.assertIsNone(out["summary"]["bias"])
        self.assertEqual(out["summary"]["mtf_score"], 0)
        self.assertFalse(out["summary"]["trade_ready"])
        self.assertIsNone(out["summary"]["active_tf"])
        self.assertIsNone(out["summary"]["direction"])
        self.assertIsNone(out["summary"]["leg_state"])
        self.assertIsNone(out["summary"]["leg_action"])
        self.assertIsNone(out["summary"]["retrace_status"])
        self.assertIsNone(out["summary"]["retrace_depth"])
        self.assertFalse(out["summary"]["ready_for_setup"])
        self.assertIn("swing", out["fd"])
        self.assertIn("impulse", out["fd"])
        self.assertIn("confluence", out["fd"])

        compact = buildCompactSummary(out)
        self.assertEqual(
            compact,
            "[1] H4=None | Score=0 | Active=None/None | Retrace=None | Ready=False",
        )


if __name__ == "__main__":
    unittest.main()
