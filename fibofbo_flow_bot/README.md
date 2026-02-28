# FiboFBO Flow Bot (Baseline Reset)

Bot ini telah di-reset ke baseline baru:
- Tiada logik DBO/FE lama
- Hanya feeder + checker untuk `chart engine` (candles DB)

## Setup
```bash
cd /root/mmhelper/fibofbo_flow_bot
cp .env.example .env
# isi FIBOFBO_FLOW_BOT_TOKEN
python3 -m pip install -r requirements.txt
./run_fibofbo_flow_bot.sh
```

## Commands
- `/start` - info bot
- `/ping` - health
- `/signal` - baca signal feeder semasa
- `/engine [tf]` - status data chart engine untuk TF
- `/candles [tf] [limit]` - preview candle terakhir
- `/dbo` - notis logic lama telah direset

## Env
- `FIBOFBO_FLOW_BOT_TOKEN` - token BotFather
- `FIBOFBO_FLOW_SIGNAL_FILE` - default `/root/mmhelper/db/twelve_data_bot/latest_signal.json`
- `FIBOFBO_FLOW_CANDLES_DB` - default `/root/mmhelper/db/twelve_data_bot/candles.db`
- `FIBOFBO_FLOW_DEFAULT_TF` - default timeframe (`h1`)
- `LOG_LEVEL` - default `INFO`

## Export Preview
```bash
python3 export_live_preview.py --tf h1 --limit 500
```
Output JSON akan ditulis ke `debug_live_<tf>.json`.
