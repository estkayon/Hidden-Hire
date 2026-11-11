from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_db_engine
from app.models import Application, Job
from app.sync import delete_old_jobs, import_jobs
from fetcher.models import Job as JobRecord

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as s:
        yield s


def record(
    job_id: str, source: str = "lever", title: str = "ML Engineer", days_old: int = 1
) -> JobRecord:
    return JobRecord(
        id=job_id,
        source=source,
        title=title,
        company="Acme",
        country="DE",
        source_url=f"https://{source}.example/{job_id}",
        posted_at=NOW - timedelta(days=days_old),
    )


def test_second_import_adds_nothing(session):
    records = [record("a"), record("b", title="Data Engineer")]
    assert import_jobs(session, iter(records), NOW) == 2
    session.commit()
    assert import_jobs(session, iter(records), NOW) == 0


def test_same_job_from_other_source_goes_to_also_seen(session):
    import_jobs(session, iter([record("a")]), NOW)
    session.commit()
    assert import_jobs(session, iter([record("b", source="himalayas")]), NOW) == 0
    session.commit()
    job = session.get(Job, "a")
    assert job.also_seen == ["himalayas: https://himalayas.example/b"]


def test_old_records_not_imported(session):
    assert import_jobs(session, iter([record("old", days_old=11)]), NOW) == 0


def test_delete_old_keeps_tracked_jobs(session):
    import_jobs(
        session,
        iter([record("a", days_old=5), record("b", title="Data Engineer", days_old=5)]),
        NOW,
    )
    session.commit()
    session.add(Application(job_id="b", status="applied"))
    session.commit()

    assert delete_old_jobs(session, NOW + timedelta(days=6)) == 1
    session.commit()
    assert list(session.scalars(select(Job.id))) == ["b"]
