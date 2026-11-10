"""MyCareersFuture (Singapore government job board) public API."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text, load_config, lookup_country
from fetcher.sources.base import FeedSource

API_URL = "https://api.mycareersfuture.gov.sg/v2/jobs"
PAGE_SIZE = 50
CURRENCY = "SGD"  # the board lists salaries in Singapore dollars
SALARY_PERIODS = {
    "monthly": "month",
    "annual": "year",
    "yearly": "year",
    "hourly": "hour",
    "daily": "day",
    "weekly": "week",
}


def _salary(item: dict) -> dict:
    if (item.get("metadata") or {}).get("isHideSalary"):
        return {}
    salary = item.get("salary") or {}
    period = SALARY_PERIODS.get(
        ((salary.get("type") or {}).get("salaryType") or "").lower()
    )
    low, high = salary.get("minimum"), salary.get("maximum")
    if period is None or (low is None and high is None):
        return {}
    return {
        "salary_min": low,
        "salary_max": high,
        "salary_currency": CURRENCY,
        "salary_period": period,
    }


def _location(item: dict) -> tuple[str, str | None]:
    address = item.get("address") or {}
    if address.get("isOverseas"):
        overseas = address.get("overseasCountry") or ""
        return overseas, lookup_country(overseas)
    districts = [
        d.get("location") for d in address.get("districts") or [] if d.get("location")
    ]
    return ", ".join([*districts, "Singapore"]), "SG"


class MyCareersFutureSource(FeedSource):
    name = "mycareersfuture"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        items: dict[str, dict] = {}
        for query in load_config("keywords.yaml")["search_queries"]:
            params = {
                "search": query,
                "limit": PAGE_SIZE,
                "page": 0,
                "sortBy": "new_posting_date",
            }
            for item in (
                http.get(client, API_URL, params=params).json().get("results") or []
            ):
                items.setdefault(item.get("uuid", ""), item)
        return [item for uuid, item in items.items() if uuid]

    def parse(self, item: dict) -> Job:
        metadata = item.get("metadata") or {}
        location_raw, country = _location(item)
        url = metadata.get("jobDetailsUrl")
        return Job(
            id=make_job_id(self.name, item["uuid"]),
            source=self.name,
            source_job_id=item["uuid"],
            source_url=url,
            title=item["title"],
            company=(item.get("postedCompany") or {})["name"],
            description=html_to_text(item.get("description") or ""),
            location_raw=location_raw,
            country=country,
            apply_url=url,
            posted_at=metadata.get("originalPostingDate"),
            **_salary(item),
        )
