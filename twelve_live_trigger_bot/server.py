#!/usr/bin/env python3
"""Twelve Data live trigger bot via WebSocket.

Separate bot for real-time zone/point trigger monitoring.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from websocket import WebSocketApp  # type: ignore[import-untyped]


LOGGER = logging.getLogger("twelve_live_trigger_bot")


@dataclass
class Config:
    api_key: str
    symbols: list[str]
    reconnect_sec: int
    request_timeout_sec: int
    log_level: str
    state_dir: Path
    db_path: Path
    zones_file: Path
    events_file: Path
    public_tick_file: Path
    live_candles_db: Path
    api_host: str
    api_port: int
    cooldown_sec: int


def load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_symbols(raw: str) -> list[str]:
    out = [p.strip().upper() for p in raw.split(",") if p.strip()]
    return out or ["XAU/USD"]


def load_config() -> Config:
    api_key = get_env("TWELVE_API_KEY")
    if not api_key:
        raise ValueError("TWELVE_API_KEY is required")

    state_dir = Path(get_env("LIVE_STATE_DIR", "/root/mmhelper/db/twelve_live_trigger_bot")).resolve()
    db_path = Path(get_env("LIVE_DB_PATH", str(state_dir / "live_ticks.db"))).resolve()
    zones_file = Path(get_env("LIVE_ZONES_FILE", str(state_dir / "zones.json"))).resolve()
    events_file = Path(get_env("LIVE_EVENTS_FILE", str(state_dir / "trigger_events.jsonl"))).resolve()
    public_tick_file = Path(get_env("LIVE_PUBLIC_TICK_FILE", "/root/mmhelper/miniapp/live-tick.json")).resolve()
    live_candles_db = Path(get_env("LIVE_CANDLES_DB", "/root/mmhelper/db/twelve_data_bot/candles.db")).resolve()

    return Config(
        api_key=api_key,
        symbols=parse_symbols(get_env("LIVE_SYMBOLS", "XAU/USD")),
        reconnect_sec=int(get_env("LIVE_RECONNECT_SEC", "5")),
        request_timeout_sec=int(get_env("LIVE_REQUEST_TIMEOUT_SEC", "15")),
        log_level=get_env("LOG_LEVEL", "INFO"),
        state_dir=state_dir,
        db_path=db_path,
        zones_file=zones_file,
        events_file=events_file,
        public_tick_file=public_tick_file,
        live_candles_db=live_candles_db,
        api_host=get_env("LIVE_API_HOST", "127.0.0.1"),
        api_port=int(get_env("LIVE_API_PORT", "8091")),
        cooldown_sec=int(get_env("LIVE_TRIGGER_COOLDOWN_SEC", "60")),
    )


class Storage:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cfg.state_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cfg.events_file.parent.mkdir(parents=True, exist_ok=True)
        self.cfg.public_tick_file.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.cfg.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS live_ticks (
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    raw TEXT NOT NULL,
                    PRIMARY KEY (ts, symbol)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trigger_state (
                    trigger_id TEXT PRIMARY KEY,
                    last_fired_at TEXT NOT NULL
                )
                """
            )

    def insert_tick(self, ts: str, symbol: str, price: float, raw: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO live_ticks (ts, symbol, price, raw) VALUES (?, ?, ?, ?)",
                (ts, symbol, price, json.dumps(raw, ensure_ascii=True)),
            )
            # Keep database small; newest 10k ticks only.
            conn.execute(
                """
                DELETE FROM live_ticks
                WHERE rowid NOT IN (
                    SELECT rowid FROM live_ticks ORDER BY ts DESC LIMIT 10000
                )
                """
            )

    def get_last_fired(self, trigger_id: str) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_fired_at FROM trigger_state WHERE trigger_id = ?",
                (trigger_id,),
            ).fetchone()
        if not row:
            return None
        raw = str(row["last_fired_at"])
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def set_last_fired(self, trigger_id: str, fired_at: datetime) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO trigger_state (trigger_id, last_fired_at) VALUES (?, ?)",
                (trigger_id, fired_at.isoformat()),
            )

    def append_event(self, payload: dict[str, Any]) -> None:
        with self.cfg.events_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True))
            f.write("\n")

    def write_public_latest_tick(self, payload: dict[str, Any]) -> None:
        tmp_path = self.cfg.public_tick_file.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        tmp_path.replace(self.cfg.public_tick_file)


