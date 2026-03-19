#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
exec "$(pwd)/.venv/bin/python" next_event_bot.py
