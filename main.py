"""
Predoctoral research opportunity scraper.

Scrapes predoc.org and NBER, deduplicates listings, saves CSV/JSON,
and sends ntfy push notifications.

Usage:
    python main.py
"""

from __future__ import annotations

import logging
import sys
from typing import Callable, List

from models import JobRecord
from scrapers.nber_scraper import scrape_nber
from scrapers.predoc_scraper import scrape_predoc
from services.notifier import send_notification
from services.storage import merge_and_save
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)

ScraperFunc = Callable[[], List[JobRecord]]


def scrape_all_sources() -> List[JobRecord]:
    """Run all scrapers, continuing if one source fails."""
    all_jobs: List[JobRecord] = []

    for source_name, scraper in (
        ("predoc.org", scrape_predoc),
        ("nber.org", scrape_nber),
    ):
        try:
            jobs = scraper()
            logger.info("Scraped %d opportunities from %s", len(jobs), source_name)
            all_jobs.extend(jobs)
        except Exception:
            logger.exception("Scraper failed for %s — continuing with other sources", source_name)

    logger.info("Total scraped opportunities across all sources: %d", len(all_jobs))
    return all_jobs


def run() -> int:
    """Execute one full scrape cycle: collect, deduplicate, save, notify."""
    setup_logging()
    logger.info("=== Predoc Scraper run started ===")

    scraped_jobs = scrape_all_sources()

    if not scraped_jobs:
        logger.warning("No jobs scraped from any source.")

    all_jobs, new_jobs, updated_count = merge_and_save(scraped_jobs)
    notified = send_notification(new_jobs)

    logger.info(
        "=== Run complete | scraped=%d total=%d new=%d updated=%d notified=%s ===",
        len(scraped_jobs),
        len(all_jobs),
        len(new_jobs),
        updated_count,
        notified,
    )
    return 0 if scraped_jobs else 1


def main() -> int:
    try:
        return run()
    except Exception:
        logger.exception("Fatal error during scraper run")
        return 1


if __name__ == "__main__":
    sys.exit(main())
