"""CSV and JSON persistence for scraped job opportunities."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from config import CSV_PATH, DATA_DIR, JSON_PATH
from models import JobRecord
from utils.dedup import DeduplicationIndex

logger = logging.getLogger(__name__)

CSV_COLUMNS = (
    "title",
    "institution",
    "university",
    "research_fields",
    "location",
    "researcher_names",
    "application_deadline",
    "date_posted",
    "job_url",
    "source_website",
    "duration",
    "description",
    "employment_type",
    "salary",
    "visa_sponsorship",
    "dedup_key",
    "first_seen",
    "last_seen",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jobs() -> List[JobRecord]:
    """Load existing jobs from JSON (preferred) or CSV fallback."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if JSON_PATH.exists():
        try:
            with JSON_PATH.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            jobs = [JobRecord.from_dict(item) for item in payload]
            logger.info("Loaded %d jobs from %s", len(jobs), JSON_PATH)
            return jobs
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.exception("Failed to load JSON from %s: %s", JSON_PATH, exc)

    if CSV_PATH.exists():
        try:
            frame = pd.read_csv(CSV_PATH, dtype=str).fillna("")
            jobs = [JobRecord.from_dict(row.to_dict()) for _, row in frame.iterrows()]
            logger.info("Loaded %d jobs from %s", len(jobs), CSV_PATH)
            return jobs
        except Exception as exc:
            logger.exception("Failed to load CSV from %s: %s", CSV_PATH, exc)

    logger.info("No existing job data found; starting fresh.")
    return []


def save_jobs(jobs: List[JobRecord]) -> None:
    """Persist all jobs to CSV and JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = [job.to_dict() for job in jobs]

    with JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)
    logger.info("Saved %d jobs to %s", len(jobs), JSON_PATH)

    frame = pd.DataFrame(records)
    for column in CSV_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame = frame[list(CSV_COLUMNS)]
    frame.to_csv(CSV_PATH, index=False, encoding="utf-8")
    logger.info("Saved %d jobs to %s", len(jobs), CSV_PATH)


def merge_and_save(scraped_jobs: List[JobRecord]) -> Tuple[List[JobRecord], List[JobRecord], int]:
    """
    Load existing data, deduplicate scraped jobs, and save updated files.

    Returns (all_jobs, new_jobs, updated_count).
    """
    existing = load_jobs()
    index = DeduplicationIndex(existing)
    timestamp = utc_now_iso()
    all_jobs, new_jobs, updated_count = index.merge_scraped(scraped_jobs, timestamp)
    save_jobs(all_jobs)
    return all_jobs, new_jobs, updated_count
