# MMHELPER Side Bot

Companion bot yang boleh redirect user ke MM HELPER (bot utama).

## Setup

1. Copy `.env.example` ke `.env`.
2. Isi `SIDEBOT_TOKEN` dan `MAIN_BOT_USERNAME`.
3. Isi `SIDEBOT_REGISTER_WEBAPP_URL` untuk butang `Daftar NEXT member` (opsyenal, tapi diperlukan untuk buka miniapp).
4. Isi `SIDEBOT_ADMIN_GROUP_ID` untuk hantar notifikasi pendaftaran baru ke group admin.
5. Isi `AMARKETS_API_BASE_URL` dan `AMARKETS_API_TOKEN` untuk semakan automatik status client under affiliate.
6. Run manual:

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

### Local Preview (Tanpa Vercel)

Jalankan:

```bash
cd /root/mmhelper/mmhelper_sidebot
./preview_miniapp.sh
```

Preview URL:

```text
http://127.0.0.1:8787
```

Guna port lain (optional):

```bash
./preview_miniapp.sh 8899
```

## Admin Group ID

Untuk dapatkan `SIDEBOT_ADMIN_GROUP_ID`, jalankan command ini dalam group yang bot sudah join:

```bash
/groupid
```

Bot akan balas nilai `chat_id` group tersebut.
