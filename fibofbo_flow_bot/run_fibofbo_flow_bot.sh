#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
if [ -x "/root/hemss_bot/venv/bin/python" ]; then
  exec /root/hemss_bot/venv/bin/python server.py
fi
exec python3 server.py
