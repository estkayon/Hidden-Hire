"""SmartRecruiters public Posting API (one company per board)."""

from datetime import UTC, datetime, timedelta

import httpx

from fetcher import http
from fetcher.filters import RETENTION_DAYS, is_tech, is_too_senior
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
PAGE_SIZE = 100
MAX_PAGES = 100
SECTION_KEYS = ("jobDescription", "qualifications", "additionalInformation")


def _is_candidate(item: dict, now: datetime) -> bool:
    """Cheap check on list data, so details are fetched only for likely matches."""
    released = item.get("releasedDate")
    if released:
        try:
            if now - datetime.fromisoformat(released) > timedelta(days=RETENTION_DAYS):
                return False
        except ValueError:
            pass
    title = item.get("name") or ""
    return is_tech(title) and not is_too_senior(title)


def _work_type(location: dict) -> str:
    if location.get("remote"):
        return "remote"
    if location.get("hybrid"):
        return "hybrid"
    return "onsite" if location else "unknown"


class SmartRecruitersSource(BoardSource):
    name = "smartrecruiters"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        url = API_URL.format(token=token)
        now = datetime.now(UTC)
        candidates = []
        for page in range(MAX_PAGES):
            params = {"limit": PAGE_SIZE, "offset": page * PAGE_SIZE}
            data = http.get(client, url, params=params).json()
            content = data.get("content") or []
            candidates.extend(item for item in content if _is_candidate(item, now))
            if not content or (page + 1) * PAGE_SIZE >= data.get("totalFound", 0):
                break
        return [self._details(client, url, item) for item in candidates]

    def _details(self, client: httpx.Client, url: str, item: dict) -> dict:
        """Full posting with description; falls back to the list item on failure."""
        try:
            return http.get(client, f"{url}/{item['id']}").json()
        except (httpx.HTTPError, ValueError, KeyError):
            return item

    def parse(self, item: dict, token: str, company: str) -> Job:
        location = item.get("location") or {}
        country = location.get("country") or ""
        sections = (item.get("jobAd") or {}).get("sections") or {}
        description = "\n".join(
            html_to_text((sections.get(key) or {}).get("text") or "")
            for key in SECTION_KEYS
        ).strip()
        job_id = str(item["id"])
        return Job(
            id=make_job_id(self.name, f"{token}:{job_id}"),
            source=self.name,
            source_job_id=job_id,
            source_url=item.get("postingUrl"),
            title=item["name"],
            company=company,
            description=description,
            location_raw=location.get("fullLocation") or "",
            country=country.upper() if len(country) == 2 else None,
            city=location.get("city") or None,
            work_type=_work_type(location),
            apply_url=item.get("applyUrl") or item.get("postingUrl"),
            posted_at=item.get("releasedDate"),
        )
