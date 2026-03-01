from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from candle_filter import analyzeCandleQualityWithConfig

@dataclass
class RetraceConfig:
    sweep_trigger_ratio: float = 0.9
    sweep_max_reclaim_candles: int = 3
    enable_sweep: bool = True
    sweep_ready_direct: bool = True
    sweep_require_micro_confirm: bool = True

    depth_micro_max: float = 0.236
    depth_shallow_max: float = 0.382
    depth_normal_max: float = 0.618
    depth_deep_max: float = 0.786
    depth_extreme_max: float = 0.9

    depth_min_by_strength: dict[str, str] = field(
        default_factory=lambda: {
            "high": "SHALLOW",   # atr_ratio >= 4
            "mid": "NORMAL",     # atr_ratio >= 2
            "low": "DEEP",       # atr_ratio < 2
        }
    )
    anomaly_filter_enabled: bool = True
    anomaly_range_multiplier: float = 4.0
    anomaly_wick_multiplier: float = 2.0
    anomaly_micro_range_ratio: float = 0.25


_DEPTH_ORDER = {
    "MICRO": 0,
    "SHALLOW": 1,
    "NORMAL": 2,
    "DEEP": 3,
    "EXTREME": 4,
    "STRUCTURE_RISK": 5,
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = -1) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _tf_candles(candles_by_tf: dict[str, list[dict[str, Any]]], tf: str) -> list[dict[str, Any]]:
    if tf in candles_by_tf:
        return candles_by_tf.get(tf) or []
    lower_map = {
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
        "D1": "d1",
        "W1": "w1",
    }
    key = lower_map.get(tf, tf.lower())
    return candles_by_tf.get(key) or []


def _depth_type(r: float, cfg: RetraceConfig) -> str:
    # Layered baseline model (broad probability capture):
    # <0.10 MICRO, 0.10-0.30 SHALLOW, 0.30-0.50 NORMAL, >=0.50 DEEP
    if r < 0.10:
        return "MICRO"
    if r < 0.30:
        return "SHALLOW"
    if r < 0.50:
        return "NORMAL"
    return "DEEP"


def _acceptable_min_depth(atr_ratio: float, cfg: RetraceConfig) -> str:
    if atr_ratio >= 4.0:
        return cfg.depth_min_by_strength.get("high", "SHALLOW")
    if atr_ratio >= 2.0:
        return cfg.depth_min_by_strength.get("mid", "NORMAL")
    return cfg.depth_min_by_strength.get("low", "DEEP")


def _check_reclaim(candles: list[dict[str, Any]], start_idx: int, boundary: float, direction: str, max_candles: int) -> tuple[bool, int]:
    # returns (reclaimed, reclaim_idx)
    end = min(len(candles), start_idx + 1 + max_candles)
    for i in range(start_idx + 1, end):
        close = _safe_float(candles[i].get("close"), 0.0)
        if direction == "BULL":
            if close > boundary:
                return True, i
        else:
            if close < boundary:
                return True, i
    return False, -1


def _opposite_bos_info(candles: list[dict[str, Any]], leg_end_idx: int, boundary: float, direction: str, max_reclaim: int) -> dict[str, Any]:
    # opposite BOS if break occurs and NOT reclaimed within max_reclaim candles.
    for i in range(max(leg_end_idx + 1, 0), len(candles)):
        if bool(candles[i].get("is_anomaly")):
            continue
        close = _safe_float(candles[i].get("close"), 0.0)
        breached = (close < boundary) if direction == "BULL" else (close > boundary)
        if not breached:
            continue
        reclaimed, reclaim_idx = _check_reclaim(candles, i, boundary, direction, max_reclaim)
        if reclaimed:
            return {
                "breach_found": True,
                "breach_idx": i,
                "reclaimed": True,
                "reclaim_idx": reclaim_idx,
                "opposite_bos": False,
            }
        return {
            "breach_found": True,
            "breach_idx": i,
            "reclaimed": False,
            "reclaim_idx": -1,
            "opposite_bos": True,
        }
    return {
        "breach_found": False,
        "breach_idx": -1,
        "reclaimed": False,
        "reclaim_idx": -1,
        "opposite_bos": False,
    }


