# MMHELPER Side Bot

Companion bot yang boleh redirect user ke MM HELPER (bot utama).

## Setup

1. Copy `.env.example` ke `.env`.
2. Isi `SIDEBOT_TOKEN` dan `MAIN_BOT_USERNAME`.
3. Isi `SIDEBOT_REGISTER_WEBAPP_URL` untuk butang `Daftar NEXT member` (opsyenal, tapi diperlukan untuk buka miniapp).
4. Isi `SIDEBOT_ADMIN_GROUP_ID` untuk hantar notifikasi pendaftaran baru ke group admin.
4. Run manual:

```bash
cd /root/mmhelper/mmhelper_sidebot
./run_sidebot.sh
```

## Systemd

Service file template ada di `deploy/mmhelper-sidebot.service`.

## Miniapp

Miniapp kosong (tema admin bot) ada di `miniapp/`:
- `miniapp/index.html`
- `miniapp/global.css`
- `miniapp/app.js`

## Admin Group ID

Untuk dapatkan `SIDEBOT_ADMIN_GROUP_ID`, jalankan command ini dalam group yang bot sudah join:

```bash
/groupid
```

Bot akan balas nilai `chat_id` group tersebut.
