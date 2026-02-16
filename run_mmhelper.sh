#!/usr/bin/env bash
set -euo pipefail

cd /root/mmhelper
exec /root/hemss_bot/venv/bin/python /root/mmhelper/mmhelper.py
