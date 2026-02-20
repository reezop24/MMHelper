# Twelve Live Trigger Bot

Bot berasingan untuk live price feed (WebSocket) dan trigger zone/point real-time.

## Fungsi
- Subscribe live tick dari Twelve Data (`LIVE_SYMBOLS`)
- Simpan tick ke SQLite (`live_ticks.db`)
- Evaluate zone trigger dari `zones.json`
- Simpan event trigger ke `trigger_events.jsonl`

## Setup
```bash
cd /root/mmhelper/twelve_live_trigger_bot
cp .env.example .env
# isi TWELVE_API_KEY
pip3 install -r requirements.txt
./run_live_trigger_bot.sh
```

## Zone file
Default: `/root/mmhelper/db/twelve_live_trigger_bot/zones.json`

Contoh:
```json
{
  "zones": [
    {
      "id": "xau_above_5100",
      "symbol": "XAU/USD",
      "kind": "above",
      "value": 5100.0,
      "enabled": true
    },
    {
      "id": "xau_reaction_zone",
      "symbol": "XAU/USD",
      "kind": "between",
      "value_low": 4980.0,
      "value_high": 4990.0,
      "enabled": true
    }
  ]
}
```

`kind` disokong: `above`, `below`, `between`.

## Output
- DB tick: `/root/mmhelper/db/twelve_live_trigger_bot/live_ticks.db`
- Trigger events: `/root/mmhelper/db/twelve_live_trigger_bot/trigger_events.jsonl`
