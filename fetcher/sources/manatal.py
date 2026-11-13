"""Manatal career pages (careers-page.com), used by Bangladeshi recruiting agencies.

These boards have no public JSON API, so the list page and each job page are read as HTML.
Title and text come from the job page's og:title and og:description meta tags.
"""

import html
import logging
import re

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.sources.base import BoardSource, describe_error

log = logging.getLogger(__name__)

BOARD_URL = "https://www.careers-page.com/{token}"
JOB_URL = "https://www.careers-page.com/{token}/job/{job_id}"
META = r'<meta\s+property="og:{name}"\s+content="([^"]*)"'
STRUCTURE = re.compile(
    r"\b(onsite|on-site|remote|hybrid)\s+in\s+([^|\n]+)", re.IGNORECASE
)
SALARY = re.compile(r"salary:\s*BDT\s*([\d,]+)(?:\s*-\s*([\d,]+))?", re.IGNORECASE)
BD_PLACES = re.compile(
    r"bangladesh|dhaka|chattogram|chittagong|sylhet|khulna|rajshahi", re.IGNORECASE
)
WORK_TYPES = {
    "onsite": "onsite",
    "on-site": "onsite",
    "remote": "remote",
    "hybrid": "hybrid",
}
TITLE_SUFFIX = " | Career Page"


def _meta(page: str, name: str) -> str:
    match = re.search(META.format(name=name), page)
    return html.unescape(match.group(1)).strip() if match else ""


def _title(raw: str) -> str:
    """'Backend Developer - Talvette | Career Page' -> 'Backend Developer'."""
    title = raw.removesuffix(TITLE_SUFFIX)
    return title.rsplit(" - ", 1)[0].strip() if " - " in title else title.strip()


def _location(text: str) -> tuple[str, str]:
    """Work type and place from a line like 'Hybrid in Dhaka, Bangladesh | Full-time'."""
    match = STRUCTURE.search(text)
    if not match:
        return "unknown", ""
    return WORK_TYPES[match.group(1).lower()], match.group(2).strip()


def _salary(text: str) -> dict:
    match = SALARY.search(text)
    if not match:
        return {}
    low = int(match.group(1).replace(",", ""))
    high = int(match.group(2).replace(",", "")) if match.group(2) else None
    return {"salary_min": low, "salary_max": high, "salary_currency": "BDT"}


class ManatalSource(BoardSource):
    name = "manatal"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        page = http.get(client, BOARD_URL.format(token=token)).text
        pattern = rf"/{re.escape(token)}/job/([A-Z0-9]+)"
        job_ids = list(dict.fromkeys(re.findall(pattern, page)))
        items = []
        for job_id in job_ids:
            url = JOB_URL.format(token=token, job_id=job_id)
            try:
                items.append(
                    {"id": job_id, "url": url, "html": http.get(client, url).text}
                )
            except httpx.HTTPError as exc:
                log.warning(
                    "%s/%s: job %s skipped (%s)",
                    self.name,
                    token,
                    job_id,
                    describe_error(exc),
                )
        return items

    def parse(self, item: dict, token: str, company: str) -> Job:
        page = item["html"]
        raw_title = _meta(page, "title")
        if not raw_title or raw_title == "Manatal":
            raise ValueError("job page without a title")
        description = _meta(page, "description")
        work_type, location = _location(description)
        return Job(
            id=make_job_id(self.name, f"{token}:{item['id']}"),
            source=self.name,
            source_job_id=item["id"],
            source_url=item["url"],
            title=_title(raw_title),
            company=company,
            description=description,
            location_raw=location,
            country="BD" if BD_PLACES.search(location) else None,
            work_type=work_type,
            apply_url=item["url"],
            posted_at=None,
            **_salary(description),
        )
