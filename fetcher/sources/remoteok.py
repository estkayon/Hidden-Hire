"""RemoteOK public API. Terms: link back to the job on Remote OK and name it as the source."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import FeedSource

API_URL = "https://remoteok.com/api"


class RemoteOKSource(FeedSource):
    name = "remoteok"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        data = http.get(client, API_URL).json()
        # The first element is a legal notice, not a job.
        return [item for item in data if isinstance(item, dict) and "id" in item]

    def parse(self, item: dict) -> Job:
        job_id = str(item["id"])
        url = item.get("url")
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["position"],
            company=item["company"],
            description=html_to_text(item.get("description") or ""),
            location_raw=item.get("location") or "",
            work_type="remote",
            apply_url=item.get("apply_url") or url,
            posted_at=item.get("date"),
        )
