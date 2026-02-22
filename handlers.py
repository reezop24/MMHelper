"""Text handlers for MM HELPER."""

from io import BytesIO
from datetime import date, timedelta
import json
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from menu import (
    MAIN_MENU_BUTTON_ADMIN_PANEL,
    MAIN_MENU_BUTTON_NEXT_EXCLUSIVE,
    MAIN_MENU_BUTTON_EXTRA,
    MAIN_MENU_BUTTON_MM_SETTING,
    MAIN_MENU_BUTTON_PROJECT_GROW,
    MAIN_MENU_BUTTON_RISK,
    MAIN_MENU_BUTTON_STATISTIC,
    MAIN_MENU_BUTTON_VIDEO_TUTORIAL,
    SUBMENU_ADMIN_BUTTON_BETA_RESET,
    SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING,
    SUBMENU_ADMIN_BUTTON_STOP_ALL_NOTIFICATION,
    SUBMENU_EXTRA_BUTTON_EDUCATION_VIDEO,
    SUBMENU_EXTRA_BUTTON_FIBO_DEWA,
    SUBMENU_EXTRA_BUTTON_FIBO_EXTENSION,
    SUBMENU_EXTRA_BUTTON_SCALPING_STRATEGY,
    SUBMENU_EXTRA_BUTTON_TRADING_ADVICE,
    SUBMENU_MM_BUTTON_BACK_MAIN,
    SUBMENU_MM_BUTTON_CORRECTION,
    SUBMENU_MM_BUTTON_SYSTEM_INFO,
    SUBMENU_PROJECT_BUTTON_ACHIEVEMENT,
    SUBMENU_PROJECT_BUTTON_MISSION,
    SUBMENU_PROJECT_BUTTON_MISSION_LOCKED,
    SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL,
    SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS,
    SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED,
    SUBMENU_STAT_BUTTON_MONTHLY_REPORTS,
    SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY,
    SUBMENU_STAT_BUTTON_WEEKLY_REPORTS,
    admin_panel_keyboard,
    extra_keyboard,
    is_admin_user,
    main_menu_keyboard,
    mm_helper_setting_keyboard,
    project_grow_keyboard,
    records_reports_keyboard,
)
from settings import (
    get_account_summary_webapp_url,
    get_balance_adjustment_webapp_url,
    get_date_override_webapp_url,
    get_initial_capital_reset_webapp_url,
    get_notification_setting_webapp_url,
    get_project_grow_mission_webapp_url,
    get_set_new_goal_webapp_url,
    get_tabung_update_webapp_url,
    get_tabung_progress_webapp_url,
    get_transaction_history_webapp_url,
    get_user_log_webapp_url,
    get_system_info_webapp_url,
)
from storage import (
    get_shared_db_health_snapshot,
    get_balance_adjustment_rules,
    can_open_project_grow_mission,
    get_current_balance_usd,
    get_current_profit_usd,
    get_initial_setup_summary,
    get_mission_progress_summary,
    get_monthly_profit_loss_usd,
    get_current_balance_as_of,
    get_tabung_balance_as_of,
    get_project_grow_goal_summary,
    get_project_grow_mission_state,
    get_project_grow_mission_status_text,
    get_tabung_start_date,
    get_tabung_progress_summary,
    get_tabung_update_state,
    get_transaction_history_records,
    get_transaction_history_records_between,
    get_tabung_balance_usd,
    get_month_start_balance_usd,
    get_total_balance_usd,
    get_weekly_frozen_daily_target_usd,
    get_weekly_profit_loss_usd,
    has_tabung_save_today,
    has_reached_daily_target_today,
    has_project_grow_goal,
    has_initial_setup,
    is_project_grow_goal_reached,
    current_user_date,
    get_beta_date_override,
    load_core_db,
    reset_all_data,
    stop_all_notification_settings,
    list_registered_user_logs_grouped_by_month,
)
from texts import (
    ACHIEVEMENT_OPENED_TEXT,
    ADMIN_PANEL_OPENED_TEXT,
    CORRECTION_OPENED_TEXT,
    EXTRA_OPENED_TEXT,
    MAIN_MENU_OPENED_TEXT,
    MISSION_OPENED_TEXT,
    MM_HELPER_SETTING_OPENED_TEXT,
    NOTIFICATION_SETTING_OPENED_TEXT,
    PROJECT_GROW_OPENED_TEXT,
    RISK_CALCULATOR_OPENED_TEXT,
    SET_NEW_GOAL_OPENED_TEXT,
    STATISTIC_OPENED_TEXT,
    SYSTEM_INFO_OPENED_TEXT,
    TABUNG_PROGRESS_OPENED_TEXT,
    TRANSACTION_HISTORY_OPENED_TEXT,
)
from ui import clear_last_screen, send_screen
from welcome import start

BETA_RESET_PASSWORD = "202210"
BETA_RESET_CB_BEGIN = "BETA_RESET_BEGIN"
BETA_RESET_CB_CANCEL = "BETA_RESET_CANCEL"
BETA_RESET_CB_CONFIRM = "BETA_RESET_CONFIRM"


def _pdf_escape(text: str) -> str:
    safe = re.sub(r"[^\x20-\x7E]", " ", str(text))
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_text(x: float, y: float, text: str, size: int = 10, bold: bool = False, rgb: tuple[float, float, float] = (0, 0, 0)) -> str:
    font = "F2" if bold else "F1"
    r, g, b = rgb
    return f"BT {r:.3f} {g:.3f} {b:.3f} rg /{font} {size} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(text)}) Tj ET"


def _pdf_rect(x: float, y: float, w: float, h: float, fill_rgb: tuple[float, float, float] | None = None, stroke_rgb: tuple[float, float, float] | None = None, line_w: float = 1.0) -> str:
    cmds: list[str] = []
    if fill_rgb is not None:
        fr, fg, fb = fill_rgb
        cmds.append(f"{fr:.3f} {fg:.3f} {fb:.3f} rg")
    if stroke_rgb is not None:
        sr, sg, sb = stroke_rgb
        cmds.append(f"{sr:.3f} {sg:.3f} {sb:.3f} RG {line_w:.2f} w")
    cmds.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
    if fill_rgb is not None and stroke_rgb is not None:
        cmds.append("B")
    elif fill_rgb is not None:
        cmds.append("f")
    else:
        cmds.append("S")
    return " ".join(cmds)


def _build_styled_pdf(commands: list[str]) -> bytes:
    stream = "\n".join(commands).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n",
        f"6 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(out)


def _trading_days_for_target_days(target_days: int) -> int:
    mapping = {30: 22, 90: 66, 180: 132}
    if target_days in mapping:
        return mapping[target_days]
    return max(1, round(float(target_days) * (22.0 / 30.0))) if target_days > 0 else 22


