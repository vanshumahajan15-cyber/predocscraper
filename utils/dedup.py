"""Deduplication logic using URL, title, and institution matching."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Set, Tuple

from models import JobRecord
from utils.normalize import (
    generate_dedup_key,
    normalize_text,
    normalize_url,
    title_institution_key,
    title_key,
)

logger = logging.getLogger(__name__)


class DeduplicationIndex:
    """In-memory index for detecting duplicate job postings."""

    def __init__(self, existing_jobs: Iterable[JobRecord]) -> None:
        self.by_dedup_key: Dict[str, JobRecord] = {}
        self.by_url: Dict[str, JobRecord] = {}
        self.by_title_institution: Dict[str, JobRecord] = {}
        self.by_title: Dict[str, JobRecord] = {}

        for job in existing_jobs:
            self._register(job)

    def _register(self, job: JobRecord) -> None:
        if job.dedup_key:
            self.by_dedup_key[job.dedup_key] = job

        url = normalize_url(job.job_url)
        if url:
            self.by_url[url] = job

        ti_key = title_institution_key(job)
        if ti_key:
            self.by_title_institution[ti_key] = job

        t_key = title_key(job)
        if t_key:
            self.by_title[t_key] = job

    def find_existing(self, job: JobRecord) -> JobRecord | None:
        """Return an existing record if this job is a duplicate."""
        if job.dedup_key and job.dedup_key in self.by_dedup_key:
            return self.by_dedup_key[job.dedup_key]

        url = normalize_url(job.job_url)
        if url and url in self.by_url:
            return self.by_url[url]

        ti_key = title_institution_key(job)
        if ti_key and ti_key in self.by_title_institution:
            return self.by_title_institution[ti_key]

        t_key = title_key(job)
        if t_key and t_key in self.by_title:
            existing = self.by_title[t_key]
            new_inst = normalize_text(job.institution or job.university)
            old_inst = normalize_text(existing.institution or existing.university)
            if new_inst and old_inst and new_inst == old_inst:
                return existing

        return None

    def merge_scraped(
        self, scraped_jobs: List[JobRecord], timestamp: str
    ) -> Tuple[List[JobRecord], List[JobRecord], int]:
        """
        Merge scraped jobs into the index.

        Returns (all_jobs, new_jobs, updated_count).
        """
        new_jobs: List[JobRecord] = []
        updated_count = 0

        for job in scraped_jobs:
            job.dedup_key = generate_dedup_key(job)
            existing = self.find_existing(job)

            if existing:
                existing.last_seen = timestamp
                _refresh_fields(existing, job)
                updated_count += 1
                continue

            job.first_seen = timestamp
            job.last_seen = timestamp
            self._register(job)
            new_jobs.append(job)

        all_jobs = list(self.by_dedup_key.values())
        logger.info(
            "Dedup complete: total=%d, new=%d, updated=%d",
            len(all_jobs),
            len(new_jobs),
            updated_count,
        )
        return all_jobs, new_jobs, updated_count


def _refresh_fields(existing: JobRecord, incoming: JobRecord) -> None:
    """Update empty fields on an existing record from a fresh scrape."""
    for field_name in (
        "institution",
        "university",
        "research_fields",
        "location",
        "researcher_names",
        "application_deadline",
        "date_posted",
        "job_url",
        "duration",
        "description",
        "employment_type",
        "salary",
        "visa_sponsorship",
    ):
        current = getattr(existing, field_name)
        new_value = getattr(incoming, field_name)
        if not current and new_value:
            setattr(existing, field_name, new_value)
