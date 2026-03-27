#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "mmhelper_shared.db"
VIDEO_STATUS_JSON = ROOT / "mmhelper_video_bot" / "video_status.json"
MY_TZ = ZoneInfo("Asia/Kuala_Lumpur")
PORT = int(os.getenv("OPS_HUD_PORT") or "8765")

SERVICES = [
    "mmhelper-sidebot",
    "mmhelper-video-bot",
    "next-event-bot",
    "mmhelper-bot",
    "reezo-moderator-bot",
]

FULLFLOW_SESSIONS = [
    {"series": "1", "session": "1", "title": "Webinar FULLFLOW SIRI 1", "start": "2026-04-07T21:00:00+08:00"},
    {"series": "1", "session": "2", "title": "Webinar FULLFLOW SIRI 1", "start": "2026-04-08T21:00:00+08:00"},
    {"series": "2", "session": "1", "title": "Webinar FULLFLOW SIRI 2", "start": "2026-04-22T21:00:00+08:00"},
    {"series": "2", "session": "2", "title": "Webinar FULLFLOW SIRI 2", "start": "2026-04-23T21:00:00+08:00"},
    {"series": "3", "session": "1", "title": "Webinar FULLFLOW SIRI 3", "start": "2026-05-14T21:00:00+08:00"},
    {"series": "3", "session": "2", "title": "Webinar FULLFLOW SIRI 3", "start": "2026-05-15T21:00:00+08:00"},
]


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fmt_dt(dt: datetime) -> str:
    return dt.astimezone(MY_TZ).strftime("%d %b %Y %I:%M %p MYT")


def _fmt_time(dt: datetime) -> str:
    return dt.astimezone(MY_TZ).strftime("%I:%M %p")


def _fmt_date(dt: datetime) -> str:
    return dt.astimezone(MY_TZ).strftime("%d %b %Y")


