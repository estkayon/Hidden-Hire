"""Working Nomads public jobs API (single list of recent remote jobs)."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import FeedSource

API_URL = "https://www.workingnomads.com/api/exposed_jobs/"


class WorkingNomadsSource(FeedSource):
    name = "workingnomads"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        data = http.get(client, API_URL).json()
        return [item for item in data if isinstance(item, dict)]

    def parse(self, item: dict) -> Job:
        url = item["url"]
        return Job(
            id=make_job_id(self.name, url),
            source=self.name,
            source_url=url,
            title=item["title"],
            company=item["company_name"],
            description=html_to_text(item.get("description") or ""),
            location_raw=(item.get("location") or "").replace(", ", "; "),
            work_type="remote",
            apply_url=url,
            posted_at=item.get("pub_date"),
        )
