"""
Scraper for https://www.nber.org/career-resources/research-assistant-positions-not-nber

HTML structure (2026):
- Listings live in div.page-header__intro-inner as consecutive <p> elements.
- Each job paragraph typically contains:
  Title (first line before <br>)
  NBER Sponsoring Researcher(s): ...
  Institution: ...
  Field(s) of Research: ...
  Link for Job Posting (anchor href)
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from config import NBER_URL
from models import JobRecord
from utils.http import fetch_html
from utils.normalize import finalize_job

logger = logging.getLogger(__name__)

JOB_MARKERS = (
    "institution:",
    "nber sponsoring researcher",
    "nber sponsoring researcher(s)",
)

LABEL_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"^nber sponsoring researcher(?:\(s\))?:\s*(.+)$", re.I), "researcher_names"),
    (re.compile(r"^institution:\s*(.+)$", re.I), "institution"),
    (re.compile(r"^field(?:\(s\))? of research:\s*(.+)$", re.I), "research_fields"),
    (re.compile(r"^deadline:\s*(.+)$", re.I), "application_deadline"),
    (re.compile(r"^location:\s*(.+)$", re.I), "location"),
    (re.compile(r"^start date:\s*(.+)$", re.I), "date_posted"),
    (re.compile(r"^visa(?: sponsorship)?:\s*(.+)$", re.I), "visa_sponsorship"),
]


def scrape_nber(url: str = NBER_URL) -> List[JobRecord]:
    """Scrape all opportunities from the NBER career resources page."""
    logger.info("Fetching NBER opportunities from %s", url)
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    container = soup.select_one("div.page-header__intro-inner")
    if not container:
        logger.error(
            "Could not find NBER listing container (page-header__intro-inner). "
            "The page layout may have changed."
        )
        return []

    paragraphs = container.find_all("p", recursive=False)
    logger.info("Found %d paragraph elements in NBER listing container", len(paragraphs))

    jobs: List[JobRecord] = []
    for paragraph in paragraphs:
        try:
            job = _parse_paragraph(paragraph, base_url=url)
            if job:
                jobs.append(finalize_job(job, base_url=url))
        except Exception:
            logger.exception("Failed to parse NBER paragraph")

    logger.info("Parsed %d NBER opportunities", len(jobs))
    return jobs


def _parse_paragraph(paragraph: Tag, base_url: str) -> Optional[JobRecord]:
    text = paragraph.get_text("\n", strip=True)
    lowered = text.lower()
    if not any(marker in lowered for marker in JOB_MARKERS):
        return None

    title = _extract_title(paragraph)
    if not title:
        return None

    fields = _extract_fields_from_lines(text)
    job_url = _extract_application_url(paragraph, base_url=base_url)
    description = _build_description(fields, fallback=text)

    return JobRecord(
        title=title,
        institution=fields.get("institution"),
        university=fields.get("institution"),
        research_fields=fields.get("research_fields"),
        location=fields.get("location"),
        researcher_names=fields.get("researcher_names"),
        application_deadline=fields.get("application_deadline"),
        date_posted=fields.get("date_posted"),
        job_url=job_url,
        source_website="nber.org",
        description=description,
        visa_sponsorship=fields.get("visa_sponsorship"),
    )


def _extract_title(paragraph: Tag) -> Optional[str]:
    parts: List[str] = []
    for child in paragraph.children:
        if getattr(child, "name", None) == "br":
            break
        if isinstance(child, str):
            text = child.strip()
            if text:
                parts.append(text)
        elif getattr(child, "name", None) == "a":
            continue
        else:
            text = child.get_text(strip=True)
            if text:
                parts.append(text)
    title = " ".join(parts).strip()
    return title or None


def _extract_fields_from_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[1:]:
        for pattern, field_name in LABEL_PATTERNS:
            match = pattern.match(line)
            if match:
                fields[field_name] = match.group(1).strip()
                break
    return fields


def _extract_application_url(paragraph: Tag, base_url: str) -> Optional[str]:
    for anchor in paragraph.find_all("a", href=True):
        href = anchor["href"].strip()
        if href and not href.startswith("#"):
            return urljoin(base_url, href)
    return None


def _build_description(fields: dict[str, str], fallback: str) -> str:
    parts = [
        f"Researcher Names: {fields['researcher_names']}" if fields.get("researcher_names") else None,
        f"Institution: {fields['institution']}" if fields.get("institution") else None,
        f"Research Fields: {fields['research_fields']}" if fields.get("research_fields") else None,
        f"Deadline: {fields['application_deadline']}" if fields.get("application_deadline") else None,
        f"Location: {fields['location']}" if fields.get("location") else None,
    ]
    description = " | ".join(part for part in parts if part)
    return description or fallback
