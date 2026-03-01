from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActiveLegConfig:
    h1_overextension_mult: float = 1.2
    m30_overextension_mult: float = 1.5
    leg_near_atr_mult: float = 0.35
    atr_threshold_by_tf: dict[str, float] = field(
        default_factory=lambda: {
            "H1": 1.6,
            "M30": 1.7,
            "M15": 1.8,
        }
    )
    anomaly_filter_enabled: bool = True
    anomaly_range_multiplier: float = 4.0
    anomaly_wick_multiplier: float = 2.0
    anomaly_micro_range_ratio: float = 0.25


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _tf_state_from_mtf(mtf_result: dict[str, Any], tf: str) -> dict[str, Any]:
    mtf_state = (mtf_result or {}).get("mtf_state", {})
    if tf == "H4":
        return ((mtf_state.get("context") or {}).get("H4") or {})
    if tf == "H1":
        return ((mtf_state.get("bridge") or {}).get("H1") or {})
    if tf == "M30":
        return ((mtf_state.get("bridge") or {}).get("M30") or {})
    if tf == "M15":
        return ((mtf_state.get("execution") or {}).get("M15") or {})
    if tf == "M5":
        return ((mtf_state.get("execution") or {}).get("M5") or {})
    return {}


def _current_price_from_mtf(mtf_result: dict[str, Any]) -> float | None:
    for tf in ("M5", "M15", "H1", "H4"):
        s = _tf_state_from_mtf(mtf_result, tf)
        x = s.get("last_close")
        if x is None:
            continue
        px = _safe_float(x, default=float("nan"))
        if px == px:  # not nan
            return px
    return None


def _leg_end_price(mtf_result: dict[str, Any], tf: str, direction: str | None) -> float | None:
    state = _tf_state_from_mtf(mtf_result, tf)
    if direction == "BULL":
        p = ((state.get("lastSwingHigh") or {}).get("price"))
    elif direction == "BEAR":
        p = ((state.get("lastSwingLow") or {}).get("price"))
    else:
        p = None
    if p is None:
        return None
    px = _safe_float(p, default=float("nan"))
    if px == px:
        return px
    return None


def _tf_impulse(impulse_result: dict[str, Any], tf: str) -> dict[str, Any]:
    out = (impulse_result or {}).get(tf, {})
    return out if isinstance(out, dict) else {}


def _is_align(direction: str | None, h4_bias: str) -> bool:
    return direction in {"BULL", "BEAR"} and direction == h4_bias


def _atr_from_impulse(imp: dict[str, Any]) -> float:
    rng = _safe_float(imp.get("range"), 0.0)
    ratio = _safe_float(imp.get("atr_ratio"), 0.0)
    if ratio <= 0:
        return 0.0
    return rng / ratio


def _state_no_valid(notes: list[str]) -> dict[str, Any]:
    return {
        "active_tf": None,
        "direction": None,
        "state": "NO_VALID_STRUCTURE",
        "action": "STANDBY",
        "leg_start_index": -1,
        "leg_end_index": -1,
        "atr_ratio": 0.0,
        "notes": notes,
    }


