from datetime import datetime

from sqlalchemy.orm import sessionmaker

from app.db import Base, create_db_engine
from app.models import Job, Score
from app.scoring.llm_score import reset_recruiter_views


def test_reset_removes_views_and_restores_stage1(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as s:
        s.add(
            Job(
                id="j",
                source="t",
                title="T",
                company="C",
                fetched_at=datetime(2026, 11, 13),
            )
        )
        s.add(
            Score(
                job_id="j",
                stage1_score=70,
                final_score=40,
                model="stage2",
                breakdown={"stage1": {}, "stage2": {"total": 40}},
            )
        )
        s.commit()
        assert reset_recruiter_views(s) == 1
        s.commit()
        score = s.get(Score, "j")
        assert (score.model, score.final_score, score.breakdown) == (
            "stage1",
            70,
            {"stage1": {}},
        )
