"""Hacker News 'Ask HN: Who is hiring?' monthly thread via the Algolia HN API."""

import html
import re

import httpx

from fetcher import http
from fetcher.filters import is_tech
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_location, detect_work_type, html_to_text
from fetcher.sources.base import FeedSource

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL = "https://hn.algolia.com/api/v1/items/{id}"
HN_LINK = "https://news.ycombinator.com/item?id={id}"
THREAD_TITLE = "Ask HN: Who is hiring?"
HREF = re.compile(r'href="([^"]+)"')
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _is_location(segment: str) -> bool:
    return (
        detect_work_type(segment) != "unknown"
        or detect_location(segment)[0] is not None
    )


def _split_header(text: str) -> tuple[str, str, str]:
    """(company, title, location) from the 'Company | Role | Location | ...' first line."""
    segments = [s.strip() for s in text.splitlines()[0].split("|") if s.strip()]
    if len(segments) < 2:
        raise ValueError("no header")
    company, rest = segments[0], segments[1:]
    title = next((s for s in rest if is_tech(s)), None) or next(
        (s for s in rest if not _is_location(s)), None
    )
    if title is None:
        raise ValueError("no title in header")
    location = "; ".join(s for s in rest if s != title and _is_location(s))
    return company, title, location


def _has_header(raw_html: str) -> bool:
    """Skip comments that do not follow the 'Company | Role | ...' format or name no role."""
    if "|" not in raw_html:
        return False
    try:
        _split_header(html_to_text(html.unescape(raw_html)))
    except ValueError:
        return False
    return True


class HackerNewsSource(FeedSource):
    name = "hackernews"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        params = {"tags": "story,author_whoishiring", "hitsPerPage": 5}
        hits = http.get(client, SEARCH_URL, params=params).json().get("hits") or []
        thread = next(
            (h for h in hits if (h.get("title") or "").startswith(THREAD_TITLE)), None
        )
        if thread is None:
            raise ValueError("no hiring thread found")
        story = http.get(client, ITEM_URL.format(id=thread["objectID"])).json()
        return [
            c for c in story.get("children") or [] if _has_header(c.get("text") or "")
        ]

    def parse(self, item: dict) -> Job:
        raw_html = html.unescape(item["text"])
        text = html_to_text(raw_html)
        company, title, location = _split_header(text)
        hn_url = HN_LINK.format(id=item["id"])
        link = HREF.search(raw_html)
        email = EMAIL.search(text)
        return Job(
            id=make_job_id(self.name, str(item["id"])),
            source=self.name,
            source_job_id=str(item["id"]),
            source_url=hn_url,
            title=title,
            company=company,
            description=text,
            location_raw=location,
            apply_url=link.group(1) if link else hn_url,
            apply_email=email.group(0) if email else None,
            posted_at=item.get("created_at"),
        )
