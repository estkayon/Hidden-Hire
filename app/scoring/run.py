"""Score every job in the database against the owner's profile (Stage 1)."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import Job, Score
from app.profile import Profile
from app.scoring.embed import similarities
from app.scoring.llm_score import STAGE1_MODEL
from app.scoring.rules import stage1_score
from app.scoring.source import candidate

log = logging.getLogger("scoring")


def profile_query(profile: Profile, text: str) -> str:
    """Roles and skills first, since the embedding model only reads the start of the text."""
    return f"Target roles: {', '.join(profile.target_roles)}\nSkills: {', '.join(profile.skills)}\n{text}"


def score_all(session: Session, profile: Profile, text: str) -> int:
    jobs = session.scalars(select(Job)).all()
    if not jobs:
        return 0
    sims = similarities(
        profile_query(profile, text),
        [f"{job.title}\n{job.description}" for job in jobs],
    )
    existing = {score.job_id: score for score in session.scalars(select(Score))}
    now = datetime.now(UTC).replace(tzinfo=None)

    for job, sim in zip(jobs, sims, strict=True):
        result = stage1_score(job, profile, sim)
        score = existing.get(job.id)
        if score is None:
            score = Score(job_id=job.id, breakdown={})
            session.add(score)
        score.stage1_score = result.score
        score.breakdown = {**(score.breakdown or {}), "stage1": result.breakdown}
        if score.model in (
            None,
            STAGE1_MODEL,
        ):  # keep a Stage 2 (LLM) score once it exists
            score.final_score = result.score
            score.model = STAGE1_MODEL
        score.scored_at = now
    return len(jobs)


def run_scoring() -> int | None:
    """Score all jobs against the master CV (or uploaded CV). Returns the number scored, or None without one."""
    found = candidate()
    if found is None:
        log.info("no CV yet, skipping scoring")
        return None
    profile, text = found
    init_db()
    with SessionLocal.begin() as session:
        return score_all(session, profile, text)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    scored = run_scoring()
    if scored is not None:
        log.info("scored %d jobs", scored)


if __name__ == "__main__":
    main()
