"""Tracked jobs: 'saved' for later, or 'applied' with the date the owner applied."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.jobs import SessionDep
from app.models import Application, Job

SAVED = "saved"
APPLIED = "applied"

router = APIRouter(prefix="/api/saved", tags=["saved"])
applied_router = APIRouter(prefix="/api/applied", tags=["applied"])


class SavedState(BaseModel):
    job_id: str
    saved: bool


class AppliedState(BaseModel):
    job_id: str
    applied_at: datetime | None


def _require_job(job_id: str, session) -> None:
    if session.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/{job_id}", response_model=SavedState)
def save_job(job_id: str, session: SessionDep) -> SavedState:
    _require_job(job_id, session)
    if session.get(Application, job_id) is None:
        session.add(Application(job_id=job_id, status=SAVED))
        session.commit()
    return SavedState(job_id=job_id, saved=True)


@router.delete("/{job_id}", response_model=SavedState)
def unsave_job(job_id: str, session: SessionDep) -> SavedState:
    """Only a plain 'saved' entry can be removed; applied jobs stay tracked."""
    application = session.get(Application, job_id)
    if application is not None:
        if application.status != SAVED:
            raise HTTPException(status_code=409, detail="Job is marked as applied")
        session.delete(application)
        session.commit()
    return SavedState(job_id=job_id, saved=False)


@applied_router.post("/{job_id}", response_model=AppliedState)
def mark_applied(job_id: str, session: SessionDep) -> AppliedState:
    _require_job(job_id, session)
    application = session.get(Application, job_id)
    if application is None:
        application = Application(job_id=job_id)
        session.add(application)
    if application.status != APPLIED:
        application.status = APPLIED
        application.applied_at = datetime.now(UTC).replace(tzinfo=None)
    session.commit()
    return AppliedState(
        job_id=job_id, applied_at=application.applied_at.replace(tzinfo=UTC)
    )


@applied_router.delete("/{job_id}", response_model=AppliedState)
def unmark_applied(job_id: str, session: SessionDep) -> AppliedState:
    """Undo a mistaken 'applied': the job goes back to saved, so nothing is lost."""
    application = session.get(Application, job_id)
    if application is not None and application.status == APPLIED:
        application.status = SAVED
        application.applied_at = None
        session.commit()
    return AppliedState(job_id=job_id, applied_at=None)
