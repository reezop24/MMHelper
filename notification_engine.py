"""Notification scheduler engine for MM HELPER."""

from __future__ import annotations

from datetime import datetime

from telegram.ext import ContextTypes

from menu import ADMIN_USER_IDS
from storage import (
    get_notification_settings,
    list_active_user_ids,
    mark_notification_sent,
    was_notification_sent,
)
from time_utils import MALAYSIA_TZ, malaysia_now


def _first_admin_id() -> int | None:
    if not ADMIN_USER_IDS:
        return None
    return sorted(ADMIN_USER_IDS)[0]


def _parse_datetime(date_str: str, time_str: str) -> datetime | None:
    if not date_str or not time_str:
        return None
    try:
        parsed = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return parsed.replace(tzinfo=MALAYSIA_TZ)
    except ValueError:
        return None


async def _broadcast(context: ContextTypes.DEFAULT_TYPE, recipients: list[int], text: str) -> None:
    if not text.strip():
        return
    for user_id in recipients:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except Exception:
            continue


async def _handle_manual_push(
    context: ContextTypes.DEFAULT_TYPE,
    now: datetime,
    admin_id: int,
    recipients: list[int],
    settings: dict,
) -> None:
    if not settings.get("enabled"):
        return

    date_str = str(settings.get("date") or "").strip()
    time_str = str(settings.get("time") or "").strip()
    message = str(settings.get("message") or "").strip()
    target_dt = _parse_datetime(date_str, time_str)
    if not target_dt or not message:
        return
    if now < target_dt:
        return

    marker = f"{date_str}|{time_str}|{message}"
    if was_notification_sent(admin_id, "manual_push", marker):
        return

    await _broadcast(context, recipients, message)
    mark_notification_sent(admin_id, "manual_push", marker)


async def _handle_daily_notifications(
    context: ContextTypes.DEFAULT_TYPE,
    now: datetime,
    admin_id: int,
    recipients: list[int],
    settings: dict,
) -> None:
    if not settings.get("enabled"):
        return

    message = str(settings.get("preset_message") or "").strip()
    times = settings.get("times", [])
    if not message or not isinstance(times, list):
        return

    today = now.strftime("%Y-%m-%d")
    now_hm = now.strftime("%H:%M")

    for raw_time in times:
        time_str = str(raw_time or "").strip()
        if not time_str:
            continue
        if now_hm < time_str:
            continue
        marker = f"{today}|{time_str}"
        if was_notification_sent(admin_id, "daily_notification", marker):
            continue
        await _broadcast(context, recipients, message)
        mark_notification_sent(admin_id, "daily_notification", marker)


async def _handle_report_notifications(
    context: ContextTypes.DEFAULT_TYPE,
    now: datetime,
    admin_id: int,
    recipients: list[int],
    settings: dict,
) -> None:
    if not settings.get("enabled"):
        return

    today = now.strftime("%Y-%m-%d")
    weekly_date = str(settings.get("weekly_remind_date") or "").strip()
    monthly_date = str(settings.get("monthly_remind_date") or "").strip()

    if weekly_date and weekly_date == today:
        marker = f"weekly|{today}"
        if not was_notification_sent(admin_id, "report_notification", marker):
            await _broadcast(
                context,
                recipients,
                "📊 Weekly report dah ready. Check sekarang untuk tengok progress minggu ni.",
            )
            mark_notification_sent(admin_id, "report_notification", marker)

    if monthly_date and monthly_date == today:
        marker = f"monthly|{today}"
        if not was_notification_sent(admin_id, "report_notification", marker):
            await _broadcast(
                context,
                recipients,
                "📈 Monthly report dah ready. Jom semak prestasi bulan ni dan plan next move.",
            )
            mark_notification_sent(admin_id, "report_notification", marker)


async def _handle_maintenance_notifications(
    context: ContextTypes.DEFAULT_TYPE,
    now: datetime,
    admin_id: int,
    recipients: list[int],
    settings: dict,
) -> None:
    if not settings.get("enabled"):
        return

    start_date = str(settings.get("start_date") or "").strip()
    start_time = str(settings.get("start_time") or "").strip()
    end_date = str(settings.get("end_date") or "").strip()
    end_time = str(settings.get("end_time") or "").strip()
    message = str(settings.get("message") or "").strip()

    start_dt = _parse_datetime(start_date, start_time)
    end_dt = _parse_datetime(end_date, end_time)

    if start_dt and message and now >= start_dt:
        marker = f"start|{start_date}|{start_time}|{message}"
        if not was_notification_sent(admin_id, "maintenance_notification", marker):
            await _broadcast(context, recipients, message)
            mark_notification_sent(admin_id, "maintenance_notification", marker)

    if end_dt and now >= end_dt:
        marker = f"end|{end_date}|{end_time}"
        if not was_notification_sent(admin_id, "maintenance_notification", marker):
            await _broadcast(
                context,
                recipients,
                "✅ Maintenance selesai. Semua fungsi MM Helper dah kembali normal.",
            )
            mark_notification_sent(admin_id, "maintenance_notification", marker)


async def run_notification_engine(context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = _first_admin_id()
    if not admin_id:
        return

    settings = get_notification_settings(admin_id)
    if not settings:
        return

    recipients = list_active_user_ids()
    if not recipients:
        return

    now = malaysia_now()
    await _handle_manual_push(context, now, admin_id, recipients, settings.get("manual_push", {}))
    await _handle_daily_notifications(context, now, admin_id, recipients, settings.get("daily_notification", {}))
    await _handle_report_notifications(context, now, admin_id, recipients, settings.get("report_notification", {}))
    await _handle_maintenance_notifications(context, now, admin_id, recipients, settings.get("maintenance_notification", {}))
