"""Ashby public job board API (one board per company)."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import lookup_country
from fetcher.sources.base import BoardSource

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"
WORK_TYPES = {"remote", "hybrid", "onsite"}


def _locations(item: dict) -> list[str]:
    names = [item.get("location") or ""]
    for extra in item.get("secondaryLocations") or []:
        names.append(
            extra.get("location", "") if isinstance(extra, dict) else str(extra)
        )
    return [name for name in names if name]


def _work_type(item: dict) -> str:
    workplace = (item.get("workplaceType") or "").lower()
    if workplace in WORK_TYPES:
        return workplace
    return "remote" if item.get("isRemote") else "unknown"


class AshbySource(BoardSource):
    name = "ashby"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        jobs = http.get(client, API_URL.format(token=token)).json().get("jobs", [])
        return [job for job in jobs if job.get("isListed", True)]

    def parse(self, item: dict, token: str, company: str) -> Job:
        address = (item.get("address") or {}).get("postalAddress") or {}
        return Job(
            id=make_job_id(self.name, f"{token}:{item['id']}"),
            source=self.name,
            source_job_id=item["id"],
            source_url=item.get("jobUrl"),
            title=item["title"],
            company=company,
            description=item.get("descriptionPlain") or "",
            location_raw="; ".join(_locations(item)),
            country=lookup_country(address.get("addressCountry") or ""),
            city=address.get("addressLocality") or None,
            work_type=_work_type(item),
            apply_url=item.get("applyUrl") or item.get("jobUrl"),
            posted_at=item.get("publishedAt"),
        )
