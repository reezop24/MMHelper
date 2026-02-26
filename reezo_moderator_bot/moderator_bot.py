"""Reezo Moderator bot: anti-spam + basic admin tools."""

from __future__ import annotations

import json
import logging
import os
import re
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, WebAppInfo
from telegram.constants import ChatType
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

MENU_CHAT_ID = "📍 Current Chat ID"
MENU_MOD_STATUS = "🛡️ Moderation Status"
MENU_BROADCAST = "📢 Broadcast To Channel"
MENU_SETTINGS = "⚙️ Settings"
MENU_MODERATION_APP = "🧰 Moderation"
MENU_MOD_ADD = "➕ Add New Group/Channel"
MENU_MOD_TARGET_SETTINGS = "⚙️ Group/Channel Setting"
MENU_SET_GROUPS = "👥 Set Group Whitelist"
MENU_SET_CHANNEL = "📡 Set Default Channel"
MENU_VIEW_SETTINGS = "📋 View Settings"
MENU_BACK = "⬅️ Back"
MENU_CANCEL = "❌ Cancel"
MENU_BROADCAST_SEND = "✅ Send Broadcast"
MENU_BROADCAST_EDIT = "✏️ Edit Text"

SPAM_PATTERNS = [
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"t\\.me/", re.IGNORECASE),
    re.compile(r"join\\s+my\\s+channel", re.IGNORECASE),
    re.compile(r"guaranteed\\s+profit", re.IGNORECASE),
    re.compile(r"double\\s+your\\s+money", re.IGNORECASE),
    re.compile(r"whatsapp", re.IGNORECASE),
]

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def profile_duration_seconds(mode: str, custom_hours: int) -> int:
    if mode == "12h":
        return 12 * 3600
    if mode == "24h":
        return 24 * 3600
    if mode == "custom":
        return max(1, custom_hours) * 3600
    return 6 * 3600


