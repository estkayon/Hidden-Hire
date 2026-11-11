"""Recruitee public careers site API (one site per company)."""

from datetime import datetime

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority, html_to_text
from fetcher.sources.base import BoardSource

API_URL = "https://{token}.recruitee.com/api/offers/"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"  # e.g. "2026-11-10 07:45:05 UTC"
SALARY_PERIODS = {"hour", "day", "week", "month", "year"}


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, TIME_FORMAT)
    except ValueError:
        return None


def _work_type(item: dict) -> str:
    if item.get("hybrid"):
        return "hybrid"
    if item.get("remote"):
        return "remote"
    if item.get("on_site"):
        return "onsite"
    return "unknown"


def _location_text(item: dict) -> str:
    names = []
    for loc in item.get("locations") or []:
        parts = (loc.get("city"), loc.get("state"), loc.get("country"))
        names.append(", ".join(part for part in parts if part))
    return "; ".join(name for name in names if name) or (item.get("location") or "")


def _salary(item: dict) -> dict:
    """Salary fields only when the posting states a usable range."""
    salary = item.get("salary") or {}
    currency = (salary.get("currency") or "").upper()
    period = (salary.get("period") or "").lower()
    try:
        low = float(salary["min"]) if salary.get("min") else None
        high = float(salary["max"]) if salary.get("max") else None
    except (TypeError, ValueError):
        return {}
    if (
        (low is None and high is None)
        or len(currency) != 3
        or period not in SALARY_PERIODS
    ):
        return {}
    return {
        "salary_min": low,
        "salary_max": high,
        "salary_currency": currency,
        "salary_period": period,
    }


class RecruiteeSource(BoardSource):
    name = "recruitee"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        return http.get(client, API_URL.format(token=token)).json().get("offers", [])

    def parse(self, item: dict, token: str, company: str) -> Job:
        job_id = str(item["id"])
        country_code = item.get("country_code") or ""
        description = "\n".join(
            html_to_text(item.get(key) or "") for key in ("description", "requirements")
        ).strip()
        close_at = _parse_time(item.get("close_at"))
        return Job(
            id=make_job_id(self.name, f"{token}:{job_id}"),
            source=self.name,
            source_job_id=job_id,
            source_url=item.get("careers_url"),
            title=item["title"],
            company=company,
            description=description,
            location_raw=_location_text(item),
            country=country_code.upper() if len(country_code) == 2 else None,
            city=item.get("city") or None,
            work_type=_work_type(item),
            apply_url=item.get("careers_apply_url") or item.get("careers_url"),
            posted_at=_parse_time(item.get("published_at") or item.get("created_at")),
            deadline=close_at.date() if close_at else None,
            seniority=detect_seniority(item.get("experience_code") or ""),
            **_salary(item),
        )
