"""Data models for scraped predoctoral research opportunities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class JobRecord:
    """Normalized job opportunity with all available scraped fields."""

    title: str
    institution: Optional[str] = None
    university: Optional[str] = None
    research_fields: Optional[str] = None
    location: Optional[str] = None
    researcher_names: Optional[str] = None
    application_deadline: Optional[str] = None
    date_posted: Optional[str] = None
    job_url: Optional[str] = None
    source_website: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None
    visa_sponsorship: Optional[str] = None
    dedup_key: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    def __post_init__(self) -> None:
        self.title = _clean(self.title) or "Untitled Position"
        self.institution = _clean(self.institution)
        self.university = _clean(self.university) or self.institution
        self.research_fields = _clean(self.research_fields)
        self.location = _clean(self.location)
        self.researcher_names = _clean(self.researcher_names)
        self.application_deadline = _clean(self.application_deadline)
        self.date_posted = _clean(self.date_posted)
        self.job_url = _clean(self.job_url)
        self.source_website = _clean(self.source_website)
        self.duration = _clean(self.duration)
        self.description = _clean(self.description)
        self.employment_type = _clean(self.employment_type)
        self.salary = _clean(self.salary)
        self.visa_sponsorship = _clean(self.visa_sponsorship)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRecord":
        allowed = set(cls.__dataclass_fields__.keys())
        filtered = {key: data.get(key) for key in allowed}
        return cls(**filtered)


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = " ".join(str(value).split())
    return cleaned or None
