"""Lever public postings API (one board per company)."""

from datetime import UTC, datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://api.lever.co/v0/postings/{token}"
WORK_TYPES = {"remote", "hybrid", "onsite"}


def _description(item: dict) -> str:
    parts = [item.get("descriptionPlain") or ""]
    for section in item.get("lists") or []:
        if isinstance(section, dict):
            parts.append(section.get("text") or "")
            parts.append(html_to_text(section.get("content") or ""))
    parts.append(item.get("additionalPlain") or "")
    return "\n".join(part.strip() for part in parts if part.strip())


class LeverSource(BoardSource):
    name = "lever"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        response = http.get(
            client, API_URL.format(token=token), params={"mode": "json"}
        )
        return response.json()

    def parse(self, item: dict, token: str, company: str) -> Job:
        categories = item.get("categories") or {}
        locations = categories.get("allLocations") or [categories.get("location") or ""]
        country = item.get("country") or ""
        workplace = item.get("workplaceType") or ""
        created_ms = item.get("createdAt")
        return Job(
            id=make_job_id(self.name, f"{token}:{item['id']}"),
            source=self.name,
            source_job_id=item["id"],
            source_url=item.get("hostedUrl"),
            title=item["text"],
            company=company,
            description=_description(item),
            location_raw="; ".join(locations),
            country=country.upper() if len(country) == 2 else None,
            work_type=workplace if workplace in WORK_TYPES else "unknown",
            apply_url=item.get("applyUrl") or item.get("hostedUrl"),
            posted_at=datetime.fromtimestamp(created_ms / 1000, UTC)
            if created_ms
            else None,
        )
