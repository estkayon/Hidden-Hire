"""BD Tech Jobs public JSON API (tech jobs from Bangladeshi companies)."""

from datetime import date

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority
from fetcher.sources.base import FeedSource

API_URL = "https://www.bdtechjobs.com/api/jobs"
LIMIT = 100
WORK_TYPES = {"remote", "hybrid", "onsite"}


def _iso_date(value: str | None) -> date | None:
    """Only clean YYYY-MM-DD values; the site also has 'Not available', 'nan', etc."""
    try:
        return date.fromisoformat(value or "")
    except ValueError:
        return None


def _description(item: dict) -> str:
    parts = []
    if item.get("experience"):
        parts.append(f"Experience: {item['experience']}")
    if item.get("requiredSkills"):
        parts.append("Skills: " + ", ".join(item["requiredSkills"]))
    return "\n".join(parts)


class BDTechJobsSource(FeedSource):
    name = "bdtechjobs"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        params = {"page": 1, "sortBy": "newest", "limit": LIMIT}
        return http.get(client, API_URL, params=params).json().get("jobs", [])

    def parse(self, item: dict) -> Job:
        job_id = str(item["id"])
        link = item.get("applyLink") or ""
        is_email = link.startswith("mailto:")
        work_type = (item.get("workType") or item.get("jobType") or "").lower()
        posted = _iso_date(item.get("postedDate"))
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=None if is_email else link or None,
            title=" ".join(item["designation"].split()),
            company=item["companyName"],
            description=_description(item),
            location_raw=item.get("location") or "",
            work_type=work_type if work_type in WORK_TYPES else "unknown",
            apply_url=None if is_email else link or None,
            apply_email=link.removeprefix("mailto:") if is_email else None,
            posted_at=posted.isoformat() if posted else None,
            deadline=_iso_date(item.get("applicationDeadline")),
            seniority=detect_seniority(item.get("seniorityLevel") or ""),
            tags=item.get("requiredSkills") or [],
        )
