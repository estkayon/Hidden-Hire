"""We Work Remotely RSS feed (programming category)."""

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import FeedSource

FEED_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def _text(item: ET.Element, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


def _split_title(raw: str) -> tuple[str, str]:
    """'Company: Job Title' -> (company, title)."""
    company, sep, title = raw.partition(": ")
    if not sep:
        raise ValueError("title without company")
    return company.strip(), title.strip()


class WeWorkRemotelySource(FeedSource):
    name = "weworkremotely"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        content = http.get(client, FEED_URL).content
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError("invalid RSS") from exc
        return [
            {
                tag: _text(item, tag)
                for tag in ("title", "region", "description", "pubDate", "link")
            }
            for item in root.iter("item")
        ]

    def parse(self, item: dict) -> Job:
        company, title = _split_title(item["title"])
        url = item["link"]
        return Job(
            id=make_job_id(self.name, url),
            source=self.name,
            source_url=url,
            title=title,
            company=company,
            description=html_to_text(item["description"]),
            location_raw=item["region"],
            work_type="remote",
            apply_url=url,
            posted_at=parsedate_to_datetime(item["pubDate"])
            if item["pubDate"]
            else None,
        )
