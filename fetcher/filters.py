"""Keep only tech jobs at intern to mid level."""

from fetcher.models import Job
from fetcher.normalize import has_any, load_config


def is_tech(title: str) -> bool:
    keywords = load_config("keywords.yaml")
    return has_any(title, keywords["tech_titles"]) and not has_any(
        title, keywords["exclude_titles"]
    )


def is_too_senior(title: str) -> bool:
    return has_any(title, load_config("keywords.yaml")["senior_titles"])


def keep_job(job: Job) -> bool:
    return is_tech(job.title) and not is_too_senior(job.title)
