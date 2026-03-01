from __future__ import annotations

from typing import Any

_PREV_RATIO_CACHE: dict[tuple[str, str, str], float] = {}


def resetFDCache() -> None:
    _PREV_RATIO_CACHE.clear()


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out


def _ratio(low: float | None, high: float | None, current_price: float | None) -> float | None:
    if low is None or high is None or current_price is None:
        return None
    rng = high - low
    if rng <= 0:
        return None
    return (current_price - low) / rng


def _normalize_bounds(low: float | None, high: float | None) -> tuple[float | None, float | None]:
    if low is None or high is None:
        return None, None
    return (low, high) if low <= high else (high, low)


def _levels(range_low: float | None, range_high: float | None) -> dict[str, float | None]:
    if range_low is None or range_high is None:
        return {
            "L0": None,
            "L12_5": None,
            "L25": None,
            "L37_5": None,
            "L50": None,
            "L62_5": None,
            "L75": None,
            "L87_5": None,
            "L100": None,
        }
    rng = range_high - range_low
    return {
        "L0": range_low,
        "L12_5": range_low + (rng * 0.125),
        "L25": range_low + (rng * 0.25),
        "L37_5": range_low + (rng * 0.375),
        "L50": range_low + (rng * 0.50),
        "L62_5": range_low + (rng * 0.625),
        "L75": range_low + (rng * 0.75),
        "L87_5": range_low + (rng * 0.875),
        "L100": range_high,
    }


