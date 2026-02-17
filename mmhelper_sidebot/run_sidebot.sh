#!/usr/bin/env bash
set -euo pipefail

cd /root/mmhelper/mmhelper_sidebot
exec /root/hemss_bot/venv/bin/python /root/mmhelper/mmhelper_sidebot/AdminBot.py