def load_local_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"").strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_token() -> str:
    load_local_env()
    token = (os.getenv("REEZO_MODERATOR_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set REEZO_MODERATOR_BOT_TOKEN in reezo_moderator_bot/.env")
    return token


def get_admin_ids() -> set[int]:
    raw = (os.getenv("REEZO_MODERATOR_ADMIN_IDS") or "").strip()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def get_default_channel_id() -> int | None:
    settings = load_runtime_settings()
    channel_id = settings.get("default_channel_id")
    if isinstance(channel_id, int):
        return channel_id

    raw = (os.getenv("REEZO_MODERATOR_CHANNEL_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def get_channel_target_settings(channel_id: int | None) -> dict:
    if channel_id is None:
        return {}
    settings = load_runtime_settings()
    target_settings = settings.get("target_settings")
    if not isinstance(target_settings, dict):
        return {}
    one = target_settings.get(str(channel_id))
    if isinstance(one, dict):
        return one
    return {}


def get_channel_broadcast_presets(channel_id: int | None) -> list[dict]:
    one = get_channel_target_settings(channel_id)
    presets = one.get("broadcast_presets") if isinstance(one, dict) else None
    if not isinstance(presets, list):
        return []
    out = []
    for item in presets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        text = str(item.get("text") or "").strip()
        if not name or not text:
            continue
        out.append({"name": name, "text": text})
    return out


def get_moderation_webapp_url() -> str:
    url = (os.getenv("REEZO_MODERATOR_WEBAPP_URL") or "").strip()
    if url.startswith("https://"):
        return url
    return ""


def _serialize_webapp_state(settings: dict) -> str:
    payload = {
        "targets": settings.get("targets") or [],
        "target_settings": settings.get("target_settings") or {},
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def get_moderation_webapp_url_for(view: str) -> str:
    base = get_moderation_webapp_url()
    if not base:
        return ""
    settings = load_runtime_settings()
    encoded_state = _serialize_webapp_state(settings)
    parts = urlsplit(base)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["view"] = view
    query["state"] = encoded_state
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def get_allowed_group_ids() -> set[int]:
    settings = load_runtime_settings()
    targets = settings.get("targets")
    if isinstance(targets, list):
        out = {
            int(item["id"])
            for item in targets
            if isinstance(item, dict)
            and item.get("type") == "group"
            and isinstance(item.get("id"), int)
        }
        if out:
            return out
    group_ids = settings.get("allowed_group_ids")
    if isinstance(group_ids, list):
        out: set[int] = set()
        for value in group_ids:
            if isinstance(value, int):
                out.add(value)
        return out

    raw = (os.getenv("REEZO_MODERATOR_GROUP_IDS") or "").strip()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def load_runtime_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    data: dict = {}
    default_channel_id = raw.get("default_channel_id")
    if isinstance(default_channel_id, int):
        data["default_channel_id"] = default_channel_id
    group_ids = raw.get("allowed_group_ids")
    if isinstance(group_ids, list):
        data["allowed_group_ids"] = [int(x) for x in group_ids if isinstance(x, int)]
    moderation_enabled = raw.get("moderation_enabled")
    if isinstance(moderation_enabled, bool):
        data["moderation_enabled"] = moderation_enabled
    mode = raw.get("mode")
    if isinstance(mode, str) and mode in {"delete_and_ban", "delete_only", "ban_only"}:
        data["mode"] = mode
    flood = raw.get("flood_threshold_per_minute")
    if isinstance(flood, int) and flood > 0:
        data["flood_threshold_per_minute"] = flood
    auto_ban = raw.get("auto_ban_user_ids")
    if isinstance(auto_ban, list):
        data["auto_ban_user_ids"] = [int(x) for x in auto_ban if isinstance(x, int)]
    blacklisted = raw.get("blacklisted_user_ids")
    if isinstance(blacklisted, list):
        data["blacklisted_user_ids"] = [int(x) for x in blacklisted if isinstance(x, int)]
    targets = raw.get("targets")
    if isinstance(targets, list):
        normalized_targets = []
        for item in targets:
            if not isinstance(item, dict):
                continue
            target_type = str(item.get("type") or "").strip().lower()
            target_name = str(item.get("name") or "").strip()
            target_id = item.get("id")
            if target_type not in {"group", "channel"}:
                continue
            if not isinstance(target_id, int):
                continue
            if not target_name:
                target_name = str(target_id)
            normalized_targets.append({"id": target_id, "name": target_name, "type": target_type})
        data["targets"] = normalized_targets
    target_settings = raw.get("target_settings")
    if isinstance(target_settings, dict):
        normalized_target_settings: dict[str, dict] = {}
        for key, value in target_settings.items():
            if not isinstance(value, dict):
                continue
            if not str(key).lstrip("-").isdigit():
                continue
            one = {}
            if isinstance(value.get("moderation_enabled"), bool):
                one["moderation_enabled"] = value["moderation_enabled"]
            mode = value.get("mode")
            if isinstance(mode, str) and mode in {"delete_and_ban", "delete_only", "ban_only"}:
                one["mode"] = mode
            flood = value.get("flood_threshold_per_minute")
            if isinstance(flood, int) and flood > 0:
                one["flood_threshold_per_minute"] = flood
            auto_ban_user_ids = value.get("auto_ban_user_ids")
            if isinstance(auto_ban_user_ids, list):
                one["auto_ban_user_ids"] = [int(x) for x in auto_ban_user_ids if isinstance(x, int)]
            discussion_group_id = value.get("discussion_group_id")
            if isinstance(discussion_group_id, int):
                one["discussion_group_id"] = discussion_group_id
            comments_on_posts_enabled = value.get("comments_on_posts_enabled")
            if isinstance(comments_on_posts_enabled, bool):
                one["comments_on_posts_enabled"] = comments_on_posts_enabled
            broadcast_presets = value.get("broadcast_presets")
            if isinstance(broadcast_presets, list):
                cleaned_presets = []
                for item in broadcast_presets:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    text = str(item.get("text") or "").strip()
                    if not name or not text:
                        continue
                    cleaned_presets.append({"name": name, "text": text})
                one["broadcast_presets"] = cleaned_presets
            enabled_profile_ids = value.get("enabled_profile_ids")
            if isinstance(enabled_profile_ids, list):
                cleaned_ids = [int(x) for x in enabled_profile_ids if isinstance(x, int) and 1 <= int(x) <= 4]
                one["enabled_profile_ids"] = sorted(set(cleaned_ids))
            group_profiles = value.get("group_profiles")
            if isinstance(group_profiles, list):
                cleaned_profiles = []
                for item in group_profiles[:4]:
                    if not isinstance(item, dict):
                        continue
                    trigger_link_mode = str(item.get("trigger_link_mode") or "all_links")
                    if trigger_link_mode not in {"all_links", "specific_prefix"}:
                        trigger_link_mode = "all_links"
                    link_action = str(item.get("link_action") or item.get("action") or "delete")
                    if link_action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
                        link_action = "delete"
                    bg_toggle_mode = str(item.get("bg_toggle_mode") or "6h")
                    if bg_toggle_mode not in {"6h", "12h", "24h", "custom"}:
                        bg_toggle_mode = "6h"
                    custom_hours = item.get("bg_toggle_custom_hours")
                    if not isinstance(custom_hours, int) or custom_hours < 1:
                        custom_hours = 6
                    comment_rules = item.get("trigger_comment_rules")
                    if not isinstance(comment_rules, list):
                        legacy_comment = str(item.get("trigger_comment") or "").strip()
                        legacy_action = str(item.get("action") or "delete")
                        comment_rules = [{"text": legacy_comment, "action": legacy_action}] if legacy_comment else []
                    normalized_rules = []
                    for rule in comment_rules:
                        if not isinstance(rule, dict):
                            continue
                        token = str(rule.get("text") or "").strip()
                        rule_action = str(rule.get("action") or "delete")
                        if rule_action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
                            rule_action = "delete"
                        if not token:
                            continue
                        normalized_rules.append({"text": token, "action": rule_action})
                    cleaned_profiles.append(
                        {
                            "trigger_link_mode": trigger_link_mode,
                            "trigger_link_prefix": str(item.get("trigger_link_prefix") or "").strip(),
                            "link_action": link_action,
                            "trigger_comment_rules": normalized_rules,
                            "disable_comments_enabled": bool(item.get("disable_comments_enabled", False)),
                            "bg_toggle_mode": bg_toggle_mode,
                            "bg_toggle_custom_hours": custom_hours,
                        }
                    )
                if cleaned_profiles:
                    while len(cleaned_profiles) < 4:
                        cleaned_profiles.append(
                            {
                                "trigger_link_mode": "all_links",
                                "trigger_link_prefix": "",
                                "link_action": "delete",
                                "trigger_comment_rules": [],
                                "disable_comments_enabled": False,
                                "bg_toggle_mode": "6h",
                                "bg_toggle_custom_hours": 6,
                            }
                        )
                    one["group_profiles"] = cleaned_profiles
            saved_at = value.get("group_profiles_saved_at")
            if isinstance(saved_at, str) and saved_at:
                one["group_profiles_saved_at"] = saved_at
            normalized_target_settings[str(key)] = one
        data["target_settings"] = normalized_target_settings
    return data


def save_runtime_settings(data: dict) -> None:
    normalized_targets = []
    for item in data.get("targets") or []:
        if not isinstance(item, dict):
            continue
        target_id = item.get("id")
        target_name = str(item.get("name") or "").strip()
        target_type = str(item.get("type") or "").strip().lower()
        if not isinstance(target_id, int) or target_type not in {"group", "channel"}:
            continue
        if not target_name:
            target_name = str(target_id)
        normalized_targets.append({"id": target_id, "name": target_name, "type": target_type})
    normalized_target_settings = {}
    for key, value in (data.get("target_settings") or {}).items():
        if not isinstance(value, dict):
            continue
        if not str(key).lstrip("-").isdigit():
            continue
        out = {
            "moderation_enabled": bool(value.get("moderation_enabled", True)),
            "mode": str(value.get("mode") or "delete_and_ban"),
            "flood_threshold_per_minute": max(1, int(value.get("flood_threshold_per_minute") or 6)),
            "auto_ban_user_ids": [
                int(x) for x in (value.get("auto_ban_user_ids") or []) if isinstance(x, int)
            ],
        }
        discussion_group_id = value.get("discussion_group_id")
        if isinstance(discussion_group_id, int):
            out["discussion_group_id"] = discussion_group_id
        comments_on_posts_enabled = value.get("comments_on_posts_enabled")
        if isinstance(comments_on_posts_enabled, bool):
            out["comments_on_posts_enabled"] = comments_on_posts_enabled
        broadcast_presets = value.get("broadcast_presets")
        if isinstance(broadcast_presets, list):
            cleaned_presets = []
            for item in broadcast_presets:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                text = str(item.get("text") or "").strip()
                if not name or not text:
                    continue
                cleaned_presets.append({"name": name, "text": text})
            out["broadcast_presets"] = cleaned_presets
        enabled_profile_ids = value.get("enabled_profile_ids")
        if isinstance(enabled_profile_ids, list):
            cleaned_ids = [int(x) for x in enabled_profile_ids if isinstance(x, int) and 1 <= int(x) <= 4]
            out["enabled_profile_ids"] = sorted(set(cleaned_ids))
        group_profiles = value.get("group_profiles")
        if isinstance(group_profiles, list):
            cleaned_profiles = []
            for item in group_profiles[:4]:
                if not isinstance(item, dict):
                    continue
                trigger_link_mode = str(item.get("trigger_link_mode") or "all_links")
                if trigger_link_mode not in {"all_links", "specific_prefix"}:
                    trigger_link_mode = "all_links"
                link_action = str(item.get("link_action") or item.get("action") or "delete")
                if link_action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
                    link_action = "delete"
                bg_toggle_mode = str(item.get("bg_toggle_mode") or "6h")
                if bg_toggle_mode not in {"6h", "12h", "24h", "custom"}:
                    bg_toggle_mode = "6h"
                custom_hours = item.get("bg_toggle_custom_hours")
                if not isinstance(custom_hours, int) or custom_hours < 1:
                    custom_hours = 6
                comment_rules = item.get("trigger_comment_rules")
                if not isinstance(comment_rules, list):
                    legacy_comment = str(item.get("trigger_comment") or "").strip()
                    legacy_action = str(item.get("action") or "delete")
                    comment_rules = [{"text": legacy_comment, "action": legacy_action}] if legacy_comment else []
                normalized_rules = []
                for rule in comment_rules:
                    if not isinstance(rule, dict):
                        continue
                    token = str(rule.get("text") or "").strip()
                    if not token:
                        continue
                    rule_action = str(rule.get("action") or "delete")
                    if rule_action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
                        rule_action = "delete"
                    normalized_rules.append({"text": token, "action": rule_action})
                cleaned_profiles.append(
                    {
                        "trigger_link_mode": trigger_link_mode,
                        "trigger_link_prefix": str(item.get("trigger_link_prefix") or "").strip(),
                        "link_action": link_action,
                        "trigger_comment_rules": normalized_rules,
                        "disable_comments_enabled": bool(item.get("disable_comments_enabled", False)),
                        "bg_toggle_mode": bg_toggle_mode,
                        "bg_toggle_custom_hours": custom_hours,
                    }
                )
            if cleaned_profiles:
                while len(cleaned_profiles) < 4:
                    cleaned_profiles.append(
                        {
                            "trigger_link_mode": "all_links",
                            "trigger_link_prefix": "",
                            "link_action": "delete",
                            "trigger_comment_rules": [],
                            "disable_comments_enabled": False,
                            "bg_toggle_mode": "6h",
                            "bg_toggle_custom_hours": 6,
                        }
                    )
                out["group_profiles"] = cleaned_profiles
        group_profiles_saved_at = value.get("group_profiles_saved_at")
        if isinstance(group_profiles_saved_at, str) and group_profiles_saved_at:
            out["group_profiles_saved_at"] = group_profiles_saved_at
        normalized_target_settings[str(key)] = out
    payload = {
        "default_channel_id": data.get("default_channel_id"),
        "allowed_group_ids": data.get("allowed_group_ids") or [],
        "moderation_enabled": bool(data.get("moderation_enabled", True)),
        "mode": str(data.get("mode") or "delete_and_ban"),
        "flood_threshold_per_minute": int(data.get("flood_threshold_per_minute") or 6),
        "auto_ban_user_ids": data.get("auto_ban_user_ids") or [],
        "blacklisted_user_ids": data.get("blacklisted_user_ids") or [],
        "targets": normalized_targets,
        "target_settings": normalized_target_settings,
    }
    with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(MENU_SET_GROUPS)],
            [KeyboardButton(MENU_SET_CHANNEL)],
            [KeyboardButton(MENU_VIEW_SETTINGS)],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_CANCEL)],
        ],
        resize_keyboard=True,
    )


