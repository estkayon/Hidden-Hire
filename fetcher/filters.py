"""Keep only fresh tech jobs at intern to mid level."""

from datetime import datetime, timedelta

from fetcher.models import Job
from fetcher.normalize import has_any, load_config

RETENTION_DAYS = 10


def is_tech(title: str) -> bool:
    keywords = load_config("keywords.yaml")
    return has_any(title, keywords["tech_titles"]) and not has_any(
        title, keywords["exclude_titles"]
    )


def is_too_senior(title: str) -> bool:
    return has_any(title, load_config("keywords.yaml")["senior_titles"])


def is_fresh(job: Job, now: datetime) -> bool:
    """Jobs without a posted date count as fresh."""
    return job.posted_at is None or now - job.posted_at <= timedelta(
        days=RETENTION_DAYS
    )


def keep_job(job: Job, now: datetime) -> bool:
    return is_fresh(job, now) and is_tech(job.title) and not is_too_senior(job.title)
