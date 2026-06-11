"""Logging configuration for the scraper."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import LOG_PATH, LOGS_DIR


def setup_logging(level: int = logging.INFO) -> None:
    """Configure console and rotating file logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
