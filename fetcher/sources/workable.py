"""Workable public widget API (one account per company)."""

from datetime import datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://apply.workable.com/api/v1/widget/accounts/{token}"


def _visible_locations(item: dict) -> list[dict]:
    return [
        loc
        for loc in item.get("locations") or []
        if isinstance(loc, dict) and not loc.get("hidden")
    ]


def _location_text(location: dict) -> str:
    parts = (location.get("city"), location.get("region"), location.get("country"))
    return ", ".join(part for part in parts if part)


class WorkableSource(BoardSource):
    name = "workable"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        response = http.get(
            client, API_URL.format(token=token), params={"details": "true"}
        )
        return response.json().get("jobs", [])

    def parse(self, item: dict, token: str, company: str) -> Job:
        locations = _visible_locations(item)
        first = locations[0] if locations else {}
        country_code = first.get("countryCode") or ""
        published = item.get("published_on") or item.get("created_at")
        return Job(
            id=make_job_id(self.name, f"{token}:{item['shortcode']}"),
            source=self.name,
            source_job_id=item["shortcode"],
            source_url=item.get("url"),
            title=item["title"],
            company=company,
            description=html_to_text(item.get("description") or ""),
            location_raw="; ".join(_location_text(loc) for loc in locations),
            country=country_code.upper() if len(country_code) == 2 else None,
            city=first.get("city") or None,
            work_type="remote" if item.get("telecommuting") else "unknown",
            apply_url=item.get("application_url") or item.get("url"),
            posted_at=datetime.fromisoformat(published) if published else None,
        )