def _micro_confirm_ok(impulse_result: dict[str, Any], direction: str) -> bool:
    m15 = (impulse_result or {}).get("M15") or {}
    m15_dir = str(m15.get("direction") or "")
    if m15_dir != direction:
        return False
    if bool(m15.get("bos")):
        return True
    notes = [str(x) for x in (m15.get("notes") or [])]
    return any("Displacement: YES" in x for x in notes)


def evaluateRetrace(
    active_leg_result: dict[str, Any],
    impulse_result: dict[str, Any],
    candlesByTF: dict[str, list[dict[str, Any]]],
    config: RetraceConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RetraceConfig()

    active_tf = str(active_leg_result.get("active_tf") or "")
    direction = str(active_leg_result.get("direction") or "")
    leg_start_index = _safe_int(active_leg_result.get("leg_start_index"), -1)
    leg_end_index = _safe_int(active_leg_result.get("leg_end_index"), -1)
    atr_ratio = _safe_float(active_leg_result.get("atr_ratio"), 0.0)

    out_base = {
        "active_tf": active_tf or None,
        "direction": direction or None,
        "retrace_ratio": 0.0,
        "depth_type": "MICRO",
        "depth": "MICRO",
        "structure_intact": False,
        "sweep_detected": False,
        "status": "INVALIDATED",
        "ready_for_setup": False,
        "notes": [],
    }

    if not active_tf or direction not in {"BULL", "BEAR"}:
        out_base["status"] = "INVALIDATED"
        out_base["notes"] = ["No active leg context"]
        return out_base

    candles = _tf_candles(candlesByTF, active_tf)
    candles = analyzeCandleQualityWithConfig(
        candles,
        atr_period=14,
        enabled=cfg.anomaly_filter_enabled,
        range_multiplier=cfg.anomaly_range_multiplier,
        wick_multiplier=cfg.anomaly_wick_multiplier,
        micro_range_ratio=cfg.anomaly_micro_range_ratio,
    )
    if not candles:
        out_base["status"] = "INVALIDATED"
        out_base["notes"] = [f"No candles for active_tf={active_tf}"]
        return out_base

    if not (0 <= leg_start_index < len(candles)) or not (0 <= leg_end_index < len(candles)):
        out_base["status"] = "INVALIDATED"
        out_base["notes"] = ["Invalid leg indices"]
        return out_base

    start = candles[leg_start_index]
    end = candles[leg_end_index]
    current_price = _safe_float(candles[-1].get("close"), 0.0)

    start_low = _safe_float(start.get("low"), 0.0)
    start_high = _safe_float(start.get("high"), 0.0)
    end_low = _safe_float(end.get("low"), 0.0)
    end_high = _safe_float(end.get("high"), 0.0)

    notes: list[str] = []

    post_leg = candles[max(leg_end_index + 1, 0) :]

    if direction == "BULL":
        leg_range = max(end_high - start_low, 1e-9)
        current_pullback = max(end_high - current_price, 0.0)
        retrace_ratio = current_pullback / leg_range
        deepest_price = min((_safe_float(c.get("low"), current_price) for c in post_leg), default=current_price)
        worst_pullback = max(end_high - deepest_price, 0.0)
        worst_retrace_ratio = worst_pullback / leg_range
        boundary = start_low
    else:
        leg_range = max(start_high - end_low, 1e-9)
        current_pullback = max(current_price - end_low, 0.0)
        retrace_ratio = current_pullback / leg_range
        highest_price = max((_safe_float(c.get("high"), current_price) for c in post_leg), default=current_price)
        worst_pullback = max(highest_price - end_low, 0.0)
        worst_retrace_ratio = worst_pullback / leg_range
        boundary = start_high

    depth_type = _depth_type(retrace_ratio, cfg)
    expected_min_depth = _acceptable_min_depth(atr_ratio, cfg)
    notes.append(f"Expected min depth by strength: {expected_min_depth}")

    bos_info = _opposite_bos_info(
        candles=candles,
        leg_end_idx=leg_end_index,
        boundary=boundary,
        direction=direction,
        max_reclaim=cfg.sweep_max_reclaim_candles,
    )
    structure_intact = not bool(bos_info.get("opposite_bos"))

    # optional signal: ATR drop during correction (simple proxy via M15/H1 phase)
    active_imp = (impulse_result or {}).get(active_tf) or {}
    phase = str(active_imp.get("phase") or "")
    if phase == "CORRECTION":
        notes.append("Correction phase flag on active_tf")

    sweep_relevant = depth_type == "EXTREME" or worst_retrace_ratio >= cfg.sweep_trigger_ratio
    sweep_detected = False

    if cfg.enable_sweep and sweep_relevant:
        breached = bool(bos_info.get("breach_found"))
        reclaimed = bool(bos_info.get("reclaimed"))
        no_opposite_bos = not bool(bos_info.get("opposite_bos"))
        micro_ok = _micro_confirm_ok(impulse_result, direction)

        if breached and reclaimed and no_opposite_bos:
            if cfg.sweep_require_micro_confirm:
                sweep_detected = micro_ok
            else:
                sweep_detected = True

    retrace_warning: str | None = None
    if not structure_intact:
        status = "INVALIDATED"
        ready = False
    else:
        # Baseline layered retrace behavior (inside directional context):
        # MICRO = early context only (not rejected)
        # SHALLOW/NORMAL = setup-ready
        # DEEP = setup-ready with warning
        if depth_type == "MICRO":
            status = "EARLY_RETRACE"
            ready = False
        elif depth_type == "SHALLOW":
            status = "VALID_RETRACE"
            ready = True
        elif depth_type == "NORMAL":
            status = "STRONG_RETRACE"
            ready = True
        else:
            status = "RISKY_RETRACE"
            ready = True
            retrace_warning = "DEEP_PULLBACK"

        # Sweep compatibility:
        # allow early-ready when micro retrace sweep confirms reclaim.
        if sweep_detected and cfg.enable_sweep and depth_type == "MICRO":
            status = "SWEEP_CONFIRMED_EARLY"
            ready = True
        elif sweep_detected and cfg.enable_sweep:
            status = "SWEEP_CONFIRMED"
            if not cfg.sweep_ready_direct:
                ready = False
                notes.append("Sweep confirmed, waiting structure confirm")

    out = {
        "active_tf": active_tf,
        "direction": direction,
        "retrace_ratio": float(round(retrace_ratio, 4)),
        "depth_type": depth_type,
        "depth": depth_type,
        "structure_intact": bool(structure_intact),
        "sweep_detected": bool(sweep_detected),
        "status": status,
        "ready_for_setup": bool(ready),
        "notes": notes,
    }
    if retrace_warning:
        out["retrace_warning"] = retrace_warning
    return out


def explainRetrace(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Active TF: {str(result.get('active_tf') or '-')}",
            f"Direction: {str(result.get('direction') or '-')}",
            f"Retrace ratio: {float(result.get('retrace_ratio') or 0.0):.2f}",
            f"Depth: {str(result.get('depth_type') or 'MICRO')}",
            f"Structure intact: {'YES' if bool(result.get('structure_intact')) else 'NO'}",
            f"Sweep detected: {'YES' if bool(result.get('sweep_detected')) else 'NO'}",
            f"Status: {str(result.get('status') or '-')}",
            f"Ready for setup: {'YES' if bool(result.get('ready_for_setup')) else 'NO'}",
        ]
    )