def _bounded_report_week(reference_date: date) -> tuple[date, date]:
    """Week window clipped to current month boundaries."""
    sunday_offset = (reference_date.weekday() + 1) % 7
    week_start = reference_date - timedelta(days=sunday_offset)
    week_end = week_start + timedelta(days=6)

    month_start = reference_date.replace(day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    if week_start < month_start:
        week_start = month_start
    if week_end > month_end:
        week_end = month_end
    return week_start, week_end


def _previous_closed_report_period(reference_date: date) -> tuple[date, date]:
    """Return immediately previous closed report period (month-clipped week)."""
    current_start, _ = _bounded_report_week(reference_date)
    prev_ref = current_start - timedelta(days=1)
    return _bounded_report_week(prev_ref)


def _month_range(reference_date: date) -> tuple[date, date]:
    month_start = reference_date.replace(day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return month_start, next_month - timedelta(days=1)


def _previous_closed_month_period(reference_date: date) -> tuple[date, date]:
    current_month_start, _ = _month_range(reference_date)
    prev_month_end = current_month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    return prev_month_start, prev_month_end


def _bounded_weeks_for_month(month_start: date, month_end: date) -> list[tuple[date, date]]:
    weeks: list[tuple[date, date]] = []
    cursor = month_start
    while cursor <= month_end:
        week_start, week_end = _bounded_report_week(cursor)
        if week_start < month_start:
            week_start = month_start
        if week_end > month_end:
            week_end = month_end
        weeks.append((week_start, week_end))
        cursor = week_end + timedelta(days=1)
    return weeks


def _build_weekly_report_pdf(user_id: int) -> tuple[bytes, str]:
    summary = get_initial_setup_summary(user_id)
    current_balance_now = get_current_balance_usd(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    total_balance = get_total_balance_usd(user_id)
    progress = get_tabung_progress_summary(user_id)
    goal = get_project_grow_goal_summary(user_id)
    today = current_user_date(user_id)
    week_start, week_end = _previous_closed_report_period(today)
    records = get_transaction_history_records_between(
        user_id,
        week_start,
        week_end,
        limit=None,
        include_hidden_adjustments=False,
    )
    db = load_core_db()
    user_obj = db.get("users", {}).get(str(user_id), {})
    sections = user_obj.get("sections", {}) if isinstance(user_obj, dict) else {}

    target_days = int(goal.get("target_days") or 0)
    trading_days = _trading_days_for_target_days(target_days)
    grow_target_remaining = float(progress.get("grow_target_usd") or 0.0)
    daily_target_usd = float(get_weekly_frozen_daily_target_usd(user_id, week_start))
    target_balance = float(goal.get("target_balance_usd") or 0.0)
    goal_baseline_balance = float(goal.get("current_balance_usd") or 0.0)
    grow_target_total = max(target_balance - goal_baseline_balance, 0.0)
    grow_target_achieved = max(min(grow_target_total - grow_target_remaining, grow_target_total), 0.0)
    remain_pct = (grow_target_remaining / grow_target_total * 100.0) if grow_target_total > 0 else 0.0
    goal_section = sections.get("project_grow_goal", {}) if isinstance(sections, dict) else {}
    goal_saved_date_raw = str(goal_section.get("saved_date") or "").strip() if isinstance(goal_section, dict) else ""
    goal_start_date: date | None = None
    if goal_saved_date_raw:
        try:
            goal_start_date = date.fromisoformat(goal_saved_date_raw)
        except ValueError:
            goal_start_date = None
    if goal_start_date is not None and week_start <= goal_start_date <= week_end:
        daily_target_usd = float(get_weekly_frozen_daily_target_usd(user_id, goal_start_date))

    setup_date = None
    try:
        setup_date = date.fromisoformat(str(summary.get("saved_date") or ""))
    except ValueError:
        setup_date = None
    is_first_month = bool(setup_date and setup_date > (week_start - timedelta(days=1)))
    if is_first_month:
        starting_balance = float(summary["initial_capital_usd"])
        starting_balance_label = "Opening Balance This Month (Initial Balance)"
    else:
        starting_balance = float(get_current_balance_as_of(user_id, week_start - timedelta(days=1)))
        starting_balance_label = "Opening Balance (Carry Forward)"

    section_total = {
        "deposit": 0.0,
        "withdrawal": 0.0,
        "trading": 0.0,
        "adjustment": 0.0,
        "tabung": 0.0,
    }
    section_count = {k: 0 for k in section_total}
    daily_trading_pl: dict[str, float] = {}
    for row in records:
        row_date_raw = str(row.get("date") or "").strip()
        try:
            row_date = date.fromisoformat(row_date_raw)
        except ValueError:
            continue
        if row_date < week_start or row_date > week_end:
            continue
        src = str(row.get("source") or "").strip().lower()
        src_map = {
            "deposit_activity": "deposit",
            "withdrawal_activity": "withdrawal",
            "trading_activity": "trading",
            "balance_adjustment": "adjustment",
            "tabung": "tabung",
            "deposit": "deposit",
            "withdrawal": "withdrawal",
            "trading": "trading",
            "adjustment": "adjustment",
        }
        src_norm = src_map.get(src, src)
        amount = float(row.get("amount_usd") or 0.0)
        if src_norm in section_total:
            section_total[src_norm] += amount
            section_count[src_norm] += 1
        if src_norm == "trading":
            daily_trading_pl[row_date_raw] = daily_trading_pl.get(row_date_raw, 0.0) + amount

    weekly_pl = sum(daily_trading_pl.values())

    tabung_records = []
    tabung_section = sections.get("tabung", {}) if isinstance(sections, dict) else {}
    tabung_data = tabung_section.get("data", {}) if isinstance(tabung_section, dict) else {}
    raw_tabung_records = tabung_data.get("records", []) if isinstance(tabung_data, dict) else []
    if isinstance(raw_tabung_records, list):
        tabung_records = [r for r in raw_tabung_records if isinstance(r, dict)]

    daily_tabung_save: dict[str, float] = {}
    for rec in tabung_records:
        mode = str(rec.get("mode") or "").strip().lower()
        if mode != "save":
            continue
        rec_date = str(rec.get("saved_date") or "").strip()
        try:
            d = date.fromisoformat(rec_date)
        except ValueError:
            continue
        if week_start <= d <= week_end:
            amt = abs(float(rec.get("amount_usd") or 0.0))
            daily_tabung_save[rec_date] = daily_tabung_save.get(rec_date, 0.0) + amt

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily_rows: list[tuple[str, str, str, str, str]] = []
    reached_count = 0
    cursor = week_start
    while cursor <= week_end:
        d_iso = cursor.isoformat()
        d_name = day_names[cursor.weekday()]
        pl = float(daily_trading_pl.get(d_iso, 0.0))
        tabung_saved = float(daily_tabung_save.get(d_iso, 0.0))
        if goal_start_date is not None and cursor < goal_start_date:
            status = "No Target"
            target_text = "-"
        elif cursor.weekday() >= 5:
            status = "No Trade Day"
            target_text = "-"
        elif daily_target_usd <= 0:
            status = "No Target"
            target_text = f"USD {daily_target_usd:.2f}"
        else:
            hit = pl > 0 and tabung_saved >= daily_target_usd
            status = "Reached" if hit else "Not Reached"
            target_text = f"USD {daily_target_usd:.2f}"
            if hit:
                reached_count += 1
        daily_rows.append((f"{d_name} {d_iso}", target_text, f"USD {pl:.2f}", f"USD {tabung_saved:.2f}", status))
        cursor += timedelta(days=1)

    remaining_calendar_days_now = 0
    remaining_trading_days_now = 0
    recalculated_daily_target_now = 0.0
    selected_target_days = max(target_days, 0)
    if grow_target_remaining > 0 and goal_start_date is not None and target_days > 0:
        goal_deadline = goal_start_date + timedelta(days=target_days)
        remaining_calendar_days_now = max((goal_deadline - today).days, 0)
        remaining_trading_days_now = _trading_days_for_target_days(remaining_calendar_days_now)
        if remaining_trading_days_now > 0:
            recalculated_daily_target_now = grow_target_remaining / float(remaining_trading_days_now)

    ending_balance = float(get_current_balance_as_of(user_id, week_end))
    tabung_balance = float(get_tabung_balance_as_of(user_id, week_end))
    total_balance = ending_balance + tabung_balance

    cmds: list[str] = []
    # Header
    cmds.append(_pdf_rect(35, 770, 525, 48, fill_rgb=(0.09, 0.20, 0.42)))
    cmds.append(_pdf_text(50, 798, "MM HELPER - WEEKLY REPORT", size=15, bold=True, rgb=(1, 1, 1)))
    cmds.append(_pdf_text(50, 782, f"User: {summary['name']}  |  Report Date: {today.isoformat()}", size=9, rgb=(0.90, 0.95, 1.0)))

    # Meta
    cmds.append(_pdf_rect(35, 730, 525, 28, fill_rgb=(0.95, 0.97, 1.0), stroke_rgb=(0.80, 0.85, 0.93), line_w=0.8))
    cmds.append(_pdf_text(48, 746, f"Report Period: {week_start.isoformat()} to {week_end.isoformat()}", size=9, bold=True, rgb=(0.16, 0.22, 0.33)))
    cmds.append(_pdf_text(320, 746, "Target reference: 22 trading days per month", size=8, rgb=(0.32, 0.38, 0.48)))

    # Starting balance section (full-width)
    cmds.append(_pdf_rect(35, 676, 525, 48, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 700, "Opening Balance", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    cmds.append(_pdf_text(48, 686, starting_balance_label, size=8, rgb=(0.28, 0.34, 0.44)))
    cmds.append(_pdf_text(340, 692, f"USD {starting_balance:.2f}", size=12, bold=True, rgb=(0.08, 0.17, 0.30)))

    # Daily target status table
    cmds.append(_pdf_rect(35, 420, 525, 248, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 652, "Daily Target Status by Day", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    cmds.append(_pdf_text(48, 638, f"Frozen Daily Target (Report Week): USD {daily_target_usd:.2f}", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(280, 638, f"Reached Days: {reached_count}", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))

    col_x = [48, 180, 290, 390, 485]
    col_titles = ["Day", "Daily Target", "Trading P/L", "Tabung", "Status"]
    cmds.append(_pdf_rect(45, 616, 505, 18, fill_rgb=(0.92, 0.95, 0.99), stroke_rgb=(0.84, 0.88, 0.93), line_w=0.5))
    for title, x in zip(col_titles, col_x):
        cmds.append(_pdf_text(x, 622, title, size=9, bold=True, rgb=(0.13, 0.22, 0.35)))

    y = 595
    for day_label, target_label, pl_label, tabung_label, status in daily_rows:
        cmds.append(_pdf_rect(45, y - 3, 505, 20, fill_rgb=(0.985, 0.988, 0.995), stroke_rgb=(0.90, 0.92, 0.95), line_w=0.3))
        pl_val = float(pl_label.replace("USD", "").strip())
        tabung_val = float(tabung_label.replace("USD", "").strip())
        pl_color = (0.65, 0.10, 0.10) if pl_val < 0 else (0.08, 0.25, 0.10)
        tabung_color = (0.08, 0.25, 0.10) if tabung_val > 0 else (0.18, 0.25, 0.36)
        status_color = (0.08, 0.40, 0.18) if status == "Reached" else (0.62, 0.18, 0.10) if status == "Not Reached" else (0.35, 0.35, 0.35)
        cmds.append(_pdf_text(col_x[0], y + 2, day_label, size=9, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(col_x[1], y + 2, target_label, size=9, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(col_x[2], y + 2, pl_label, size=9, bold=True, rgb=pl_color))
        cmds.append(_pdf_text(col_x[3], y + 2, tabung_label, size=9, bold=True, rgb=tabung_color))
        cmds.append(_pdf_text(col_x[4], y + 2, status, size=9, bold=True, rgb=status_color))
        y -= 25

    # Weekly transaction totals (full-width)
    cmds.append(_pdf_rect(35, 304, 525, 104, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 392, "Weekly Transaction Totals by Category", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    tx_headers = [("Category", 52), ("Count", 310), ("Total (USD)", 420)]
    cmds.append(_pdf_rect(45, 372, 505, 16, fill_rgb=(0.92, 0.95, 0.99), stroke_rgb=(0.84, 0.88, 0.93), line_w=0.5))
    for txt, x in tx_headers:
        cmds.append(_pdf_text(x, 377, txt, size=8, bold=True, rgb=(0.13, 0.22, 0.35)))
    tx_rows = [
        ("Deposit", section_count["deposit"], section_total["deposit"]),
        ("Withdrawal", section_count["withdrawal"], section_total["withdrawal"]),
        ("Trading (Net)", section_count["trading"], section_total["trading"]),
        ("Balance Adjustment", section_count["adjustment"], section_total["adjustment"]),
        ("Tabung", section_count["tabung"], section_total["tabung"]),
    ]
    y = 356
    for cat, cnt, amt in tx_rows:
        cmds.append(_pdf_rect(45, y - 2, 505, 13, fill_rgb=(0.985, 0.988, 0.995), stroke_rgb=(0.90, 0.92, 0.95), line_w=0.3))
        cmds.append(_pdf_text(52, y + 2, cat, size=8, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(315, y + 2, str(cnt), size=8, bold=True, rgb=(0.18, 0.25, 0.36)))
        amt_color = (0.65, 0.10, 0.10) if amt < 0 else (0.08, 0.25, 0.10)
        cmds.append(_pdf_text(420, y + 2, f"{amt:.2f}", size=8, bold=True, rgb=amt_color))
        y -= 14

    # Goal summary section
    cmds.append(_pdf_rect(35, 168, 525, 124, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 276, "Current Goal Summary (calculated from tabung grow only)", size=10, bold=True, rgb=(0.10, 0.20, 0.35)))
    cmds.append(_pdf_rect(45, 256, 505, 16, fill_rgb=(0.92, 0.95, 0.99), stroke_rgb=(0.84, 0.88, 0.93), line_w=0.5))
    cmds.append(_pdf_text(52, 261, "Item", size=9, bold=True, rgb=(0.13, 0.22, 0.35)))
    cmds.append(_pdf_text(340, 261, "Value", size=9, bold=True, rgb=(0.13, 0.22, 0.35)))

    goal_rows: list[tuple[str, str, tuple[float, float, float]]] = []
    if grow_target_total <= 0:
        goal_rows.append(("Goal Status", "New goal is not set yet", (0.62, 0.18, 0.10)))
    else:
        goal_rows.extend(
            [
                ("Selected Goal Duration", f"{selected_target_days} days", (0.18, 0.25, 0.36)),
                ("Remaining Grow Target", f"USD {grow_target_remaining:.2f}", (0.62, 0.18, 0.10) if grow_target_remaining > 0 else (0.08, 0.40, 0.18)),
                ("Remaining Goal Percentage", f"{remain_pct:.2f}%", (0.62, 0.18, 0.10) if remain_pct > 0 else (0.08, 0.40, 0.18)),
            ]
        )
        if grow_target_remaining <= 0:
            goal_rows.append(("New Daily Target", "Target already achieved", (0.08, 0.40, 0.18)))
        elif remaining_trading_days_now > 0:
            goal_rows.append(
                (
                    "New Daily Target",
                    f"USD {recalculated_daily_target_now:.2f} per day",
                    (0.18, 0.25, 0.36),
                )
            )
        else:
            goal_rows.append(("New Daily Target", "Goal period is near end / no trading days left", (0.62, 0.18, 0.10)))

    y = 240
    for metric, value, color in goal_rows[:5]:
        cmds.append(_pdf_rect(45, y - 2, 505, 16, fill_rgb=(0.985, 0.988, 0.995), stroke_rgb=(0.90, 0.92, 0.95), line_w=0.3))
        cmds.append(_pdf_text(52, y + 2, metric, size=9, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(340, y + 2, value, size=9, bold=True, rgb=color))
        y -= 18

    # Final summary with ending balance
    pnl_color = (0.65, 0.10, 0.10) if weekly_pl < 0 else (0.08, 0.25, 0.10)
    cmds.append(_pdf_rect(35, 70, 525, 92, fill_rgb=(0.96, 0.98, 1.0), stroke_rgb=(0.78, 0.84, 0.92), line_w=0.8))
    cmds.append(_pdf_text(48, 142, "Ending Balance", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    cmds.append(_pdf_text(52, 124, f"Weekly P/L: USD {weekly_pl:.2f}", size=9, bold=True, rgb=pnl_color))
    cmds.append(_pdf_text(52, 106, f"Tabung Balance: USD {tabung_balance:.2f}", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(52, 88, f"Capital: USD {total_balance:.2f}", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(340, 106, "Ending Balance", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(340, 88, f"USD {ending_balance:.2f}", size=12, bold=True, rgb=(0.08, 0.17, 0.30)))

    cmds.append(_pdf_text(48, 58, "Note: Summary generated from saved records for the selected period.", size=8, rgb=(0.34, 0.38, 0.45)))

    pdf_bytes = _build_styled_pdf(cmds)
    filename = f"weekly-report-{today.isoformat()}.pdf"
    return pdf_bytes, filename


def _build_monthly_report_pdf(user_id: int) -> tuple[bytes, str]:
    summary = get_initial_setup_summary(user_id)
    current_balance_now = get_current_balance_usd(user_id)
    today = current_user_date(user_id)
    month_start, month_end = _previous_closed_month_period(today)
    records = get_transaction_history_records_between(
        user_id,
        month_start,
        month_end,
        limit=None,
        include_hidden_adjustments=False,
    )
    db = load_core_db()
    user_obj = db.get("users", {}).get(str(user_id), {})
    sections = user_obj.get("sections", {}) if isinstance(user_obj, dict) else {}

    progress = get_tabung_progress_summary(user_id)
    goal = get_project_grow_goal_summary(user_id)
    target_days = int(goal.get("target_days") or 0)
    target_balance = float(goal.get("target_balance_usd") or 0.0)
    goal_baseline_balance = float(goal.get("current_balance_usd") or 0.0)
    grow_target_total = max(target_balance - goal_baseline_balance, 0.0)
    tabung_balance_end = float(get_tabung_balance_as_of(user_id, month_end))
    grow_target_remaining_end = max(grow_target_total - tabung_balance_end, 0.0)
    grow_target_achieved_end = max(min(grow_target_total - grow_target_remaining_end, grow_target_total), 0.0)
    achieved_pct_end = (grow_target_achieved_end / grow_target_total * 100.0) if grow_target_total > 0 else 0.0

    goal_section = sections.get("project_grow_goal", {}) if isinstance(sections, dict) else {}
    goal_saved_date_raw = str(goal_section.get("saved_date") or "").strip() if isinstance(goal_section, dict) else ""
    goal_start_date: date | None = None
    if goal_saved_date_raw:
        try:
            goal_start_date = date.fromisoformat(goal_saved_date_raw)
        except ValueError:
            goal_start_date = None
    days_left_month_end = 0
    if goal_start_date is not None and target_days > 0:
        elapsed_days_month_end = max((month_end - goal_start_date).days, 0)
        days_left_month_end = max(target_days - elapsed_days_month_end, 0)

    setup_date = None
    try:
        setup_date = date.fromisoformat(str(summary.get("saved_date") or ""))
    except ValueError:
        setup_date = None
    is_first_month = bool(setup_date and month_start <= setup_date <= month_end)
    if is_first_month:
        opening_balance = float(summary["initial_capital_usd"])
        opening_balance_label = "Opening Balance This Month (Initial Balance)"
    else:
        opening_balance = float(get_current_balance_as_of(user_id, month_start - timedelta(days=1)))
        opening_balance_label = "Opening Balance (Carry Forward)"

    section_total = {
        "deposit": 0.0,
        "withdrawal": 0.0,
        "trading": 0.0,
        "adjustment": 0.0,
        "tabung": 0.0,
    }
    section_count = {k: 0 for k in section_total}
    daily_trading_pl: dict[str, float] = {}
    for row in records:
        row_date_raw = str(row.get("date") or "").strip()
        try:
            row_date = date.fromisoformat(row_date_raw)
        except ValueError:
            continue
        if row_date < month_start or row_date > month_end:
            continue
        src = str(row.get("source") or "").strip().lower()
        src_map = {
            "deposit_activity": "deposit",
            "withdrawal_activity": "withdrawal",
            "trading_activity": "trading",
            "balance_adjustment": "adjustment",
            "tabung": "tabung",
            "deposit": "deposit",
            "withdrawal": "withdrawal",
            "trading": "trading",
            "adjustment": "adjustment",
        }
        src_norm = src_map.get(src, src)
        amount = float(row.get("amount_usd") or 0.0)
        if src_norm in section_total:
            section_total[src_norm] += amount
            section_count[src_norm] += 1
        if src_norm == "trading":
            daily_trading_pl[row_date_raw] = daily_trading_pl.get(row_date_raw, 0.0) + amount

    monthly_pl = sum(daily_trading_pl.values())

    tabung_records = []
    tabung_section = sections.get("tabung", {}) if isinstance(sections, dict) else {}
    tabung_data = tabung_section.get("data", {}) if isinstance(tabung_section, dict) else {}
    raw_tabung_records = tabung_data.get("records", []) if isinstance(tabung_data, dict) else []
    if isinstance(raw_tabung_records, list):
        tabung_records = [r for r in raw_tabung_records if isinstance(r, dict)]

    daily_tabung_save: dict[str, float] = {}
    for rec in tabung_records:
        mode = str(rec.get("mode") or "").strip().lower()
        if mode != "save":
            continue
        rec_date = str(rec.get("saved_date") or "").strip()
        try:
            d = date.fromisoformat(rec_date)
        except ValueError:
            continue
        if month_start <= d <= month_end:
            amt = abs(float(rec.get("amount_usd") or 0.0))
            daily_tabung_save[rec_date] = daily_tabung_save.get(rec_date, 0.0) + amt

    weekly_rows: list[tuple[str, str, str, str, str]] = []
    for wk_start, wk_end in _bounded_weeks_for_month(month_start, month_end):
        week_label = f"{wk_start.isoformat()} to {wk_end.isoformat()}"
        week_target = float(get_weekly_frozen_daily_target_usd(user_id, wk_start))
        week_pl = 0.0
        week_tabung = 0.0
        reached_days = 0
        trading_days = 0
        cursor = wk_start
        while cursor <= wk_end:
            d_iso = cursor.isoformat()
            if cursor.weekday() < 5:
                trading_days += 1
            day_pl = float(daily_trading_pl.get(d_iso, 0.0))
            day_tabung = float(daily_tabung_save.get(d_iso, 0.0))
            week_pl += day_pl
            week_tabung += day_tabung

            if goal_start_date is not None and cursor < goal_start_date:
                cursor += timedelta(days=1)
                continue
            if cursor.weekday() >= 5:
                cursor += timedelta(days=1)
                continue
            if week_target > 0 and day_pl > 0 and day_tabung >= week_target:
                reached_days += 1
            cursor += timedelta(days=1)

        if goal_start_date is not None and wk_end < goal_start_date:
            target_label = "No Target"
            hit_label = "-"
        elif week_target <= 0:
            target_label = "No Target"
            hit_label = "-"
        else:
            target_label = f"USD {week_target:.2f}"
            hit_label = f"{reached_days}/{trading_days}"
        weekly_rows.append(
            (
                week_label,
                target_label,
                f"USD {week_pl:.2f}",
                f"USD {week_tabung:.2f}",
                hit_label,
            )
        )

    ending_balance = float(get_current_balance_as_of(user_id, month_end))
    total_balance_end = ending_balance + tabung_balance_end

    cmds: list[str] = []
    cmds.append(_pdf_rect(35, 770, 525, 48, fill_rgb=(0.09, 0.20, 0.42)))
    cmds.append(_pdf_text(50, 798, "MM HELPER - MONTHLY REPORT", size=15, bold=True, rgb=(1, 1, 1)))
    cmds.append(_pdf_text(50, 782, f"User: {summary['name']}  |  Report Date: {today.isoformat()}", size=9, rgb=(0.90, 0.95, 1.0)))

    cmds.append(_pdf_rect(35, 730, 525, 28, fill_rgb=(0.95, 0.97, 1.0), stroke_rgb=(0.80, 0.85, 0.93), line_w=0.8))
    cmds.append(_pdf_text(48, 746, f"Report Period: {month_start.isoformat()} to {month_end.isoformat()}", size=9, bold=True, rgb=(0.16, 0.22, 0.33)))
    cmds.append(_pdf_text(320, 746, "Weekly split: Sunday-Saturday (month-clipped)", size=8, rgb=(0.32, 0.38, 0.48)))

    cmds.append(_pdf_rect(35, 676, 525, 48, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 700, "Opening Balance", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    cmds.append(_pdf_text(48, 686, opening_balance_label, size=8, rgb=(0.28, 0.34, 0.44)))
    cmds.append(_pdf_text(340, 692, f"USD {opening_balance:.2f}", size=12, bold=True, rgb=(0.08, 0.17, 0.30)))

    cmds.append(_pdf_rect(35, 500, 525, 166, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 650, "Grow Target Weekly Breakdown", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    col_x = [48, 215, 315, 395, 485]
    col_titles = ["Week", "Daily Target", "Trading P/L", "Tabung", "Reached"]
    cmds.append(_pdf_rect(45, 630, 505, 18, fill_rgb=(0.92, 0.95, 0.99), stroke_rgb=(0.84, 0.88, 0.93), line_w=0.5))
    for title, x in zip(col_titles, col_x):
        cmds.append(_pdf_text(x, 636, title, size=8, bold=True, rgb=(0.13, 0.22, 0.35)))

    y = 610
    for week_label, target_label, pl_label, tabung_label, reached_label in weekly_rows[:5]:
        cmds.append(_pdf_rect(45, y - 3, 505, 20, fill_rgb=(0.985, 0.988, 0.995), stroke_rgb=(0.90, 0.92, 0.95), line_w=0.3))
        pl_val = float(pl_label.replace("USD", "").strip())
        tabung_val = float(tabung_label.replace("USD", "").strip())
        pl_color = (0.65, 0.10, 0.10) if pl_val < 0 else (0.08, 0.25, 0.10)
        tabung_color = (0.08, 0.25, 0.10) if tabung_val > 0 else (0.18, 0.25, 0.36)
        cmds.append(_pdf_text(col_x[0], y + 2, week_label, size=8, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(col_x[1], y + 2, target_label, size=8, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(col_x[2], y + 2, pl_label, size=8, bold=True, rgb=pl_color))
        cmds.append(_pdf_text(col_x[3], y + 2, tabung_label, size=8, bold=True, rgb=tabung_color))
        cmds.append(_pdf_text(col_x[4], y + 2, reached_label, size=8, bold=True, rgb=(0.18, 0.25, 0.36)))
        y -= 25

    cmds.append(_pdf_rect(35, 368, 525, 122, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 474, "Monthly Transaction Totals by Category", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    tx_headers = [("Category", 52), ("Count", 310), ("Total (USD)", 420)]
    cmds.append(_pdf_rect(45, 454, 505, 16, fill_rgb=(0.92, 0.95, 0.99), stroke_rgb=(0.84, 0.88, 0.93), line_w=0.5))
    for txt, x in tx_headers:
        cmds.append(_pdf_text(x, 459, txt, size=8, bold=True, rgb=(0.13, 0.22, 0.35)))
    tx_rows = [
        ("Deposit", section_count["deposit"], section_total["deposit"]),
        ("Withdrawal", section_count["withdrawal"], section_total["withdrawal"]),
        ("Trading (Net)", section_count["trading"], section_total["trading"]),
        ("Balance Adjustment", section_count["adjustment"], section_total["adjustment"]),
        ("Tabung", section_count["tabung"], section_total["tabung"]),
    ]
    y = 438
    for cat, cnt, amt in tx_rows:
        cmds.append(_pdf_rect(45, y - 2, 505, 13, fill_rgb=(0.985, 0.988, 0.995), stroke_rgb=(0.90, 0.92, 0.95), line_w=0.3))
        cmds.append(_pdf_text(52, y + 2, cat, size=8, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(315, y + 2, str(cnt), size=8, bold=True, rgb=(0.18, 0.25, 0.36)))
        amt_color = (0.65, 0.10, 0.10) if amt < 0 else (0.08, 0.25, 0.10)
        cmds.append(_pdf_text(420, y + 2, f"{amt:.2f}", size=8, bold=True, rgb=amt_color))
        y -= 14

    cmds.append(_pdf_rect(35, 212, 525, 146, fill_rgb=(1, 1, 1), stroke_rgb=(0.82, 0.85, 0.90), line_w=0.8))
    cmds.append(_pdf_text(48, 342, "Grow Target Summary (Month End)", size=10, bold=True, rgb=(0.10, 0.20, 0.35)))
    summary_rows: list[tuple[str, str, tuple[float, float, float]]] = []
    if grow_target_total <= 0:
        summary_rows.append(("Goal Status", "New goal is not set yet", (0.62, 0.18, 0.10)))
    else:
        summary_rows.extend(
            [
                ("Selected Goal Duration", f"{target_days} days", (0.18, 0.25, 0.36)),
                ("Days Left (Month End)", f"{days_left_month_end} hari", (0.18, 0.25, 0.36)),
                ("Grow Target Total", f"USD {grow_target_total:.2f}", (0.18, 0.25, 0.36)),
                ("Achieved by Month End", f"USD {grow_target_achieved_end:.2f}", (0.08, 0.40, 0.18)),
                ("Remaining at Month End", f"USD {grow_target_remaining_end:.2f}", (0.62, 0.18, 0.10) if grow_target_remaining_end > 0 else (0.08, 0.40, 0.18)),
                ("Progress at Month End", f"{achieved_pct_end:.2f}%", (0.08, 0.40, 0.18)),
            ]
        )
    y = 322
    for metric, value, color in summary_rows[:6]:
        cmds.append(_pdf_rect(45, y - 2, 505, 16, fill_rgb=(0.985, 0.988, 0.995), stroke_rgb=(0.90, 0.92, 0.95), line_w=0.3))
        cmds.append(_pdf_text(52, y + 2, metric, size=9, rgb=(0.18, 0.25, 0.36)))
        cmds.append(_pdf_text(340, y + 2, value, size=9, bold=True, rgb=color))
        y -= 18

    pnl_color = (0.65, 0.10, 0.10) if monthly_pl < 0 else (0.08, 0.25, 0.10)
    cmds.append(_pdf_rect(35, 70, 525, 128, fill_rgb=(0.96, 0.98, 1.0), stroke_rgb=(0.78, 0.84, 0.92), line_w=0.8))
    cmds.append(_pdf_text(48, 178, "Ending Balance", size=11, bold=True, rgb=(0.10, 0.20, 0.35)))
    cmds.append(_pdf_text(52, 160, f"Monthly P/L: USD {monthly_pl:.2f}", size=9, bold=True, rgb=pnl_color))
    cmds.append(_pdf_text(52, 142, f"Tabung Balance at Month End: USD {tabung_balance_end:.2f}", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(52, 124, f"Capital at Month End: USD {total_balance_end:.2f}", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(52, 106, f"Current Balance (Now): USD {current_balance_now:.2f}", size=9, rgb=(0.32, 0.38, 0.48)))
    cmds.append(_pdf_text(340, 142, "Ending Balance (Month End)", size=9, bold=True, rgb=(0.08, 0.17, 0.30)))
    cmds.append(_pdf_text(340, 124, f"USD {ending_balance:.2f}", size=12, bold=True, rgb=(0.08, 0.17, 0.30)))

    cmds.append(_pdf_text(48, 58, "Note: Summary generated from saved records for the selected period.", size=8, rgb=(0.34, 0.38, 0.45)))

    pdf_bytes = _build_styled_pdf(cmds)
    filename = f"monthly-report-{month_start.strftime('%Y-%m')}.pdf"
    return pdf_bytes, filename


def _beta_reset_begin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Ya, teruskan", callback_data=BETA_RESET_CB_BEGIN)],
            [InlineKeyboardButton("❌ Batal", callback_data=BETA_RESET_CB_CANCEL)],
        ]
    )


def _beta_reset_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑️ Confirm BETA RESET", callback_data=BETA_RESET_CB_CONFIRM)],
            [InlineKeyboardButton("❌ Batal", callback_data=BETA_RESET_CB_CANCEL)],
        ]
    )


async def handle_admin_inline_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    await query.answer()
    cb = str(query.data or "").strip()
    if cb not in {
        BETA_RESET_CB_BEGIN,
        BETA_RESET_CB_CANCEL,
        BETA_RESET_CB_CONFIRM,
    }:
        return

    if not is_admin_user(user.id):
        await send_screen(
            context,
            query.message.chat_id,
            "❌ Akses ditolak.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    if cb == BETA_RESET_CB_CANCEL:
        context.user_data.pop("beta_reset_wait_password", None)
        context.user_data.pop("beta_reset_ready_confirm", None)
        await send_screen(
            context,
            query.message.chat_id,
            "BETA RESET dibatalkan.",
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        )
        return

    if cb == BETA_RESET_CB_BEGIN:
        context.user_data["beta_reset_wait_password"] = True
        context.user_data.pop("beta_reset_ready_confirm", None)
        await send_screen(
            context,
            query.message.chat_id,
            "Masukkan password BETA RESET.\n\nPassword hint: 6 digit.",
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        )
        return

    if not context.user_data.get("beta_reset_ready_confirm"):
        await send_screen(
            context,
            query.message.chat_id,
            "❌ Sesi reset tak sah. Mulakan semula dari butang BETA RESET.",
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        )
        return

    reset_all_data()
    context.user_data.clear()
    await clear_last_screen(context, query.message.chat_id)
    await start(update, context)


def _build_mm_setting_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    rules = get_balance_adjustment_rules(user_id)
    reset_url = get_initial_capital_reset_webapp_url(
        name=summary["name"],
        initial_capital=summary["initial_capital_usd"],
        current_balance=get_current_balance_usd(user_id),
        saved_date=summary["saved_date"],
        can_reset=True,
    )
    balance_adjustment_url = get_balance_adjustment_webapp_url(
        name=summary["name"],
        current_balance=get_current_balance_usd(user_id),
        saved_date=summary["saved_date"],
        can_adjust=rules["can_adjust"],
        used_this_month=rules["used_this_month"],
        window_open=rules["window_open"],
        window_label=rules["window_label"],
    )
    system_info_url = get_system_info_webapp_url()
    return mm_helper_setting_keyboard(reset_url, balance_adjustment_url, system_info_url)


def _build_admin_panel_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    notification_url = get_notification_setting_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
    )
    logs_by_month = list_registered_user_logs_grouped_by_month(limit_total=2000)
    compact_logs: dict[str, list[list[str]]] = {}
    for month_key, rows in logs_by_month.items():
        compact_rows: list[list[str]] = []
        for row in rows:
            compact_rows.append(
                [
                    str(row.get("name") or ""),
                    str(row.get("user_id") or ""),
                    str(row.get("telegram_username") or ""),
                    str(row.get("registered_at") or ""),
                ]
            )
        compact_logs[str(month_key)] = compact_rows
    user_logs_payload_json = json.dumps({"m": compact_logs}, ensure_ascii=False, separators=(",", ":"))
    current_override = get_beta_date_override(user_id)
    date_override_url = get_date_override_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        selected_user_id=user_id,
        current_enabled=bool(current_override.get("enabled")),
        current_override_date=str(current_override.get("override_date") or ""),
        current_updated_at=str(current_override.get("updated_at") or ""),
    )
    user_log_url = get_user_log_webapp_url(user_logs_payload_json)
    return admin_panel_keyboard(notification_url, date_override_url, user_log_url)


async def handle_db_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if not is_admin_user(user.id):
        await message.reply_text("❌ Access denied.")
        return

    snap = get_shared_db_health_snapshot()
    tables = snap.get("tables", {}) if isinstance(snap.get("tables"), dict) else {}

    def _c(name: str) -> str:
        value = tables.get(name)
        if value is None:
            return "-"
        return str(value)

    month_keys = snap.get("activity_month_keys", [])
    month_count = len(month_keys) if isinstance(month_keys, list) else 0
    text = (
        "📊 MMHELPER DB Health\n\n"
        f"Path: {snap.get('shared_db_path')}\n"
        f"Exists: {'yes' if snap.get('exists') else 'no'}\n"
        f"Size: {int(snap.get('size_bytes') or 0)} bytes\n"
        f"Core users: {int(snap.get('core_users') or 0)}\n"
        f"Activity months: {month_count}\n\n"
        "Tables:\n"
        f"- mmhelper_kv_state: {_c('mmhelper_kv_state')}\n"
        f"- mmhelper_activity_monthly: {_c('mmhelper_activity_monthly')}\n"
        f"- vip_whitelist: {_c('vip_whitelist')}\n"
        f"- sidebot_users: {_c('sidebot_users')}\n"
        f"- sidebot_submissions: {_c('sidebot_submissions')}\n"
        f"- sidebot_kv_state: {_c('sidebot_kv_state')}"
    )
    await message.reply_text(text)


def _build_records_reports_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    reference_date = current_user_date(user_id)
    current_balance = get_current_balance_usd(user_id)
    current_profit = get_current_profit_usd(user_id)
    total_balance = get_total_balance_usd(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    weekly = get_weekly_profit_loss_usd(user_id)
    monthly = get_monthly_profit_loss_usd(user_id)
    tabung_start = get_tabung_start_date(user_id)
    goal = get_project_grow_goal_summary(user_id)
    mission_state = get_project_grow_mission_state(user_id)
    mission = get_mission_progress_summary(user_id)
    target_capital = float(goal.get("target_balance_usd") or 0.0)
    grow_target_total = max(target_capital - float(goal.get("current_balance_usd") or 0.0), 0.0)
    grow_target = max(grow_target_total - tabung_balance, 0.0)
    target_label = str(goal.get("target_label") or "-")
    opening_balance = float(get_month_start_balance_usd(user_id, reference_date))
    opening_balance_label = "Opening Balance"
    try:
        setup_date = date.fromisoformat(str(summary.get("saved_date") or ""))
        if setup_date.year == reference_date.year and setup_date.month == reference_date.month:
            opening_balance_label = "Opening Balance (Initial)"
        else:
            opening_balance_label = "Opening Balance (Carry Forward)"
    except ValueError:
        opening_balance_label = "Opening Balance (Carry Forward)"
    account_summary_url = get_account_summary_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start,
        initial_balance_usd=opening_balance,
        current_balance_usd=current_balance,
        current_profit_usd=current_profit,
        capital_usd=total_balance,
        tabung_balance_usd=tabung_balance,
        weekly_pl_usd=weekly,
        monthly_pl_usd=monthly,
        target_capital_usd=target_capital,
        grow_target_usd=grow_target,
        target_label=target_label,
        mission_active=bool(mission_state.get("active")),
        mission_mode_level=str(mission.get("mode_level") or "-"),
        mission_status_text=str(mission.get("progress_count") or "-"),
        opening_balance_label=opening_balance_label,
    )
    tx_history_url = get_transaction_history_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        reference_date=reference_date.isoformat(),
        records_7d=get_transaction_history_records(user_id, days=7, limit=20),
        records_30d=get_transaction_history_records(user_id, days=30, limit=20),
    )
    return records_reports_keyboard(account_summary_url, tx_history_url)


def _build_project_grow_keyboard_for_user(user_id: int):
    summary = get_initial_setup_summary(user_id)
    goal_summary = get_project_grow_goal_summary(user_id)
    mission_state = get_project_grow_mission_state(user_id)
    tabung_balance = get_tabung_balance_usd(user_id)
    current_balance = get_current_balance_usd(user_id)
    mission_status = get_project_grow_mission_status_text(user_id)
    tabung_start_date = get_tabung_start_date(user_id)
    tabung_progress = get_tabung_progress_summary(user_id)
    grow_target_usd = tabung_progress["grow_target_usd"]
    total_balance = get_total_balance_usd(user_id)
    goal_reached = is_project_grow_goal_reached(user_id)
    tabung_state = get_tabung_update_state(user_id)
    daily_target_reached_today = has_reached_daily_target_today(user_id)
    tabung_saved_today = has_tabung_save_today(user_id)
    mission_url = get_project_grow_mission_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        target_balance_usd=goal_summary["target_balance_usd"],
        target_days=goal_summary["target_days"],
        target_label=goal_summary["target_label"],
        tabung_balance_usd=tabung_balance,
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        mission_active=mission_state["active"],
        mission_mode=mission_state["mode"],
        mission_started_date=mission_state["started_date"],
    )
    provisional_set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        has_goal=goal_summary["target_balance_usd"] > 0,
        goal_reached=goal_reached,
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=grow_target_usd,
        target_days=int(goal_summary["target_days"]),
        target_label=goal_summary["target_label"],
        tabung_update_url="",
        goal_baseline_balance_usd=float(goal_summary["current_balance_usd"]),
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=tabung_saved_today,
    )
    tabung_update_url = get_tabung_update_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        current_balance_usd=current_balance,
        tabung_balance_usd=tabung_balance,
        total_balance_usd=total_balance,
        target_balance_usd=float(goal_summary["target_balance_usd"]),
        goal_reached=goal_reached,
        emergency_left=int(tabung_state["emergency_left"]),
        set_new_goal_url=provisional_set_new_goal_url,
    )
    set_new_goal_url = get_set_new_goal_webapp_url(
        name=summary["name"],
        current_balance_usd=current_balance,
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        mission_status=mission_status,
        has_goal=goal_summary["target_balance_usd"] > 0,
        goal_reached=goal_reached,
        target_balance_usd=goal_summary["target_balance_usd"],
        grow_target_usd=grow_target_usd,
        target_days=int(goal_summary["target_days"]),
        target_label=goal_summary["target_label"],
        tabung_update_url=tabung_update_url,
        goal_baseline_balance_usd=float(goal_summary["current_balance_usd"]),
        daily_target_reached_today=daily_target_reached_today,
        has_tabung_save_today=tabung_saved_today,
    )
    tabung_progress_url = get_tabung_progress_webapp_url(
        name=summary["name"],
        saved_date=summary["saved_date"],
        tabung_start_date=tabung_start_date,
        tabung_balance_usd=tabung_progress["tabung_balance_usd"],
        grow_target_usd=tabung_progress["grow_target_usd"],
        days_left=tabung_progress["days_left"],
        days_left_label=tabung_progress["days_left_label"],
        grow_progress_pct=tabung_progress["grow_progress_pct"],
        weekly_grow_usd=tabung_progress["weekly_grow_usd"],
        monthly_grow_usd=tabung_progress["monthly_grow_usd"],
    )
    return project_grow_keyboard(
        set_new_goal_url=set_new_goal_url,
        mission_url=mission_url,
        can_open_mission=can_open_project_grow_mission(user_id),
        tabung_progress_url=tabung_progress_url,
        can_open_tabung_progress=has_project_grow_goal(user_id),
    )


async def handle_text_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not message.text or not user:
        return

    text = message.text.strip()

    if context.user_data.get("beta_reset_wait_password"):
        if not is_admin_user(user.id):
            context.user_data.pop("beta_reset_wait_password", None)
            context.user_data.pop("beta_reset_ready_confirm", None)
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        if text != BETA_RESET_PASSWORD:
            await send_screen(
                context,
                message.chat_id,
                "❌ Password salah. Cuba lagi atau tekan BETA RESET semula.",
                reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            )
            return

        context.user_data.pop("beta_reset_wait_password", None)
        context.user_data["beta_reset_ready_confirm"] = True
        await send_screen(
            context,
            message.chat_id,
            "Password betul ✅\n\nConfirm terakhir: tekan button bawah untuk reset semua data.",
            reply_markup=_beta_reset_confirm_keyboard(),
        )
        return

    if not has_initial_setup(user.id):
        await start(update, context)
        return

    if text == MAIN_MENU_BUTTON_ADMIN_PANEL:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        await send_screen(
            context,
            message.chat_id,
            ADMIN_PANEL_OPENED_TEXT,
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ADMIN_BUTTON_BETA_RESET:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        context.user_data.pop("beta_reset_wait_password", None)
        context.user_data.pop("beta_reset_ready_confirm", None)
        await send_screen(
            context,
            message.chat_id,
            "⚠️ BETA RESET akan padam SEMUA data semua user.\n\nTeruskan?",
            reply_markup=_beta_reset_begin_keyboard(),
        )
        return

    if text == SUBMENU_ADMIN_BUTTON_NOTIFICATION_SETTING:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        await send_screen(
            context,
            message.chat_id,
            NOTIFICATION_SETTING_OPENED_TEXT,
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_ADMIN_BUTTON_STOP_ALL_NOTIFICATION:
        if not is_admin_user(user.id):
            await send_screen(
                context,
                message.chat_id,
                "❌ Akses ditolak.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        ok = stop_all_notification_settings(user.id)
        if not ok:
            await send_screen(
                context,
                message.chat_id,
                "❌ Gagal stop notification. Cuba lagi.",
                reply_markup=_build_admin_panel_keyboard_for_user(user.id),
            )
            return

        await send_screen(
            context,
            message.chat_id,
            "✅ Semua notification dah dihentikan. User takkan terima mesej lagi sehingga admin set notification baru.",
            reply_markup=_build_admin_panel_keyboard_for_user(user.id),
        )
        return

    if text == MAIN_MENU_BUTTON_MM_SETTING:
        await send_screen(
            context,
            message.chat_id,
            MM_HELPER_SETTING_OPENED_TEXT,
            reply_markup=_build_mm_setting_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_RISK:
        await send_screen(
            context,
            message.chat_id,
            RISK_CALCULATOR_OPENED_TEXT,
            reply_markup=main_menu_keyboard(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_PROJECT_GROW:
        await send_screen(
            context,
            message.chat_id,
            PROJECT_GROW_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_STATISTIC:
        await send_screen(
            context,
            message.chat_id,
            STATISTIC_OPENED_TEXT,
            reply_markup=_build_records_reports_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == MAIN_MENU_BUTTON_EXTRA:
        await send_screen(
            context,
            message.chat_id,
            EXTRA_OPENED_TEXT,
            reply_markup=extra_keyboard(user.id),
            parse_mode="Markdown",
        )
        return

    if text in {
        SUBMENU_EXTRA_BUTTON_FIBO_DEWA,
        SUBMENU_EXTRA_BUTTON_SCALPING_STRATEGY,
        SUBMENU_EXTRA_BUTTON_TRADING_ADVICE,
        SUBMENU_EXTRA_BUTTON_EDUCATION_VIDEO,
    }:
        await send_screen(
            context,
            message.chat_id,
            "Coming soon. Feature ni masih dalam pembangunan.",
            reply_markup=extra_keyboard(user.id),
        )
        return

    if text == MAIN_MENU_BUTTON_VIDEO_TUTORIAL:
        await send_screen(
            context,
            message.chat_id,
            "Coming soon. Feature ni masih dalam pembangunan.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    if text == SUBMENU_MM_BUTTON_BACK_MAIN:
        await send_screen(
            context,
            message.chat_id,
            MAIN_MENU_OPENED_TEXT,
            reply_markup=main_menu_keyboard(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_MM_BUTTON_CORRECTION:
        await send_screen(
            context,
            message.chat_id,
            CORRECTION_OPENED_TEXT,
            reply_markup=_build_mm_setting_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_MM_BUTTON_SYSTEM_INFO:
        await send_screen(
            context,
            message.chat_id,
            SYSTEM_INFO_OPENED_TEXT,
            reply_markup=_build_mm_setting_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_STAT_BUTTON_TRANSACTION_HISTORY:
        await send_screen(
            context,
            message.chat_id,
            TRANSACTION_HISTORY_OPENED_TEXT,
            reply_markup=_build_records_reports_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_STAT_BUTTON_WEEKLY_REPORTS:
        summary = get_initial_setup_summary(user.id)
        today = current_user_date(user.id)
        prev_week_start, prev_week_end = _previous_closed_report_period(today)
        try:
            setup_date = date.fromisoformat(str(summary.get("saved_date") or ""))
        except ValueError:
            setup_date = None
        if setup_date is not None and setup_date > prev_week_end:
            await send_screen(
                context,
                message.chat_id,
                (
                    "Weekly report belum tersedia.\n"
                    "Report hanya untuk period sebelumnya yang sudah ditutup.\n"
                    f"Period tersedia seterusnya bermula selepas {prev_week_end.isoformat()}."
                ),
                reply_markup=_build_records_reports_keyboard_for_user(user.id),
            )
            return
        try:
            pdf_bytes, filename = _build_weekly_report_pdf(user.id)
            await context.bot.send_document(
                chat_id=message.chat_id,
                document=BytesIO(pdf_bytes),
                filename=filename,
                caption="Weekly report PDF siap. Ini ringkasan minggu semasa anda.",
            )
            await send_screen(
                context,
                message.chat_id,
                "Weekly report PDF dah dihantar. Boleh semak dan simpan fail tersebut.",
                reply_markup=main_menu_keyboard(user.id),
            )
        except Exception:
            await send_screen(
                context,
                message.chat_id,
                "Gagal jana Weekly report PDF. Cuba lagi sebentar.",
                reply_markup=main_menu_keyboard(user.id),
            )
        return

    if text == SUBMENU_STAT_BUTTON_MONTHLY_REPORTS:
        summary = get_initial_setup_summary(user.id)
        today = current_user_date(user.id)
        prev_month_start, prev_month_end = _previous_closed_month_period(today)
        try:
            setup_date = date.fromisoformat(str(summary.get("saved_date") or ""))
        except ValueError:
            setup_date = None
        if setup_date is not None and setup_date > prev_month_end:
            await send_screen(
                context,
                message.chat_id,
                (
                    "Monthly report belum tersedia.\n"
                    "Report hanya untuk bulan sebelumnya yang sudah ditutup.\n"
                    f"Bulan tersedia seterusnya bermula selepas {prev_month_end.isoformat()}."
                ),
                reply_markup=_build_records_reports_keyboard_for_user(user.id),
            )
            return
        try:
            pdf_bytes, filename = _build_monthly_report_pdf(user.id)
            await context.bot.send_document(
                chat_id=message.chat_id,
                document=BytesIO(pdf_bytes),
                filename=filename,
                caption="Monthly report PDF siap. Ini ringkasan bulan sebelumnya.",
            )
            await send_screen(
                context,
                message.chat_id,
                "Monthly report PDF dah dihantar. Boleh semak dan simpan fail tersebut.",
                reply_markup=main_menu_keyboard(user.id),
            )
        except Exception:
            await send_screen(
                context,
                message.chat_id,
                "Gagal jana Monthly report PDF. Cuba lagi sebentar.",
                reply_markup=main_menu_keyboard(user.id),
            )
        return

    if text == SUBMENU_PROJECT_BUTTON_SET_NEW_GOAL:
        await send_screen(
            context,
            message.chat_id,
            SET_NEW_GOAL_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_MISSION:
        await send_screen(
            context,
            message.chat_id,
            MISSION_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_MISSION_LOCKED:
        await send_screen(
            context,
            message.chat_id,
            "Mission masih locked. Pastikan balance tabung minimum USD 20.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS:
        await send_screen(
            context,
            message.chat_id,
            TABUNG_PROGRESS_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_TABUNG_PROGRESS_LOCKED:
        await send_screen(
            context,
            message.chat_id,
            "Tabung Progress masih locked. Set New Goal dulu baru boleh buka.",
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
        )
        return

    if text == SUBMENU_PROJECT_BUTTON_ACHIEVEMENT:
        await send_screen(
            context,
            message.chat_id,
            ACHIEVEMENT_OPENED_TEXT,
            reply_markup=_build_project_grow_keyboard_for_user(user.id),
            parse_mode="Markdown",
        )
        return