def moderation_app_keyboard() -> ReplyKeyboardMarkup:
    add_url = get_moderation_webapp_url_for("add")
    settings_url = get_moderation_webapp_url_for("settings")
    add_btn = KeyboardButton(MENU_MOD_ADD, web_app=WebAppInfo(url=add_url)) if add_url else KeyboardButton(MENU_MOD_ADD)
    settings_btn = (
        KeyboardButton(MENU_MOD_TARGET_SETTINGS, web_app=WebAppInfo(url=settings_url))
        if settings_url
        else KeyboardButton(MENU_MOD_TARGET_SETTINGS)
    )
    return ReplyKeyboardMarkup(
        [
            [add_btn],
            [settings_btn],
            [KeyboardButton(MENU_BACK), KeyboardButton(MENU_CANCEL)],
        ],
        resize_keyboard=True,
    )


def main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(MENU_CHAT_ID)], [KeyboardButton(MENU_MOD_STATUS)]]
    if is_admin:
        rows.append([KeyboardButton(MENU_MODERATION_APP)])
        rows.append([KeyboardButton(MENU_BROADCAST)])
        rows.append([KeyboardButton(MENU_SETTINGS)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def looks_like_spam(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    hits = 0
    for pat in SPAM_PATTERNS:
        if pat.search(lowered):
            hits += 1
    if hits >= 2:
        return True
    if len(lowered) > 400 and hits >= 1:
        return True
    if lowered.count("@") >= 5:
        return True
    if re.search(r"(.)\\1{12,}", lowered):
        return True
    return False


def extract_links(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"(https?://\S+|t\.me/\S+)", text, flags=re.IGNORECASE)


def add_blacklisted_user(user_id: int) -> None:
    settings = load_runtime_settings()
    existing = settings.get("blacklisted_user_ids")
    if not isinstance(existing, list):
        existing = []
    ids = set(int(x) for x in existing if isinstance(x, int))
    ids.add(int(user_id))
    settings["blacklisted_user_ids"] = sorted(ids)
    save_runtime_settings(settings)


async def apply_profile_action(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    msg_id: int,
    user_id: int,
    action: str,
    reason: str,
    chance_key: str,
) -> None:
    one_chance = context.bot_data.setdefault("one_chance_tracker", {})
    base_reason = reason.strip() or "trigger"
    if action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
        action = "delete"

    if action == "delete":
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            logger.exception("Failed delete (profile action) chat_id=%s msg_id=%s", chat_id, msg_id)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Message deleted (`{base_reason}`).",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Failed sending group action message chat_id=%s", chat_id)
        return

    if action == "delete_and_ban":
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            logger.exception("Failed delete before ban chat_id=%s msg_id=%s", chat_id, msg_id)
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id, revoke_messages=True)
            add_blacklisted_user(user_id)
        except Exception:
            logger.exception("Failed ban (profile action) chat_id=%s user_id=%s", chat_id, user_id)
            return
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 User `{user_id}` deleted + banned (`{base_reason}`). Kalau ban kesilapan, sila hubungi admin.",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Failed sending group action message chat_id=%s", chat_id)
        return

    count = int(one_chance.get(chance_key, 0)) + 1
    one_chance[chance_key] = count
    if count == 1:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            logger.exception("Failed delete (one chance) chat_id=%s msg_id=%s", chat_id, msg_id)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ User `{user_id}` warning 1/1. Message deleted (`{base_reason}`). Repeat = ban.",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Failed sending one-chance warning chat_id=%s", chat_id)
        return

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        logger.exception("Failed delete on second chance chat_id=%s msg_id=%s", chat_id, msg_id)
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id, revoke_messages=True)
        add_blacklisted_user(user_id)
    except Exception:
        logger.exception("Failed ban on second chance chat_id=%s user_id=%s", chat_id, user_id)
        return
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚫 User `{user_id}` repeated offense. Deleted + banned (`{base_reason}`). Kalau ban kesilapan, sila hubungi admin.",
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Failed sending second-chance ban message chat_id=%s", chat_id)


