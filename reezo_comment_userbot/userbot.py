from __future__ import annotations

import json
import os
import re
from pathlib import Path

from telethon import TelegramClient, events, functions, types

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "state.json"


def load_local_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_env() -> tuple[int, str, int, str, str]:
    load_local_env()
    api_id = int((os.getenv("REEZO_USERBOT_API_ID") or "0").strip())
    api_hash = (os.getenv("REEZO_USERBOT_API_HASH") or "").strip()
    owner_id = int((os.getenv("REEZO_USERBOT_OWNER_ID") or "0").strip())
    session_name = (os.getenv("REEZO_USERBOT_SESSION") or "reezo_userbot").strip()
    session_string = (os.getenv("REEZO_USERBOT_SESSION_STRING") or "").strip()
    if api_id <= 0 or not api_hash or owner_id <= 0:
        raise RuntimeError("Set REEZO_USERBOT_API_ID, REEZO_USERBOT_API_HASH, REEZO_USERBOT_OWNER_ID in .env")
    return api_id, api_hash, owner_id, session_name, session_string


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"discussion_map": {}}
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"discussion_map": {}}
    if not isinstance(raw, dict):
        return {"discussion_map": {}}
    if not isinstance(raw.get("discussion_map"), dict):
        raw["discussion_map"] = {}
    return raw


def save_state(data: dict) -> None:
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def resolve_entity(client: TelegramClient, raw: str):
    value = raw.strip()
    value = value.replace("https://", "").replace("http://", "")

    m_private = re.search(r"(?:t\.me/)?c/(\d+)", value, flags=re.IGNORECASE)
    if m_private:
        return await client.get_entity(int(f"-100{m_private.group(1)}"))

    m_public = re.search(r"(?:t\.me/)?([A-Za-z0-9_]{5,})(?:/\d+)?", value)
    if m_public and not value.startswith("-"):
        return await client.get_entity("@" + m_public.group(1))

    if value.startswith("@"):
        return await client.get_entity(value)

    if re.match(r"^-?\d+$", value):
        return await client.get_entity(int(value))

    raise ValueError("Unrecognized entity format")


def parse_cmd(text: str) -> list[str]:
    return [x for x in text.strip().split() if x]


async def main() -> None:
    api_id, api_hash, owner_id, session_name, session_string = get_env()

    if session_string:
        from telethon.sessions import StringSession

        client = TelegramClient(StringSession(session_string), api_id, api_hash)
    else:
        client = TelegramClient(str(BASE_DIR / session_name), api_id, api_hash)

    state = load_state()

    @client.on(events.NewMessage(pattern=r"^/(comments_on|comments_off|set_discussion|show_discussion|channelid)\\b"))
    async def handler(event: events.NewMessage.Event) -> None:
        sender = await event.get_sender()
        sender_id = int(getattr(sender, "id", 0) or 0)
        if sender_id != owner_id:
            return

        parts = parse_cmd(event.raw_text or "")
        if not parts:
            return
        cmd = parts[0].lower()

        try:
            if cmd == "/channelid":
                if len(parts) < 2:
                    await event.reply("Usage: /channelid <link|@username|-100...>")
                    return
                entity = await resolve_entity(client, parts[1])
                await event.reply(f"channel_id: {entity.id}\ntype: {type(entity).__name__}")
                return

            if cmd == "/set_discussion":
                if len(parts) < 3:
                    await event.reply("Usage: /set_discussion <channel> <discussion_group>")
                    return
                channel = await resolve_entity(client, parts[1])
                group = await resolve_entity(client, parts[2])
                state["discussion_map"][str(channel.id)] = int(group.id)
                save_state(state)
                await event.reply(f"Saved map: channel {channel.id} -> discussion {group.id}")
                return

            if cmd == "/show_discussion":
                if len(parts) < 2:
                    await event.reply("Usage: /show_discussion <channel>")
                    return
                channel = await resolve_entity(client, parts[1])
                group_id = state["discussion_map"].get(str(channel.id))
                await event.reply(f"channel {channel.id} discussion: {group_id}")
                return

            if cmd == "/comments_on":
                if len(parts) >= 3:
                    channel = await resolve_entity(client, parts[1])
                    group = await resolve_entity(client, parts[2])
                    state["discussion_map"][str(channel.id)] = int(group.id)
                    save_state(state)
                elif len(parts) >= 2:
                    channel = await resolve_entity(client, parts[1])
                    group_id = state["discussion_map"].get(str(channel.id))
                    if group_id is None:
                        await event.reply("No discussion map. Use /set_discussion first or pass <group>.")
                        return
                    group = await resolve_entity(client, str(group_id))
                else:
                    await event.reply("Usage: /comments_on <channel> [discussion_group]")
                    return

                await client(
                    functions.channels.SetDiscussionGroupRequest(
                        broadcast=channel,
                        group=group,
                    )
                )
                await event.reply(f"Comments ON for channel {channel.id} (discussion {group.id}).")
                return

            if cmd == "/comments_off":
                if len(parts) < 2:
                    await event.reply("Usage: /comments_off <channel>")
                    return
                channel = await resolve_entity(client, parts[1])
                await client(
                    functions.channels.SetDiscussionGroupRequest(
                        broadcast=channel,
                        group=types.InputChannelEmpty(),
                    )
                )
                await event.reply(f"Comments OFF for channel {channel.id}.")
                return

        except Exception as exc:
            await event.reply(f"Error: {exc}")

    await client.start()
    me = await client.get_me()
    print(f"Reezo userbot running as {me.id}")
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
