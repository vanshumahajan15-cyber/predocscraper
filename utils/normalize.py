"""Text normalization and deduplication key helpers."""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from models import JobRecord

WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = WHITESPACE_RE.sub(" ", value).strip().lower()
    return cleaned or None


def normalize_url(url: Optional[str], base_url: str = "") -> Optional[str]:
    """Normalize URLs for stable comparison (strip fragments, sort query params)."""
    if not url:
        return None

    url = url.strip()
    if base_url and not urlparse(url).netloc:
        url = urljoin(base_url, url)

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    sorted_query = urlencode(sorted(query.items()), doseq=True)
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or parsed.path,
            parsed.params,
            sorted_query,
            "",  # drop fragment
        )
    )
    return normalized


def generate_dedup_key(job: JobRecord) -> str:
    """Primary dedup key: prefer normalized URL, else title+institution hash."""
    normalized_url = normalize_url(job.job_url)
    if normalized_url:
        return f"url:{normalized_url}"

    fingerprint = "|".join(
        part
        for part in (
            normalize_text(job.title),
            normalize_text(job.institution or job.university),
        )
        if part
    )
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"hash:{digest}"


def title_institution_key(job: JobRecord) -> Optional[str]:
    """Secondary dedup key from normalized title + institution."""
    title = normalize_text(job.title)
    institution = normalize_text(job.institution or job.university)
    if not title or not institution:
        return None
    return f"ti:{title}|{institution}"


def title_key(job: JobRecord) -> Optional[str]:
    """Tertiary dedup key from normalized title alone."""
    title = normalize_text(job.title)
    return f"t:{title}" if title else None


def finalize_job(job: JobRecord, base_url: str = "") -> JobRecord:
    """Apply normalization and compute dedup metadata."""
    job.job_url = normalize_url(job.job_url, base_url=base_url) or job.job_url
    if job.institution and not job.university:
        job.university = job.institution
    elif job.university and not job.institution:
        job.institution = job.university
    job.dedup_key = generate_dedup_key(job)
    return job