class ZoneEngine:
    def __init__(self, cfg: Config, store: Storage):
        self.cfg = cfg
        self.store = store

    def load_zones(self) -> list[dict[str, Any]]:
        if not self.cfg.zones_file.exists():
            sample = {
                "zones": [
                    {
                        "id": "xau_above_5100",
                        "symbol": "XAU/USD",
                        "kind": "above",
                        "value": 5100.0,
                        "enabled": False,
                    }
                ]
            }
            self.cfg.zones_file.write_text(json.dumps(sample, ensure_ascii=True, indent=2), encoding="utf-8")
            return sample["zones"]

        try:
            loaded = json.loads(self.cfg.zones_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Invalid zones JSON. Ignoring.")
            return []

        if isinstance(loaded, dict) and isinstance(loaded.get("zones"), list):
            return [z for z in loaded["zones"] if isinstance(z, dict)]
        if isinstance(loaded, list):
            return [z for z in loaded if isinstance(z, dict)]
        return []

    def _match_zone(self, zone: dict[str, Any], symbol: str, price: float) -> bool:
        if not bool(zone.get("enabled", True)):
            return False
        if str(zone.get("symbol") or "").upper() != symbol.upper():
            return False

        kind = str(zone.get("kind") or "").lower()
        if kind == "above":
            return price >= float(zone.get("value"))
        if kind == "below":
            return price <= float(zone.get("value"))
        if kind == "between":
            lo = float(zone.get("value_low"))
            hi = float(zone.get("value_high"))
            return lo <= price <= hi
        return False

    def evaluate(self, symbol: str, price: float, raw: dict[str, Any]) -> None:
        now = datetime.now(UTC)
        zones = self.load_zones()

        for zone in zones:
            zid = str(zone.get("id") or "").strip()
            if not zid:
                continue
            if not self._match_zone(zone, symbol, price):
                continue

            last_fired = self.store.get_last_fired(zid)
            if last_fired is not None:
                elapsed = (now - last_fired).total_seconds()
                if elapsed < self.cfg.cooldown_sec:
                    continue

            event = {
                "ts": utc_now_iso(),
                "type": "zone_trigger",
                "zone_id": zid,
                "symbol": symbol,
                "price": price,
                "zone": zone,
                "raw": raw,
            }
            self.store.append_event(event)
            self.store.set_last_fired(zid, now)
            LOGGER.info("Zone triggered id=%s symbol=%s price=%.5f", zid, symbol, price)


def extract_price_symbol(payload: dict[str, Any]) -> tuple[str | None, float | None]:
    symbol = None
    price = None

    if "symbol" in payload:
        symbol = str(payload.get("symbol") or "").upper() or None

    # Common fields across different streams/providers.
    for key in ("price", "close", "last", "bid", "ask"):
        raw = payload.get(key)
        try:
            if raw is not None:
                price = float(raw)
                break
        except (TypeError, ValueError):
            continue

    # Handle nested payloads like {"event":"price","data":{...}}
    data = payload.get("data")
    if isinstance(data, dict):
        sym2, px2 = extract_price_symbol(data)
        if symbol is None:
            symbol = sym2
        if price is None:
            price = px2

    return symbol, price


def load_tf_candles(db_path: Path, timeframe: str, limit: int) -> list[dict[str, Any]]:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            SELECT ts, open, high, low, close
            FROM candles
            WHERE timeframe = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (timeframe, limit),
        ).fetchall()
    finally:
        con.close()

    rows.reverse()
    out: list[dict[str, Any]] = []
    for idx, (ts, o, h, l, c) in enumerate(rows):
        out.append(
            {
                "idx": idx,
                "ts": str(ts),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
        )
    return out


def find_pivots(candles: list[dict[str, Any]], swing_window: int = 2) -> list[dict[str, Any]]:
    if len(candles) < (swing_window * 2 + 1):
        return []

    pivots: list[dict[str, Any]] = []
    for i in range(swing_window, len(candles) - swing_window):
        center = candles[i]
        chunk = candles[i - swing_window : i + swing_window + 1]
        highs = [x["high"] for x in chunk]
        lows = [x["low"] for x in chunk]

        if center["high"] == max(highs):
            pivots.append({"idx": i, "ts": center["ts"], "kind": "H", "price": center["high"]})
        if center["low"] == min(lows):
            pivots.append({"idx": i, "ts": center["ts"], "kind": "L", "price": center["low"]})

    if not pivots:
        return []

    pivots.sort(key=lambda x: int(x["idx"]))
    compressed = [pivots[0]]
    for p in pivots[1:]:
        last = compressed[-1]
        if p["kind"] != last["kind"]:
            compressed.append(p)
            continue
        if p["kind"] == "H" and float(p["price"]) > float(last["price"]):
            compressed[-1] = p
        if p["kind"] == "L" and float(p["price"]) < float(last["price"]):
            compressed[-1] = p
    return compressed


def detect_dbo(candles: list[dict[str, Any]], pivots: list[dict[str, Any]], tol_pct: float = 0.003) -> dict[str, Any]:
    if not candles or len(pivots) < 5:
        return {"status": "NO_SETUP"}

    latest_close = float(candles[-1]["close"])
    best: dict[str, Any] | None = None
    for i in range(4, len(pivots)):
        seq = pivots[i - 4 : i + 1]
        kinds = "".join(str(x["kind"]) for x in seq)

        if kinds == "LHLHL":
            ls, _, head, right_high, rs = seq
            if not (float(head["price"]) < float(ls["price"]) and float(head["price"]) < float(rs["price"])):
                continue
            near_equal = abs(float(rs["price"]) - float(ls["price"])) / max(float(ls["price"]), 1e-9) <= tol_pct
            qm_shape = float(rs["price"]) > float(ls["price"]) * (1 + tol_pct)
            if not (near_equal or qm_shape):
                continue
            trigger_level = float(right_high["price"])
            triggered = latest_close > trigger_level
            best = {
                "status": "TRIGGERED" if triggered else "ARMED",
                "side": "BUY",
                "pattern": "INV_HNS" if near_equal else "QM_BULL",
                "trigger_level": trigger_level,
                "latest_close": latest_close,
                "points": {"left_shoulder": ls, "head": head, "right_shoulder": rs},
            }

        if kinds == "HLHLH":
            ls, _, head, right_low, rs = seq
            if not (float(head["price"]) > float(ls["price"]) and float(head["price"]) > float(rs["price"])):
                continue
            near_equal = abs(float(rs["price"]) - float(ls["price"])) / max(float(ls["price"]), 1e-9) <= tol_pct
            qm_shape = float(rs["price"]) < float(ls["price"]) * (1 - tol_pct)
            if not (near_equal or qm_shape):
                continue
            trigger_level = float(right_low["price"])
            triggered = latest_close < trigger_level
            best = {
                "status": "TRIGGERED" if triggered else "ARMED",
                "side": "SELL",
                "pattern": "HNS" if near_equal else "QM_BEAR",
                "trigger_level": trigger_level,
                "latest_close": latest_close,
                "points": {"left_shoulder": ls, "head": head, "right_shoulder": rs},
            }

    return best or {"status": "NO_SETUP"}


class LiveBot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = Storage(cfg)
        self.zone_engine = ZoneEngine(cfg, self.store)
        self.ws: WebSocketApp | None = None
        self._api_server: ThreadingHTTPServer | None = None

    def _ws_url(self) -> str:
        return f"wss://ws.twelvedata.com/v1/quotes/price?apikey={self.cfg.api_key}"

    def _subscribe_payload(self) -> dict[str, Any]:
        return {
            "action": "subscribe",
            "params": {
                "symbols": ",".join(self.cfg.symbols),
            },
        }

    def on_open(self, ws: WebSocketApp) -> None:  # noqa: ARG002
        payload = self._subscribe_payload()
        self.ws.send(json.dumps(payload, ensure_ascii=True))
        LOGGER.info("WebSocket connected; subscribed symbols=%s", ",".join(self.cfg.symbols))

    def on_message(self, ws: WebSocketApp, message: str) -> None:  # noqa: ARG002
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            LOGGER.debug("Ignoring non-JSON message")
            return

        if not isinstance(payload, dict):
            return

        symbol, price = extract_price_symbol(payload)
        if not symbol or price is None:
            # Keep debug low-noise; only logs in debug.
            LOGGER.debug("Non-price message: %s", payload)
            return

        ts = utc_now_iso()
        self.store.insert_tick(ts=ts, symbol=symbol, price=price, raw=payload)
        self.store.write_public_latest_tick(
            {
                "ts": ts,
                "symbol": symbol,
                "price": price,
                "source": "twelve_live_trigger_bot",
            }
        )
        self.zone_engine.evaluate(symbol=symbol, price=price, raw=payload)
        LOGGER.info("Tick symbol=%s price=%.5f", symbol, price)

    def on_error(self, ws: WebSocketApp, error: Any) -> None:  # noqa: ARG002
        LOGGER.warning("WebSocket error: %s", error)

    def on_close(self, ws: WebSocketApp, status_code: int, msg: str) -> None:  # noqa: ARG002
        LOGGER.warning("WebSocket closed code=%s msg=%s", status_code, msg)

    def _start_api_server(self) -> None:
        cfg = self.cfg
        store = self.store

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
                self.send_response(int(status))
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path

                if path == "/healthz":
                    self._send_json(HTTPStatus.OK, {"ok": True})
                    return

                if path == "/live-tick.json":
                    try:
                        payload = json.loads(store.cfg.public_tick_file.read_text(encoding="utf-8"))
                        if not isinstance(payload, dict):
                            raise ValueError("invalid tick payload")
                        self._send_json(HTTPStatus.OK, payload)
                        return
                    except Exception as exc:  # noqa: BLE001
                        self._send_json(
                            HTTPStatus.SERVICE_UNAVAILABLE,
                            {"ok": False, "error": "tick_unavailable", "detail": str(exc)},
                        )
                        return

                if path == "/dbo-preview":
                    if not cfg.live_candles_db.exists():
                        self._send_json(
                            HTTPStatus.SERVICE_UNAVAILABLE,
                            {"ok": False, "error": "candles_db_missing"},
                        )
                        return
                    query = parse_qs(parsed.query)
                    tf = str((query.get("tf") or ["m5"])[0]).strip().lower()
                    if tf not in {"m5", "m15", "m30", "h1", "h4"}:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_tf"})
                        return
                    try:
                        limit = int((query.get("limit") or ["400"])[0])
                    except ValueError:
                        limit = 400
                    limit = max(80, min(limit, 1200))
                    candles = load_tf_candles(cfg.live_candles_db, tf, limit)
                    pivots = find_pivots(candles, swing_window=2)
                    setup = detect_dbo(candles, pivots)
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "ok": True,
                            "timeframe": tf,
                            "candles": candles,
                            "setup": setup,
                        },
                    )
                    return

                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                LOGGER.debug("api %s - %s", self.address_string(), format % args)

        server = ThreadingHTTPServer((cfg.api_host, cfg.api_port), Handler)
        self._api_server = server
        thread = threading.Thread(target=server.serve_forever, name="live_api_server", daemon=True)
        thread.start()
        LOGGER.info("HTTP API started at http://%s:%s", cfg.api_host, cfg.api_port)

    def run_forever(self) -> None:
        self._start_api_server()
        while True:
            try:
                self.ws = WebSocketApp(
                    self._ws_url(),
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Live bot loop failed: %s", exc)

            LOGGER.info("Reconnect in %ss", self.cfg.reconnect_sec)
            time.sleep(self.cfg.reconnect_sec)


def main() -> None:
    load_local_env()
    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    LOGGER.info(
        "Starting live trigger bot symbols=%s state_dir=%s db=%s",
        ",".join(cfg.symbols),
        cfg.state_dir,
        cfg.db_path,
    )
    bot = LiveBot(cfg)
    bot.run_forever()


if __name__ == "__main__":
    main()
