"""Jobicy public API. Terms: credit Jobicy with a link; apply links go to the feed's job URL."""

from datetime import UTC, datetime, timedelta

import httpx

from fetcher import http
from fetcher.filters import RETENTION_DAYS
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority, html_to_text
from fetcher.sources.base import FeedSource

API_URL = "https://jobicy.com/api/v2/remote-jobs"
COUNT = 50
MAX_PAGES = 10
SALARY_PERIODS = {
    "yearly": "year",
    "annual": "year",
    "monthly": "month",
    "weekly": "week",
    "daily": "day",
    "hourly": "hour",
}


def _salary(item: dict) -> dict:
    """Salary fields only when the posting states an amount and currency."""
    low, high = item.get("salaryMin"), item.get("salaryMax")
    currency = (item.get("salaryCurrency") or "").upper()
    period = SALARY_PERIODS.get((item.get("salaryPeriod") or "").lower())
    if (low is None and high is None) or len(currency) != 3 or period is None:
        return {}
    return {
        "salary_min": low,
        "salary_max": high,
        "salary_currency": currency,
        "salary_period": period,
    }


class JobicySource(FeedSource):
    name = "jobicy"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
        items: list[dict] = []
        cursor = None
        for _ in range(MAX_PAGES):
            params = {"count": COUNT, **({"cursor": cursor} if cursor else {})}
            data = http.get(client, API_URL, params=params).json()
            jobs = data.get("jobs") or []
            items.extend(jobs)
            cursor = data.get("nextCursor")
            last = jobs[-1].get("pubDate") if jobs else None
            if not jobs or not data.get("hasMore") or not cursor:
                break
            if last and datetime.fromisoformat(last) < cutoff:
                break
        return items

    def parse(self, item: dict) -> Job:
        job_id = str(item["id"])
        url = item["url"]
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["jobTitle"],
            company=item["companyName"],
            description=html_to_text(item.get("jobDescription") or ""),
            location_raw=(item.get("jobGeo") or "").replace(", ", "; "),
            work_type="remote",
            apply_url=url,
            posted_at=item.get("pubDate"),
            seniority=detect_seniority(item.get("jobLevel") or ""),
            **_salary(item),
        )
