# Reezo Comment Userbot

Userbot (MTProto) untuk toggle ruang komen post channel:
- `/comments_on <channel> [discussion_group]`
- `/comments_off <channel>`

Owner-only berdasarkan `REEZO_USERBOT_OWNER_ID`.

## Setup

1. Isi env:
```bash
cd /root/mmhelper/reezo_comment_userbot
cp .env.example .env
```

2. Isi:
- `REEZO_USERBOT_API_ID`
- `REEZO_USERBOT_API_HASH`
- `REEZO_USERBOT_OWNER_ID`

3. Install dependency (sekali):
```bash
/root/hemss_bot/venv/bin/pip install -r /root/mmhelper/reezo_comment_userbot/requirements.txt
```

4. Run manual (first login minta code Telegram):
```bash
cd /root/mmhelper/reezo_comment_userbot
./run_userbot.sh
```

## Commands

- `/channelid <link|@username|-100...>`
- `/set_discussion <channel> <discussion_group>`
- `/show_discussion <channel>`
- `/comments_on <channel> [discussion_group]`
- `/comments_off <channel>`

Contoh:
- `/comments_on @Reezo_Project24 -1002110957593`
- `/comments_off @Reezo_Project24`

## Systemd (optional)

```bash
cp /root/mmhelper/reezo_comment_userbot/deploy/reezo-comment-userbot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now reezo-comment-userbot
systemctl status reezo-comment-userbot
```
