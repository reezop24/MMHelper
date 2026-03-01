#!/usr/bin/env python3
"""Twelve Data auto-analysis bot for XAUUSD."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


LOGGER = logging.getLogger("twelve_auto_analysis_bot")

INTERVAL_MINUTES = {
    "m5": 5,
    "m15": 15,
    "m30": 30,
    "h1": 60,
    "h4": 240,
}

RETENTION_WINDOWS = {
    "m5": timedelta(days=30),
    "m15": timedelta(days=30),
    "m30": timedelta(days=90),
    "h1": timedelta(days=90),
    "h4": timedelta(days=365),
    "d1": timedelta(days=730),
    "w1": timedelta(days=1825),
    "mn1": timedelta(days=3650),
}

@dataclass
class Config:
    api_key: str
    symbol: str
    poll_interval_sec: int
    request_timeout_sec: int
    max_retries: int
    log_level: str
    state_dir: Path
    db_path: Path
    bootstrap_m5_points: int
    bootstrap_h1_points: int
    bootstrap_d1_points: int
    bootstrap_w1_points: int
    bootstrap_mn1_points: int
    incremental_m5_points: int
    incremental_h1_points: int
    direct_points: int
    analysis_timeframe: str
    run_once: bool
    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_send_hold: bool
    telegram_min_interval_sec: int
    direct_fetch_d1_sec: int
    direct_fetch_w1_sec: int
    direct_fetch_mn1_sec: int
    direct_fetch_daily_time_myt: str
    m5_session_start_myt: str
    m5_fetch_delay_sec: int
    h1_session_start_myt: str
    h1_fetch_delay_sec: int
    display_timezone: str
    h4_session_mode: str


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


def load_config() -> Config:
    api_key = get_env("TWELVE_API_KEY")
    if not api_key:
        raise ValueError("TWELVE_API_KEY is required")

    state_dir = Path(get_env("BOT_STATE_DIR", "/root/mmhelper/db/twelve_data_bot")).resolve()
    db_path = Path(get_env("BOT_DB_PATH", str(state_dir / "candles.db"))).resolve()
    return Config(
        api_key=api_key,
        symbol=get_env("TD_SYMBOL", "XAU/USD"),
        poll_interval_sec=int(get_env("POLL_INTERVAL_SEC", "120")),
        request_timeout_sec=int(get_env("REQUEST_TIMEOUT_SEC", "15")),
        max_retries=int(get_env("MAX_RETRIES", "3")),
        log_level=get_env("LOG_LEVEL", "INFO"),
        state_dir=state_dir,
        db_path=db_path,
        bootstrap_m5_points=int(get_env("BOOTSTRAP_M5_POINTS", "1500")),
        bootstrap_h1_points=int(get_env("BOOTSTRAP_H1_POINTS", "690")),
        bootstrap_d1_points=int(get_env("BOOTSTRAP_D1_POINTS", "365")),
        bootstrap_w1_points=int(get_env("BOOTSTRAP_W1_POINTS", "104")),
        bootstrap_mn1_points=int(get_env("BOOTSTRAP_MN1_POINTS", "24")),
        incremental_m5_points=int(get_env("INCREMENTAL_M5_POINTS", "250")),
        incremental_h1_points=int(get_env("INCREMENTAL_H1_POINTS", "48")),
        direct_points=int(get_env("DIRECT_HIGHER_TF_POINTS", "220")),
        analysis_timeframe=get_env("ANALYSIS_TIMEFRAME", "h1").lower(),
        run_once=get_env("RUN_ONCE", "0") == "1",
        telegram_enabled=get_env("TELEGRAM_ENABLED", "0") == "1",
        telegram_bot_token=get_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=get_env("TELEGRAM_CHAT_ID"),
        telegram_send_hold=get_env("TELEGRAM_SEND_HOLD", "0") == "1",
        telegram_min_interval_sec=int(get_env("TELEGRAM_MIN_INTERVAL_SEC", "300")),
        direct_fetch_d1_sec=int(get_env("DIRECT_FETCH_D1_SEC", "86400")),
        direct_fetch_w1_sec=int(get_env("DIRECT_FETCH_W1_SEC", "604800")),
        direct_fetch_mn1_sec=int(get_env("DIRECT_FETCH_MN1_SEC", "2592000")),
        direct_fetch_daily_time_myt=get_env("DIRECT_FETCH_DAILY_TIME_MYT", "06:00:15"),
        m5_session_start_myt=get_env("M5_SESSION_START_MYT", "07:00"),
        m5_fetch_delay_sec=int(get_env("M5_FETCH_DELAY_SEC", "5")),
        h1_session_start_myt=get_env("H1_SESSION_START_MYT", "07:00"),
        h1_fetch_delay_sec=int(get_env("H1_FETCH_DELAY_SEC", "15")),
        display_timezone=get_env("DISPLAY_TIMEZONE", "Asia/Kuala_Lumpur"),
        h4_session_mode=get_env("H4_SESSION_MODE", "auto").lower(),
    )


def parse_iso_utc(raw: str) -> datetime:
    # Twelve Data may return either full timestamp or date-only string
    # depending on interval (e.g. 5min vs 1day/1week/1month).
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {raw}")


def to_iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def to_iso_local(dt: datetime, tz_name: str) -> str:
    try:
        local_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        local_tz = ZoneInfo("UTC")
    return dt.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S")


def _first_sunday(year: int, month: int) -> date:
    d = date(year, month, 1)
    shift = (6 - d.weekday()) % 7  # Monday=0 .. Sunday=6
    return d + timedelta(days=shift)


def _second_sunday(year: int, month: int) -> date:
    return _first_sunday(year, month) + timedelta(days=7)


def _is_dst_myt_date(d: date) -> bool:
    # DST season: first Sunday November until second Sunday March.
    if d.month >= 11:
        return d >= _first_sunday(d.year, 11)
    if d.month <= 3:
        return d < _second_sunday(d.year, 3)
    return False


def _is_dst_myt_datetime(ts_local: datetime) -> bool:
    return _is_dst_myt_date(ts_local.date())


def _mode_for_local(ts_local: datetime, mode: str) -> str:
    raw = str(mode or "").strip().lower()
    if raw in {"standard", "dst"}:
        return raw
    return "dst" if _is_dst_myt_datetime(ts_local) else "standard"


def _market_open_hour_myt(ts_local: datetime) -> int:
    # DST -> 07:00 open, non-DST -> 06:00 open.
    return 7 if _is_dst_myt_datetime(ts_local) else 6


def _market_close_hour_myt(ts_local: datetime) -> int:
    # DST -> 06:00 close, non-DST -> 05:00 close.
    return 6 if _is_dst_myt_datetime(ts_local) else 5


def _daily_session_start_hour_for_date(d: date, mode: str) -> int:
    raw = str(mode or "").strip().lower()
    if raw == "dst":
        return 6
    if raw == "standard":
        return 7
    # auto
    return 7 if _is_dst_myt_date(d) else 6


def is_market_closed_myt(ts_utc: datetime) -> bool:
    myt = ts_utc.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    wd = myt.weekday()  # Mon=0 ... Sun=6
    mins = myt.hour * 60 + myt.minute
    sat_close_mins = _market_close_hour_myt(myt) * 60
    mon_open_mins = _market_open_hour_myt(myt) * 60
    if wd == 5 and mins >= sat_close_mins:
        return True
    if wd == 6:  # Sun
        return True
    if wd == 0 and mins < mon_open_mins:
        return True
    return False


def filter_open_market_rows(timeframe: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tf = str(timeframe or "").strip().lower()
    if tf in {"w1", "mn1"}:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        raw_ts = row.get("ts")
        if not isinstance(raw_ts, str):
            continue
        try:
            ts = parse_iso_utc(raw_ts)
        except ValueError:
            continue
        if is_market_closed_myt(ts):
            continue
        out.append(row)
    return out


def parse_hhmm(value: str, fallback_hour: int = 6, fallback_minute: int = 30) -> tuple[int, int]:
    try:
        raw = value.strip()
        hh, mm = raw.split(":", 1)
        hour = max(0, min(23, int(hh)))
        minute = max(0, min(59, int(mm)))
        return hour, minute
    except (ValueError, AttributeError):
        return fallback_hour, fallback_minute


def parse_hhmmss(
    value: str,
    fallback_hour: int = 6,
    fallback_minute: int = 0,
    fallback_second: int = 15,
) -> tuple[int, int, int]:
    try:
        raw = value.strip()
        parts = raw.split(":")
        if len(parts) == 2:
            hh, mm = parts
            ss = "0"
        elif len(parts) == 3:
            hh, mm, ss = parts
        else:
            return fallback_hour, fallback_minute, fallback_second
        hour = max(0, min(23, int(hh)))
        minute = max(0, min(59, int(mm)))
        second = max(0, min(59, int(ss)))
        return hour, minute, second
    except (ValueError, AttributeError):
        return fallback_hour, fallback_minute, fallback_second


def session_date_for_hour(ts_local: datetime, start_hour: int) -> datetime.date:
    if ts_local.hour < start_hour:
        return (ts_local - timedelta(days=1)).date()
    return ts_local.date()


def build_local_datetime(base_date: datetime.date, hour: int, minute: int, second: int, tz: ZoneInfo) -> datetime:
    return datetime(base_date.year, base_date.month, base_date.day, hour, minute, second, tzinfo=tz)


def current_m5_slot_time(ts_local: datetime, cfg: Config, tz: ZoneInfo) -> datetime | None:
    _, start_minute = parse_hhmm(cfg.m5_session_start_myt, 7, 0)
    start_hour = _market_open_hour_myt(ts_local)
    base_date = session_date_for_hour(ts_local, start_hour)
    session_start = build_local_datetime(base_date, start_hour, start_minute, 0, tz)
    first_fetch = session_start + timedelta(minutes=5, seconds=cfg.m5_fetch_delay_sec)
    if ts_local < first_fetch:
        return None
    elapsed_sec = int((ts_local - first_fetch).total_seconds())
    slot_count = elapsed_sec // 300
    return first_fetch + timedelta(minutes=slot_count * 5)


def next_m5_slot_time(ts_local: datetime, cfg: Config, tz: ZoneInfo) -> datetime:
    _, start_minute = parse_hhmm(cfg.m5_session_start_myt, 7, 0)
    start_hour = _market_open_hour_myt(ts_local)
    base_date = session_date_for_hour(ts_local, start_hour)
    session_start = build_local_datetime(base_date, start_hour, start_minute, 0, tz)
    first_fetch = session_start + timedelta(minutes=5, seconds=cfg.m5_fetch_delay_sec)
    if ts_local < first_fetch:
        return first_fetch
    elapsed_sec = int((ts_local - first_fetch).total_seconds())
    slot_count = (elapsed_sec // 300) + 1
    return first_fetch + timedelta(minutes=slot_count * 5)


def h1_slot_times_for_session(base_date: datetime.date, cfg: Config, tz: ZoneInfo) -> list[datetime]:
    _, start_minute = parse_hhmm(cfg.h1_session_start_myt, 7, 0)
    start_hour = 7 if _is_dst_myt_date(base_date) else 6
    base = datetime(base_date.year, base_date.month, base_date.day, start_hour, start_minute, 0, tzinfo=tz)
    # H1 closes 08:00..06:00 next day (23 closes from 07:00 session start).
    close_offsets = range(1, 24)
    return [base + timedelta(hours=offset, seconds=cfg.h1_fetch_delay_sec) for offset in close_offsets]


def current_h1_slot_time(ts_local: datetime, cfg: Config, tz: ZoneInfo) -> datetime | None:
    start_hour = _market_open_hour_myt(ts_local)
    base_date = session_date_for_hour(ts_local, start_hour)
    slots = h1_slot_times_for_session(base_date, cfg, tz)
    eligible = [slot for slot in slots if slot <= ts_local]
    if eligible:
        return eligible[-1]
    prev_slots = h1_slot_times_for_session(base_date - timedelta(days=1), cfg, tz)
    prev_eligible = [slot for slot in prev_slots if slot <= ts_local]
    return prev_eligible[-1] if prev_eligible else None


def next_h1_slot_time(ts_local: datetime, cfg: Config, tz: ZoneInfo) -> datetime:
    start_hour = _market_open_hour_myt(ts_local)
    base_date = session_date_for_hour(ts_local, start_hour)
    slots = h1_slot_times_for_session(base_date, cfg, tz)
    for slot in slots:
        if slot > ts_local:
            return slot
    next_slots = h1_slot_times_for_session(base_date + timedelta(days=1), cfg, tz)
    return next_slots[0]


def _daily_fetch_datetime_for_date(base_date: date, cfg: Config, tz: ZoneInfo) -> datetime:
    _, fetch_minute, fetch_second = parse_hhmmss(cfg.direct_fetch_daily_time_myt, 6, 0, 15)
    fetch_hour = 6 if _is_dst_myt_date(base_date) else 5
    return datetime(base_date.year, base_date.month, base_date.day, fetch_hour, fetch_minute, fetch_second, tzinfo=tz)


def current_daily_htf_slot_time(ts_local: datetime, cfg: Config, tz: ZoneInfo) -> datetime:
    today_slot = _daily_fetch_datetime_for_date(ts_local.date(), cfg, tz)
    if ts_local >= today_slot:
        return today_slot
    return _daily_fetch_datetime_for_date(ts_local.date() - timedelta(days=1), cfg, tz)


def next_daily_htf_slot_time(ts_local: datetime, cfg: Config, tz: ZoneInfo) -> datetime:
    today_slot = _daily_fetch_datetime_for_date(ts_local.date(), cfg, tz)
    if ts_local < today_slot:
        return today_slot
    return _daily_fetch_datetime_for_date(ts_local.date() + timedelta(days=1), cfg, tz)


class Storage:
    def __init__(self, root: Path, db_path: Path):
        self.root = root
        self.db_path = db_path
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def path_for(self, name: str) -> Path:
        return self.root / f"{name}.json"

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candles (
                    timeframe TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (timeframe, ts)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_candles_tf_ts ON candles(timeframe, ts)")

    def load_series(self, name: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ts, open, high, low, close, volume
                FROM candles
                WHERE timeframe = ?
                ORDER BY ts ASC
                """,
                (name,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_series(self, name: str, rows: list[dict[str, Any]]) -> None:
        clean_rows = filter_open_market_rows(name, rows)
        with self._connect() as conn:
            conn.execute("DELETE FROM candles WHERE timeframe = ?", (name,))
            if clean_rows:
                conn.executemany(
                    """
                    INSERT INTO candles (timeframe, ts, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            name,
                            row["ts"],
                            row["open"],
                            row["high"],
                            row["low"],
                            row["close"],
                            row.get("volume", 0.0),
                        )
                        for row in clean_rows
                    ],
                )

    def save_snapshot(self, name: str, payload: dict[str, Any]) -> None:
        self.path_for(name).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def load_snapshot(self, name: str) -> dict[str, Any]:
        path = self.path_for(name)
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            LOGGER.warning("Invalid JSON snapshot for %s; resetting", path)
        return {}


class TwelveDataClient:
    base_url = "https://api.twelvedata.com/time_series"

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def fetch(self, *, interval: str, outputsize: int) -> list[dict[str, Any]]:
        params = {
            "symbol": self.cfg.symbol,
            "interval": interval,
            "outputsize": str(outputsize),
            "apikey": self.cfg.api_key,
            "timezone": "UTC",
            "format": "JSON",
            "order": "ASC",
        }
        query = urlencode(params)
        url = f"{self.base_url}?{query}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "mmhelper-twelve-bot/1.0",
            },
        )

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                with urlopen(request, timeout=self.cfg.request_timeout_sec) as response:
                    body = response.read().decode("utf-8")
                payload = json.loads(body)
                values = payload.get("values")
                if isinstance(values, list):
                    return values

                code = str(payload.get("code") or "")
                message = str(payload.get("message") or "unknown error")
                if code == "429":
                    delay = min(2**attempt, 20)
                    LOGGER.warning("Rate limit hit, retrying in %ss", delay)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"Twelve Data API error: {code} {message}")
            except HTTPError as exc:
                body_text = ""
                try:
                    body_text = exc.read().decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    body_text = ""

                detail = body_text.strip()
                if detail:
                    try:
                        parsed = json.loads(detail)
                        detail = str(parsed.get("message") or parsed)
                    except json.JSONDecodeError:
                        pass

                if exc.code == 429 and attempt < self.cfg.max_retries:
                    delay = min(2**attempt, 20)
                    LOGGER.warning("Rate limit hit (HTTP 429), retrying in %ss", delay)
                    time.sleep(delay)
                    continue

                raise RuntimeError(
                    f"Twelve Data HTTP {exc.code} for {interval}. Detail: {detail or exc.reason}"
                ) from exc
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt == self.cfg.max_retries:
                    raise RuntimeError(f"Failed to fetch Twelve Data {interval}") from exc
                delay = min(2**attempt, 20)
                LOGGER.warning("Fetch %s failed (%s), retry in %ss", interval, exc, delay)
                time.sleep(delay)
        return []


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        dt = row.get("datetime")
        if not isinstance(dt, str):
            continue
        try:
            ts = parse_iso_utc(dt)
            normalized.append(
                {
                    "ts": to_iso_utc(ts),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume") or 0.0),
                }
            )
        except (KeyError, ValueError, TypeError):
            continue
    normalized.sort(key=lambda item: item["ts"])
    return normalized


def merge_incremental(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_ts = {row["ts"]: row for row in existing}
    for row in incoming:
        merged_by_ts[row["ts"]] = row
    merged = list(merged_by_ts.values())
    merged.sort(key=lambda item: item["ts"])
    return merged


def prune_by_window(rows: list[dict[str, Any]], keep: timedelta) -> list[dict[str, Any]]:
    if not rows:
        return rows
    now = datetime.now(UTC)
    cutoff = now - keep
    return [row for row in rows if parse_iso_utc(row["ts"]) >= cutoff]


def bucket_start(ts: datetime, minutes: int) -> datetime:
    total = int(ts.timestamp())
    step = minutes * 60
    return datetime.fromtimestamp(total - (total % step), tz=UTC)


def resample(rows: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    if not rows:
        return []

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ts = parse_iso_utc(row["ts"])
        key = to_iso_utc(bucket_start(ts, minutes))
        groups.setdefault(key, []).append(row)

    aggregated: list[dict[str, Any]] = []
    for key in sorted(groups):
        values = groups[key]
        values.sort(key=lambda item: item["ts"])
        aggregated.append(
            {
                "ts": key,
                "open": values[0]["open"],
                "high": max(v["high"] for v in values),
                "low": min(v["low"] for v in values),
                "close": values[-1]["close"],
                "volume": sum(v.get("volume", 0.0) for v in values),
            }
        )
    return aggregated


def h4_session_window_local(ts_local: datetime, mode: str) -> tuple[datetime, datetime] | None:
    # H4 session aligned to MYT trading windows with daily maintenance break.
    # standard mode windows (MYT):
    # 07-11, 11-15, 15-19, 19-23, 23-03, 03-06
    # dst mode windows (MYT):
    # 06-10, 10-14, 14-18, 18-22, 22-02, 02-05
    active_mode = _mode_for_local(ts_local, mode)
    if active_mode == "dst":
        start_offsets = [6, 10, 14, 18, 22, 26]
        end_offsets = [10, 14, 18, 22, 26, 29]
        day_cutoff = 6
    else:
        start_offsets = [7, 11, 15, 19, 23, 27]
        end_offsets = [11, 15, 19, 23, 27, 30]
        day_cutoff = 7

    base_date = ts_local.date()
    if ts_local.hour < day_cutoff:
        base_date = (ts_local - timedelta(days=1)).date()
    base = datetime(base_date.year, base_date.month, base_date.day, tzinfo=ts_local.tzinfo)

    for start_h, end_h in zip(start_offsets, end_offsets):
        start = base + timedelta(hours=start_h)
        end = base + timedelta(hours=end_h)
        if start <= ts_local < end:
            return start, end
    return None


def resample_h4_session(
    rows: list[dict[str, Any]],
    timezone_name: str,
    mode: str,
    include_incomplete: bool,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_tz = ZoneInfo("Asia/Kuala_Lumpur")

    normalized_mode = "dst" if mode == "dst" else "standard"
    groups: dict[str, dict[str, Any]] = {}
    now_utc = datetime.now(UTC)

    for row in rows:
        ts_utc = parse_iso_utc(row["ts"])
        ts_local = ts_utc.astimezone(local_tz)
        window = h4_session_window_local(ts_local, normalized_mode)
        if window is None:
            continue
        start_local, end_local = window
        start_utc = start_local.astimezone(UTC)
        end_utc = end_local.astimezone(UTC)
        key = to_iso_utc(start_utc)
        bucket = groups.setdefault(key, {"rows": [], "end_utc": end_utc})
        bucket["rows"].append(row)

    aggregated: list[dict[str, Any]] = []
    for key in sorted(groups):
        bucket = groups[key]
        end_utc = bucket["end_utc"]
        if not include_incomplete and end_utc > now_utc:
            continue
        values = bucket["rows"]
        values.sort(key=lambda item: item["ts"])
        aggregated.append(
            {
                "ts": key,
                "open": values[0]["open"],
                "high": max(v["high"] for v in values),
                "low": min(v["low"] for v in values),
                "close": values[-1]["close"],
                "volume": sum(v.get("volume", 0.0) for v in values),
            }
        )
    return aggregated


def _daily_session_start_hour(mode: str) -> int:
    return _daily_session_start_hour_for_date(
        datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date(),
        mode,
    )


def resample_d1_session(
    rows: list[dict[str, Any]],
    timezone_name: str,
    mode: str,
    include_incomplete: bool,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_tz = ZoneInfo("Asia/Kuala_Lumpur")

    normalized_mode = str(mode or "").strip().lower()
    groups: dict[str, dict[str, Any]] = {}
    now_utc = datetime.now(UTC)

    for row in rows:
        ts_utc = parse_iso_utc(row["ts"])
        ts_local = ts_utc.astimezone(local_tz)
        start_hour = _daily_session_start_hour_for_date(ts_local.date(), normalized_mode)
        slot_date = ts_local.date()
        if ts_local.hour < start_hour:
            slot_date = (ts_local - timedelta(days=1)).date()
        slot_start_hour = _daily_session_start_hour_for_date(slot_date, normalized_mode)
        next_slot_date = slot_date + timedelta(days=1)
        next_start_hour = _daily_session_start_hour_for_date(next_slot_date, normalized_mode)
        start_local = datetime(slot_date.year, slot_date.month, slot_date.day, slot_start_hour, 0, 0, tzinfo=local_tz)
        end_local = datetime(next_slot_date.year, next_slot_date.month, next_slot_date.day, next_start_hour, 0, 0, tzinfo=local_tz)
        start_utc = start_local.astimezone(UTC)
        end_utc = end_local.astimezone(UTC)
        key = to_iso_utc(start_utc)
        bucket = groups.setdefault(key, {"rows": [], "end_utc": end_utc})
        bucket["rows"].append(row)

    out: list[dict[str, Any]] = []
    for key in sorted(groups):
        bucket = groups[key]
        end_utc = bucket["end_utc"]
        if not include_incomplete and end_utc > now_utc:
            continue
        values = bucket["rows"]
        values.sort(key=lambda item: item["ts"])
        out.append(
            {
                "ts": key,
                "open": values[0]["open"],
                "high": max(v["high"] for v in values),
                "low": min(v["low"] for v in values),
                "close": values[-1]["close"],
                "volume": sum(v.get("volume", 0.0) for v in values),
            }
        )
    return out


def resample_w1_from_d1(
    rows: list[dict[str, Any]],
    timezone_name: str,
    mode: str,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_tz = ZoneInfo("Asia/Kuala_Lumpur")
    normalized_mode = str(mode or "").strip().lower()
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ts_local = parse_iso_utc(row["ts"]).astimezone(local_tz)
        monday = ts_local.date() - timedelta(days=ts_local.weekday())
        start_hour = _daily_session_start_hour_for_date(monday, normalized_mode)
        start_local = datetime(monday.year, monday.month, monday.day, start_hour, 0, 0, tzinfo=local_tz)
        key = to_iso_utc(start_local.astimezone(UTC))
        groups.setdefault(key, []).append(row)

    out: list[dict[str, Any]] = []
    for key in sorted(groups):
        values = sorted(groups[key], key=lambda item: item["ts"])
        out.append(
            {
                "ts": key,
                "open": values[0]["open"],
                "high": max(v["high"] for v in values),
                "low": min(v["low"] for v in values),
                "close": values[-1]["close"],
                "volume": sum(v.get("volume", 0.0) for v in values),
            }
        )
    return out


def resample_mn1_from_d1(
    rows: list[dict[str, Any]],
    timezone_name: str,
    mode: str,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_tz = ZoneInfo("Asia/Kuala_Lumpur")
    normalized_mode = str(mode or "").strip().lower()
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ts_local = parse_iso_utc(row["ts"]).astimezone(local_tz)
        first = ts_local.replace(day=1)
        start_hour = _daily_session_start_hour_for_date(first.date(), normalized_mode)
        start_local = datetime(first.year, first.month, first.day, start_hour, 0, 0, tzinfo=local_tz)
        key = to_iso_utc(start_local.astimezone(UTC))
        groups.setdefault(key, []).append(row)

    out: list[dict[str, Any]] = []
    for key in sorted(groups):
        values = sorted(groups[key], key=lambda item: item["ts"])
        out.append(
            {
                "ts": key,
                "open": values[0]["open"],
                "high": max(v["high"] for v in values),
                "low": min(v["low"] for v in values),
                "close": values[-1]["close"],
                "volume": sum(v.get("volume", 0.0) for v in values),
            }
        )
    return out


def align_rows_to_session_start(
    rows: list[dict[str, Any]],
    timezone_name: str,
    mode: str,
) -> list[dict[str, Any]]:
    """Align candle timestamps to MYT session start hour (07:00 standard / 06:00 dst)."""
    if not rows:
        return rows
    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_tz = ZoneInfo("Asia/Kuala_Lumpur")
    normalized_mode = str(mode or "").strip().lower()

    out: list[dict[str, Any]] = []
    for row in rows:
        ts_local = parse_iso_utc(row["ts"]).astimezone(local_tz)
        start_hour = _daily_session_start_hour_for_date(ts_local.date(), normalized_mode)
        aligned_local = datetime(
            ts_local.year,
            ts_local.month,
            ts_local.day,
            start_hour,
            0,
            0,
            tzinfo=local_tz,
        )
        copied = dict(row)
        copied["ts"] = to_iso_utc(aligned_local.astimezone(UTC))
        out.append(copied)

    out.sort(key=lambda item: item["ts"])
    return out


def find_swings(rows: list[dict[str, Any]], lookback: int = 2) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    highs: list[dict[str, Any]] = []
    lows: list[dict[str, Any]] = []
    if len(rows) < (lookback * 2 + 1):
        return highs, lows

    for i in range(lookback, len(rows) - lookback):
        current = rows[i]
        left = rows[i - lookback : i]
        right = rows[i + 1 : i + 1 + lookback]
        if all(current["high"] > x["high"] for x in left + right):
            highs.append(current)
        if all(current["low"] < x["low"] for x in left + right):
            lows.append(current)
    return highs, lows


def detect_dbo_structure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    highs, lows = find_swings(rows)
    if len(highs) < 2 or len(lows) < 2:
        return {"status": "insufficient_swings"}

    last_high = highs[-1]
    prev_high = highs[-2]
    last_low = lows[-1]
    prev_low = lows[-2]

    if last_high["high"] > prev_high["high"] and last_low["low"] > prev_low["low"]:
        regime = "bullish_structure"
    elif last_high["high"] < prev_high["high"] and last_low["low"] < prev_low["low"]:
        regime = "bearish_structure"
    else:
        regime = "range_or_transition"

    return {
        "status": "ok",
        "regime": regime,
        "last_high_ts": last_high["ts"],
        "last_low_ts": last_low["ts"],
    }


def compute_fib_extension(rows: list[dict[str, Any]]) -> dict[str, Any]:
    highs, lows = find_swings(rows)
    if not highs or not lows:
        return {"status": "insufficient_swings"}

    points = sorted(highs[-2:] + lows[-2:], key=lambda r: r["ts"])
    if len(points) < 3:
        return {"status": "insufficient_points"}

    a, b, c = points[-3], points[-2], points[-1]
    ab = b["close"] - a["close"]
    if abs(ab) < 1e-9:
        return {"status": "invalid_leg"}

    fib1272 = c["close"] + ab * 1.272
    fib1618 = c["close"] + ab * 1.618
    fib2000 = c["close"] + ab * 2.0

    return {
        "status": "ok",
        "a_ts": a["ts"],
        "b_ts": b["ts"],
        "c_ts": c["ts"],
        "level_1_272": round(fib1272, 5),
        "level_1_618": round(fib1618, 5),
        "level_2_0": round(fib2000, 5),
    }


def m5_pipeline(client: TwelveDataClient, store: Storage, cfg: Config, *, do_fetch: bool) -> list[dict[str, Any]]:
    existing = store.load_series("m5")
    if not do_fetch:
        LOGGER.info("m5 candles reused=%s fetched=0", len(existing))
        return existing
    outputsize = cfg.incremental_m5_points if existing else cfg.bootstrap_m5_points
    fetched = normalize_rows(client.fetch(interval="5min", outputsize=outputsize))

    merged = merge_incremental(existing, fetched)
    merged = prune_by_window(merged, RETENTION_WINDOWS["m5"])
    store.save_series("m5", merged)
    LOGGER.info("m5 candles saved=%s fetched=%s", len(merged), len(fetched))
    return merged


def h1_pipeline(client: TwelveDataClient, store: Storage, cfg: Config, *, do_fetch: bool) -> list[dict[str, Any]]:
    existing = store.load_series("h1")
    if not do_fetch:
        LOGGER.info("h1 candles reused=%s fetched=0", len(existing))
        return existing
    need_bootstrap = len(existing) < cfg.bootstrap_h1_points
    outputsize = cfg.bootstrap_h1_points if need_bootstrap else cfg.incremental_h1_points
    fetched = normalize_rows(client.fetch(interval="1h", outputsize=outputsize))

    merged = merge_incremental(existing, fetched)
    merged = prune_by_window(merged, RETENTION_WINDOWS["h1"])
    store.save_series("h1", merged)
    LOGGER.info(
        "h1 candles saved=%s fetched=%s outputsize=%s bootstrap=%s",
        len(merged),
        len(fetched),
        outputsize,
        "yes" if need_bootstrap else "no",
    )
    return merged


def build_derived_timeframes(
    store: Storage,
    m5_rows: list[dict[str, Any]],
    h1_rows: list[dict[str, Any]],
    cfg: Config,
) -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {}
    for key, mins in (("m15", 15), ("m30", 30)):
        built = resample(m5_rows, mins)
        pruned = prune_by_window(built, RETENTION_WINDOWS[key])
        store.save_series(key, pruned)
        data[key] = pruned
        LOGGER.info("%s candles saved=%s", key, len(pruned))
    data["h1"] = h1_rows

    h4_built = resample_h4_session(
        h1_rows,
        cfg.display_timezone,
        cfg.h4_session_mode,
        include_incomplete=False,
    )
    h4_pruned = prune_by_window(h4_built, RETENTION_WINDOWS["h4"])
    store.save_series("h4", h4_pruned)
    store.save_series("h4_live", h4_pruned)
    data["h4"] = h4_pruned
    data["h4_live"] = h4_pruned
    LOGGER.info("h4 candles rebuilt_from_h1=%s mode=%s tz=%s", len(h4_pruned), cfg.h4_session_mode, cfg.display_timezone)
    return data


def fetch_daily_higher_tfs(
    client: TwelveDataClient,
    store: Storage,
    cfg: Config,
    *,
    daily_due: bool,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, bool]]:
    direct_map = {
        "d1": "1day",
        "w1": "1week",
        "mn1": "1month",
    }
    bootstrap_rows = {
        "d1": cfg.bootstrap_d1_points,
        "w1": cfg.bootstrap_w1_points,
        "mn1": cfg.bootstrap_mn1_points,
    }
    state = store.load_snapshot("direct_fetch_state")
    now = datetime.now(UTC)
    out: dict[str, list[dict[str, Any]]] = {}
    status: dict[str, bool] = {}
    for key, interval in direct_map.items():
        existing_rows = store.load_series(key)
        min_rows = bootstrap_rows[key]
        need_bootstrap = len(existing_rows) < min_rows
        should_fetch = daily_due or need_bootstrap

        if should_fetch:
            outputsize = max(cfg.direct_points, min_rows)
            try:
                rows = normalize_rows(client.fetch(interval=interval, outputsize=outputsize))
                rows = align_rows_to_session_start(rows, cfg.display_timezone, cfg.h4_session_mode)
                rows = prune_by_window(rows, RETENTION_WINDOWS[key])
                store.save_series(key, rows)
                state[key] = now.isoformat()
                out[key] = rows
                LOGGER.info(
                    "%s candles saved=%s fetched=1 outputsize=%s bootstrap=%s",
                    key,
                    len(rows),
                    outputsize,
                    "yes" if need_bootstrap else "no",
                )
                status[key] = True
            except Exception as exc:  # noqa: BLE001
                rows = align_rows_to_session_start(existing_rows, cfg.display_timezone, cfg.h4_session_mode)
                if rows != existing_rows:
                    store.save_series(key, rows)
                out[key] = rows
                LOGGER.warning("%s fetch failed, reused/aligned=%s (%s)", key, len(rows), exc)
                status[key] = False
        else:
            rows = existing_rows
            aligned = align_rows_to_session_start(rows, cfg.display_timezone, cfg.h4_session_mode)
            if aligned != rows:
                rows = aligned
                store.save_series(key, rows)
            out[key] = rows
            LOGGER.info("%s candles reused=%s fetched=0", key, len(rows))
            status[key] = True

    store.save_snapshot("direct_fetch_state", state)
    return out, status


def build_signal_payload(
    symbol: str,
    analysis_tf: str,
    rows_by_tf: dict[str, list[dict[str, Any]]],
    direct_rows: dict[str, list[dict[str, Any]]],
    display_timezone: str,
) -> dict[str, Any]:
    tf_rows = rows_by_tf.get(analysis_tf) or []
    latest_close = tf_rows[-1]["close"] if tf_rows else None

    market_structure = detect_dbo_structure(tf_rows)
    fib = compute_fib_extension(tf_rows)

    signal = "HOLD"
    if market_structure.get("regime") == "bullish_structure":
        signal = "BUY_BIAS"
    elif market_structure.get("regime") == "bearish_structure":
        signal = "SELL_BIAS"

    generated_at = datetime.now(UTC)
    payload = {
        "generated_at": generated_at.isoformat(),
        "generated_at_myt": to_iso_local(generated_at, display_timezone),
        "display_timezone": display_timezone,
        "symbol": symbol,
        "analysis_timeframe": analysis_tf,
        "signal": signal,
        "latest_close": latest_close,
        "dbo_market_structure": market_structure,
        "fibo_extension": fib,
        "available_rows": {k: len(v) for k, v in rows_by_tf.items()},
        "direct_rows": {k: len(v) for k, v in direct_rows.items()},
    }
    h4_closed = rows_by_tf.get("h4") or []
    h4_live = rows_by_tf.get("h4_live") or []
    payload["h4_mode"] = {
        "closed_last_ts": h4_closed[-1]["ts"] if h4_closed else None,
        "live_last_ts": h4_live[-1]["ts"] if h4_live else None,
    }
    return payload


def format_telegram_signal_message(payload: dict[str, Any]) -> str:
    tf = payload.get("analysis_timeframe") or "-"
    signal = payload.get("signal") or "HOLD"
    symbol = payload.get("symbol") or "-"
    close = payload.get("latest_close")
    market = payload.get("dbo_market_structure") or {}
    fib = payload.get("fibo_extension") or {}
    regime = market.get("regime") or market.get("status") or "-"
    level_1272 = fib.get("level_1_272", "-")
    level_1618 = fib.get("level_1_618", "-")
    level_20 = fib.get("level_2_0", "-")
    ts = payload.get("generated_at") or "-"
    ts_myt = payload.get("generated_at_myt") or "-"
    tz_name = payload.get("display_timezone") or "Asia/Kuala_Lumpur"

    return (
        "XAU Feeder Alert\\n"
        f"Signal: {signal}\\n"
        f"Symbol: {symbol}\\n"
        f"TF: {tf}\\n"
        f"Close: {close}\\n"
        f"Market: {regime}\\n"
        f"Fib 1.272: {level_1272}\\n"
        f"Fib 1.618: {level_1618}\\n"
        f"Fib 2.0: {level_20}\\n"
        f"Time(UTC): {ts}\\n"
        f"Time({tz_name}): {ts_myt}"
    )


def send_telegram_message(cfg: Config, text: str) -> None:
    if not cfg.telegram_enabled:
        return
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        LOGGER.warning("Telegram enabled but TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID missing")
        return

    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    payload = urlencode(
        {
            "chat_id": cfg.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "mmhelper-twelve-bot/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        response.read()


def maybe_send_telegram_alert(cfg: Config, store: Storage, payload: dict[str, Any]) -> None:
    if not cfg.telegram_enabled:
        return

    signal = str(payload.get("signal") or "HOLD")
    if signal == "HOLD" and not cfg.telegram_send_hold:
        return

    state = store.load_snapshot("telegram_state")
    last_signal = str(state.get("last_signal") or "")
    last_sent_raw = str(state.get("last_sent_at") or "")
    last_sent_at: datetime | None = None
    if last_sent_raw:
        try:
            last_sent_at = datetime.fromisoformat(last_sent_raw.replace("Z", "+00:00"))
        except ValueError:
            last_sent_at = None

    now = datetime.now(UTC)
    if signal == last_signal and last_sent_at:
        elapsed = (now - last_sent_at).total_seconds()
        if elapsed < cfg.telegram_min_interval_sec:
            LOGGER.info(
                "Telegram skipped signal=%s elapsed=%ss (<%ss)",
                signal,
                int(elapsed),
                cfg.telegram_min_interval_sec,
            )
            return

    text = format_telegram_signal_message(payload)
    send_telegram_message(cfg, text)
    store.save_snapshot(
        "telegram_state",
        {"last_signal": signal, "last_sent_at": now.isoformat()},
    )
    LOGGER.info("Telegram alert sent signal=%s", signal)


def run_cycle(cfg: Config, *, fetch_m5: bool, fetch_h1: bool, fetch_daily_htf: bool) -> dict[str, bool]:
    store = Storage(cfg.state_dir, cfg.db_path)
    client = TwelveDataClient(cfg)

    try:
        m5_rows = m5_pipeline(client, store, cfg, do_fetch=fetch_m5)
    except Exception as exc:  # noqa: BLE001
        m5_rows = store.load_series("m5")
        if not m5_rows:
            raise
        LOGGER.warning("m5 fetch failed, using cached m5 rows=%s (%s)", len(m5_rows), exc)
    try:
        h1_rows = h1_pipeline(client, store, cfg, do_fetch=fetch_h1)
    except Exception as exc:  # noqa: BLE001
        h1_rows = store.load_series("h1")
        if not h1_rows:
            raise
        LOGGER.warning("h1 fetch failed, using cached h1 rows=%s (%s)", len(h1_rows), exc)
    derived = build_derived_timeframes(store, m5_rows, h1_rows, cfg)
    direct, daily_status = fetch_daily_higher_tfs(client, store, cfg, daily_due=fetch_daily_htf)
    rows_for_signal = dict(derived)
    rows_for_signal.update(direct)

    signal_payload = build_signal_payload(
        cfg.symbol,
        cfg.analysis_timeframe,
        rows_for_signal,
        direct,
        cfg.display_timezone,
    )
    store.save_snapshot("latest_signal", signal_payload)
    try:
        maybe_send_telegram_alert(cfg, store, signal_payload)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Telegram alert failed: %s", exc)
    store.save_snapshot(
        "bot_state",
        asdict(cfg) | {"state_dir": str(cfg.state_dir), "db_path": str(cfg.db_path)},
    )
    LOGGER.info("Signal updated: %s", signal_payload.get("signal"))
    return daily_status


def main() -> None:
    load_local_env()
    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    LOGGER.info(
        "Starting bot symbol=%s poll=%ss state_dir=%s db=%s",
        cfg.symbol,
        cfg.poll_interval_sec,
        cfg.state_dir,
        cfg.db_path,
    )

    try:
        schedule_tz = ZoneInfo(cfg.display_timezone)
    except ZoneInfoNotFoundError:
        schedule_tz = ZoneInfo("Asia/Kuala_Lumpur")

    schedule_store = Storage(cfg.state_dir, cfg.db_path)

    if cfg.run_once:
        try:
            run_cycle(cfg, fetch_m5=True, fetch_h1=True, fetch_daily_htf=True)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Cycle failed: %s", exc)
        LOGGER.info("RUN_ONCE=1 detected, exiting after one cycle")
        return

    while True:
        now_utc = datetime.now(UTC)
        now_local = now_utc.astimezone(schedule_tz)
        state = schedule_store.load_snapshot("schedule_state")
        last_m5_slot = str(state.get("m5_slot") or "")
        last_h1_slot = str(state.get("h1_slot") or "")
        last_daily_htf_slot = str(state.get("daily_htf_slot") or "")
        retry_slot = str(state.get("daily_retry_slot") or "")
        retry_count = int(state.get("daily_retry_count") or 0)
        retry_next_raw = str(state.get("daily_retry_next_at") or "")
        retry_next_at: datetime | None = None
        if retry_next_raw:
            try:
                retry_next_at = datetime.fromisoformat(retry_next_raw)
                if retry_next_at.tzinfo is None:
                    retry_next_at = retry_next_at.replace(tzinfo=schedule_tz)
            except ValueError:
                retry_next_at = None

        m5_slot = current_m5_slot_time(now_local, cfg, schedule_tz)
        h1_slot = current_h1_slot_time(now_local, cfg, schedule_tz)
        daily_htf_slot = current_daily_htf_slot_time(now_local, cfg, schedule_tz)
        daily_slot_id = daily_htf_slot.isoformat() if daily_htf_slot else ""

        m5_due = bool(m5_slot and m5_slot.isoformat() != last_m5_slot)
        h1_due = bool(h1_slot and h1_slot.isoformat() != last_h1_slot)
        daily_htf_due = bool(daily_htf_slot and daily_slot_id != last_daily_htf_slot)
        retry_due = bool(
            retry_slot
            and daily_slot_id
            and retry_slot == daily_slot_id
            and 0 < retry_count < 6
            and retry_next_at is not None
            and now_local >= retry_next_at
        )
        fetch_daily_now = daily_htf_due or retry_due

        if not (m5_due or h1_due or fetch_daily_now):
            next_m5 = next_m5_slot_time(now_local, cfg, schedule_tz).astimezone(UTC)
            next_h1 = next_h1_slot_time(now_local, cfg, schedule_tz).astimezone(UTC)
            next_daily_htf = next_daily_htf_slot_time(now_local, cfg, schedule_tz).astimezone(UTC)
            if (
                retry_slot
                and daily_slot_id
                and retry_slot == daily_slot_id
                and 0 < retry_count < 6
                and retry_next_at is not None
            ):
                next_daily_htf = min(next_daily_htf, retry_next_at.astimezone(UTC))
            next_due = min(next_m5, next_h1, next_daily_htf)
            sleep_for = max(0.2, (next_due - now_utc).total_seconds())
            time.sleep(min(sleep_for, 60))
            continue

        try:
            daily_status = run_cycle(cfg, fetch_m5=m5_due, fetch_h1=h1_due, fetch_daily_htf=fetch_daily_now)
            if m5_due and m5_slot is not None:
                state["m5_slot"] = m5_slot.isoformat()
            if h1_due and h1_slot is not None:
                state["h1_slot"] = h1_slot.isoformat()
            if daily_htf_due and daily_htf_slot is not None:
                # Mark slot as attempted so we don't spam every loop;
                # retries are controlled via daily_retry_* fields.
                state["daily_htf_slot"] = daily_slot_id
                state["daily_retry_slot"] = daily_slot_id
                state["daily_retry_count"] = 0
                state["daily_retry_next_at"] = ""
            if fetch_daily_now and daily_htf_slot is not None:
                ok = all(daily_status.get(k, False) for k in ("d1", "w1", "mn1"))
                if ok:
                    state["daily_retry_slot"] = ""
                    state["daily_retry_count"] = 0
                    state["daily_retry_next_at"] = ""
                else:
                    count = int(state.get("daily_retry_count") or 0) + 1
                    if count < 6:
                        next_retry = now_local + timedelta(minutes=10)
                        state["daily_retry_slot"] = daily_slot_id
                        state["daily_retry_count"] = count
                        state["daily_retry_next_at"] = next_retry.isoformat()
                        LOGGER.warning(
                            "Daily HTF retry scheduled slot=%s attempt=%s/6 next=%s",
                            daily_slot_id,
                            count,
                            next_retry.isoformat(),
                        )
                    else:
                        state["daily_retry_slot"] = ""
                        state["daily_retry_count"] = 0
                        state["daily_retry_next_at"] = ""
                        LOGGER.error("Daily HTF retries exhausted for slot=%s", daily_slot_id)
            schedule_store.save_snapshot("schedule_state", state)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Cycle failed: %s", exc)
            time.sleep(2)


if __name__ == "__main__":
    main()
