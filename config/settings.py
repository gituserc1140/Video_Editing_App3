"""Configuration settings for the Creatomate Streamlit micro-app."""

import os

CREATOMATE_BASE_URL = os.getenv("CREATOMATE_BASE_URL", "https://api.creatomate.com/v1")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "3"))
RENDER_WAIT_TIMEOUT = int(os.getenv("RENDER_WAIT_TIMEOUT", "300"))
