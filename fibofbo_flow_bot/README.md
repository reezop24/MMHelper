# FiboFBO Flow Bot (Clean Baseline)

Bot ini dalam clean state untuk foundation engine:
- MTF Bias + Scoring
- Impulse phase sensor
- Active leg decision layer
- Retrace context layer

Bot ini tidak execute trade. Ia hanya context + readiness output.

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
- `/mtf` - run MTF Bias + Scoring (XAUUSD)
- `/impulse` - run impulse phase sensor (H4/H1/M30/M15)
- `/activeleg` - run active leg evaluation
- `/retrace` - run retrace evaluation
- `/preview` - link web preview
- `/dbo` - notis logic lama telah direset

## Env
- `FIBOFBO_FLOW_BOT_TOKEN` - token BotFather
- `FIBOFBO_FLOW_SIGNAL_FILE` - default `/root/mmhelper/db/twelve_data_bot/latest_signal.json`
- `FIBOFBO_FLOW_CANDLES_DB` - default `/root/mmhelper/db/twelve_data_bot/candles.db`
- `FIBOFBO_FLOW_DEFAULT_TF` - default timeframe (`h1`)
- `FIBOFBO_FLOW_PREVIEW_URL` - link web preview yang dihantar oleh command `/preview`
- `FIBOFBO_FLOW_MTF_SCORE_MIN` - minimum score ready (default `7`)
- `FIBOFBO_FLOW_MTF_NEAR_END_MIN` - cutoff near session end (default `45`)
- `FIBOFBO_FLOW_DAILY_CONFLICT_MODE` - `soft|strict`
- `FIBOFBO_FLOW_WEEKLY_CONFLICT_MODE` - `soft|ignore`
- `FIBOFBO_FLOW_MTF_SWING_LOOKBACK` - fractal lookback (default `2`)
- `FIBOFBO_FLOW_MTF_TREND_SWINGS_N` - min swings for trend (default `4`)
- `FIBOFBO_FLOW_IMPULSE_SWING_LOOKBACK` - impulse swing lookback (default `2`)
- `FIBOFBO_FLOW_ACTIVELEG_H1_OVEREXT` - H1 overextension multiplier (default `1.2`)
- `FIBOFBO_FLOW_ACTIVELEG_M30_OVEREXT` - M30 overextension multiplier (default `1.5`)
- `FIBOFBO_FLOW_RETRACE_ENABLE_SWEEP` - enable sweep logic (`1|0`)
- `FIBOFBO_FLOW_RETRACE_SWEEP_READY_DIRECT` - sweep direct ready (`1|0`)
- `FIBOFBO_FLOW_RETRACE_SWEEP_REQUIRE_MICRO_CONFIRM` - require M15 micro confirm (`1|0`)
- `FIBOFBO_FLOW_RETRACE_SWEEP_MAX_RECLAIM_CANDLES` - max reclaim candles (default `3`)
- `FIBOFBO_FLOW_RETRACE_SWEEP_TRIGGER_RATIO` - sweep trigger ratio (default `0.9`)
- `LOG_LEVEL` - default `INFO`
- `SIM_PREVIEW_HOST` - host simulator preview (default `0.0.0.0`)
- `SIM_PREVIEW_PORT` - port simulator preview (default `8766`)

## Systemd
Service bot utama:
- `fibofbo-flow-bot.service`

Service web preview:
- `fibofbo-flow-simulator.service`

## Unit Tests
```bash
cd /root/mmhelper/fibofbo_flow_bot
python3 -m unittest \
  tests/test_mtf_engine.py \
  tests/test_impulse_engine.py \
  tests/test_active_leg_engine.py \
  tests/test_retrace_engine.py -v
```
