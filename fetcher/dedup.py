"""Merge the same job found on several sources into one record."""

import re

from rapidfuzz import fuzz

from fetcher.models import Job

ATS_SOURCES = {
    "greenhouse",
    "lever",
    "ashby",
    "workable",
    "recruitee",
    "smartrecruiters",
}
COMPANY_THRESHOLD = 90
TITLE_THRESHOLD = 95
GENDER_MARKERS = re.compile(
    r"\((?:[mwfdx]\s*/\s*)+[mwfdx]\)|\(all genders\)", re.IGNORECASE
)
NON_WORD = re.compile(r"[^\w\s]")
COMPANY_SUFFIXES = re.compile(
    r"\b(inc|llc|ltd|limited|gmbh|ag|pte|plc|corp|corporation|co|bv|sa|sas|srl)\b"
)


def clean_text(text: str) -> str:
    """Lowercase, drop gender markers like '(m/w/d)' and punctuation."""
    text = NON_WORD.sub(" ", GENDER_MARKERS.sub(" ", text.lower()))
    return " ".join(text.split())


def clean_company(name: str) -> str:
    return " ".join(COMPANY_SUFFIXES.sub(" ", clean_text(name)).split())


def is_same_job(a: Job, b: Job) -> bool:
    if a.country and b.country and a.country != b.country:
        return False
    if (
        fuzz.ratio(clean_company(a.company), clean_company(b.company))
        < COMPANY_THRESHOLD
    ):
        return False
    return fuzz.ratio(clean_text(a.title), clean_text(b.title)) >= TITLE_THRESHOLD


def _rank(job: Job) -> tuple[bool, int]:
    """Company's own ATS first, then the longer description."""
    return job.source in ATS_SOURCES, len(job.description)


def _merge(group: list[Job]) -> Job:
    best = max(group, key=_rank)
    others = [
        f"{job.source}: {job.source_url or job.apply_url or ''}"
        for job in group
        if job is not best
    ]
    return best.model_copy(update={"also_seen": others}) if others else best


def dedup_jobs(jobs: list[Job]) -> list[Job]:
    groups: list[list[Job]] = []
    for job in jobs:
        group = next((g for g in groups if is_same_job(g[0], job)), None)
        if group is None:
            groups.append([job])
        else:
            group.append(job)
    return [_merge(group) for group in groups]
