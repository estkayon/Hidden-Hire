"""Bulldogjob listing pages (job data embedded as Next.js page data)."""

import json
import re

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority
from fetcher.sources.base import FeedSource

BASE_URL = "https://bulldogjob.com"
SEARCHES = ["city,Switzerland"]  # path parts after /companies/jobs/s/
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


class BulldogjobSource(FeedSource):
    name = "bulldogjob"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        items: dict[str, dict] = {}
        for search in SEARCHES:
            page = http.get(client, f"{BASE_URL}/companies/jobs/s/{search}").text
            match = NEXT_DATA.search(page)
            if match is None:
                raise ValueError("page data not found")
            for job in (
                json.loads(match.group(1))["props"]["pageProps"].get("jobs") or []
            ):
                items.setdefault(job.get("id", ""), job)
        return [job for job_id, job in items.items() if job_id]

    def parse(self, item: dict) -> Job:
        url = f"{BASE_URL}/companies/jobs/{item['id']}"
        tags = item.get("technologyTags") or []
        return Job(
            id=make_job_id(self.name, item["id"]),
            source=self.name,
            source_job_id=item["id"],
            source_url=url,
            title=item["position"],
            company=(item.get("company") or {})["name"],
            description="Tech stack: " + ", ".join(tags) if tags else "",
            location_raw=(item.get("city") or "").replace(", ", "; "),
            work_type="remote" if item.get("remote") else "unknown",
            apply_url=url,
            seniority=detect_seniority(item.get("experienceLevel")),
            tags=tags if isinstance(tags, list) else [],
        )
