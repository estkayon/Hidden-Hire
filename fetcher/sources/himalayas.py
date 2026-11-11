"""Himalayas public jobs API (newest first, cursor pagination)."""

from datetime import UTC, datetime, timedelta

import httpx

from fetcher import http
from fetcher.filters import RETENTION_DAYS
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority, html_to_text
from fetcher.sources.base import FeedSource

API_URL = "https://himalayas.app/jobs/api"
PAGE_SIZE = 20
MAX_PAGES = 25
SALARY_PERIODS = {
    "annual": "year",
    "monthly": "month",
    "weekly": "week",
    "daily": "day",
    "hourly": "hour",
}


def _salary(item: dict) -> dict:
    """Salary fields only when the posting states an amount and currency."""
    low, high = item.get("minSalary"), item.get("maxSalary")
    currency = (item.get("currency") or "").upper()
    period = SALARY_PERIODS.get((item.get("salaryPeriod") or "").lower())
    if (low is None and high is None) or len(currency) != 3 or period is None:
        return {}
    return {
        "salary_min": low,
        "salary_max": high,
        "salary_currency": currency,
        "salary_period": period,
    }


class HimalayasSource(FeedSource):
    name = "himalayas"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        cutoff = (datetime.now(UTC) - timedelta(days=RETENTION_DAYS)).timestamp()
        items: list[dict] = []
        cursor = None
        for _ in range(MAX_PAGES):
            params = {"limit": PAGE_SIZE, **({"cursor": cursor} if cursor else {})}
            data = http.get(client, API_URL, params=params).json()
            jobs = data.get("jobs") or []
            items.extend(jobs)
            cursor = data.get("nextCursor")
            oldest = min((job.get("pubDate") or 0 for job in jobs), default=0)
            if not jobs or not cursor or oldest < cutoff:
                break
        return items

    def parse(self, item: dict) -> Job:
        url = item["guid"]
        published = item.get("pubDate")
        return Job(
            id=make_job_id(self.name, url),
            source=self.name,
            source_url=url,
            title=item["title"],
            company=item["companyName"],
            description=html_to_text(item.get("description") or ""),
            location_raw="; ".join(item.get("locationRestrictions") or []),
            work_type="remote",
            apply_url=item.get("applicationLink") or url,
            posted_at=datetime.fromtimestamp(published, UTC) if published else None,
            seniority=detect_seniority(item.get("seniority")),
            **_salary(item),
        )
