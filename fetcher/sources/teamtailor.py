"""Teamtailor career-site RSS feed (documented by Teamtailor for syndication)."""

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text, lookup_country
from fetcher.sources.base import BoardSource

FEED_URL = "https://{token}/jobs.rss"
TT = "{https://teamtailor.com/locations}"
REMOTE_STATUS = {
    "hybrid": "hybrid",
    "fully": "remote",
    "remote": "remote",
    "none": "onsite",
}


def _text(element: ET.Element, tag: str) -> str:
    return (element.findtext(tag) or element.findtext(TT + tag) or "").strip()


def _locations(item: ET.Element) -> list[tuple[str, str]]:
    """(city, country) pairs."""
    return [
        (_text(loc, "city") or _text(loc, "name"), _text(loc, "country"))
        for loc in item.iter(TT + "location")
    ]


class TeamtailorSource(BoardSource):
    name = "teamtailor"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        content = http.get(
            client, FEED_URL.format(token=token), params={"per_page": 100}
        ).content
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError("invalid RSS") from exc
        return [
            {
                "title": _text(item, "title"),
                "description": _text(item, "description"),
                "link": _text(item, "link"),
                "guid": _text(item, "guid"),
                "pubDate": _text(item, "pubDate"),
                "remoteStatus": _text(item, "remoteStatus").lower(),
                "locations": _locations(item),
            }
            for item in root.iter("item")
        ]

    def parse(self, item: dict, token: str, company: str) -> Job:
        locations = item["locations"]
        first_city, first_country = locations[0] if locations else ("", "")
        return Job(
            id=make_job_id(self.name, f"{token}:{item['guid'] or item['link']}"),
            source=self.name,
            source_job_id=item["guid"] or None,
            source_url=item["link"] or None,
            title=item["title"],
            company=company,
            description=html_to_text(item["description"]),
            location_raw="; ".join(
                ", ".join(p for p in pair if p) for pair in locations
            ),
            country=lookup_country(first_country),
            city=first_city or None,
            work_type=REMOTE_STATUS.get(item["remoteStatus"], "unknown"),
            apply_url=item["link"] or None,
            posted_at=parsedate_to_datetime(item["pubDate"])
            if item["pubDate"]
            else None,
        )
