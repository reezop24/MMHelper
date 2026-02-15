"""Runtime settings for MM HELPER."""

import os

DEFAULT_SETUP_WEBAPP_URL = "https://example.com/mmhelper/setup"


def get_setup_webapp_url() -> str:
    url = (os.getenv("MMHELPER_SETUP_URL") or "").strip()
    return url or DEFAULT_SETUP_WEBAPP_URL
