#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from active_leg_engine import ActiveLegConfig, evaluateActiveLeg
from dbo import load_candles
from impulse_engine import ImpulseConfig, detectImpulseAll
from mtf_engine import MTFConfig, evaluateMTF
from retrace_engine import RetraceConfig, evaluateRetrace
from swing_engine import detectSwingStructureAll
from unified_state import buildUnifiedState


BASE_DIR = Path(__file__).resolve().parent
PREVIEW_FILE = BASE_DIR / "simulator_preview.html"
VALID_TFS = {"m5", "m15", "m30", "h1", "h4", "d1", "w1", "mn1"}
STATE_TFS = {"W1", "D1", "H4", "H1", "M30", "M15", "M5"}


def _env(name: str, default: str) -> str:
    return (os.getenv(name) or default).strip()


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name, "1" if default else "0").lower()
    return raw in {"1", "true", "yes", "on"}


def _candles_for_tf(db_path: Path, tf: str, limit: int) -> list[dict[str, Any]]:
    rows = load_candles(db_path=db_path, timeframe=tf, limit=limit)
    return [
        {
            "time": row.ts,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
        }
        for row in rows
    ]


def _candles_for_tf_window(db_path: Path, tf: str, start_ts: str, end_ts: str, limit: int) -> list[dict[str, Any]]:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            SELECT ts, open, high, low, close
            FROM candles
            WHERE timeframe = ?
              AND ts >= ?
              AND ts <= ?
            ORDER BY ts ASC
            LIMIT ?
            """,
            (tf, start_ts, end_ts, max(10, int(limit))),
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "time": str(ts),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
        }
        for ts, o, h, l, c in rows
    ]


def _build_mtf_inputs(db_path: Path, limit: int = 320) -> dict[str, list[dict[str, Any]]]:
    tf_map = {
        "W1": "w1",
        "D1": "d1",
        "H4": "h4",
        "H1": "h1",
        "M30": "m30",
        "M15": "m15",
        "M5": "m5",
    }
    out: dict[str, list[dict[str, Any]]] = {}
    for tf, tf_key in tf_map.items():
        out[tf] = _candles_for_tf(db_path, tf_key, limit)
    return out


def _parse_ts(ts: str) -> datetime | None:
    raw = str(ts or "").strip()
    if not raw:
        return None
    s = raw.replace(" ", "T")
    if s.endswith("Z"):
        s = s[:-1]
    # allow datetime-local without seconds
    if len(s) == 16:
        s = f"{s}:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _is_market_closed_myt(ts: str) -> bool:
    dt = _parse_ts(ts)
    if dt is None:
        return False
    myt = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
    wd = myt.weekday()  # Mon=0 ... Sun=6
    mins = myt.hour * 60 + myt.minute
    if wd == 5 and mins >= 360:
        return True
    if wd == 6:
        return True
    if wd == 0 and mins < 420:
        return True
    return False


def _filter_market_closed(tf: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tf_low = str(tf or "").lower()
    # Keep weekly/monthly as-is; filter intraday + daily.
    if tf_low in {"w1", "mn1"}:
        return list(rows)
    return [r for r in rows if not _is_market_closed_myt(str(r.get("time") or ""))]


def _filter_until(candles_by_tf: dict[str, list[dict[str, Any]]], cutoff_ts: str | None) -> dict[str, list[dict[str, Any]]]:
    if not cutoff_ts:
        return {k: list(v) for k, v in candles_by_tf.items()}
    cutoff = _parse_ts(cutoff_ts)
    if cutoff is None:
        return {k: list(v) for k, v in candles_by_tf.items()}
    out: dict[str, list[dict[str, Any]]] = {}
    for tf, rows in candles_by_tf.items():
        clipped: list[dict[str, Any]] = []
        for r in rows:
            ts = _parse_ts(str(r.get("time") or ""))
            if ts is None:
                continue
            if ts <= cutoff:
                clipped.append(r)
        out[tf] = _filter_market_closed(tf, clipped)
    return out


def _build_engine_state_from_inputs(candles_by_tf: dict[str, list[dict[str, Any]]], anchor_tf: str = "M5") -> dict[str, Any]:
    mtf_cfg = MTFConfig(
        score_min=max(1, min(_env_int("FIBOFBO_FLOW_MTF_SCORE_MIN", 7), 10)),
        near_session_end_minutes=max(1, _env_int("FIBOFBO_FLOW_MTF_NEAR_END_MIN", 45)),
        daily_conflict_mode=_env("FIBOFBO_FLOW_DAILY_CONFLICT_MODE", "soft").lower(),
        weekly_conflict_mode=_env("FIBOFBO_FLOW_WEEKLY_CONFLICT_MODE", "soft").lower(),
        swing_lookback=max(1, _env_int("FIBOFBO_FLOW_MTF_SWING_LOOKBACK", 2)),
        trend_swings_n=max(3, _env_int("FIBOFBO_FLOW_MTF_TREND_SWINGS_N", 4)),
        anomaly_filter_enabled=_env_bool("FIBOFBO_FLOW_ANOMALY_FILTER_ENABLED", True),
        anomaly_range_multiplier=_env_float("FIBOFBO_FLOW_ANOMALY_RANGE_MULTIPLIER", 4.0),
        anomaly_wick_multiplier=_env_float("FIBOFBO_FLOW_ANOMALY_WICK_MULTIPLIER", 2.0),
        anomaly_micro_range_ratio=_env_float("FIBOFBO_FLOW_ANOMALY_MICRO_RANGE_RATIO", 0.25),
    )
    impulse_cfg = ImpulseConfig(
        swing_lookback=max(1, _env_int("FIBOFBO_FLOW_IMPULSE_SWING_LOOKBACK", 2)),
        anomaly_filter_enabled=_env_bool("FIBOFBO_FLOW_ANOMALY_FILTER_ENABLED", True),
        anomaly_range_multiplier=_env_float("FIBOFBO_FLOW_ANOMALY_RANGE_MULTIPLIER", 4.0),
        anomaly_wick_multiplier=_env_float("FIBOFBO_FLOW_ANOMALY_WICK_MULTIPLIER", 2.0),
        anomaly_micro_range_ratio=_env_float("FIBOFBO_FLOW_ANOMALY_MICRO_RANGE_RATIO", 0.25),
    )
    active_cfg = ActiveLegConfig(
        h1_overextension_mult=_env_float("FIBOFBO_FLOW_ACTIVELEG_H1_OVEREXT", 1.2),
        m30_overextension_mult=_env_float("FIBOFBO_FLOW_ACTIVELEG_M30_OVEREXT", 1.5),
    )
    retrace_cfg = RetraceConfig(
        enable_sweep=_env_bool("FIBOFBO_FLOW_RETRACE_ENABLE_SWEEP", True),
        sweep_ready_direct=_env_bool("FIBOFBO_FLOW_RETRACE_SWEEP_READY_DIRECT", True),
        sweep_require_micro_confirm=_env_bool("FIBOFBO_FLOW_RETRACE_SWEEP_REQUIRE_MICRO_CONFIRM", True),
        sweep_max_reclaim_candles=max(1, _env_int("FIBOFBO_FLOW_RETRACE_SWEEP_MAX_RECLAIM_CANDLES", 3)),
        sweep_trigger_ratio=_env_float("FIBOFBO_FLOW_RETRACE_SWEEP_TRIGGER_RATIO", 0.9),
        anomaly_filter_enabled=_env_bool("FIBOFBO_FLOW_ANOMALY_FILTER_ENABLED", True),
        anomaly_range_multiplier=_env_float("FIBOFBO_FLOW_ANOMALY_RANGE_MULTIPLIER", 4.0),
        anomaly_wick_multiplier=_env_float("FIBOFBO_FLOW_ANOMALY_WICK_MULTIPLIER", 2.0),
        anomaly_micro_range_ratio=_env_float("FIBOFBO_FLOW_ANOMALY_MICRO_RANGE_RATIO", 0.25),
    )

    mtf_result = evaluateMTF(
        symbol="XAUUSD",
        candlesByTF=candles_by_tf,
        nowTimestamp=datetime.now(timezone.utc),
        config=mtf_cfg,
    )
    impulse_result = detectImpulseAll(
        {
            "H4": candles_by_tf["H4"],
            "H1": candles_by_tf["H1"],
            "M30": candles_by_tf["M30"],
            "M15": candles_by_tf["M15"],
        },
        impulse_cfg,
    )
    active_leg_result = evaluateActiveLeg(mtf_result, impulse_result, active_cfg)
    retrace_result = evaluateRetrace(
        active_leg_result=active_leg_result,
        impulse_result=impulse_result,
        candlesByTF={
            "H4": candles_by_tf["H4"],
            "H1": candles_by_tf["H1"],
            "M30": candles_by_tf["M30"],
            "M15": candles_by_tf["M15"],
            "M5": candles_by_tf["M5"],
        },
        config=retrace_cfg,
    )
    swing_result = detectSwingStructureAll(
        {
            "W1": candles_by_tf["W1"],
            "D1": candles_by_tf["D1"],
            "H4": candles_by_tf["H4"],
        }
    )

    anchor = anchor_tf.upper()
    if anchor not in STATE_TFS:
        anchor = "M5"
    anchor_rows = candles_by_tf.get(anchor) or []
    candle_index = len(anchor_rows) - 1
    timestamp = str(anchor_rows[-1].get("time")) if anchor_rows else datetime.now(timezone.utc).isoformat()
    unified = buildUnifiedState(
        candle_index=candle_index,
        timestamp=timestamp,
        mtf_result=mtf_result,
        impulse_result=impulse_result,
        active_leg_result=active_leg_result,
        retrace_result=retrace_result,
    )
    return {
        "symbol": "XAUUSD",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mtf": mtf_result,
        "impulse": impulse_result,
        "active": active_leg_result,
        "retrace": retrace_result,
        "swing": swing_result,
        "unified": unified,
    }


def _build_engine_state(db_path: Path, cutoff_ts: str | None = None, anchor_tf: str = "M5") -> dict[str, Any]:
    candles_by_tf = _build_mtf_inputs(db_path, limit=320)
    candles_by_tf = {tf: _filter_market_closed(tf, rows) for tf, rows in candles_by_tf.items()}
    candles_by_tf = _filter_until(candles_by_tf, cutoff_ts)
    return _build_engine_state_from_inputs(candles_by_tf, anchor_tf=anchor_tf)


class SimulatorHandler(BaseHTTPRequestHandler):
    server_version = "FiboFboFlowSimulator/1.0"

    def _json(self, payload: dict[str, Any], code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str, code: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        db_path = Path(_env("FIBOFBO_FLOW_CANDLES_DB", "/root/mmhelper/db/twelve_data_bot/candles.db")).resolve()

        if path in {"/", "/simulator", "/preview"}:
            if PREVIEW_FILE.exists():
                self._html(PREVIEW_FILE.read_text(encoding="utf-8"))
                return
            self._html("<h1>simulator_preview.html not found</h1>", code=404)
            return

        if path == "/api/health":
            self._json({"ok": True, "service": "fibofbo-flow-simulator", "db": str(db_path)})
            return

        if path == "/api/candles":
            tf = str((query.get("tf") or ["h1"])[0]).lower()
            if tf not in VALID_TFS:
                self._json({"ok": False, "error": f"invalid tf={tf}"}, code=400)
                return
            limit = max(10, min(_env_int("SIM_PREVIEW_LIMIT", 400), 1500))
            try:
                req_limit = int((query.get("limit") or [str(limit)])[0])
                limit = max(10, min(req_limit, 1500))
            except ValueError:
                pass
            start_ts = str((query.get("start") or [""])[0]).strip()
            end_ts = str((query.get("end") or [""])[0]).strip()
            if start_ts and end_ts:
                candles = _candles_for_tf_window(db_path=db_path, tf=tf, start_ts=start_ts, end_ts=end_ts, limit=limit)
            else:
                candles = _candles_for_tf(db_path=db_path, tf=tf, limit=limit)
            candles = _filter_market_closed(tf, candles)
            self._json(
                {
                    "ok": True,
                    "symbol": "XAUUSD",
                    "timeframe": tf,
                    "count": len(candles),
                    "candles": candles,
                    "window": {"start": start_ts or None, "end": end_ts or None},
                }
            )
            return

        if path == "/api/state":
            try:
                anchor_tf = str((query.get("anchor_tf") or ["m5"])[0]).upper()
                payload = _build_engine_state(db_path, cutoff_ts=None, anchor_tf=anchor_tf)
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, code=500)
                return
            payload["ok"] = True
            self._json(payload)
            return

        if path == "/api/state_at":
            ts = str((query.get("ts") or [""])[0]).strip()
            anchor_tf = str((query.get("anchor_tf") or ["m5"])[0]).upper()
            if not ts:
                self._json({"ok": False, "error": "missing ts"}, code=400)
                return
            try:
                payload = _build_engine_state(db_path, cutoff_ts=ts, anchor_tf=anchor_tf)
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, code=500)
                return
            payload["ok"] = True
            payload["replay_ts"] = ts
            payload["anchor_tf"] = anchor_tf
            self._json(payload)
            return

        self._json({"ok": False, "error": "not found"}, code=404)


def main() -> int:
    host = _env("SIM_PREVIEW_HOST", "0.0.0.0")
    port = _env_int("SIM_PREVIEW_PORT", 8766)
    server = ThreadingHTTPServer((host, port), SimulatorHandler)
    print(f"Simulator preview running on http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
