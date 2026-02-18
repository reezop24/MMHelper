# MMHELPER Video Bot

Bot berasingan khas untuk menu video supaya tidak ganggu bot sedia ada.

## Menu Main (Reply Keyboard)

- `NEXT eVideo26 Full Silibus`
- `Intraday Strategy`
- `Fibo Extension Custom Strategy`

## Setup

1. Copy `.env.example` ke `.env`
2. Isi `VIDEO_BOT_TOKEN`
3. Isi `VIDEO_DB_GROUP_ID` (group Telegram tempat video disimpan)
4. Isi `VIDEO_EVIDEO_WEBAPP_URL` (URL miniapp eVideo)
4. Run:

```bash
cd /root/mmhelper/mmhelper_video_bot
chmod +x run_video_bot.sh
./run_video_bot.sh
```

## Video List / Catalog

Semua senarai video disimpan di:

- `mmhelper_video_bot/video_catalog.py`

Tambah video hanya di fail ini (ikut level `basic`, `intermediate`, `advanced`) dengan format:

```python
{"title": "Nama Video", "message_id": 123}
```

## Letak Group ID

Masukkan `VIDEO_DB_GROUP_ID` di:

- `mmhelper_video_bot/.env`

Contoh:

```env
VIDEO_DB_GROUP_ID=-1001234567890
VIDEO_EVIDEO_WEBAPP_URL=https://domain-anda/mmhelper_video_bot/miniapp/index.html
```

## Miniapp eVideo

Fail miniapp ada di:

- `mmhelper_video_bot/miniapp/index.html`
- `mmhelper_video_bot/miniapp/global.css`
- `mmhelper_video_bot/miniapp/app.js`

## Systemd

Template service:

- `mmhelper_video_bot/deploy/mmhelper-video-bot.service`
