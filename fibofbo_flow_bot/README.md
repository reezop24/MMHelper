# FiboFBO Flow Bot (Baseline + MTF Scoring Foundation)

Bot ini sekarang ada 2 layer asas:
- Chart engine feeder/checker
- MTF Bias + Scoring Engine foundation (modular, explainable)

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
- `/mtf` - run MTF Bias + Scoring (XAUUSD) dan papar explain ringkas

## Env
- `FIBOFBO_FLOW_BOT_TOKEN` - token BotFather
- `FIBOFBO_FLOW_SIGNAL_FILE` - default `/root/mmhelper/db/twelve_data_bot/latest_signal.json`
- `FIBOFBO_FLOW_CANDLES_DB` - default `/root/mmhelper/db/twelve_data_bot/candles.db`
- `FIBOFBO_FLOW_DEFAULT_TF` - default timeframe (`h1`)
- `FIBOFBO_FLOW_MTF_SCORE_MIN` - minimum score ready (default `7`)
- `FIBOFBO_FLOW_MTF_NEAR_END_MIN` - cutoff near session end (default `45`)
- `FIBOFBO_FLOW_DAILY_CONFLICT_MODE` - `soft|strict`
- `FIBOFBO_FLOW_WEEKLY_CONFLICT_MODE` - `soft|ignore`
- `FIBOFBO_FLOW_MTF_SWING_LOOKBACK` - fractal lookback (default `2`)
- `FIBOFBO_FLOW_MTF_TREND_SWINGS_N` - min swings for trend (default `4`)
- `LOG_LEVEL` - default `INFO`

## Core API (for next modules)
Dalam `mtf_engine.py`:
- `evaluateMTF(symbol, candlesByTF, nowTimestamp, config, open_position_session=None)`
- `explainMTF(result)`

Modul ini direka supaya detector lain (Impulse/Retrace/FE/Risk) boleh plug-in pada result JSON yang sama.

## Unit Tests
```bash
cd /root/mmhelper/fibofbo_flow_bot
python3 -m unittest tests/test_mtf_engine.py -v
```

## Export Preview
```bash
python3 export_live_preview.py --tf h1 --limit 500
```
Output JSON ditulis ke `debug_live_<tf>.json`.
