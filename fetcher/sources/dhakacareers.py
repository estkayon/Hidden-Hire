"""DhakaCareers WordPress REST API (Bangladesh job circulars, many scraped from BDJobs)."""

import html

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority, html_to_text
from fetcher.sources.base import FeedSource

API_URL = "https://dhakacareers.com/wp-json/wp/v2/jobs"
PER_PAGE = 100
CURRENCY = "BDT"  # Bangladesh-only board
WORKPLACE = {
    "at office": "onsite",
    "on site": "onsite",
    "onsite": "onsite",
    "remote": "remote",
    "hybrid": "hybrid",
}
DESCRIPTION_FIELDS = (
    "excerpt",
    "responsibilities",
    "qualifications",
    "skill_requirements",
    "experience_requirements",
    "education_requirements",
)


def _terms(item: dict) -> dict[str, list[str]]:
    """Taxonomy name -> term names, from the _embed=wp:term data."""
    terms: dict[str, list[str]] = {}
    for group in (item.get("_embedded") or {}).get("wp:term") or []:
        for term in group or []:
            terms.setdefault(term.get("taxonomy", ""), []).append(
                html.unescape(term.get("name", ""))
            )
    return terms


def _salary(fields: dict) -> dict:
    low, high = fields.get("salary_min"), fields.get("salary_max")
    if not isinstance(low, int | float) and not isinstance(high, int | float):
        return {}
    return {
        "salary_min": low if isinstance(low, int | float) else None,
        "salary_max": high if isinstance(high, int | float) else None,
        "salary_currency": CURRENCY,
    }


class DhakaCareersSource(FeedSource):
    name = "dhakacareers"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        params = {"per_page": PER_PAGE, "_embed": "wp:term"}
        items = http.get(client, API_URL, params=params).json()
        return [
            item
            for item in items
            if not ((item.get("acf") or {}).get("common_fields") or {}).get(
                "expired_status"
            )
        ]

    def parse(self, item: dict) -> Job:
        fields = (item.get("acf") or {}).get("common_fields") or {}
        terms = _terms(item)
        job_id = str(item["id"])
        page_url = item.get("link")
        workplace = (terms.get("workplace-types") or [""])[0].lower()
        location = ", ".join(
            [*terms.get("locations", []), fields.get("job_address") or ""]
        ).strip(", ")
        description = "\n".join(
            html_to_text(fields.get(name) or "")
            for name in DESCRIPTION_FIELDS
            if fields.get(name)
        )
        return Job(
            id=make_job_id(self.name, job_id),
            source=self.name,
            source_job_id=job_id,
            source_url=page_url,
            title=html.unescape(
                fields.get("custom_job_title") or item["title"]["rendered"]
            ),
            company=(
                terms.get("companies") or [fields.get("hiring_organization_name") or ""]
            )[0],
            description=description,
            location_raw=location,
            country="BD",
            work_type=WORKPLACE.get(workplace, "unknown"),
            apply_url=fields.get("application_url")
            or fields.get("job_source_url")
            or page_url,
            apply_email=fields.get("contact_email") or None,
            posted_at=fields.get("original_publish_date") or item.get("date_gmt"),
            deadline=fields.get("application_end_date") or None,
            seniority=detect_seniority(terms.get("experience-levels")),
            **_salary(fields),
        )