def _side(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    if abs(ratio - 0.5) <= 1e-12:
        return "EQ"
    return "DISCOUNT" if ratio < 0.5 else "PREMIUM"


def _shift_flags(cache_key: tuple[str, str, str], ratio: float | None) -> tuple[bool, bool]:
    prev_ratio = _PREV_RATIO_CACHE.get(cache_key)
    shift_up = False
    shift_down = False
    if ratio is not None and prev_ratio is not None:
        shift_up = prev_ratio < 0.5 and ratio >= 0.5
        shift_down = prev_ratio > 0.5 and ratio <= 0.5
    if ratio is not None:
        _PREV_RATIO_CACHE[cache_key] = ratio
    return shift_up, shift_down


def _build_fd_block(
    *,
    mode: str,
    symbol: str,
    tf: str,
    low: float | None,
    high: float | None,
    current_close: float | None,
    is_impulse: bool,
    force_invalid: bool = False,
) -> dict[str, Any]:
    range_low, range_high = _normalize_bounds(low, high)
    valid = not force_invalid and range_low is not None and range_high is not None and current_close is not None
    invalid_reason: str | None = None
    ratio: float | None = None

    if valid:
        raw_ratio = _ratio(range_low, range_high, current_close)
        if raw_ratio is None:
            valid = False
            invalid_reason = "invalid_range"
        elif not is_impulse and (raw_ratio < 0.0 or raw_ratio > 1.0):
            # Swing FD strict validity: close must remain inside swing range.
            valid = False
            invalid_reason = "price outside range"
        elif is_impulse:
            # Impulse FD strict bounded ratio in [0, 1].
            ratio = max(0.0, min(1.0, raw_ratio))
        else:
            ratio = raw_ratio
    else:
        invalid_reason = "price outside range"

    levels = _levels(range_low, range_high)
    reaction_low = bool(valid and ratio is not None and ratio <= 0.25)
    reaction_high = bool(valid and ratio is not None and ratio >= 0.75)
    reaction_zone = reaction_low or reaction_high

    shift_up = False
    shift_down = False
    shift_crossed = False
    if valid:
        cache_key = (symbol, mode, tf)
        shift_up, shift_down = _shift_flags(cache_key, ratio)
        shift_crossed = shift_up or shift_down

    return {
        "valid": bool(valid),
        "invalid_reason": invalid_reason,
        "zone": (_classify_impulse(ratio) if is_impulse else _classify_external(ratio)) if valid else None,
        "range_low": range_low,
        "range_high": range_high,
        "current_close": current_close,
        "ratio": ratio if valid else None,
        "levels": levels,
        "reaction_zone": reaction_zone,
        "reaction_low": reaction_low,
        "reaction_high": reaction_high,
        "side": _side(ratio) if valid else None,
        "shift_up": shift_up,
        "shift_down": shift_down,
        "shift_crossed": shift_crossed,
    }


def _classify_external(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    if ratio < 0.25:
        return "DISCOUNT_EXT"
    if ratio < 0.5:
        return "LOW_RANGE_EXT"
    if abs(ratio - 0.5) <= 1e-12:
        return "EQUILIBRIUM_EXT"
    if ratio < 0.75:
        return "UPPER_RANGE_EXT"
    if ratio <= 1.0:
        return "PREMIUM_EXT"
    return "EXTREME_EXT"


def _classify_impulse(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    if ratio < 0.25:
        return "DISCOUNT_IMP"
    if ratio < 0.5:
        return "LOW_RANGE_IMP"
    if abs(ratio - 0.5) <= 1e-12:
        return "EQUILIBRIUM_IMP"
    if ratio < 0.75:
        return "UPPER_RANGE_IMP"
    if ratio <= 1.0:
        return "PREMIUM_IMP"
    return "EXTREME_IMP"


def computeExternalSwingFD(
    lastSwingLow: float | int | None,
    lastSwingHigh: float | int | None,
    current_price: float | int | None,
) -> dict[str, Any]:
    return _build_fd_block(
        mode="swing",
        symbol="XAUUSD",
        tf="H4",
        low=_safe_float(lastSwingLow),
        high=_safe_float(lastSwingHigh),
        current_close=_safe_float(current_price),
        is_impulse=False,
    )


def computeImpulseFD(
    impulse_low: float | int | None,
    impulse_high: float | int | None,
    current_price: float | int | None,
) -> dict[str, Any]:
    return _build_fd_block(
        mode="impulse",
        symbol="XAUUSD",
        tf="ACTIVE",
        low=_safe_float(impulse_low),
        high=_safe_float(impulse_high),
        current_close=_safe_float(current_price),
        is_impulse=True,
    )


def _find_current_price(mtf_result: dict[str, Any]) -> float | None:
    mtf_state = (mtf_result or {}).get("mtf_state") or {}
    for group_key, tf_list in (
        ("execution", ("M5", "M15")),
        ("bridge", ("H1", "M30")),
        ("context", ("H4", "D1", "W1")),
    ):
        grp = mtf_state.get(group_key) or {}
        for tf in tf_list:
            tf_state = grp.get(tf) or {}
            cp = _safe_float(tf_state.get("last_close"))
            if cp is not None:
                return cp
    return None


def _tf_state(mtf_result: dict[str, Any], tf: str) -> dict[str, Any]:
    mtf_state = (mtf_result or {}).get("mtf_state") or {}
    if tf == "H4":
        return ((mtf_state.get("context") or {}).get("H4") or {})
    if tf in {"H1", "M30"}:
        return ((mtf_state.get("bridge") or {}).get(tf) or {})
    if tf in {"M15", "M5"}:
        return ((mtf_state.get("execution") or {}).get(tf) or {})
    return {}


def evaluateFD(
    mtf_result: dict[str, Any],
    active_leg_result: dict[str, Any],
) -> dict[str, Any]:
    mtf_state = (mtf_result or {}).get("mtf_state") or {}
    symbol = str(mtf_state.get("symbol") or "XAUUSD")
    current_price = _find_current_price(mtf_result)

    h4_state = _tf_state(mtf_result, "H4")
    h4_low = _safe_float(((h4_state.get("lastSwingLow") or {}).get("price")))
    h4_high = _safe_float(((h4_state.get("lastSwingHigh") or {}).get("price")))
    swing = _build_fd_block(
        mode="swing",
        symbol=symbol,
        tf="H4",
        low=h4_low,
        high=h4_high,
        current_close=current_price,
        is_impulse=False,
    )

    impulse_low = _safe_float(active_leg_result.get("impulse_low"))
    impulse_high = _safe_float(active_leg_result.get("impulse_high"))
    active_state = str(active_leg_result.get("state") or "")
    impulse_force_invalid = active_state in {"RANGE", "NO_VALID_STRUCTURE"}
    if impulse_low is None or impulse_high is None:
        active_tf = str(active_leg_result.get("active_tf") or "")
        if active_tf:
            tf_state = _tf_state(mtf_result, active_tf)
            direction = str(active_leg_result.get("direction") or "")
            if direction == "BULL":
                impulse_low = _safe_float(((tf_state.get("lastSwingLow") or {}).get("price")))
                impulse_high = _safe_float(((tf_state.get("lastSwingHigh") or {}).get("price")))
            elif direction == "BEAR":
                # Keep low/high order as true price bounds for ratio calculation.
                impulse_low = _safe_float(((tf_state.get("lastSwingLow") or {}).get("price")))
                impulse_high = _safe_float(((tf_state.get("lastSwingHigh") or {}).get("price")))
    active_tf = str(active_leg_result.get("active_tf") or "ACTIVE")
    impulse = _build_fd_block(
        mode="impulse",
        symbol=symbol,
        tf=active_tf,
        low=impulse_low,
        high=impulse_high,
        current_close=current_price,
        is_impulse=True,
        force_invalid=impulse_force_invalid or impulse_low is None or impulse_high is None,
    )

    return {
        "swing": swing,
        "external": swing,  # backward compatibility for older consumers
        "impulse": impulse,
        "confluence": {
            "swing_reaction": bool(swing.get("reaction_zone")),
            "swing_shift": bool(swing.get("shift_crossed")),
            "impulse_reaction": bool(impulse.get("reaction_zone")),
            "impulse_shift": bool(impulse.get("shift_crossed")),
        },
    }
