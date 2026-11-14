"""keep_job and dedup_jobs as run.py uses them: whole jobs, not single helpers."""

from datetime import UTC, datetime, timedelta

import pytest

from fetcher.dedup import dedup_jobs
from fetcher.filters import is_fresh, keep_job
from fetcher.models import Job, make_job_id

NOW = datetime(2026, 11, 14, 6, 0, tzinfo=UTC)


def job(**overrides) -> Job:
    fields = {
        "source": "greenhouse",
        "source_job_id": "1",
        "title": "Software Engineer",
        "company": "Acme",
        "description": "Build web services in Python.",
        "location_raw": "Dhaka, Bangladesh",
        "country": "BD",
        "work_type": "onsite",
        "apply_url": "https://example.com/jobs/1",
        "posted_at": NOW - timedelta(days=2),
    }
    fields.update(overrides)
    fields["id"] = make_job_id(fields["source"], fields["source_job_id"])
    return Job(**fields)


def test_job_without_date_counts_as_fresh():
    assert is_fresh(job(posted_at=None), NOW)


def test_fresh_bangladesh_tech_job_is_kept():
    assert keep_job(job(), NOW)


@pytest.mark.parametrize(
    "overrides",
    [
        {"posted_at": NOW - timedelta(days=11)},
        {"title": "Senior Software Engineer"},
        {"title": "Sales Executive"},
    ],
    ids=["too old", "too senior", "not tech"],
)
def test_jobs_failing_any_filter_are_dropped(overrides):
    assert not keep_job(job(**overrides), NOW)


def test_remote_job_from_any_country_is_kept():
    assert keep_job(
        job(country="US", location_raw="United States", work_type="remote"), NOW
    )


def test_same_job_from_two_sources_is_merged():
    first = job(source="greenhouse", source_job_id="1")
    second = job(
        source="hackernews", source_job_id="abc", apply_url="https://example.com/apply"
    )
    other = job(source="lever", source_job_id="2", title="Data Analyst")
    assert len(dedup_jobs([first, second, other])) == 2
