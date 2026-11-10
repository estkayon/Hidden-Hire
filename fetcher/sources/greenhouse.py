"""Greenhouse public job board API (one board per company)."""

import html
import logging

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import FetchResult, Source, describe_error

API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

log = logging.getLogger(__name__)


class GreenhouseSource(Source):
    name = "greenhouse"

    def __init__(self, boards: dict[str, str]) -> None:
        """boards: board token -> company display name."""
        self.boards = boards

    def fetch(self, client: httpx.Client) -> FetchResult:
        result = FetchResult()
        for token, company in self.boards.items():
            try:
                response = http.get(
                    client, API_URL.format(token=token), params={"content": "true"}
                )
                items = response.json().get("jobs", [])
            except (httpx.HTTPError, ValueError) as exc:
                error = f"{self.name}/{token}: {describe_error(exc)}"
                log.warning(error)
                result.errors.append(error)
                continue

            for item in items:
                try:
                    result.jobs.append(self._parse(item, token, company))
                except (KeyError, TypeError, ValueError) as exc:
                    result.errors.append(
                        f"{self.name}/{token}: bad job ({describe_error(exc)})"
                    )
        return result

    def _parse(self, item: dict, token: str, company: str) -> Job:
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