async def is_chat_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in {"administrator", "creator"}
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return
    if user.id not in get_admin_ids():
        return
    is_admin = user.id in get_admin_ids()
    await msg.reply_text(
        "Reezo Moderator active. Pilih menu.",
        reply_markup=main_keyboard(is_admin),
    )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat:
        return
    if chat.type == ChatType.CHANNEL:
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"chat_id: `{chat.id}`\\nchat_type: `{chat.type}`",
            parse_mode="Markdown",
        )
        return
    if not user:
        return
    if user.id not in get_admin_ids():
        return
    await msg.reply_text(f"chat_id: `{chat.id}`\\nchat_type: `{chat.type}`", parse_mode="Markdown")


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return
    username = f"@{user.username}" if user.username else "-"
    await msg.reply_text(
        f"user_id: `{user.id}`\nusername: `{username}`",
        parse_mode="Markdown",
    )


def extract_forwarded_channel_info(message) -> tuple[int | None, str | None]:
    forward_from_chat = getattr(message, "forward_from_chat", None)
    if forward_from_chat is not None and getattr(forward_from_chat, "type", None) == ChatType.CHANNEL:
        return int(forward_from_chat.id), str(getattr(forward_from_chat, "title", "") or "")
    forward_origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(forward_origin, "chat", None)
    if origin_chat is not None and getattr(origin_chat, "type", None) == ChatType.CHANNEL:
        return int(origin_chat.id), str(getattr(origin_chat, "title", "") or "")
    return None, None


async def forwarded_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat:
        return
    if chat.type != ChatType.PRIVATE:
        return
    channel_id, title = extract_forwarded_channel_info(msg)
    if channel_id is None:
        if getattr(msg, "forward_origin", None) is not None or getattr(msg, "forward_date", None) is not None:
            await msg.reply_text(
                "Tak dapat baca channel id dari forward ini.\n"
                "Kemungkinan channel aktifkan protected content.\n"
                "Guna `/channelid <link t.me/c/...>` atau `/channelid @username`.",
                parse_mode="Markdown",
            )
        return
    title_text = title if title else "-"
    await msg.reply_text(
        f"forwarded_channel_id: `{channel_id}`\nchannel_title: `{title_text}`",
        parse_mode="Markdown",
    )


