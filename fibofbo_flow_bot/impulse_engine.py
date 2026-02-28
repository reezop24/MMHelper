from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TARGET_TFS = ("H4", "H1", "M30", "M15")


@dataclass
class ImpulseConfig:
    swing_lookback: int = 2
    atr_period: int = 14
    body_dominance_ratio: float = 0.60
    body_dominance_min_count: int = 2
    displacement_body_avg_mult: float = 1.30
    correction_atr_ratio_max: float = 1.20
    correction_overlap_min: float = 0.55
    correction_retrace_min: float = 0.30
    correction_retrace_max: float = 0.70
    compression_min_candles: int = 8
    compression_max_candles: int = 20
    compression_window: int = 12
    compression_overlap_min: float = 0.70
    compression_wick_dom_min: float = 0.55
    compression_range_atr_mult: float = 1.10
    retrace_guard_max: float = 0.50
    atr_multiplier_by_tf: dict[str, float] = field(
        default_factory=lambda: {
            "H4": 1.5,
            "H1": 1.6,
            "M30": 1.7,
            "M15": 1.8,
        }
    )


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _norm_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows or []):
        if not isinstance(r, dict):
            continue
        o = _to_float(r.get("open"))
        h = _to_float(r.get("high"))
        l = _to_float(r.get("low"))
        c = _to_float(r.get("close"))
        ts = str(r.get("time") or r.get("ts") or "")
        if h == 0.0 and l == 0.0 and o == 0.0 and c == 0.0:
            continue
        out.append({"idx": i, "ts": ts, "open": o, "high": h, "low": l, "close": c})
    return out


def _detect_swings(candles: list[dict[str, Any]], lookback: int) -> list[dict[str, Any]]:
    if len(candles) < (lookback * 2 + 1):
        return []
    raw: list[dict[str, Any]] = []
    for i in range(lookback, len(candles) - lookback):
        c = candles[i]
        others = candles[i - lookback : i] + candles[i + 1 : i + lookback + 1]
        if all(c["high"] > x["high"] for x in others):
            raw.append({"idx": i, "ts": c["ts"], "kind": "H", "price": c["high"]})
        elif all(c["low"] < x["low"] for x in others):
            raw.append({"idx": i, "ts": c["ts"], "kind": "L", "price": c["low"]})

    # compress repeated same-kind swings
    out: list[dict[str, Any]] = []
    for s in raw:
        if not out:
            out.append(s)
            continue
        p = out[-1]
        if p["kind"] != s["kind"]:
            out.append(s)
            continue
        if s["kind"] == "H" and s["price"] > p["price"]:
            out[-1] = s
        if s["kind"] == "L" and s["price"] < p["price"]:
            out[-1] = s
    return out


def _true_range(curr: dict[str, Any], prev_close: float | None) -> float:
    h = float(curr["high"])
    l = float(curr["low"])
    if prev_close is None:
        return max(h - l, 0.0)
    return max(h - l, abs(h - prev_close), abs(l - prev_close))


def _atr(candles: list[dict[str, Any]], period: int) -> list[float]:
    if not candles:
        return []
    out: list[float] = []
    trs: list[float] = []
    prev_close: float | None = None
    for c in candles:
        tr = _true_range(c, prev_close)
        trs.append(tr)
        prev_close = float(c["close"])
        if len(trs) < period:
            out.append(sum(trs) / max(1, len(trs)))
        else:
            window = trs[-period:]
            out.append(sum(window) / period)
    return out


def _avg_body(candles: list[dict[str, Any]]) -> float:
    if not candles:
        return 0.0
    return sum(abs(float(c["close"]) - float(c["open"])) for c in candles) / len(candles)


def _overlap_ratio(candles: list[dict[str, Any]]) -> float:
    if len(candles) < 2:
        return 0.0
    cnt = 0
    for i in range(1, len(candles)):
        a = candles[i - 1]
        b = candles[i]
        lo = max(float(a["low"]), float(b["low"]))
        hi = min(float(a["high"]), float(b["high"]))
        if hi > lo:
            cnt += 1
    return cnt / (len(candles) - 1)


