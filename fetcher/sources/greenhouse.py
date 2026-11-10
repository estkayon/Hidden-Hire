"""Greenhouse public job board API (one board per company)."""

import html

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseSource(BoardSource):
    name = "greenhouse"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        response = http.get(
            client, API_URL.format(token=token), params={"content": "true"}
        )
        return response.json().get("jobs", [])

    def parse(self, item: dict, token: str, company: str) -> Job:
        job_id = str(item["id"])
        url = item.get("absolute_url")
        return Job(
            id=make_job_id(self.name, f"{token}:{job_id}"),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["title"],
            company=company,
            description=html_to_text(html.unescape(item.get("content") or "")),
            location_raw=(item.get("location") or {}).get("name", ""),
            apply_url=url,
            posted_at=item.get("first_published") or item.get("updated_at"),
        )
