# Twelve Data Auto Analysis Bot (XAUUSD)

Bot berasingan untuk:
- Fetch data XAUUSD dari Twelve Data
- Simpan candle dalam SQLite (`candles.db`)
- Resample M5 -> M15/M30/H1/H4 (UTC boundary) + retention:
  - M5: 30 hari
  - M15: 30 hari
  - M30: 90 hari
  - H1: 90 hari
  - H4: 365 hari
- Request D1/W1/MN1 secara direct (request berasingan)
  - D1 fetch: sekali sehari (slot MYT)
  - W1 fetch: sekali sehari (slot MYT, untuk update high/low semasa)
  - MN1 fetch: sekali sehari (slot MYT, untuk update high/low semasa)
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
- `DIRECT_FETCH_D1_SEC=86400`
- `DIRECT_FETCH_D1_TIME_MYT=06:30` (daily fetch ikut jam tetap MYT)
- `DIRECT_FETCH_W1_SEC=604800`
- `DIRECT_FETCH_MN1_SEC=2592000`

Nota:
- `D1/W1/MN1` semua guna slot masa `DIRECT_FETCH_D1_TIME_MYT`.
- `W1/MN1` dikemaskini harian pada slot yang sama untuk capture perubahan candle semasa.

## Timezone paparan

- Storage candle kekal UTC (standard, selamat untuk analisis).
- Paparan masa dalam output/telegram boleh set:
  - `DISPLAY_TIMEZONE=Asia/Kuala_Lumpur`

## H4 Session Mode (Malaysia)

`H4` guna sesi khas (bukan bucket UTC biasa) ikut waktu Malaysia:
- `H4_SESSION_MODE=standard`
  - 07-11, 11-15, 15-19, 19-23, 23-03, 03-06
- `H4_SESSION_MODE=dst`
  - 06-10, 10-14, 14-18, 18-22, 22-02, 02-05

Bila masuk tempoh DST, tukar ke `dst`.

`H4` disimpan dalam 2 mode:
- `h4` = confirmed candles sahaja (hanya selepas candle tutup)
- `h4_live` = floating candle (in-progress) untuk monitoring

Signal utama guna `h4` confirmed (elak repaint).

## Output files

Default disimpan di `/root/mmhelper/db/twelve_data_bot`:
- `candles.db` (semua timeframe candle)
- `latest_signal.json`
- `bot_state.json`

## Check bootstrap + visual chart

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

Generate chart HTML (candlestick):
```bash
cd /root/mmhelper/twelve_auto_analysis_bot
python3 export_chart.py --tf m5 --limit 300
```

Output akan jadi:
- `/root/mmhelper/db/twelve_data_bot/chart_m5.html`

## Notes penting

- Bot guna incremental update untuk M5 selepas bootstrap awal.
- Kalau rate limit (429), bot retry dengan backoff.
- Semua timestamp disimpan dalam UTC.
