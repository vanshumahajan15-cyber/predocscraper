"""Application configuration loaded from environment variables with sensible defaults."""

from __future__ import annotations

import os
from pathlib import Path

# Project paths
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
CSV_PATH = DATA_DIR / "predoc_jobs.csv"
JSON_PATH = DATA_DIR / "predoc_jobs.json"
LOG_PATH = LOGS_DIR / "scraper.log"

# Source URLs
PREDOC_URL = os.getenv("PREDOC_URL", "https://www.predoc.org/opportunities")
NBER_URL = os.getenv(
    "NBER_URL",
    "https://www.nber.org/career-resources/research-assistant-positions-not-nber",
)

# HTTP settings
USER_AGENT = os.getenv(
    "USER_AGENT",
    "PredocScraper/1.0 (+https://github.com/vanshumahajan15-cyber/predocscraper)",
)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "3"))
HTTP_RETRY_BASE_DELAY = float(os.getenv("HTTP_RETRY_BASE_DELAY", "2"))
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() in {"1", "true", "yes"}

# ntfy notification settings
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "predoc")
NTFY_BASE_URL = os.getenv("NTFY_BASE_URL", "https://ntfy.sh")
NTFY_TITLE = os.getenv("NTFY_TITLE", "Predoc Scraper")
