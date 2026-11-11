"""Japan Dev jobs API (English-friendly tech jobs in Japan). Default page is 20; limit returns all."""

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.sources.base import FeedSource

API_URL = "https://api.japan-dev.com/api/v1/jobs"
LIMIT = 500  # the board lists a few hundred jobs; one request gets all of them
JOB_URL = "https://japan-dev.com/jobs/{company}/{slug}"
JAPAN_ONLY = "candidate_location_japan_only"
REMOTE_LEVEL = {
    "remote_level_none": "onsite",
    "remote_level_partial": "hybrid",
    "remote_level_around_office": "remote",
    "remote_level_full_japan": "remote",
    "remote_level_worldwide": "remote",
}


def _label(enum_value: str | None, prefix: str) -> str:
    """'japanese_level_business_level' -> 'business level'."""
    return (enum_value or "").removeprefix(prefix).replace("_", " ").strip()


def _description(attrs: dict) -> str:
    lines = [attrs.get("intro") or ""]
    if attrs.get("candidate_location") == "candidate_location_anywhere":
        lines.append("Applicants: can apply from overseas (anywhere).")
    if japanese := _label(attrs.get("japanese_level_enum"), "japanese_level_"):
        lines.append(f"Japanese level: {japanese}")
    if english := _label(attrs.get("english_level_enum"), "english_level_"):
        lines.append(f"English level: {english}")
    if attrs.get("skills"):
        lines.append("Skills: " + ", ".join(str(s) for s in attrs["skills"]))
    return "\n".join(line for line in lines if line)


def _salary(attrs: dict) -> dict:
    low, high = attrs.get("salary_min"), attrs.get("salary_max")
    if low is None and high is None:
        return {}
    return {
        "salary_min": low,
        "salary_max": high,
        "salary_currency": "JPY",
        "salary_period": "year",
    }


class JapanDevSource(FeedSource):
    name = "japandev"

    def fetch_items(self, client: httpx.Client) -> list[dict]:
        data = (
            http.get(client, API_URL, params={"limit": LIMIT}).json().get("data") or []
        )
        return [
            item
            for item in data
            if (item.get("attributes") or {}).get("candidate_location") != JAPAN_ONLY
        ]

    def parse(self, item: dict) -> Job:
        attrs = item["attributes"]
        company = attrs.get("company") or {}
        page_url = JOB_URL.format(company=company.get("slug", ""), slug=attrs["slug"])
        remote_level = attrs.get("remote_level") or ""
        return Job(
            id=make_job_id(self.name, str(item["id"])),
            source=self.name,
            source_job_id=str(item["id"]),
            source_url=page_url,
            title=attrs["title"],
            company=company["name"],
            description=_description(attrs),
            location_raw=attrs.get("location") or "",
            country="JP",
            city=attrs.get("location") or None,
            work_type=REMOTE_LEVEL.get(remote_level, "unknown"),
            remote_scope="worldwide"
            if remote_level == "remote_level_worldwide"
            else "unknown",
            apply_url=attrs.get("application_url") or page_url,
            apply_email=attrs.get("application_email") or None,
            posted_at=attrs.get("published_at"),
            tags=[str(s) for s in attrs.get("skills") or []],
            **_salary(attrs),
        )
