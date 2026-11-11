"""SEEK (AU, NZ) and JobStreet (MY, PH) job search via the site's own public JSON endpoint.

Undocumented endpoint: it may change without notice. Runs only twice a day to stay polite.
"""

import logging
from datetime import UTC, datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import load_config
from fetcher.sources.base import (
    FetchResult,
    Source,
    _parse_items,
    _record_error,
    describe_error,
)

SITES = {
    "AU-Main": "https://au.seek.com",
    "NZ-Main": "https://nz.seek.com",
    "MY-Main": "https://my.jobstreet.com",
    "PH-Main": "https://ph.jobstreet.com",
    "SG-Main": "https://sg.jobstreet.com",
}
SEARCH_PATH = "/api/jobsearch/v5/search"
RUN_EVERY_HOURS = 12  # with a 3-hour schedule this gives 2 runs a day

log = logging.getLogger(__name__)


class SeekSource(Source):
    name = "seek"

    def fetch(self, client: httpx.Client) -> FetchResult:
        result = FetchResult()
        if datetime.now(UTC).hour % RUN_EVERY_HOURS >= 3:
            log.info("%s: skipped this run (twice a day)", self.name)
            return result
        for site_key, host in SITES.items():
            label = f"{self.name}/{site_key}"
            try:
                items = self._search_site(client, site_key, host)
            except (httpx.HTTPError, ValueError) as exc:
                _record_error(result, f"{label}: {describe_error(exc)}")
                continue
            _parse_items(result, items, lambda item, h=host: self.parse(item, h), label)
        return result

    def _search_site(
        self, client: httpx.Client, site_key: str, host: str
    ) -> list[dict]:
        items: dict[str, dict] = {}
        for query in load_config("keywords.yaml")["search_queries"]:
            params = {
                "siteKey": site_key,
                "keywords": query,
                "page": 1,
                "sortmode": "ListedDate",
            }
            for item in (
                http.get(client, host + SEARCH_PATH, params=params).json().get("data")
                or []
            ):
                items.setdefault(str(item.get("id", "")), item)
        return [item for job_id, item in items.items() if job_id]

    def parse(self, item: dict, host: str) -> Job:
        job_id = str(item["id"])
        location = (item.get("locations") or [{}])[0]
        country = location.get("countryCode") or ""
        url = f"{host}/job/{job_id}"
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["title"],
            company=item.get("companyName")
            or (item.get("advertiser") or {})["description"],
            description=item.get("teaser") or "",
            location_raw=location.get("label") or "",
            country=country.upper() if len(country) == 2 else None,
            apply_url=url,
            posted_at=item.get("listingDate"),
        )
