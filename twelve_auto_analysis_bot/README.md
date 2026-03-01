# Twelve Data Auto Analysis Bot (XAUUSD)

Bot berasingan untuk:
- Fetch data XAUUSD dari Twelve Data
- Simpan candle dalam SQLite (`candles.db`)
- Resample ikut flow rasmi:
  - `m15/m30` dibina dari `m5`
  - `h4` dibina dari `h1` ikut sesi MYT
  - `d1/w1/mn1` direct fetch harian
- Retention:
  - M5: 30 hari
  - M15: 30 hari
  - M30: 90 hari
  - H1: 90 hari
  - H4: 365 hari
- Hasilkan `latest_signal.json` dengan stub DBO Market Structure + Fibo Extension
- Optional: hantar alert ke Telegram bila signal berubah / ikut cooldown

## Setup

```bash
cd /root/mmhelper/twelve_auto_analysis_bot
cp .env.example .env
# edit .env dan isi TWELVE_API_KEY
./run_twelve_bot.sh
```

Untuk test sekali cycle sahaja:
```bash
RUN_ONCE=1 ./run_twelve_bot.sh
```

## Telegram alert (optional)

Set dalam `.env`:
- `TELEGRAM_ENABLED=1`
- `TELEGRAM_BOT_TOKEN=<token_botfather>`
- `TELEGRAM_CHAT_ID=<chat_id>`
- `TELEGRAM_SEND_HOLD=0` (default tak hantar HOLD)
- `TELEGRAM_MIN_INTERVAL_SEC=300` (anti spam untuk signal sama)

## Direct TF schedule

Set dalam `.env` kalau nak ubah kekerapan:
- `DIRECT_FETCH_DAILY_TIME_MYT=06:00:15` (slot harian D1/W1/MN1)
- `DIRECT_FETCH_W1_SEC=604800`
- `DIRECT_FETCH_MN1_SEC=2592000`
- `H1_SESSION_START_MYT=07:00`
- `H1_FETCH_DELAY_SEC=15`
- `M5_SESSION_START_MYT=07:00`
- `M5_FETCH_DELAY_SEC=5`

Nota:
- `D1/W1/MN1` guna slot harian yang sama.
- Bila fetch harian gagal, bot retry setiap 10 minit (max 6 kali).

## Timezone paparan

- Storage candle kekal UTC (standard, selamat untuk analisis).
- Paparan masa dalam output/telegram boleh set:
  - `DISPLAY_TIMEZONE=Asia/Kuala_Lumpur`

## H4 Session Mode (Malaysia)

`H4` guna sesi khas (bukan bucket UTC biasa) ikut waktu Malaysia:
- `H4_SESSION_MODE=auto` (default, ikut kalendar DST)
- `H4_SESSION_MODE=standard` (paksa manual)
  - 07-11, 11-15, 15-19, 19-23, 23-03, 03-06
- `H4_SESSION_MODE=dst` (paksa manual)
  - 06-10, 10-14, 14-18, 18-22, 22-02, 02-05

Mode `auto` ikut rule DST: Ahad pertama November hingga Ahad kedua Mac.

`h4` dibina dari `h1` dan disimpan sebagai candle confirmed.

## Output files

Default disimpan di `/root/mmhelper/db/twelve_data_bot`:
- `candles.db` (semua timeframe candle)
- `latest_signal.json`
- `bot_state.json`

## Check bootstrap + preview rasmi

Semak count/range setiap timeframe:
```bash
python3 - <<'PY'
import sqlite3
con=sqlite3.connect('/root/mmhelper/db/twelve_data_bot/candles.db')
for tf in ['m5','m15','m30','h1','h4','d1','w1','mn1']:
    c,min_ts,max_ts=con.execute(
        "SELECT COUNT(*), MIN(ts), MAX(ts) FROM candles WHERE timeframe=?",(tf,)
    ).fetchone()
    print(tf, c, min_ts, max_ts)
con.close()
PY
```

Generate preview rasmi:
```bash
cd /root/mmhelper/twelve_auto_analysis_bot
python3 export_multi_chart.py
```

Output rasmi:
- `/root/mmhelper/twelve_auto_analysis_bot/chart_multi.html`

## Notes penting

- Bot guna incremental update untuk M5 selepas bootstrap awal.
- Kalau rate limit (429), bot retry dengan backoff.
- Semua timestamp disimpan dalam UTC.
