# Reezo Moderator Bot

Bot moderation berasingan untuk group Telegram:
- auto detect spam asas
- auto delete mesej spam
- auto kick user spam
- menu ringkas (ReplyKeyboard)
- fungsi semak `chat_id`
- broadcast mesej ke channel

## Setup

1. Salin env:
```bash
cd /root/mmhelper/reezo_moderator_bot
cp .env.example .env
```
2. Isi `REEZO_MODERATOR_BOT_TOKEN`
3. Isi `REEZO_MODERATOR_ADMIN_IDS` (user id admin bot)
4. (Opsyenal) isi `REEZO_MODERATOR_CHANNEL_ID`

## Keperluan Telegram

1. Jadikan bot sebagai admin di group target.
2. Beri permission:
- Delete messages
- Ban users
3. Untuk bot baca mesej user di group, disable privacy mode di BotFather:
- `/setprivacy` -> pilih bot -> `Disable`

## Run manual

```bash
cd /root/mmhelper/reezo_moderator_bot
./run_moderator_bot.sh
```

## Systemd service

Template service:
- `deploy/reezo-moderator-bot.service`

Contoh install:
```bash
cp /root/mmhelper/reezo_moderator_bot/deploy/reezo-moderator-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now reezo-moderator-bot
systemctl status reezo-moderator-bot
```

## Broadcast ke channel

Boleh guna bot yang sama untuk broadcast channel.

Di private chat bot:
- tekan `📢 Broadcast To Channel`
- hantar teks mesej
- opsyen: baris pertama boleh letak channel id `-100...`
