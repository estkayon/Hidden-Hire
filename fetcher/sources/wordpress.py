"""Job posts from Bangladeshi company WordPress sites, read through the public WP REST API.

Board token is the REST collection URL, e.g. https://www.bracits.com/wp-json/wp/v2/awsm_job_openings.
Only Bangladeshi company sites go in this list, so every job is marked as Bangladesh.
"""

import html
import re

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

PER_PAGE = 50
LOCATION_CLASS = re.compile(r"^job-location-(.+)$")


def _rendered(item: dict, key: str) -> str:
    return (item.get(key) or {}).get("rendered") or ""


def _location(item: dict) -> str:
    """'job-location-dhaka' in class_list (WP Job Openings plugin) -> 'Dhaka'."""
    classes = item.get("class_list")
    for name in classes if isinstance(classes, list) else []:
        match = LOCATION_CLASS.match(name)
        if match:
            return match.group(1).replace("-", " ").title()
    return ""


class WordPressSource(BoardSource):
    name = "wordpress"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        data = http.get(client, token, params={"per_page": PER_PAGE}).json()
        return data if isinstance(data, list) else []

    def parse(self, item: dict, token: str, company: str) -> Job:
        title = html.unescape(_rendered(item, "title")).strip()
        if not title:
            raise ValueError("job without a title")
        job_id = str(item["id"])
        link = item.get("link")
        content = _rendered(item, "content") or _rendered(item, "excerpt")
        return Job(
            id=make_job_id(self.name, f"{token}:{job_id}"),
            source=self.name,
            source_job_id=job_id,
            source_url=link,
            title=title,
            company=company,
            description=html_to_text(content),
            location_raw=", ".join(filter(None, [_location(item), "Bangladesh"])),
            country="BD",
            apply_url=link,
            posted_at=item.get("date_gmt"),
        )
