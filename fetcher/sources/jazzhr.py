"""JazzHR public job feed (XML export for job board syndication), one board per company.

Board token is 'company' or 'company:Country Name' to keep jobs from one country only.
"""

import xml.etree.ElementTree as ET

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://app.jazz.co/feeds/export/jobs/{company}"


def jobs_from_xml(content: bytes, country: str = "") -> list[dict]:
    """Open jobs from the feed as tag -> text dicts, optionally for one country."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("bad JazzHR XML") from exc
    jobs = [
        {child.tag: (child.text or "").strip() for child in job}
        for job in root.iter("job")
    ]
    return [
        job
        for job in jobs
        if job.get("status", "Open").lower() == "open"
        and (not country or job.get("country", "").lower() == country.lower())
    ]


class JazzHRSource(BoardSource):
    name = "jazzhr"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        company, _, country = token.partition(":")
        response = http.get(client, API_URL.format(company=company))
        return jobs_from_xml(response.content, country)

    def parse(self, item: dict, token: str, company: str) -> Job:
        job_id = item["id"]
        country = item.get("country", "")
        url = item.get("url") or None
        return Job(
            id=make_job_id(self.name, f"{token}:{job_id}"),
            source=self.name,
            source_job_id=job_id,
            source_url=url,
            title=item["title"],
            company=company,
            description=html_to_text(item.get("description", "")),
            location_raw=", ".join(
                filter(None, [item.get("city"), item.get("state"), country])
            ),
            country="BD" if country.lower() == "bangladesh" else None,
            apply_url=url,
            posted_at=None,
        )