def _service_status(name: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        return (result.stdout or "").strip() or "unknown"
    except Exception:
        return "unknown"


def _recent_error_for_service(name: str) -> str:
    try:
        result = subprocess.run(
            [
                "journalctl",
                "-u",
                name,
                "-p",
                "err",
                "--since",
                "-12h",
                "-n",
                "1",
                "--no-pager",
                "-o",
                "cat",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def _ram_storage_snapshot() -> tuple[str, str]:
    ram = "-"
    storage = "-"
    try:
        result = subprocess.run(["free", "-h"], check=False, capture_output=True, text=True, timeout=3)
        for line in (result.stdout or "").splitlines():
            if line.lower().startswith("mem:"):
                parts = line.split()
                if len(parts) >= 3:
                    ram = f"{parts[2]} / {parts[1]}"
                break
    except Exception:
        pass
    try:
        result = subprocess.run(["df", "-h", "/"], check=False, capture_output=True, text=True, timeout=3)
        lines = [line for line in (result.stdout or "").splitlines() if line.strip()]
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 3:
                storage = f"{parts[2]} / {parts[1]}"
    except Exception:
        pass
    return ram, storage


def _flow_label(flow: str) -> str:
    raw = str(flow or "").strip()
    if raw.startswith("webinar_s"):
        if "_new_registration" in raw:
            kind = "Pelanggan Baru"
        elif "_ib_transfer" in raw:
            kind = "Penukaran IB"
        elif "_under_ib_reezo" in raw:
            kind = "Client Under IB Reezo"
        elif "_special_invitation" in raw:
            kind = "Special Invitation"
        else:
            kind = "Webinar"
        series = raw.split("_")[1].upper()
        return f"{series} - {kind}"
    if raw == "one_time_purchase":
        return "Beli eVideo"
    if raw in {"new_registration", "ib_transfer", "under_ib_reezo"}:
        mapping = {
            "new_registration": "NEXTexclusive - Pelanggan Baru",
            "ib_transfer": "NEXTexclusive - Penukaran IB",
            "under_ib_reezo": "NEXTexclusive - Client Under IB Reezo",
        }
        return mapping.get(raw, raw)
    return raw or "-"


def _load_submissions() -> list[sqlite3.Row]:
    try:
        with _db_connect() as conn:
            return conn.execute(
                """
                SELECT submission_id, user_id, status, registration_flow, full_name, telegram_username,
                       wallet_id, api_is_client_under_ib, api_check_message, submitted_at, reviewed_at
                FROM sidebot_submissions
                ORDER BY datetime(submitted_at) DESC
                LIMIT 120
                """
            ).fetchall()
    except Exception:
        return []


def _load_video_available_on_entries() -> list[dict[str, str]]:
    if not VIDEO_STATUS_JSON.exists():
        return []
    try:
        payload = json.loads(VIDEO_STATUS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows: list[dict[str, str]] = []
    today = datetime.now(MY_TZ).date()
    for level, topics in payload.items():
        if not isinstance(topics, dict):
            continue
        for topic_no, row in topics.items():
            if not isinstance(row, dict):
                continue
            if str(row.get("status") or "") != "available_on":
                continue
            available_on = str(row.get("available_on") or "").strip()
            if not available_on:
                continue
            try:
                available_date = datetime.strptime(available_on, "%Y-%m-%d").date()
            except ValueError:
                continue
            if available_date < today:
                continue
            rows.append(
                {
                    "level": str(level),
                    "topic_no": str(topic_no),
                    "available_on": available_on,
                }
            )
    rows.sort(key=lambda item: item["available_on"])
    return rows


def _build_upcoming_events(now_local: datetime) -> list[dict[str, Any]]:
    out = []
    for row in FULLFLOW_SESSIONS:
        start_dt = _parse_iso(row["start"])
        if start_dt is None:
            continue
        start_local = start_dt.astimezone(MY_TZ)
        if start_local < now_local:
            continue
        delta = start_local - now_local
        hours = int(delta.total_seconds() // 3600)
        out.append(
            {
                "title": f"{row['title']} Sesi {row['session']}",
                "start_local": _fmt_dt(start_local),
                "hours_left": hours,
                "series": row["series"],
            }
        )
    return out[:3]


def build_payload() -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(MY_TZ)
    submissions = _load_submissions()

    recent_next = []
    recent_webinar = []
    pending_counter = Counter()
    timeline: list[dict[str, Any]] = []

    for row in submissions:
        flow = str(row["registration_flow"] or "")
        status = str(row["status"] or "pending").lower()
        submitted_at = _parse_iso(str(row["submitted_at"] or "")) or now_utc
        item = {
            "title": _flow_label(flow),
            "name": str(row["full_name"] or "-"),
            "time": _fmt_time(submitted_at),
            "submitted_at": str(row["submitted_at"] or ""),
            "status": status,
            "wallet_id": str(row["wallet_id"] or ""),
            "api_status": row["api_is_client_under_ib"],
            "api_message": str(row["api_check_message"] or ""),
        }
        if status == "pending":
            if flow.startswith("webinar_"):
                pending_counter["webinar"] += 1
            elif flow == "one_time_purchase":
                pending_counter["evideo"] += 1
            else:
                pending_counter["next"] += 1

        if flow.startswith("webinar_"):
            api_text = "API PASS" if item["api_status"] == 1 else ("API FAIL" if item["api_status"] == 0 else "API pending")
            timeline.append(
                {
                    "kind": "alert",
                    "dt": submitted_at,
                    "priority": "amber" if status == "pending" else "green",
                    "title": "Daftar Webinar",
                    "time": _fmt_time(submitted_at),
                    "date": _fmt_date(submitted_at),
                    "desc": f"{item['name']} daftar {item['title']}. {api_text}.",
                    "pill": "Webinar",
                    "pill_class": "amber",
                    "text": f"{item['name']} daftar {item['title']}.",
                }
            )
        elif flow in {"new_registration", "ib_transfer", "under_ib_reezo", "one_time_purchase"}:
            timeline.append(
                {
                    "kind": "alert",
                    "dt": submitted_at,
                    "priority": "red" if status == "pending" else "green",
                    "title": item["title"],
                    "time": _fmt_time(submitted_at),
                    "date": _fmt_date(submitted_at),
                    "desc": f"{item['name']} hantar permohonan baru.",
                    "pill": "Admin",
                    "pill_class": "red",
                    "text": f"{item['name']} hantar {item['title']}.",
                }
            )

        if flow.startswith("webinar_") and len(recent_webinar) < 4:
            recent_webinar.append(item)
        elif flow in {"new_registration", "ib_transfer", "under_ib_reezo", "one_time_purchase"} and len(recent_next) < 4:
            recent_next.append(item)

    for service in SERVICES:
        error_line = _recent_error_for_service(service)
        if error_line:
            timeline.append(
                {
                    "kind": "alert",
                    "dt": now_utc,
                    "priority": "red",
                    "title": f"Error Log: {service}",
                    "time": now_local.strftime("%I:%M %p"),
                    "date": now_local.strftime("%d %b %Y"),
                    "desc": error_line[:180],
                    "pill": "System",
                    "pill_class": "red",
                    "text": f"{service}: {error_line[:180]}",
                }
            )

    available_entries = _load_video_available_on_entries()
    if available_entries:
        first = available_entries[0]
        timeline.append(
            {
                "kind": "alert",
                "dt": now_utc,
                "priority": "blue",
                "title": "eVideo Reminder",
                "time": now_local.strftime("%I:%M %p"),
                "date": now_local.strftime("%d %b %Y"),
                "desc": f"{first['level'].title()} Topik {first['topic_no']} available on {first['available_on']}.",
                "pill": "eVideo",
                "pill_class": "blue",
                "text": f"{first['level'].title()} topik {first['topic_no']} available on {first['available_on']}.",
            }
        )

    upcoming_events = _build_upcoming_events(now_local)
    if upcoming_events:
        event = upcoming_events[0]
        timeline.append(
            {
                "kind": "alert",
                "dt": now_utc,
                "priority": "amber",
                "title": "Upcoming Event",
                "time": now_local.strftime("%I:%M %p"),
                "date": now_local.strftime("%d %b %Y"),
                "desc": f"{event['title']} bermula {event['start_local']}.",
                "pill": "Event",
                "pill_class": "green",
                "text": f"{event['title']} pada {event['start_local']}.",
            }
        )

    timeline.sort(key=lambda row: row.get("dt") or now_utc, reverse=True)
    alerts = [
        {
            "priority": row["priority"],
            "title": row["title"],
            "time": row["time"],
            "desc": row["desc"],
        }
        for row in timeline[:4]
    ]

    service_rows = []
    for service in SERVICES[:4]:
        status = _service_status(service)
        dot = "green" if status == "active" else "red"
        service_rows.append({"name": service, "status": status, "dot": dot})

    ram, storage = _ram_storage_snapshot()
    system_pulse = "Stable" if all(row["status"] == "active" for row in service_rows[:3]) else "Warning"

    ticker = [
        {
            "time": row["time"],
            "date": row.get("date") or now_local.strftime("%d %b %Y"),
            "pill": row["pill"],
            "pill_class": row["pill_class"],
            "text": row["text"],
        }
        for row in timeline[:15]
    ]
    if not ticker:
        ticker.append(
            {
                "time": now_local.strftime("%I:%M %p"),
                "date": now_local.strftime("%d %b %Y"),
                "pill": "System",
                "pill_class": "blue",
                "text": "Tiada event penting buat masa ini.",
            }
        )

    return {
        "ok": True,
        "generated_at": now_utc.isoformat(),
        "pending_total": sum(pending_counter.values()),
        "alerts": alerts,
        "queue": [
            {
                "priority": "red",
                "label": "Group Admin",
                "title": "Pending Approval",
                "count": pending_counter["next"] + pending_counter["evideo"] + pending_counter["webinar"],
                "items": [
                    f"{pending_counter['next']} x NEXTexclusive",
                    f"{pending_counter['evideo']} x eVideo",
                    f"{pending_counter['webinar']} x webinar",
                ],
            },
            {
                "priority": "amber",
                "label": "Upcoming Event",
                "title": "Reminder Queue",
                "count": len(upcoming_events) + (1 if available_entries else 0),
                "items": [
                    *[f"{row['title']} ({row['start_local']})" for row in upcoming_events[:2]],
                    *([f"eVideo available on {available_entries[0]['available_on']}"] if available_entries else []),
                ][:3],
            },
        ],
        "system": {
            "pulse": system_pulse,
            "ram": ram,
            "storage": storage,
            "services": service_rows,
        },
        "ticker": ticker,
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/ops-hud":
            try:
                self._json(200, build_payload())
            except Exception as exc:
                self._json(500, {"ok": False, "error": "snapshot_failed", "detail": str(exc)})
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"ops_hud_server listening on :{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
