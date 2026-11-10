"""Bundesagentur fuer Arbeit job search API (Germany). Uses the public client id, not a secret."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import load_config, lookup_country
from fetcher.sources.base import FeedSource

API_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}
JOB_PAGE_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}"

DEFAULT_COUNTRY = "DE"


class ArbeitsagenturSource(FeedSource):
    name = "arbeitsagentur"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        items: dict[str, dict] = {}
        for query in load_config("keywords.yaml")["search_queries"]:
            params = {
                "was": query,
                "angebotsart": 1,
                "veroeffentlichtseit": 1,
                "size": 100,
            }
            data = http.get(client, API_URL, params=params, headers=HEADERS).json()
            for item in data.get("ergebnisliste") or []:
                items.setdefault(item.get("referenznummer", ""), item)
        return [item for ref, item in items.items() if ref]

    def parse(self, item: dict) -> Job:
        ref = item["referenznummer"]
        locations = item.get("stellenlokationen") or [{}]
        address = locations[0].get("adresse") or {}
        city = address.get("ort") or ""
        land = address.get("land") or ""
        url = JOB_PAGE_URL.format(ref=ref)
        return Job(
            id=make_job_id(self.name, ref),
            source=self.name,
            source_job_id=ref,
            source_url=url,
            title=item["stellenangebotsTitel"],
            company=item["firma"],
            location_raw=", ".join(part for part in (city, land.title()) if part),
            country=lookup_country(land) or DEFAULT_COUNTRY,
            city=city or None,
            apply_url=url,
            posted_at=item.get("datumErsteVeroeffentlichung"),
        )
