"""Reed.co.uk job search API (UK). Needs REED_API_KEY."""

import base64
from datetime import datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import load_config
from fetcher.sources.base import FeedSource, FetchResult

API_URL = "https://www.reed.co.uk/api/1.0/search"
DATE_FORMAT = "%d/%m/%Y"
PAGE_SIZE = 100


def _salary(item: dict) -> dict:
    """Amounts and currency as stated; Reed gives no salary period, so none is set."""
    currency = (item.get("currency") or "").upper()
    low, high = item.get("minimumSalary"), item.get("maximumSalary")
    if (low is None and high is None) or len(currency) != 3:
        return {}
    return {"salary_min": low, "salary_max": high, "salary_currency": currency}


class ReedSource(FeedSource):
    name = "reed"

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def fetch(self, client: httpx.Client) -> FetchResult:
        if not self.api_key:
            return FetchResult(errors=[f"{self.name}: missing REED_API_KEY"])
        return super().fetch(client)

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        token = base64.b64encode(f"{self.api_key}:".encode()).decode()
        headers = {"Authorization": f"Basic {token}"}
        items: dict[int, dict] = {}
        for query in load_config("keywords.yaml")["search_queries"]:
            params = {"keywords": query, "resultsToTake": PAGE_SIZE}
            for item in (
                http.get(client, API_URL, params=params, headers=headers)
                .json()
                .get("results")
                or []
            ):
                items.setdefault(item.get("jobId"), item)
        return [item for job_id, item in items.items() if job_id]

    def parse(self, item: dict) -> Job:
        job_id = str(item["jobId"])
        url = item.get("jobUrl")
        location = item.get("locationName") or ""
        posted = item.get("date")
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["jobTitle"],
            company=item["employerName"],
            description=item.get("jobDescription") or "",
            location_raw=location,
            country="GB",
            city=location or None,
            apply_url=url,
            posted_at=datetime.strptime(posted, DATE_FORMAT) if posted else None,
            **_salary(item),
        )
