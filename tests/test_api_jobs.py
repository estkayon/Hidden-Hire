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


def test_main_view_hides_older_than_7_days(client):
    data = client.get("/api/jobs").json()
    assert [j["id"] for j in data["jobs"]] == ["new", "week"]
    assert data["jobs"][0]["is_new"] is True
    assert data["jobs"][1]["is_new"] is False


def test_search_finds_older_jobs(client):
    data = client.get("/api/jobs", params={"q": "python"}).json()
    assert [j["id"] for j in data["jobs"]] == ["old"]


def test_country_filter(client):
    data = client.get("/api/jobs", params={"country": "au"}).json()
    assert [j["id"] for j in data["jobs"]] == ["week"]


def test_job_detail_and_404(client):
    assert client.get("/api/jobs/new").json()["title"] == "ML Engineer"
    assert client.get("/api/jobs/missing").status_code == 404
