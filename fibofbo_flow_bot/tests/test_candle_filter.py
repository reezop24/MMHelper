from __future__ import annotations

import unittest

from candle_filter import analyzeCandleQuality


def mk_candle(o: float, h: float, l: float, c: float, i: int) -> dict:
    return {
        "time": f"2026-02-01 00:{i:02d}:00",
        "open": o,
        "high": h,
        "low": l,
        "close": c,
    }


class TestCandleFilter(unittest.TestCase):
    def test_normal_trend_no_anomaly(self) -> None:
        candles = []
        px = 100.0
        for i in range(40):
            o = px
            c = px + 0.6
            h = c + 0.3
            l = o - 0.3
            candles.append(mk_candle(o, h, l, c, i))
            px = c
        out = analyzeCandleQuality(candles, atr_period=14)
        flagged = [c for c in out if c.get("is_anomaly")]
        self.assertEqual(len(flagged), 0)

    def test_single_spike_flagged(self) -> None:
        candles = []
        px = 100.0
        for i in range(25):
            o = px
            c = px + 0.2
            h = c + 0.25
            l = o - 0.25
            candles.append(mk_candle(o, h, l, c, i))
            px = c
        candles.append(mk_candle(px, px + 8.0, px - 8.0, px + 0.1, 26))
        out = analyzeCandleQuality(candles, atr_period=14)
        self.assertTrue(bool(out[-1].get("is_anomaly")))

    def test_huge_wick_thin_body_flagged(self) -> None:
        candles = []
        px = 100.0
        for i in range(25):
            o = px
            c = px + 0.2
            h = c + 0.25
            l = o - 0.25
            candles.append(mk_candle(o, h, l, c, i))
            px = c
        # tiny body, huge lower wick
        candles.append(mk_candle(px, px + 0.2, px - 5.5, px + 0.01, 26))
        out = analyzeCandleQuality(candles, atr_period=14)
        self.assertTrue(bool(out[-1].get("is_anomaly")))


if __name__ == "__main__":
    unittest.main()

