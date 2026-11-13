"""Recruiterbox (Trakstar Hire) public openings API, one board per company (e.g. Therap BD)."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://jsapi.recruiterbox.com/v1/openings"
PAGE_SIZE = 50
MAX_PAGES = 20


class RecruiterboxSource(BoardSource):
    name = "recruiterbox"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        items: list[dict] = []
        for page in range(MAX_PAGES):
            params = {
                "client_name": token,
                "limit": PAGE_SIZE,
                "offset": page * PAGE_SIZE,
            }
            data = http.get(client, API_URL, params=params).json()
            objects = data.get("objects") or []
            items.extend(objects)
            if not objects or len(items) >= (data.get("meta") or {}).get("total", 0):
                break
        return items

    def parse(self, item: dict, token: str, company: str) -> Job:
        location = item.get("location") or {}
        country = (location.get("country") or "").strip()
        url = item.get("hosted_url")
        job_id = str(item["id"])
        return Job(
            id=make_job_id(self.name, f"{token}:{job_id}"),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["title"],
            company=company,
            description=html_to_text(item.get("description") or ""),
            location_raw=", ".join(filter(None, [location.get("city"), country])),
            country="BD" if country.lower() == "bangladesh" else None,
            # Boards label these "Partially remote", so treat them as hybrid.
            work_type="hybrid" if item.get("allows_remote") else "unknown",
            apply_url=url,
            posted_at=None,
        )
