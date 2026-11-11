"""RemoteIntegrity careers API (public JSON used by their careers page)."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.sources.base import FeedSource

API_URL = "https://atsserver.remoteintegrity.com/api/v1/ats-jobs/open"
CAREERS_URL = "https://careers.remoteintegrity.com/"
COMPANY = "RemoteIntegrity"


def _salary(item: dict) -> dict:
    salary = item.get("salary") or {}
    currency = (salary.get("currency") or "").upper()
    low, high = salary.get("min"), salary.get("max")
    if salary.get("hideSalary") or len(currency) != 3 or (low is None and high is None):
        return {}
    return {"salary_min": low, "salary_max": high, "salary_currency": currency}


class RemoteIntegritySource(FeedSource):
    name = "remoteintegrity"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        data = http.get(client, API_URL).json()
        return [item for item in data.get("data") or [] if item.get("status") == "Open"]

    def parse(self, item: dict) -> Job:
        job_id = item["_id"]
        location = item.get("location") or ""
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=CAREERS_URL,
            title=item["title"],
            company=COMPANY,
            description=(item.get("description") or "").replace("**", "").strip(),
            location_raw=location,
            work_type="remote" if "remote" in location.lower() else "unknown",
            apply_url=CAREERS_URL,
            posted_at=item.get("createdAt"),
            **_salary(item),
        )
