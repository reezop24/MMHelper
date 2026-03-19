# NEXT Event Bot

Bot khas untuk handle pendaftaran event sahaja.

## Main Menu (Reply Keyboard)

- `Maklumat terkini`
- `Pendaftaran`

## Submenu Pendaftaran

- `Berbuka Puasa 2026`
- `Webinar`
- `Seminar`
- `Kembali ke menu utama`

Untuk pilihan `Webinar` dan `Seminar`, bot akan balas:

`Tiada pendaftaran Seminar/Webinar dibuka ketika ini , sila tunggu mahklumat lanjut seterusnya`

## Setup

1. Isi fail `.env`:

```env
BOT_TOKEN=
SUPERUSER_ID=
```

2. Jalankan bot:

```bash
cd /root/mmhelper/NEXT_Event_BOT
chmod +x run_next_event_bot.sh
./run_next_event_bot.sh
```
