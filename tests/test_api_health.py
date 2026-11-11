from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.health import source_status
from app.db import Base, create_db_engine, get_session
from app.main import app
from app.models import SourceRun

OLD = datetime(2026, 11, 10, 9, 0)
NEW = datetime(2026, 11, 11, 9, 0)


@pytest.mark.parametrize(
    "found, errors, expected",
    [
        (10, [], "ok"),
        (10, ["x: bad job"], "partial"),
        (0, [], "empty"),
        (0, ["x: HTTP 500"], "failing"),
    ],
)
def test_source_status(found, errors, expected):
    assert source_status(found, errors) == expected


def test_health_returns_latest_run_per_source(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as s:
        s.add_all(
            [
                SourceRun(
                    source="lever",
                    run_at=OLD,
                    jobs_found=0,
                    jobs_kept=0,
                    errors=["lever: HTTP 500"],
                ),
                SourceRun(
                    source="lever", run_at=NEW, jobs_found=40, jobs_kept=5, errors=[]
                ),
                SourceRun(
                    source="reed",
                    run_at=NEW,
                    jobs_found=0,
                    jobs_kept=0,
                    errors=["reed: missing REED_API_KEY"],
                ),
            ]
        )
        s.commit()

    def override():
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    try:
        data = TestClient(app).get("/api/health").json()
    finally:
        app.dependency_overrides.clear()

    by_source = {s["source"]: s for s in data["sources"]}
    assert by_source["lever"]["status"] == "ok"
    assert by_source["lever"]["jobs_found"] == 40
    assert by_source["reed"]["status"] == "failing"
    assert data["last_run_at"].startswith("2026-11-11T09:00")
