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


PASTE = {
    "title": "Junior ML Engineer",
    "company": "Acme",
    "location": "Remote, Malaysia",
    "text": "We are hiring a Junior ML Engineer. Send your CV to jobs@acme.com or apply at https://acme.com/careers/ml.",
}


def test_paste_extracts_email_and_link(client):
    response = client.post("/api/jobs/paste", json=PASTE)
    assert response.status_code == 201
    job = response.json()
    assert job["source"] == "paste"
    assert job["apply_email"] == "jobs@acme.com"
    assert job["apply_url"] == "https://acme.com/careers/ml"
    assert job["country"] == "MY"
    assert job["work_type"] == "remote"


def test_paste_same_text_twice_returns_same_job(client):
    first = client.post("/api/jobs/paste", json=PASTE).json()
    second = client.post("/api/jobs/paste", json=PASTE).json()
    assert first["id"] == second["id"]


def test_paste_rejects_non_http_url(client):
    response = client.post(
        "/api/jobs/paste", json={**PASTE, "url": "javascript:alert(1)"}
    )
    assert response.status_code == 422


def test_save_and_unsave(client):
    assert client.post("/api/saved/old").json()["saved"] is True
    saved = client.get("/api/jobs", params={"saved": "true"}).json()
    assert [j["id"] for j in saved["jobs"]] == ["old"]
    assert saved["jobs"][0]["saved"] is True

    assert client.delete("/api/saved/old").json()["saved"] is False
    assert client.get("/api/jobs", params={"saved": "true"}).json()["total"] == 0
    assert client.post("/api/saved/missing").status_code == 404


def test_job_detail_and_404(client):
    assert client.get("/api/jobs/new").json()["title"] == "ML Engineer"
    assert client.get("/api/jobs/missing").status_code == 404
