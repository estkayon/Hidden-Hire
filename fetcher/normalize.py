"""Normalization of raw job data: plain text, country, city, work type, remote scope."""

import html
import re
from functools import cache
from html.parser import HTMLParser
from pathlib import Path

import pycountry
import yaml

from fetcher.models import Job, RemoteScope, WorkType

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

BLOCK_TAGS = {"p", "div", "br", "ul", "ol", "tr"}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
SKIP_TAGS = {"script", "style"}

LOCATION_SPLIT = re.compile(r"[;|/]")
SEGMENT_SPLIT = re.compile(r"[,()\-–]")
REMOTE_WORDS = ["remote", "work from home", "wfh", "distributed"]
HYBRID_WORDS = ["hybrid"]
ONSITE_WORDS = ["onsite", "on-site", "on site", "in office", "in-office"]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag in HEADING_TAGS:
            self.parts.append("\n## ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "li" or tag in HEADING_TAGS or tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(raw: str) -> str:
    """HTML to plain text. Headings become '## ' lines and list items '• ' lines."""
    if not raw:
        return ""
    if "&lt;" in raw and "<" not in raw:
        raw = html.unescape(raw)  # some feeds escape their HTML twice
    parser = _TextExtractor()
    parser.feed(raw)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line and line not in ("•", "##"))


@cache
def load_config(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@cache
def _word_pattern(phrase: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)


def has_any(text: str, phrases: list[str]) -> bool:
    """True if any phrase appears in text as a whole word, case-insensitive."""
    return any(_word_pattern(phrase).search(text) for phrase in phrases)


def country_tier(code: str | None) -> int:
    for tier, codes in load_config("countries.yaml")["tiers"].items():
        if code in codes:
            return int(tier)
    return 3


def lookup_country(segment: str) -> str | None:
    """ISO code for a country name. Short codes are skipped to avoid US states (CA, IN, DE)."""
    name = segment.strip().lower()
    aliases = load_config("countries.yaml")["country_aliases"]
    if name in aliases:
        return aliases[name]
    if len(name) <= 3:
        return None
    try:
        return pycountry.countries.lookup(name).alpha_2
    except LookupError:
        return None


def _scope_words() -> list[str]:
    cfg = load_config("countries.yaml")
    return REMOTE_WORDS + cfg["worldwide_words"] + cfg["region_words"]


def _detect_part(segments: list[str]) -> tuple[str | None, str | None]:
    cities = load_config("countries.yaml")["city_aliases"]
    country, city = None, None
    for segment in segments:
        name = segment.lower()
        if name in cities:
            city = city or segment
            country = country or cities[name]
        elif code := lookup_country(segment):
            country = country or code
        elif city is None and not has_any(segment, _scope_words()):
            city = segment
    return country, city if country else None


def detect_location(location_raw: str) -> tuple[str | None, str | None]:
    """(country, city) from a raw location. With several locations, the best-tier country wins."""
    best: tuple[str | None, str | None] = (None, None)
    for part in LOCATION_SPLIT.split(location_raw):
        segments = [s.strip() for s in SEGMENT_SPLIT.split(part) if s.strip()]
        country, city = _detect_part(segments)
        if country and (
            best[0] is None or country_tier(country) < country_tier(best[0])
        ):
            best = (country, city)
    return best


def detect_work_type(text: str) -> WorkType:
    if has_any(text, HYBRID_WORDS):
        return "hybrid"
    if has_any(text, REMOTE_WORDS):
        return "remote"
    if has_any(text, ONSITE_WORDS):
        return "onsite"
    return "unknown"


def detect_remote_scope(location_raw: str, country: str | None) -> RemoteScope:
    cfg = load_config("countries.yaml")
    if has_any(location_raw, cfg["worldwide_words"]):
        return "worldwide"
    if has_any(location_raw, cfg["region_words"]):
        return "regions"
    return "country" if country else "unknown"


def detect_seniority(value: str | list[str] | None) -> str | None:
    """Level stated in a title or a source's level field, e.g. 'mid_level' -> 'Mid-level'."""
    text = ", ".join(map(str, value)) if isinstance(value, list) else (value or "")
    text = text.replace("_", " ")
    for level, words in load_config("keywords.yaml")["seniority_levels"].items():
        if has_any(text, words):
            return level
    return None


def normalize_job(job: Job) -> Job:
    """Fill country, city, work type and remote scope when the source did not set them."""
    country, city = detect_location(job.location_raw)
    country = job.country or country

    work_type = job.work_type
    if work_type == "unknown":
        work_type = detect_work_type(f"{job.title} {job.location_raw}")

    remote_scope = job.remote_scope
    if work_type == "remote" and remote_scope == "unknown":
        remote_scope = detect_remote_scope(f"{job.title} {job.location_raw}", country)

    return job.model_copy(
        update={
            "country": country,
            "city": job.city or city,
            "work_type": work_type,
            "remote_scope": remote_scope,
            "seniority": job.seniority or detect_seniority(job.title),
        }
    )
