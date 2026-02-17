# MMHELPER Side Bot

Companion bot yang boleh redirect user ke MM HELPER (bot utama).

## Setup

1. Copy `.env.example` ke `.env`.
2. Isi `SIDEBOT_TOKEN` dan `MAIN_BOT_USERNAME`.
3. Run manual:

```bash
cd /root/mmhelper/mmhelper_sidebot
./run_sidebot.sh
```

## Systemd

Service file template ada di `deploy/mmhelper-sidebot.service`.
