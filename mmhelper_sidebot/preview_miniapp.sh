#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8787}"

cd /root/mmhelper/mmhelper_sidebot/miniapp

echo "Miniapp preview running on:"
echo "  http://127.0.0.1:${PORT}"
echo "Stop with Ctrl+C"

exec python3 -m http.server "${PORT}" --bind 127.0.0.1