def _wick_dominance(candles: list[dict[str, Any]]) -> float:
    if not candles:
        return 0.0
    wick_dominant = 0
    for c in candles:
        o = float(c["open"])
        h = float(c["high"])
        l = float(c["low"])
        cl = float(c["close"])
        body = abs(cl - o)
        upper = max(0.0, h - max(o, cl))
        lower = max(0.0, min(o, cl) - l)
        wick = upper + lower
        if wick > body:
            wick_dominant += 1
    return wick_dominant / len(candles)


def _find_last_leg(swings: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(swings) < 2:
        return None
    a = swings[-2]
    b = swings[-1]
    if a["kind"] == b["kind"]:
        return None
    direction = "BULL" if a["kind"] == "L" and b["kind"] == "H" else "BEAR"
    start_idx = int(min(a["idx"], b["idx"]))
    end_idx = int(max(a["idx"], b["idx"]))
    return {
        "direction": direction,
        "start": a,
        "end": b,
        "start_idx": start_idx,
        "end_idx": end_idx,
        "range": abs(float(b["price"]) - float(a["price"])),
    }


def _collect_legs(swings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(1, len(swings)):
        a = swings[i - 1]
        b = swings[i]
        if a["kind"] == b["kind"]:
            continue
        direction = "BULL" if a["kind"] == "L" and b["kind"] == "H" else "BEAR"
        out.append(
            {
                "direction": direction,
                "start": a,
                "end": b,
                "start_idx": int(min(a["idx"], b["idx"])),
                "end_idx": int(max(a["idx"], b["idx"])),
                "range": abs(float(b["price"]) - float(a["price"])),
            }
        )
    return out


def _pick_effective_leg(swings: list[dict[str, Any]], candles: list[dict[str, Any]], atrs: list[float]) -> dict[str, Any] | None:
    legs = _collect_legs(swings)
    if not legs:
        return _recent_leg_from_price(candles, window=10)
    # Filter by recency: only legs ending within last 25% candles.
    min_end_idx = int(len(candles) * 0.75)
    recent_legs = [leg for leg in legs if int(leg.get("end_idx", -1)) >= min_end_idx]
    if not recent_legs:
        return _recent_leg_from_price(candles, window=10)

    scored: list[dict[str, Any]] = []
    for leg in recent_legs:
        e = int(leg["end_idx"])
        if e < 0 or e >= len(candles):
            continue
        atr_ref = atrs[e] if e < len(atrs) else (atrs[-1] if atrs else 0.0)
        if atr_ref <= 0:
            continue
        ratio = float(leg["range"]) / atr_ref
        x = dict(leg)
        x["atr_ratio"] = ratio
        scored.append(x)
    if not scored:
        return _recent_leg_from_price(candles, window=10)

    # Choose highest ATR-ratio leg in recent zone only if sufficiently meaningful.
    viable = [x for x in scored if float(x.get("atr_ratio", 0.0)) >= 1.0]
    if viable:
        return max(viable, key=lambda x: float(x.get("atr_ratio", 0.0)))
    return _recent_leg_from_price(candles, window=10)


def _recent_leg_from_price(candles: list[dict[str, Any]], window: int = 14) -> dict[str, Any] | None:
    if len(candles) < 3:
        return None
    n = max(3, min(window, len(candles)))
    off = len(candles) - n
    seg = candles[-n:]
    lows = [(i, float(c["low"])) for i, c in enumerate(seg)]
    highs = [(i, float(c["high"])) for i, c in enumerate(seg)]
    low_i, low_v = min(lows, key=lambda x: x[1])
    high_i, high_v = max(highs, key=lambda x: x[1])

    if low_i == high_i:
        return None
    if low_i < high_i:
        start_i = off + low_i
        end_i = off + high_i
        direction = "BULL"
        rng = high_v - low_v
        start = {"idx": start_i, "ts": candles[start_i]["ts"], "kind": "L", "price": low_v}
        end = {"idx": end_i, "ts": candles[end_i]["ts"], "kind": "H", "price": high_v}
    else:
        start_i = off + high_i
        end_i = off + low_i
        direction = "BEAR"
        rng = high_v - low_v
        start = {"idx": start_i, "ts": candles[start_i]["ts"], "kind": "H", "price": high_v}
        end = {"idx": end_i, "ts": candles[end_i]["ts"], "kind": "L", "price": low_v}
    return {
        "direction": direction,
        "start": start,
        "end": end,
        "start_idx": int(start_i),
        "end_idx": int(end_i),
        "range": abs(float(rng)),
    }


def _find_prev_same_swing(swings: list[dict[str, Any]], idx: int, kind: str) -> dict[str, Any] | None:
    for i in range(idx - 1, -1, -1):
        s = swings[i]
        if s["kind"] == kind:
            return s
    return None


def _detect_bos(candles: list[dict[str, Any]], swings: list[dict[str, Any]], leg: dict[str, Any]) -> bool:
    if not leg:
        return False
    end = leg["end"]
    end_pos = next((i for i, s in enumerate(swings) if s["idx"] == end["idx"] and s["kind"] == end["kind"]), -1)
    if end_pos < 0:
        # Leg may come from price-extrema fallback and not map 1:1 to swings.
        if leg["direction"] == "BULL":
            prev_hs = [s for s in swings if s["kind"] == "H" and int(s["idx"]) < int(leg["start_idx"])]
            if not prev_hs:
                return False
            level = max(float(s["price"]) for s in prev_hs)
            return any(float(c["close"]) > level for c in candles[leg["start_idx"] : leg["end_idx"] + 1])
        prev_ls = [s for s in swings if s["kind"] == "L" and int(s["idx"]) < int(leg["start_idx"])]
        if not prev_ls:
            return False
        level = min(float(s["price"]) for s in prev_ls)
        return any(float(c["close"]) < level for c in candles[leg["start_idx"] : leg["end_idx"] + 1])

    if leg["direction"] == "BULL":
        prev_h = _find_prev_same_swing(swings, end_pos, "H")
        if not prev_h:
            return False
        level = float(prev_h["price"])
        for c in candles[leg["start_idx"] : leg["end_idx"] + 1]:
            if float(c["close"]) > level:
                return True
        return False

    prev_l = _find_prev_same_swing(swings, end_pos, "L")
    if not prev_l:
        return False
    level = float(prev_l["price"])
    for c in candles[leg["start_idx"] : leg["end_idx"] + 1]:
        if float(c["close"]) < level:
            return True
    return False


def _body_dominance(leg_candles: list[dict[str, Any]], ratio: float) -> tuple[bool, int]:
    strong = 0
    for c in leg_candles:
        rng = max(float(c["high"]) - float(c["low"]), 1e-9)
        body = abs(float(c["close"]) - float(c["open"]))
        if body / rng >= ratio:
            strong += 1
    return strong >= 2, strong


def _spike_penalty(leg_candles: list[dict[str, Any]]) -> bool:
    if not leg_candles:
        return False
    if len(leg_candles) <= 2:
        return True
    ranges = [max(float(c["high"]) - float(c["low"]), 0.0) for c in leg_candles]
    total = sum(ranges)
    if total <= 0:
        return False
    return (max(ranges) / total) >= 0.70


def _retrace_guard_ok(candles: list[dict[str, Any]], leg: dict[str, Any], retrace_guard_max: float) -> bool:
    if not leg:
        return False
    end_idx = int(leg["end_idx"])
    if end_idx >= len(candles) - 1:
        return True
    chk = candles[end_idx + 1 : min(len(candles), end_idx + 3)]
    if not chk:
        return True

    leg_range = max(float(leg["range"]), 1e-9)
    end_price = float(leg["end"]["price"])

    if leg["direction"] == "BULL":
        worst = min(float(c["low"]) for c in chk)
        retr = (end_price - worst) / leg_range
    else:
        worst = max(float(c["high"]) for c in chk)
        retr = (worst - end_price) / leg_range

    return retr <= retrace_guard_max


def _latest_compression(
    candles: list[dict[str, Any]],
    atrs: list[float],
    cfg: ImpulseConfig,
    atr_ratio: float,
    tf_threshold: float,
) -> dict[str, Any]:
    n = min(max(cfg.compression_window, cfg.compression_min_candles), cfg.compression_max_candles)
    if len(candles) < n:
        return {"is_compression": False}
    win = candles[-n:]
    win_range = max(float(c["high"]) for c in win) - min(float(c["low"]) for c in win)
    atr_now = atrs[-1] if atrs else 0.0
    overlap = _overlap_ratio(win)
    wick_dom = _wick_dominance(win)

    # no BOS in compression window: closes remain inside first half's bounds
    half = max(2, n // 2)
    ref_high = max(float(c["high"]) for c in win[:half])
    ref_low = min(float(c["low"]) for c in win[:half])
    bos_inside = any((float(c["close"]) > ref_high or float(c["close"]) < ref_low) for c in win[half:])

    is_compression = (
        atr_now > 0
        and win_range <= (atr_now * cfg.compression_range_atr_mult)
        and overlap >= cfg.compression_overlap_min
        and wick_dom >= cfg.compression_wick_dom_min
        and not bos_inside
    )
    if atr_ratio >= tf_threshold:
        is_compression = False
    return {
        "is_compression": bool(is_compression),
        "start_index": len(candles) - n,
        "end_index": len(candles) - 1,
        "range": win_range,
        "overlap": overlap,
        "wick_dom": wick_dom,
    }


def _find_prev_impulse_leg(swings: list[dict[str, Any]], candles: list[dict[str, Any]], atrs: list[float], tf_threshold: float, cfg: ImpulseConfig) -> dict[str, Any] | None:
    if len(swings) < 4:
        return None
    # scan backward for recent valid impulse-like leg
    for pos in range(len(swings) - 1, 1, -1):
        sub = swings[: pos + 1]
        leg = _find_last_leg(sub)
        if not leg:
            continue
        s = int(leg["start_idx"])
        e = int(leg["end_idx"])
        if e <= s or e >= len(candles):
            continue
        seg = candles[s : e + 1]
        if len(seg) < 2:
            continue
        atr_ref = atrs[e] if e < len(atrs) else (atrs[-1] if atrs else 0.0)
        if atr_ref <= 0:
            continue
        atr_ratio = float(leg["range"]) / atr_ref
        body_ok, _ = _body_dominance(seg, cfg.body_dominance_ratio)
        bos = _detect_bos(candles, sub, leg)
        if bos and body_ok and atr_ratio >= tf_threshold:
            leg["atr_ratio"] = atr_ratio
            return leg
    return None


def analyzeImpulse(tf_name: str, candles: list[dict[str, Any]], config: ImpulseConfig | None = None) -> dict[str, Any]:
    cfg = config or ImpulseConfig()
    tf = str(tf_name or "").upper()
    if tf not in TARGET_TFS:
        raise ValueError(f"Unsupported tf: {tf}")

    rows = _norm_candles(candles)
    if len(rows) < 30:
        return {
            "timeframe": tf,
            "phase": "COMPRESSION",
            "direction": None,
            "valid_impulse": False,
            "strength_score": 0,
            "bos": False,
            "atr_ratio": 0.0,
            "range": 0.0,
            "start_index": 0,
            "end_index": max(0, len(rows) - 1),
            "notes": ["Not enough candles"],
        }

    swings = _detect_swings(rows, cfg.swing_lookback)
    atrs = _atr(rows, cfg.atr_period)
    leg = _pick_effective_leg(swings, rows, atrs)
    tf_threshold = float(cfg.atr_multiplier_by_tf.get(tf, 1.6))
    compression = _latest_compression(rows, atrs, cfg, atr_ratio=0.0, tf_threshold=tf_threshold)

    if not leg:
        notes = ["No clear leg from swings"]
        if compression.get("is_compression"):
            notes.append("Compression detected")
        return {
            "timeframe": tf,
            "phase": "COMPRESSION" if compression.get("is_compression") else "CORRECTION",
            "direction": None,
            "valid_impulse": False,
            "strength_score": 0,
            "bos": False,
            "atr_ratio": 0.0,
            "range": 0.0,
            "start_index": int(compression.get("start_index", 0)),
            "end_index": int(compression.get("end_index", len(rows) - 1)),
            "notes": notes,
        }

    s_idx = int(leg["start_idx"])
    e_idx = int(leg["end_idx"])
    seg = rows[s_idx : e_idx + 1]

    atr_ref = atrs[e_idx] if e_idx < len(atrs) else atrs[-1]
    atr_ratio = (float(leg["range"]) / atr_ref) if atr_ref > 0 else 0.0
    compression = _latest_compression(rows, atrs, cfg, atr_ratio=atr_ratio, tf_threshold=tf_threshold)

    body_dom_ok, strong_body_count = _body_dominance(seg, cfg.body_dominance_ratio)
    bos = _detect_bos(rows, swings, leg)
    spike_pen = _spike_penalty(seg)

    displacement = (
        atr_ratio >= tf_threshold
        and strong_body_count >= cfg.body_dominance_min_count
    )

    score = 0
    notes: list[str] = []
    if bos:
        score += 3
        notes.append("BOS: YES")
    else:
        notes.append("BOS: NO")

    if atr_ratio >= tf_threshold:
        score += 2
        notes.append(f"ATR ratio {atr_ratio:.2f} >= {tf_threshold:.2f}")
    else:
        notes.append(f"ATR ratio {atr_ratio:.2f} < {tf_threshold:.2f}")

    if displacement:
        score += 1
        notes.append("Displacement: YES")
    else:
        notes.append("Displacement: NO")

    if body_dom_ok:
        score += 2
        notes.append("Body dominance: YES")
    else:
        notes.append("Body dominance: NO")

    if spike_pen:
        score -= 2
        notes.append("Spike penalty applied")

    compression_breakout_bonus = 0
    if compression.get("is_compression") and displacement and bos:
        compression_breakout_bonus = 1
        score += 1
        notes.append("Compression breakout bonus")

    prev_impulse = _find_prev_impulse_leg(swings, rows, atrs, tf_threshold, cfg)
    overlap_seg = _overlap_ratio(seg)

    # Priority-based classification:
    # 1) IMPULSE, 2) COMPRESSION(low ATR), 3) CORRECTION-like, 4) fallback CORRECTION.
    phase = "CORRECTION"
    correction_like = False
    if bos and atr_ratio >= tf_threshold:
        phase = "IMPULSE"
    elif compression.get("is_compression") and atr_ratio < tf_threshold:
        phase = "COMPRESSION"
    else:
        correction_retrace = None
        if prev_impulse is not None:
            prev_range = max(float(prev_impulse.get("range", 0.0)), 1e-9)
            if prev_impulse["direction"] == "BULL":
                correction_retrace = (float(prev_impulse["end"]["price"]) - float(leg["end"]["price"])) / prev_range
            else:
                correction_retrace = (float(leg["end"]["price"]) - float(prev_impulse["end"]["price"])) / prev_range

        correction_like = (
            atr_ratio < cfg.correction_atr_ratio_max
            and overlap_seg >= cfg.correction_overlap_min
        )
        if correction_retrace is not None:
            correction_like = correction_like and (cfg.correction_retrace_min <= correction_retrace <= cfg.correction_retrace_max)

        if correction_like:
            phase = "CORRECTION"
        else:
            phase = "CORRECTION"

    valid_impulse = bool(phase == "IMPULSE" and score >= 6)

    direction: str | None = None
    if phase in {"IMPULSE", "CORRECTION"}:
        direction = str(leg["direction"])

    return {
        "timeframe": tf,
        "phase": phase,
        "direction": direction,
        "valid_impulse": valid_impulse,
        "strength_score": max(0, min(10, int(score))),
        "bos": bool(bos),
        "atr_ratio": float(round(atr_ratio, 4)),
        "range": float(round(float(leg["range"]), 4)),
        "start_index": s_idx if phase != "COMPRESSION" else int(compression.get("start_index", s_idx)),
        "end_index": e_idx if phase != "COMPRESSION" else int(compression.get("end_index", e_idx)),
        "notes": notes,
    }


def detectImpulseAll(candlesByTF: dict[str, list[dict[str, Any]]], config: ImpulseConfig | None = None) -> dict[str, dict[str, Any]]:
    cfg = config or ImpulseConfig()
    out: dict[str, dict[str, Any]] = {}
    for tf in TARGET_TFS:
        out[tf] = analyzeImpulse(tf, candlesByTF.get(tf, []), cfg)
    return out


def explainImpulse(result: dict[str, Any]) -> str:
    tf = str(result.get("timeframe") or "?")
    phase = str(result.get("phase") or "UNKNOWN")
    direction = str(result.get("direction") or "-")
    score = int(result.get("strength_score") or 0)
    rng = float(result.get("range") or 0.0)
    atr_ratio = float(result.get("atr_ratio") or 0.0)
    bos = "YES" if bool(result.get("bos")) else "NO"
    displacement = "YES" if any("Displacement: YES" in str(n) for n in (result.get("notes") or [])) else "NO"

    lines = [
        f"{tf} -> {phase} {direction} (score {score})",
        f"Range: {rng:.2f}",
        f"ATR ratio: {atr_ratio:.2f}",
        f"BOS: {bos}",
        f"Displacement: {displacement}",
    ]
    return "\n".join(lines)
