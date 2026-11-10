from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from fetcher.models import Job, make_job_id


def make_job(**overrides) -> Job:
    data = {
        "id": make_job_id("greenhouse", "123"),
        "source": "greenhouse",
        "title": "ML Engineer",
        "company": "Acme",
    }
    data.update(overrides)
    return Job(**data)


def test_valid_job_has_defaults():
    job = make_job(country="DE")
    assert job.country == "DE"
    assert job.work_type == "unknown"
    assert job.tags == []
    assert job.fetched_at.tzinfo == UTC


def test_job_id_is_stable_and_source_specific():
    assert make_job_id("greenhouse", "123") == make_job_id("Greenhouse ", " 123")
    assert make_job_id("greenhouse", "123") != make_job_id("lever", "123")


def test_naive_datetime_becomes_utc():
    job = make_job(posted_at=datetime(2026, 11, 10, 8, 0))
    assert job.posted_at == datetime(2026, 11, 10, 8, 0, tzinfo=UTC)


def test_aware_datetime_converted_to_utc():
    dhaka = timezone(timedelta(hours=6))
    job = make_job(posted_at=datetime(2026, 11, 10, 14, 0, tzinfo=dhaka))
    assert job.posted_at == datetime(2026, 11, 10, 8, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "field, value",
    [
        ("country", "Germany"),
        ("salary_currency", "usd"),
        ("work_type", "office"),
        ("title", " "),
    ],
)
def test_invalid_values_rejected(field, value):
    with pytest.raises(ValidationError):
        make_job(**{field: value})


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        make_job(salary="100k")
