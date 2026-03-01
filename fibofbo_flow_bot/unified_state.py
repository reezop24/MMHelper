from __future__ import annotations

from copy import deepcopy
from typing import Any

from fd_engine import evaluateFD

def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return bool(value)


def _get_h4_bias(mtf_result: dict[str, Any]) -> str | None:
    mtf_state = _as_dict(mtf_result.get("mtf_state"))
    context = _as_dict(mtf_state.get("context"))
    h4 = _as_dict(context.get("H4"))
    bias = h4.get("bias")
    return str(bias) if bias is not None else None


def _normalize_fd(fd_value: dict[str, Any]) -> dict[str, Any]:
    fd_src = _as_dict(fd_value)
    swing = _as_dict(fd_src.get("swing"))
    if not swing:
        swing = _as_dict(fd_src.get("external"))
    impulse = _as_dict(fd_src.get("impulse"))
    confluence = _as_dict(fd_src.get("confluence"))
    if not confluence:
        confluence = {
            "swing_reaction": bool(swing.get("reaction_zone")),
            "swing_shift": bool(swing.get("shift_crossed")),
            "impulse_reaction": bool(impulse.get("reaction_zone")),
            "impulse_shift": bool(impulse.get("shift_crossed")),
        }
    return {
        "swing": swing,
        "impulse": impulse,
        "confluence": confluence,
        "external": swing,
    }


def buildUnifiedState(
    candle_index: int,
    timestamp: str,
    mtf_result: dict,
    impulse_result: dict,
    active_leg_result: dict,
    retrace_result: dict,
    fd_result: dict | None = None,
) -> dict:
    mtf_src = _as_dict(mtf_result)
    impulse_src = _as_dict(impulse_result)
    active_src = _as_dict(active_leg_result)
    retrace_src = _as_dict(retrace_result)
    fd_src = _normalize_fd(fd_result if fd_result is not None else evaluateFD(mtf_src, active_src))

    score_state = _as_dict(mtf_src.get("score_state"))

    summary = {
        "bias": _get_h4_bias(mtf_src),
        "mtf_score": _safe_int(score_state.get("score"), 0),
        "trade_ready": _safe_bool(score_state.get("trade_ready"), False),
        "active_tf": active_src.get("active_tf"),
        "direction": active_src.get("direction"),
        "leg_state": active_src.get("state"),
        "leg_action": active_src.get("action"),
        "retrace_status": retrace_src.get("status"),
        "retrace_depth": retrace_src.get("depth_type"),
        "ready_for_setup": _safe_bool(retrace_src.get("ready_for_setup"), False),
    }

    return {
        "candle_index": _safe_int(candle_index, 0),
        "timestamp": str(timestamp),
        "summary": summary,
        "mtf": deepcopy(mtf_src),
        "impulse": deepcopy(impulse_src),
        "active": deepcopy(active_src),
        "retrace": deepcopy(retrace_src),
        "fd": deepcopy(fd_src),
    }


def buildCompactSummary(state: dict) -> str:
    src = _as_dict(state)
    summary = _as_dict(src.get("summary"))
    idx = _safe_int(src.get("candle_index"), 0)
    bias = summary.get("bias")
    score = _safe_int(summary.get("mtf_score"), 0)
    active_tf = summary.get("active_tf")
    leg_state = summary.get("leg_state")
    retrace_depth = summary.get("retrace_depth")
    ready = _safe_bool(summary.get("ready_for_setup"), False)

    bias_txt = str(bias) if bias is not None else "None"
    active_tf_txt = str(active_tf) if active_tf is not None else "None"
    leg_state_txt = str(leg_state) if leg_state is not None else "None"
    retrace_depth_txt = str(retrace_depth) if retrace_depth is not None else "None"

    return (
        f"[{idx}] H4={bias_txt} | Score={score} | "
        f"Active={active_tf_txt}/{leg_state_txt} | "
        f"Retrace={retrace_depth_txt} | Ready={ready}"
    )
