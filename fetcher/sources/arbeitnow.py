"""Arbeitnow public job board API (mostly Germany)."""

from datetime import UTC, datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_location, html_to_text
from fetcher.sources.base import FeedSource

API_URL = "https://www.arbeitnow.com/api/job-board-api"
DEFAULT_COUNTRY = "DE"


class ArbeitnowSource(FeedSource):
    name = "arbeitnow"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        return http.get(client, API_URL).json().get("data", [])

    def parse(self, item: dict) -> Job:
        location = item.get("location") or ""
        created = item.get("created_at")
        return Job(
            id=make_job_id(self.name, item["slug"]),
            source=self.name,
            source_job_id=item["slug"],
            source_url=item.get("url"),
            title=item["title"],
            company=item["company_name"],
            description=html_to_text(item.get("description") or ""),
            location_raw=location,
            country=detect_location(location)[0] or DEFAULT_COUNTRY,
            work_type="remote" if item.get("remote") else "unknown",
            apply_url=item.get("url"),
            posted_at=datetime.fromtimestamp(created, UTC) if created else None,
        )
