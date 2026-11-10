"""Remotive public API. Terms: link back to Remotive, name it as the source, max 4 requests a day."""

import logging
from datetime import UTC, datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import FeedSource, FetchResult

API_URL = "https://remotive.com/api/remote-jobs"
RUN_EVERY_HOURS = 6  # with a 3-hour schedule this gives 4 runs a day

log = logging.getLogger(__name__)


class RemotiveSource(FeedSource):
    name = "remotive"

    def fetch(self, client: httpx.Client) -> FetchResult:
        if datetime.now(UTC).hour % RUN_EVERY_HOURS >= 3:
            log.info("%s: skipped this run (rate limit)", self.name)
            return FetchResult()
        return super().fetch(client)

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        return http.get(client, API_URL).json().get("jobs", [])

    def parse(self, item: dict) -> Job:
        job_id = str(item["id"])
        url = item.get("url")
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["title"],
            company=item["company_name"],
            description=html_to_text(item.get("description") or ""),
            location_raw=item.get("candidate_required_location") or "",
            work_type="remote",
            apply_url=url,
            posted_at=item.get("publication_date"),
        )
