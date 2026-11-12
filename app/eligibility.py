"""Can the owner (based in Bangladesh) take this job? A rule-based label, no LLM."""

from typing import Literal, Protocol

from fetcher.normalize import has_any, load_config

Eligibility = Literal[
    "bd",
    "remote_worldwide",
    "remote_regions",
    "remote_unknown",
    "remote_country",
    "visa",
    "local_only",
    "check_visa",
]

REMOTE_SCOPES: dict[str, Eligibility] = {
    "worldwide": "remote_worldwide",
    "regions": "remote_regions",
    "country": "remote_country",
}


class JobLike(Protocol):
    country: str | None
    work_type: str
    remote_scope: str
    title: str
    description: str


def eligibility(job: JobLike) -> Eligibility:
    if job.country == "BD":
        return "bd"
    if job.work_type == "remote":
        return REMOTE_SCOPES.get(job.remote_scope, "remote_unknown")
    keywords = load_config("keywords.yaml")
    text = f"{job.title}\n{job.description}"
    if has_any(text, keywords["visa_denied"]):
        return "local_only"
    if has_any(text, keywords["visa_support"]):
        return "visa"
    return "check_visa"
