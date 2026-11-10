from datetime import UTC, datetime, timedelta

import pytest

from fetcher.filters import is_fresh, is_open_to_bd, is_tech, is_too_senior
from fetcher.models import Job

NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "age_days, expected",
    [(None, True), (3, True), (10, True), (11, False)],
)
def test_is_fresh(age_days, expected):
    posted = None if age_days is None else NOW - timedelta(days=age_days)
    job = Job(
        id="x", source="test", title="ML Engineer", company="Acme", posted_at=posted
    )
    assert is_fresh(job, NOW) is expected


@pytest.mark.parametrize(
    "title",
    [
        "Machine Learning Engineer",
        "Junior Backend Developer",
        "Data Analyst Intern",
        "MLOps Engineer",
    ],
)
def test_tech_titles_kept(title):
    assert is_tech(title)


@pytest.mark.parametrize(
    "title",
    [
        "Account Executive",
        "Benefits Analyst",
        "AI Sales Specialist",
        "Technical Recruiter",
    ],
)
def test_non_tech_titles_dropped(title):
    assert not is_tech(title)


@pytest.mark.parametrize(
    "title", ["Senior Data Engineer", "Staff ML Engineer", "Engineering Manager"]
)
def test_senior_titles_flagged(title):
    assert is_too_senior(title)


def test_junior_title_not_senior():
    assert not is_too_senior("Associate Software Engineer")


@pytest.mark.parametrize(
    "work_type, country, description, expected",
    [
        ("onsite", "DE", "Python, SQL. Relocation support offered.", True),
        ("onsite", "DE", "We are unable to sponsor work visas.", False),
        ("hybrid", "US", "Must be legally authorized to work in the US.", False),
        ("remote", "US", "No visa sponsorship.", True),
        ("onsite", "BD", "Citizens only.", True),
        ("unknown", None, "Requires active security clearance.", False),
    ],
)
def test_is_open_to_bd(work_type, country, description, expected):
    job = Job(
        id="x",
        source="test",
        title="ML Engineer",
        company="Acme",
        work_type=work_type,
        country=country,
        description=description,
    )
    assert is_open_to_bd(job) is expected
