"""
Scraper for https://www.predoc.org/opportunities

HTML structure (2026):
- Each opportunity is an <article> element.
- Title + application URL: article h2 a[href]
- Metadata: div.swiss-text with labeled <strong> fields:
  Sponsoring Researcher(s), Sponsoring Institution, Fields of Research,
  Deadline, Location, Start Date, Visa, etc.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from config import PREDOC_URL
from models import JobRecord
from utils.http import fetch_html
from utils.normalize import finalize_job

logger = logging.getLogger(__name__)

FIELD_ALIASES: Dict[str, str] = {
    "sponsoring researcher(s)": "researcher_names",
    "sponsoring researchers(s)": "researcher_names",
    "sponsoring institution": "institution",
    "sponsoring institution(s)": "institution",
    "fields of research": "research_fields",
    "field(s) of research": "research_fields",
    "deadline": "application_deadline",
    "deadline/first review date": "application_deadline",
    "location": "location",
    "start date": "date_posted",
    "visa": "visa_sponsorship",
    "duration": "duration",
    "employment type": "employment_type",
    "salary": "salary",
    "compensation": "salary",
}

TEXT_FIELD_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"sponsoring researcher(?:\(s\))?s?\)?\s*:\s*(.+?)"
            r"(?=\s*sponsoring institution|\s*fields? of research|\s*deadline|\s*location|\s*visa|\s*start date|$)",
            re.I | re.S,
        ),
        "researcher_names",
    ),
    (
        re.compile(
            r"sponsoring institution(?:\(s\))?\s*:\s*(.+?)"
            r"(?=\s*fields? of research|\s*deadline|\s*location|\s*visa|\s*start date|$)",
            re.I | re.S,
        ),
        "institution",
    ),
    (
        re.compile(
            r"fields? of research\s*:\s*(.+?)"
            r"(?=\s*deadline|\s*location|\s*visa|\s*start date|$)",
            re.I | re.S,
        ),
        "research_fields",
    ),
    (
        re.compile(
            r"(?:deadline|deadline/first review date)\s*:\s*(.+?)"
            r"(?=\s*visa|\s*start date|$)",
            re.I | re.S,
        ),
        "application_deadline",
    ),
    (re.compile(r"location\s*:\s*(.+?)(?=\s*visa|\s*start date|$)", re.I | re.S), "location"),
    (re.compile(r"start date\s*:\s*(.+?)(?=\s*visa|$)", re.I | re.S), "date_posted"),
    (re.compile(r"visa\s*:\s*(.+)$", re.I | re.S), "visa_sponsorship"),
]


def scrape_predoc(url: str = PREDOC_URL) -> List[JobRecord]:
    """Scrape all opportunities from predoc.org."""
    logger.info("Fetching predoc.org opportunities from %s", url)
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article")
    logger.info("Found %d article elements on predoc.org", len(articles))

    if not articles:
        logger.warning(
            "No article elements found on predoc.org — page layout may have changed."
        )

    jobs: List[JobRecord] = []
    for article in articles:
        try:
            job = _parse_article(article)
            if job:
                jobs.append(finalize_job(job, base_url=url))
        except Exception:
            title_tag = article.find("h2")
            title_text = title_tag.get_text(strip=True) if title_tag else "unknown"
            logger.exception("Failed to parse predoc article '%s'", title_text)

    logger.info("Parsed %d predoc.org opportunities", len(jobs))
    return jobs


def _parse_article(article: Tag) -> Optional[JobRecord]:
    title_link = article.select_one("h2 a")
    title_tag = article.find("h2")
    if not title_tag:
        return None

    title = title_link.get_text(strip=True) if title_link else title_tag.get_text(strip=True)
    if not title:
        return None

    job_url = None
    if title_link and title_link.get("href"):
        job_url = title_link["href"].strip()
    else:
        img_link = article.select_one("a.swiss-img")
        if img_link and img_link.get("href"):
            job_url = img_link["href"].strip()

    fields = _extract_labeled_fields(article)
    description = _build_description(fields)

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
        source_website="predoc.org",
        duration=fields.get("duration"),
        description=description,
        employment_type=fields.get("employment_type"),
        salary=fields.get("salary"),
        visa_sponsorship=fields.get("visa_sponsorship"),
    )


def _extract_labeled_fields(article: Tag) -> Dict[str, str]:
    extracted: Dict[str, str] = {}
    swiss_text = article.select_one("div.swiss-text")
    if not swiss_text:
        return extracted

    for strong in swiss_text.find_all("strong"):
        label = _normalize_label(strong.get_text())
        field_key = FIELD_ALIASES.get(label)
        if not field_key:
            continue
        value = _value_after_label(strong)
        if value:
            extracted[field_key] = value

    plain_text = swiss_text.get_text(" ", strip=True)
    for pattern, field_key in TEXT_FIELD_PATTERNS:
        if field_key in extracted:
            continue
        match = pattern.search(plain_text)
        if match:
            extracted[field_key] = _clean_field_value(match.group(1))

    return extracted


def _normalize_label(text: str) -> str:
    return re.sub(r"[\s:]+$", "", text.strip().lower())


def _value_after_label(strong: Tag) -> str:
    chunks: List[str] = []
    for sibling in strong.next_siblings:
        if isinstance(sibling, str):
            text = sibling.strip()
            if text:
                chunks.append(text)
            continue
        if getattr(sibling, "name", None) == "strong":
            break
        if getattr(sibling, "name", None) == "br":
            continue
        text = sibling.get_text(" ", strip=True)
        if text:
            chunks.append(text)
    return _clean_field_value(" ".join(chunks))


def _clean_field_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" :;-")
    value = re.sub(r"^\)\s*:\s*", "", value)
    return value.strip()


def _build_description(fields: Dict[str, str]) -> Optional[str]:
    if not fields:
        return None
    label_map = {
        "researcher_names": "Researcher Names",
        "institution": "Institution",
        "research_fields": "Research Fields",
        "application_deadline": "Application Deadline",
        "location": "Location",
        "date_posted": "Date Posted",
        "visa_sponsorship": "Visa Sponsorship",
        "duration": "Duration",
        "employment_type": "Employment Type",
        "salary": "Salary",
    }
    parts = [
        f"{label_map.get(key, key)}: {value}"
        for key, value in fields.items()
        if value
    ]
    return " | ".join(parts) if parts else None
