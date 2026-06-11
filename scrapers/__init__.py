"""Scraper package."""

from scrapers.nber_scraper import scrape_nber
from scrapers.predoc_scraper import scrape_predoc

__all__ = ["scrape_nber", "scrape_predoc"]
