# FiboFBO Flow Telegram Bot

Scaffold bot Telegram untuk test signal DBO + Fibo sebelum logic penuh dimasukkan.

## Setup
```bash
cd /root/mmhelper/fibofbo_flow_bot
cp .env.example .env
# isi FIBOFBO_FLOW_BOT_TOKEN
python3 -m pip install -r requirements.txt
./run_fibofbo_flow_bot.sh
```

## Commands
- `/start` - menu ringkas
- `/ping` - health check
- `/signal` - baca signal semasa dari `FIBOFBO_FLOW_SIGNAL_FILE`
- `/dbo [tf]` - check setup DBO asas (contoh `/dbo m5`, `/dbo h1`)

## Env
- `FIBOFBO_FLOW_BOT_TOKEN` - token BotFather
- `FIBOFBO_FLOW_SIGNAL_FILE` - default `/root/mmhelper/db/twelve_data_bot/latest_signal.json`
- `FIBOFBO_FLOW_CANDLES_DB` - default `/root/mmhelper/db/twelve_data_bot/candles.db`
- `FIBOFBO_FLOW_DBO_TF` - default timeframe untuk `/dbo` (default `m5`)
- `FIBOFBO_FLOW_DBO_LOOKBACK` - jumlah candle dibaca (default `600`)
- `LOG_LEVEL` - default `INFO`
