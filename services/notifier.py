"""ntfy.sh push notification delivery."""

from __future__ import annotations

import logging
from typing import List

import requests

from config import NTFY_BASE_URL, NTFY_TITLE, NTFY_TOPIC, REQUEST_TIMEOUT
from models import JobRecord

logger = logging.getLogger(__name__)

MAX_MESSAGE_BYTES = 3800
NO_NEW_JOBS_MESSAGE = "Predoc Scraper: No new opportunities found today."


def send_notification(new_jobs: List[JobRecord]) -> bool:
    """Send ntfy notification for new jobs or a no-new-jobs message."""
    if new_jobs:
        message = _format_new_jobs_message(new_jobs)
        title = f"{NTFY_TITLE}: {len(new_jobs)} new job(s)"
    else:
        message = NO_NEW_JOBS_MESSAGE
        title = NTFY_TITLE

    url = f"{NTFY_BASE_URL.rstrip('/')}/{NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Tags": "books,mag",
        "Priority": "3",
    }
    if len(new_jobs) == 1 and new_jobs[0].job_url:
        headers["Click"] = new_jobs[0].job_url

    try:
        response = requests.post(
            url,
            data=message.encode("utf-8"),
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        logger.info("ntfy notification sent to %s", url)
        return True
    except requests.RequestException as exc:
        logger.exception("Failed to send ntfy notification to %s: %s", url, exc)
        return False


def _format_new_jobs_message(new_jobs: List[JobRecord]) -> str:
    lines = [f"{len(new_jobs)} new predoc opportunity(ies) found:\n"]

    for job in new_jobs:
        institution = job.institution or job.university or "Unknown Institution"
        link = job.job_url or "No link available"
        block = f"• {job.title}\n  {institution}\n  {link}"
        candidate = "\n".join(lines + [block])
        if len(candidate.encode("utf-8")) > MAX_MESSAGE_BYTES:
            remaining = len(new_jobs) - (len(lines) - 1)
            lines.append(f"\n...and {remaining} more (see data/predoc_jobs.csv)")
            break
        lines.append(block)

    return "\n".join(lines).strip()
