"""Personio public XML job feed (documented by Personio for career sites and job boards)."""

import xml.etree.ElementTree as ET

import httpx

from fetcher import http
from fetcher.models import Job, make_job_id
from fetcher.normalize import detect_seniority, html_to_text
from fetcher.sources.base import BoardSource

FEED_URL = "https://{token}.jobs.personio.de/xml"
JOB_URL = "https://{token}.jobs.personio.de/job/{id}"


def _text(element: ET.Element, tag: str) -> str:
    return (element.findtext(tag) or "").strip()


def _description(position: ET.Element) -> str:
    parts = []
    for section in position.iter("jobDescription"):
        parts.append(_text(section, "name"))
        parts.append(html_to_text(_text(section, "value")))
    return "\n".join(part for part in parts if part)


def _offices(position: ET.Element) -> list[str]:
    names = [
        _text(position, "office"),
        *(o.text or "" for o in position.iter("additionalOffice")),
    ]
    return [name.removesuffix(" Office").strip() for name in names if name.strip()]


class PersonioSource(BoardSource):
    name = "personio"

    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        content = http.get(
            client, FEED_URL.format(token=token), params={"language": "en"}
        ).content
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError("invalid XML") from exc
        return [
            {
                "id": _text(position, "id"),
                "name": _text(position, "name"),
                "description": _description(position),
                "offices": _offices(position),
                "seniority": _text(position, "seniority"),
                "keywords": _text(position, "keywords"),
                "createdAt": _text(position, "createdAt"),
            }
            for position in root.iter("position")
        ]

    def parse(self, item: dict, token: str, company: str) -> Job:
        url = JOB_URL.format(token=token, id=item["id"])
        return Job(
            id=make_job_id(self.name, f"{token}:{item['id']}"),
            source=self.name,
            source_job_id=item["id"],
            source_url=url,
            title=item["name"],
            company=company,
            description=item["description"],
            location_raw="; ".join(item["offices"]),
            apply_url=url,
            posted_at=item["createdAt"] or None,
            seniority=detect_seniority(item["seniority"]),
            tags=[k.strip() for k in item["keywords"].split(",") if k.strip()],
        )