def evaluateActiveLeg(
    mtf_result: dict[str, Any],
    impulse_result: dict[str, Any],
    config: ActiveLegConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ActiveLegConfig()

    h4_state = _tf_state_from_mtf(mtf_result, "H4")
    h4_bias = str(h4_state.get("bias") or "RANGE")
    h4_phase = str(h4_state.get("phase") or "UNKNOWN")
    h4_invalidated = bool(h4_state.get("invalidated"))
    score_state = (mtf_result or {}).get("score_state") or {}
    direction_ready = bool(score_state.get("direction_ready"))
    # Backward compatibility for old mtf payloads that do not expose direction_ready yet.
    if "direction_ready" not in score_state:
        direction_ready = h4_bias in {"BULL", "BEAR"} and not h4_invalidated

    if not direction_ready:
        return _state_no_valid(["Direction not ready"])
    if h4_invalidated:
        return _state_no_valid(["H4 invalidated"])
    if h4_bias not in {"BULL", "BEAR"}:
        return _state_no_valid(["H4 context not directional"])

    h1_imp = _tf_impulse(impulse_result, "H1")
    m30_imp = _tf_impulse(impulse_result, "M30")
    m15_imp = _tf_impulse(impulse_result, "M15")

    h1_dir = str(h1_imp.get("direction") or "")
    h1_phase = str(h1_imp.get("phase") or "")
    m30_dir = str(m30_imp.get("direction") or "")
    m30_phase = str(m30_imp.get("phase") or "")
    m15_dir = str(m15_imp.get("direction") or "")
    m15_phase = str(m15_imp.get("phase") or "")

    notes: list[str] = []

    # hard structure conflict: locked H4 context vs opposite H1 impulse.
    if h1_phase == "IMPULSE" and h1_dir in {"BULL", "BEAR"} and h1_dir != h4_bias:
        return _state_no_valid(["H1 impulse conflicts with H4 bias"])

    active_tf: str | None = None
    active_imp: dict[str, Any] = {}
    direction: str | None = None

    if h1_phase == "IMPULSE" and _is_align(h1_dir, h4_bias):
        active_tf = "H1"
        active_imp = h1_imp
        direction = h1_dir
        notes.append("H1 impulse aligned with H4")
    elif h1_phase != "IMPULSE" and m30_phase == "IMPULSE" and _is_align(m30_dir, h4_bias):
        active_tf = "M30"
        active_imp = m30_imp
        direction = m30_dir
        notes.append("M30 temporary active leg (H1 not impulse)")
    else:
        # Keep directional context alive even when no fresh H1/M30 impulse is present.
        # M15-only impulse remains execution-only and should not become primary active leg.
        active_tf = "H1"
        active_imp = h1_imp if isinstance(h1_imp, dict) else {}
        direction = h4_bias
        if m15_phase == "IMPULSE" and _is_align(m15_dir, h4_bias):
            notes.append("Only M15 impulse detected (execution layer only)")
        notes.append("No aligned H1/M30 impulse, using H4 directional context")

    atr_ratio = _safe_float(active_imp.get("atr_ratio"), 0.0)
    leg_start = int(active_imp.get("start_index") or -1)
    leg_end = int(active_imp.get("end_index") or -1)

    current_price = _current_price_from_mtf(mtf_result)
    leg_end_price = _leg_end_price(mtf_result, active_tf, direction)
    est_atr = _atr_from_impulse(active_imp)

    # overextension
    overextension_mult = cfg.h1_overextension_mult if active_tf == "H1" else cfg.m30_overextension_mult
    is_overextended = False
    if current_price is not None and leg_end_price is not None and est_atr > 0:
        if direction == "BULL":
            is_overextended = (current_price - leg_end_price) > (est_atr * overextension_mult)
        elif direction == "BEAR":
            is_overextended = (leg_end_price - current_price) > (est_atr * overextension_mult)

    lower_tf_correction = False
    if active_tf == "H1":
        lower_tf_correction = (m30_phase == "CORRECTION") or (m15_phase == "CORRECTION")
    elif active_tf == "M30":
        lower_tf_correction = (m15_phase == "CORRECTION")

    atr_threshold = _safe_float(cfg.atr_threshold_by_tf.get(active_tf or "", 1.6), 1.6)

    near_leg_end = False
    if current_price is not None and leg_end_price is not None and est_atr > 0:
        near_leg_end = abs(current_price - leg_end_price) <= (est_atr * cfg.leg_near_atr_mult)

    if h4_phase == "COMPRESSION_IN_TREND":
        state = "COMPRESSION_ACTIVE"
        action = "WAIT_BREAKOUT_OR_RETRACE"
        notes.append("H4 compression-in-trend context")
    elif h4_phase == "PULLBACK":
        state = "PULLBACK_ACTIVE"
        action = "WAIT_RETRACE"
        notes.append("H4 pullback context")
    elif is_overextended:
        state = "WAIT_RETRACE"
        action = "WAIT_CORRECTION"
        notes.append("Leg overextended from current price")
    elif lower_tf_correction:
        state = "RETRACE_IN_PROGRESS"
        action = "MONITOR_FIBO_ZONE"
        notes.append("Lower timeframe correction detected")
    elif h4_phase == "EXPANSION":
        state = "EXPANSION_ACTIVE"
        action = "WAIT_RETRACE"
        notes.append("H4 expansion context")
    elif str(active_imp.get("phase") or "") == "IMPULSE" and atr_ratio >= atr_threshold and near_leg_end:
        state = "EXPANSION_ACTIVE"
        action = "WAIT_RETRACE"
        notes.append("Impulse expansion still active")
    else:
        state = "PULLBACK_ACTIVE"
        action = "WAIT_RETRACE"
        notes.append("Directional context active; waiting for cleaner retrace setup")

    return {
        "active_tf": active_tf,
        "direction": direction,
        "state": state,
        "action": action,
        "leg_start_index": leg_start,
        "leg_end_index": leg_end,
        "atr_ratio": float(round(atr_ratio, 4)),
        "notes": notes,
    }


def explainActiveLeg(result: dict[str, Any]) -> str:
    tf = str(result.get("active_tf") or "-")
    direction = str(result.get("direction") or "-")
    state = str(result.get("state") or "NO_VALID_STRUCTURE")
    action = str(result.get("action") or "STANDBY")
    atr_ratio = _safe_float(result.get("atr_ratio"), 0.0)
    return "\n".join(
        [
            f"Active TF: {tf}",
            f"Direction: {direction}",
            f"State: {state}",
            f"Action: {action}",
            f"ATR ratio: {atr_ratio:.2f}",
        ]
    )