async def channel_id_from_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return
    if user.id not in get_admin_ids():
        return
    args = context.args or []
    if not args:
        await msg.reply_text(
            "Guna:\n"
            "- `/channelid https://t.me/c/1234567890/11`\n"
            "- `/channelid @channelusername`",
            parse_mode="Markdown",
        )
        return
    raw = " ".join(args).strip()
    raw = raw.replace("https://", "").replace("http://", "").strip()
    # Parse t.me/c/<id>/<msg> -> channel_id = -100<id>
    m = re.search(r"(?:t\.me/)?c/(\d+)", raw, flags=re.IGNORECASE)
    if m:
        channel_id = int(f"-100{m.group(1)}")
        await msg.reply_text(f"channel_id: {channel_id}")
        return
    # Parse t.me/<username>/<post_id>
    m_user = re.search(r"(?:t\.me/)?([A-Za-z0-9_]{5,})/\d+", raw)
    if m_user:
        username = "@" + m_user.group(1)
        try:
            chat = await context.bot.get_chat(username)
        except Exception:
            await msg.reply_text("Tak dapat resolve username channel dari link.")
            return
        await msg.reply_text(f"channel_id: {chat.id}\nchat_type: {chat.type}")
        return
    # Parse @username by get_chat
    if raw.startswith("@"):
        try:
            chat = await context.bot.get_chat(raw)
        except Exception:
            await msg.reply_text("Tak dapat resolve username channel.")
            return
        await msg.reply_text(f"channel_id: {chat.id}\nchat_type: {chat.type}")
        return
    await msg.reply_text("Format tak dikenali. Hantar link `t.me/c/...` atau `@username`.", parse_mode="Markdown")


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user:
        return
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return

    settings = load_runtime_settings()
    if settings.get("moderation_enabled") is False:
        return

    allowed_groups = get_allowed_group_ids()
    if allowed_groups and chat.id not in allowed_groups:
        return

    target_settings = settings.get("target_settings") if isinstance(settings.get("target_settings"), dict) else {}
    one_target = target_settings.get(str(chat.id)) if isinstance(target_settings, dict) else {}
    if not isinstance(one_target, dict):
        one_target = {}

    # NOTE:
    # comments_on_posts_enabled is currently metadata only.
    # Telegram Bot API does not provide a direct per-post discussion toggle here.

    # Group lock window from profile settings: if active, delete comments for selected duration.
    profiles = one_target.get("group_profiles")
    enabled_profile_ids = one_target.get("enabled_profile_ids")
    saved_at_raw = one_target.get("group_profiles_saved_at")
    if isinstance(profiles, list) and isinstance(enabled_profile_ids, list) and isinstance(saved_at_raw, str):
        try:
            start_ts = datetime.fromisoformat(saved_at_raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            start_ts = 0.0
        now_ts = datetime.now(timezone.utc).timestamp()
        for pid in enabled_profile_ids:
            if not isinstance(pid, int) or pid < 1 or pid > len(profiles):
                continue
            profile = profiles[pid - 1]
            if not isinstance(profile, dict):
                continue
            if not bool(profile.get("disable_comments_enabled", False)):
                continue
            bg_mode = str(profile.get("bg_toggle_mode") or "6h")
            custom_hours = profile.get("bg_toggle_custom_hours")
            if not isinstance(custom_hours, int):
                custom_hours = 6
            duration = profile_duration_seconds(bg_mode, custom_hours)
            if start_ts <= 0 or now_ts > start_ts + duration:
                continue
            try:
                await context.bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
            except Exception:
                logger.exception("Failed deleting message in disable-comment window chat_id=%s msg_id=%s", chat.id, msg.message_id)
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"🔒 Comment disabled by profile {pid} window. Message deleted.",
                )
            except Exception:
                logger.exception("Failed sending disable-comment action message chat_id=%s", chat.id)
            return

    text = (msg.text or msg.caption or "").strip()
    user_is_admin = await is_chat_admin(context, chat.id, user.id)

    # Group trigger profiles (link/comment rules).
    if text and not user_is_admin and isinstance(profiles, list) and isinstance(enabled_profile_ids, list):
        links = extract_links(text)
        text_lower = text.lower()
        for pid in enabled_profile_ids:
            if not isinstance(pid, int) or pid < 1 or pid > len(profiles):
                continue
            p = profiles[pid - 1]
            if not isinstance(p, dict):
                continue

            link_mode = str(p.get("trigger_link_mode") or "all_links")
            link_prefix = str(p.get("trigger_link_prefix") or "").strip().lower()
            link_action = str(p.get("link_action") or "delete")
            link_hit = False
            if link_mode == "all_links":
                link_hit = bool(links)
            elif link_mode == "specific_prefix" and link_prefix:
                link_hit = any(url.lower().startswith(link_prefix) for url in links)
            if link_hit:
                chance_key = f"{chat.id}:{user.id}:p{pid}:link"
                await apply_profile_action(
                    context=context,
                    chat_id=chat.id,
                    msg_id=msg.message_id,
                    user_id=user.id,
                    action=link_action,
                    reason=f"profile {pid} link",
                    chance_key=chance_key,
                )
                return

            rules = p.get("trigger_comment_rules")
            if not isinstance(rules, list):
                single_comment = str(p.get("trigger_comment") or "").strip()
                if single_comment:
                    rules = [{"text": single_comment, "action": str(p.get("action") or "delete")}]
                else:
                    rules = []
            for ridx, rule in enumerate(rules, start=1):
                if not isinstance(rule, dict):
                    continue
                token = str(rule.get("text") or "").strip().lower()
                if not token:
                    continue
                if token not in text_lower:
                    continue
                action = str(rule.get("action") or "delete")
                chance_key = f"{chat.id}:{user.id}:p{pid}:c{ridx}:{token}"
                await apply_profile_action(
                    context=context,
                    chat_id=chat.id,
                    msg_id=msg.message_id,
                    user_id=user.id,
                    action=action,
                    reason=f"profile {pid} comment:{token}",
                    chance_key=chance_key,
                )
                return

    mode = str(one_target.get("mode") or settings.get("mode") or "delete_and_ban")
    flood_threshold = int(one_target.get("flood_threshold_per_minute") or settings.get("flood_threshold_per_minute") or 6)
    auto_ban_raw = one_target.get("auto_ban_user_ids")
    if not isinstance(auto_ban_raw, list):
        auto_ban_raw = settings.get("auto_ban_user_ids") or []
    auto_ban_user_ids = set(int(x) for x in auto_ban_raw if isinstance(x, int))
    moderation_enabled = one_target.get("moderation_enabled")
    if isinstance(moderation_enabled, bool) and not moderation_enabled:
        return

    # Immediate ban list check.
    if user.id in auto_ban_user_ids and not await is_chat_admin(context, chat.id, user.id):
        if mode in {"delete_and_ban", "delete_only"}:
            try:
                await context.bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
            except Exception:
                logger.exception("Failed deleting message from auto-ban user chat_id=%s msg_id=%s", chat.id, msg.message_id)
        if mode in {"delete_and_ban", "ban_only"}:
            try:
                await context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id, revoke_messages=True)
                add_blacklisted_user(user.id)
            except Exception:
                logger.exception("Failed banning auto-ban user chat_id=%s user_id=%s", chat.id, user.id)
            else:
                try:
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"🚫 User `{user.id}` banned by auto-ban rule. Kalau ban kesilapan, sila hubungi admin.",
                        parse_mode="Markdown",
                    )
                except Exception:
                    logger.exception("Failed sending auto-ban group message chat_id=%s", chat.id)
        return

    # Flood control per user per chat.
    now_ts = datetime.now(timezone.utc).timestamp()
    bucket = context.bot_data.setdefault("flood_bucket", {})
    key = f"{chat.id}:{user.id}"
    recent = [t for t in bucket.get(key, []) if now_ts - t <= 60]
    recent.append(now_ts)
    bucket[key] = recent
    is_flood = len(recent) >= max(1, flood_threshold)

    spam_text = msg.text or msg.caption or ""
    if not looks_like_spam(spam_text) and not is_flood:
        return

    if user_is_admin:
        return

    if mode in {"delete_and_ban", "delete_only"}:
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
        except Exception:
            logger.exception("Failed deleting spam message chat_id=%s msg_id=%s", chat.id, msg.message_id)

    if mode in {"delete_and_ban", "ban_only"}:
        try:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id, revoke_messages=True)
            add_blacklisted_user(user.id)
        except Exception:
            logger.exception("Failed banning spam user chat_id=%s user_id=%s", chat.id, user.id)
            return

    reason = f"Auto-kick spam at {datetime.now(timezone.utc).isoformat()}"
    try:
        action_text = "moderated"
        if mode == "delete_only":
            action_text = "message deleted"
        elif mode == "ban_only":
            action_text = "user banned. Kalau ban kesilapan, sila hubungi admin."
        else:
            action_text = "user banned + message deleted. Kalau ban kesilapan, sila hubungi admin."
        await context.bot.send_message(chat_id=chat.id, text=f"🚫 User `{user.id}` {action_text}. {reason}", parse_mode="Markdown")
    except Exception:
        logger.exception("Failed sending moderation notification")


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not msg.web_app_data or not user:
        return
    if user.id not in get_admin_ids():
        return
    try:
        payload = json.loads(msg.web_app_data.data)
    except json.JSONDecodeError:
        await msg.reply_text("❌ WebApp payload invalid.")
        return
    payload_type = str(payload.get("type") or "").strip()
    if payload_type == "reezo_moderator_back_to_menu":
        await msg.reply_text("Back to main menu.", reply_markup=main_keyboard(True))
        return

    if payload_type == "reezo_moderator_target_add":
        target_type = str(payload.get("target_type") or "").strip().lower()
        target_name = str(payload.get("target_name") or "").strip()
        target_id = payload.get("target_id")
        if target_type not in {"group", "channel"}:
            await msg.reply_text("❌ target_type mesti `group` atau `channel`.")
            return
        if not isinstance(target_id, int):
            await msg.reply_text("❌ target_id mesti integer.")
            return
        if target_id >= 0:
            await msg.reply_text("❌ target_id mesti nombor negatif (`-100...`).")
            return
        if not target_name:
            await msg.reply_text("❌ target_name wajib diisi.")
            return

        settings = load_runtime_settings()
        targets = settings.get("targets")
        if not isinstance(targets, list):
            targets = []
        replaced = False
        for item in targets:
            if isinstance(item, dict) and item.get("id") == target_id:
                item["name"] = target_name
                item["type"] = target_type
                replaced = True
                break
        if not replaced:
            targets.append({"id": target_id, "name": target_name, "type": target_type})
        settings["targets"] = targets
        save_runtime_settings(settings)
        action = "updated" if replaced else "added"
        await msg.reply_text(
            f"✅ {target_type.title()} `{target_name}` ({target_id}) {action}.",
            parse_mode="Markdown",
            reply_markup=moderation_app_keyboard(),
        )
        return

    if payload_type == "reezo_moderator_target_settings_save":
        target_id = payload.get("target_id")
        target_type = str(payload.get("target_type") or "").strip().lower()

        if target_type not in {"group", "channel"}:
            await msg.reply_text("❌ target_type invalid.")
            return
        if not isinstance(target_id, int):
            await msg.reply_text("❌ target_id invalid.")
            return

        settings = load_runtime_settings()
        targets = settings.get("targets") if isinstance(settings.get("targets"), list) else []
        matched_target = None
        for item in targets:
            if isinstance(item, dict) and item.get("id") == target_id and item.get("type") == target_type:
                matched_target = item
                break
        if not matched_target:
            await msg.reply_text("❌ Target belum wujud. Guna Add New Group/Channel dulu.")
            return

        target_settings = settings.get("target_settings")
        if not isinstance(target_settings, dict):
            target_settings = {}
        existing = target_settings.get(str(target_id))
        if not isinstance(existing, dict):
            existing = {}

        if target_type == "group":
            raw_profiles = payload.get("group_profiles")
            enabled_profile_ids = payload.get("enabled_profile_ids")
            if not isinstance(raw_profiles, list):
                await msg.reply_text("❌ group_profiles invalid.")
                return
            if not isinstance(enabled_profile_ids, list):
                await msg.reply_text("❌ enabled_profile_ids invalid.")
                return

            cleaned_profiles: list[dict] = []
            for idx, item in enumerate(raw_profiles[:4], start=1):
                if not isinstance(item, dict):
                    await msg.reply_text(f"❌ profile {idx} invalid.")
                    return
                trigger_link_mode = str(item.get("trigger_link_mode") or "all_links")
                if trigger_link_mode not in {"all_links", "specific_prefix"}:
                    trigger_link_mode = "all_links"
                link_action = str(item.get("link_action") or item.get("action") or "delete")
                if link_action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
                    link_action = "delete"
                bg_toggle_mode = str(item.get("bg_toggle_mode") or "6h")
                if bg_toggle_mode not in {"6h", "12h", "24h", "custom"}:
                    bg_toggle_mode = "6h"
                custom_hours = item.get("bg_toggle_custom_hours")
                if not isinstance(custom_hours, int) or custom_hours < 1:
                    custom_hours = 6
                comment_rules = item.get("trigger_comment_rules")
                if not isinstance(comment_rules, list):
                    legacy_comment = str(item.get("trigger_comment") or "").strip()
                    legacy_action = str(item.get("action") or "delete")
                    comment_rules = [{"text": legacy_comment, "action": legacy_action}] if legacy_comment else []
                normalized_rules = []
                for rule in comment_rules:
                    if not isinstance(rule, dict):
                        continue
                    token = str(rule.get("text") or "").strip()
                    if not token:
                        continue
                    rule_action = str(rule.get("action") or "delete")
                    if rule_action not in {"delete", "delete_and_ban", "delete_plus_one_chance"}:
                        rule_action = "delete"
                    normalized_rules.append({"text": token, "action": rule_action})
                cleaned_profiles.append(
                    {
                        "trigger_link_mode": trigger_link_mode,
                        "trigger_link_prefix": str(item.get("trigger_link_prefix") or "").strip(),
                        "link_action": link_action,
                        "trigger_comment_rules": normalized_rules,
                        "disable_comments_enabled": bool(item.get("disable_comments_enabled", False)),
                        "bg_toggle_mode": bg_toggle_mode,
                        "bg_toggle_custom_hours": custom_hours,
                    }
                )
            while len(cleaned_profiles) < 4:
                cleaned_profiles.append(
                    {
                        "trigger_link_mode": "all_links",
                        "trigger_link_prefix": "",
                        "link_action": "delete",
                        "trigger_comment_rules": [],
                        "disable_comments_enabled": False,
                        "bg_toggle_mode": "6h",
                        "bg_toggle_custom_hours": 6,
                    }
                )
            cleaned_enabled = sorted(
                set(int(x) for x in enabled_profile_ids if isinstance(x, int) and 1 <= int(x) <= 4)
            )
            if not cleaned_enabled:
                await msg.reply_text("❌ Pilih sekurang-kurangnya 1 profile.")
                return

            existing["group_profiles"] = cleaned_profiles
            existing["enabled_profile_ids"] = cleaned_enabled
            existing["group_profiles_saved_at"] = utc_now_iso()
            target_settings[str(target_id)] = existing
            settings["target_settings"] = target_settings
            save_runtime_settings(settings)

            summary_lines = []
            for pid in cleaned_enabled:
                p = cleaned_profiles[pid - 1]
                link_rule = "all_links" if p["trigger_link_mode"] == "all_links" else f"prefix:{p['trigger_link_prefix'] or '-'}"
                bg_rule = p["bg_toggle_mode"]
                if bg_rule == "custom":
                    bg_rule = f"custom:{p['bg_toggle_custom_hours']}h"
                comment_rules = p.get("trigger_comment_rules") or []
                comments_text = ", ".join(
                    f"{r.get('text')}:{r.get('action')}" for r in comment_rules if isinstance(r, dict) and r.get("text")
                ) or "-"
                summary_lines.append(
                    f"P{pid} link={link_rule} link_action={p['link_action']} comments={comments_text} disable_comment={'on' if p['disable_comments_enabled'] else 'off'} bg={bg_rule}"
                )
            await msg.reply_text(
                "✅ Group profile settings saved.\n"
                f"- target: {matched_target.get('name')} ({target_id})\n"
                f"- active profiles: {', '.join(str(x) for x in cleaned_enabled)}\n"
                + "\n".join(f"- {line}" for line in summary_lines),
                reply_markup=moderation_app_keyboard(),
            )
            return

        discussion_group_id = payload.get("discussion_group_id")
        comments_on_posts_enabled = payload.get("comments_on_posts_enabled")
        broadcast_presets = payload.get("broadcast_presets")
        if discussion_group_id is not None and not isinstance(discussion_group_id, int):
            await msg.reply_text("❌ discussion_group_id invalid.")
            return
        if comments_on_posts_enabled is not None and not isinstance(comments_on_posts_enabled, bool):
            await msg.reply_text("❌ comments_on_posts_enabled invalid.")
            return
        cleaned_presets = []
        if broadcast_presets is not None:
            if not isinstance(broadcast_presets, list):
                await msg.reply_text("❌ broadcast_presets invalid.")
                return
            for item in broadcast_presets:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                ptext = str(item.get("text") or "").strip()
                if not name or not ptext:
                    continue
                cleaned_presets.append({"name": name, "text": ptext})

        if isinstance(discussion_group_id, int):
            existing["discussion_group_id"] = discussion_group_id
        else:
            existing.pop("discussion_group_id", None)
        if isinstance(comments_on_posts_enabled, bool):
            existing["comments_on_posts_enabled"] = comments_on_posts_enabled
        else:
            existing["comments_on_posts_enabled"] = True
        existing["broadcast_presets"] = cleaned_presets
        target_settings[str(target_id)] = existing
        settings["target_settings"] = target_settings
        save_runtime_settings(settings)

        await msg.reply_text(
            "✅ Target settings saved.\n"
            f"- target: {matched_target.get('name')} ({target_id})\n"
            f"- discussion_group_id: {discussion_group_id if isinstance(discussion_group_id, int) else '(not set)'}\n"
            f"- comments_on_posts: {'on' if existing.get('comments_on_posts_enabled', True) else 'off'}\n"
            f"- broadcast_presets: {len(cleaned_presets)}",
            reply_markup=moderation_app_keyboard(),
        )
        return

    if payload_type != "reezo_moderator_settings_save":
        await msg.reply_text("ℹ️ WebApp payload received.", reply_markup=moderation_app_keyboard())
        return

    target_chat_ids = payload.get("target_chat_ids")
    auto_ban_user_ids = payload.get("auto_ban_user_ids")
    moderation_enabled = bool(payload.get("moderation_enabled", True))
    mode = str(payload.get("mode") or "delete_and_ban")
    flood = int(payload.get("flood_threshold_per_minute") or 6)

    if not isinstance(target_chat_ids, list) or not all(isinstance(x, int) for x in target_chat_ids):
        await msg.reply_text("❌ target_chat_ids invalid.")
        return
    if not isinstance(auto_ban_user_ids, list) or not all(isinstance(x, int) for x in auto_ban_user_ids):
        await msg.reply_text("❌ auto_ban_user_ids invalid.")
        return
    if mode not in {"delete_and_ban", "delete_only", "ban_only"}:
        await msg.reply_text("❌ mode invalid.")
        return
    if flood < 1:
        flood = 1

    settings = load_runtime_settings()
    settings["allowed_group_ids"] = target_chat_ids
    settings["auto_ban_user_ids"] = auto_ban_user_ids
    settings["moderation_enabled"] = moderation_enabled
    settings["mode"] = mode
    settings["flood_threshold_per_minute"] = flood
    # Backward-compat payload writes into new targets model too.
    existing_targets = settings.get("targets") if isinstance(settings.get("targets"), list) else []
    by_id = {
        int(item["id"]): item
        for item in existing_targets
        if isinstance(item, dict) and isinstance(item.get("id"), int)
    }
    for chat_id in target_chat_ids:
        if chat_id not in by_id:
            by_id[chat_id] = {"id": chat_id, "name": str(chat_id), "type": "group"}
        else:
            by_id[chat_id]["type"] = "group"
    settings["targets"] = list(by_id.values())
    save_runtime_settings(settings)

    await msg.reply_text(
        "✅ Moderation settings saved.\n"
        f"- enabled: {moderation_enabled}\n"
        f"- mode: {mode}\n"
        f"- target chats: {len(target_chat_ids)}\n"
        f"- auto-ban users: {len(auto_ban_user_ids)}\n"
        f"- flood/min: {flood}",
        reply_markup=main_keyboard(True),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not msg or not user or not chat or not msg.text:
        return

    text = msg.text.strip()
    admin_ids = get_admin_ids()
    is_admin = user.id in admin_ids
    if not is_admin:
        return

    awaiting_settings = str(context.user_data.get("awaiting_settings") or "").strip()
    if awaiting_settings and chat.type == ChatType.PRIVATE:
        if not is_admin:
            context.user_data.pop("awaiting_settings", None)
            await msg.reply_text("❌ Admin only.")
            return
        if text == MENU_CANCEL or text.lower() in {"cancel", "batal"}:
            context.user_data.pop("awaiting_settings", None)
            await msg.reply_text("Setting dibatalkan.", reply_markup=settings_keyboard())
            return

        settings = load_runtime_settings()
        if awaiting_settings == "groups":
            parts = [x.strip() for x in text.split(",") if x.strip()]
            groups: list[int] = []
            for part in parts:
                try:
                    val = int(part)
                except ValueError:
                    await msg.reply_text("Format tak sah. Contoh: `-100111,-100222`", parse_mode="Markdown")
                    return
                if val >= 0:
                    await msg.reply_text("Group ID mesti nombor negatif (`-100...`).", parse_mode="Markdown")
                    return
                groups.append(val)
            settings["allowed_group_ids"] = groups
            save_runtime_settings(settings)
            context.user_data.pop("awaiting_settings", None)
            await msg.reply_text(
                f"✅ Group whitelist disimpan: {', '.join(str(x) for x in groups) if groups else '(empty = all groups)'}",
                reply_markup=settings_keyboard(),
            )
            return

        if awaiting_settings == "channel":
            raw = text.strip()
            try:
                channel_id = int(raw)
            except ValueError:
                await msg.reply_text("Format tak sah. Contoh channel id: `-1001234567890`", parse_mode="Markdown")
                return
            if channel_id >= 0:
                await msg.reply_text("Channel ID mesti nombor negatif (`-100...`).", parse_mode="Markdown")
                return
            settings["default_channel_id"] = channel_id
            save_runtime_settings(settings)
            context.user_data.pop("awaiting_settings", None)
            await msg.reply_text(f"✅ Default channel disimpan: {channel_id}", reply_markup=settings_keyboard())
            return

    if context.user_data.get("awaiting_broadcast") and chat.type == ChatType.PRIVATE:
        pending = context.user_data.get("pending_broadcast")
        if text == MENU_CANCEL or text.lower() in {"cancel", "batal"}:
            context.user_data.pop("awaiting_broadcast", None)
            context.user_data.pop("pending_broadcast", None)
            await msg.reply_text("Broadcast dibatalkan.", reply_markup=main_keyboard(is_admin))
            return

        if isinstance(pending, dict):
            if text == MENU_BROADCAST_EDIT:
                context.user_data.pop("pending_broadcast", None)
                await msg.reply_text(
                    "Hantar semula text broadcast baru.",
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton(MENU_CANCEL)]], resize_keyboard=True),
                )
                return
            if text != MENU_BROADCAST_SEND:
                await msg.reply_text(
                    "Pilih `✅ Send Broadcast` untuk hantar atau `✏️ Edit Text` untuk ubah.",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton(MENU_BROADCAST_SEND), KeyboardButton(MENU_BROADCAST_EDIT)], [KeyboardButton(MENU_CANCEL)]],
                        resize_keyboard=True,
                    ),
                )
                return
            channel_id = pending.get("channel_id")
            body = str(pending.get("body") or "").strip()
            if not isinstance(channel_id, int) or not body:
                context.user_data.pop("pending_broadcast", None)
                await msg.reply_text("Preview rosak. Sila hantar semula broadcast text.")
                return
            try:
                await context.bot.send_message(chat_id=channel_id, text=body)
            except (BadRequest, Forbidden):
                await msg.reply_text("Gagal broadcast. Pastikan bot admin di channel dan channel_id betul.")
                return
            context.user_data.pop("pending_broadcast", None)
            context.user_data.pop("awaiting_broadcast", None)
            await msg.reply_text(f"✅ Broadcast berjaya ke {channel_id}.", reply_markup=main_keyboard(is_admin))
            return

        channel_id: int | None = get_default_channel_id()
        body = text
        if "\n" in text:
            first_line, rest = text.split("\n", 1)
            first_line = first_line.strip()
            if first_line.startswith("-100") and first_line[1:].isdigit():
                channel_id = int(first_line)
                body = rest.strip()
        presets = get_channel_broadcast_presets(channel_id)
        # Allow selecting preset by number only, e.g. "1".
        if body.isdigit() and presets:
            idx = int(body)
            if 1 <= idx <= len(presets):
                body = presets[idx - 1]["text"]
        # Allow selecting preset by exact preset name.
        if presets and body:
            for item in presets:
                if body.strip().lower() == item["name"].strip().lower():
                    body = item["text"]
                    break

        if channel_id is None:
            await msg.reply_text(
                "Set REEZO_MODERATOR_CHANNEL_ID dalam .env, atau hantar format:\n-100xxxxxxxxxx\\n<isi mesej>",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton(MENU_CANCEL)]], resize_keyboard=True),
            )
            return

        if not body:
            await msg.reply_text("Mesej kosong. Cuba lagi atau cancel.")
            return

        context.user_data["pending_broadcast"] = {"channel_id": channel_id, "body": body}
        preview = body if len(body) <= 700 else (body[:700] + "...")
        await msg.reply_text(
            f"Preview broadcast ke `{channel_id}`:\n\n{preview}\n\nTekan `✅ Send Broadcast` untuk hantar.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(MENU_BROADCAST_SEND), KeyboardButton(MENU_BROADCAST_EDIT)], [KeyboardButton(MENU_CANCEL)]],
                resize_keyboard=True,
            ),
        )
        return

    if text == MENU_CHAT_ID:
        await chat_id(update, context)
        return

    if text == MENU_MOD_STATUS:
        allowed_groups = sorted(get_allowed_group_ids())
        group_text = ", ".join(str(x) for x in allowed_groups) if allowed_groups else "ALL GROUPS (no whitelist set)"
        settings = load_runtime_settings()
        targets = settings.get("targets") if isinstance(settings.get("targets"), list) else []
        group_count = len([x for x in targets if isinstance(x, dict) and x.get("type") == "group"])
        channel_count = len([x for x in targets if isinstance(x, dict) and x.get("type") == "channel"])
        await msg.reply_text(
            "Moderation ON.\\n- Auto detect spam\\n- Auto delete message\\n- Auto kick user\\n"
            f"- Whitelist groups: {group_text}\\n"
            f"- Saved targets: {group_count} groups, {channel_count} channels",
            reply_markup=main_keyboard(is_admin),
        )
        return

    if text == MENU_MODERATION_APP:
        if not is_admin:
            return
        webapp_url = get_moderation_webapp_url()
        if not webapp_url:
            await msg.reply_text("Set REEZO_MODERATOR_WEBAPP_URL dalam .env dahulu.")
            return
        await msg.reply_text("Pilih menu moderation miniapp:", reply_markup=moderation_app_keyboard())
        return

    if text in {MENU_MOD_ADD, MENU_MOD_TARGET_SETTINGS}:
        if not is_admin:
            return
        await msg.reply_text("Sila buka melalui button WebApp dalam menu ni.", reply_markup=moderation_app_keyboard())
        return

    if text == MENU_BROADCAST:
        if not is_admin:
            await msg.reply_text("❌ Admin only.")
            return
        context.user_data["awaiting_broadcast"] = True
        context.user_data.pop("pending_broadcast", None)
        channel_id = get_default_channel_id()
        presets = get_channel_broadcast_presets(channel_id)
        preset_lines = ""
        if presets:
            preset_lines = "\nPreset tersedia:\n" + "\n".join(
                f"{idx}. {item['name']}" for idx, item in enumerate(presets, start=1)
            ) + "\n(Hantar nombor preset atau nama preset untuk guna text siap.)"
        await msg.reply_text(
            "Hantar mesej broadcast sekarang.\\nOpsyen: baris pertama boleh channel_id (-100...).\\n"
            "Selepas hantar text, bot akan tunjuk preview dulu sebelum send."
            + preset_lines,
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(MENU_CANCEL)]], resize_keyboard=True),
        )
        return

    if text == MENU_SETTINGS:
        if not is_admin:
            await msg.reply_text("❌ Admin only.")
            return
        await msg.reply_text("Settings menu:", reply_markup=settings_keyboard())
        return

    if text == MENU_SET_GROUPS:
        if not is_admin:
            await msg.reply_text("❌ Admin only.")
            return
        context.user_data["awaiting_settings"] = "groups"
        await msg.reply_text(
            "Masukkan group ID whitelist dipisahkan koma.\nContoh: `-100111,-100222`\n\nHantar kosong tak dibenarkan.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(MENU_CANCEL)]], resize_keyboard=True),
        )
        return

    if text == MENU_SET_CHANNEL:
        if not is_admin:
            await msg.reply_text("❌ Admin only.")
            return
        context.user_data["awaiting_settings"] = "channel"
        await msg.reply_text(
            "Masukkan default channel ID.\nContoh: `-1001234567890`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(MENU_CANCEL)]], resize_keyboard=True),
        )
        return

    if text == MENU_VIEW_SETTINGS:
        if not is_admin:
            await msg.reply_text("❌ Admin only.")
            return
        settings = load_runtime_settings()
        channel_id = settings.get("default_channel_id")
        groups = settings.get("allowed_group_ids") or []
        groups_text = ", ".join(str(x) for x in groups) if groups else "(empty = all groups)"
        await msg.reply_text(
            "Current settings:\n"
            f"- default_channel_id: {channel_id if channel_id is not None else '(not set)'}\n"
            f"- allowed_group_ids: {groups_text}\n"
            f"- targets_saved: {len(settings.get('targets') or [])}",
            reply_markup=settings_keyboard(),
        )
        return

    if text == MENU_BACK:
        await msg.reply_text("Kembali ke menu utama.", reply_markup=main_keyboard(is_admin))
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled error: %s", context.error, exc_info=context.error)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = ApplicationBuilder().token(get_token()).build()

    app.add_handler(CommandHandler("userid", user_id))
    app.add_handler(CommandHandler("channelid", channel_id_from_input))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chatid", chat_id))
    app.add_handler(CommandHandler("groupid", chat_id))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, forwarded_channel_id), group=1)
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & (filters.TEXT | filters.CaptionRegex(r".+")),
            handle_group_message,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("Reezo moderator bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
