#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
exec /root/hemss_bot/venv/bin/python video_bot.py

