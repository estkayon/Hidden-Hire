"""Shared test fixtures: an API client backed by a temporary database with three sample jobs."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_db_engine, get_session
from app.main import app
from app.models import Job

NOW = datetime.now(UTC).replace(tzinfo=None)


def make_job(job_id: str, title: str, hours_old: int, country: str = "DE") -> Job:
    posted = NOW - timedelta(hours=hours_old)
    return Job(
        id=job_id,
        source="lever",
        title=title,
        company="Acme",
        country=country,
        work_type="remote",
        posted_at=posted,
        fetched_at=posted,
    )


@pytest.fixture
def client(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as s:
        s.add_all(
            [
                make_job("new", "ML Engineer", hours_old=5),
                make_job("week", "Data Engineer", hours_old=24 * 5, country="AU"),
                make_job("old", "Python Developer", hours_old=24 * 9),
            ]
        )
        s.commit()

    def override():
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
