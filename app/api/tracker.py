"""Saved jobs: the 'saved' status of the application tracker."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.jobs import SessionDep
from app.models import Application, Job

router = APIRouter(prefix="/api/saved", tags=["saved"])


class SavedState(BaseModel):
    job_id: str
    saved: bool


@router.post("/{job_id}", response_model=SavedState)
def save_job(job_id: str, session: SessionDep) -> SavedState:
    if session.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if session.get(Application, job_id) is None:
        session.add(Application(job_id=job_id, status="saved"))
        session.commit()
    return SavedState(job_id=job_id, saved=True)


@router.delete("/{job_id}", response_model=SavedState)
def unsave_job(job_id: str, session: SessionDep) -> SavedState:
    """Only a plain 'saved' entry can be removed; applied/interview jobs stay tracked."""
    application = session.get(Application, job_id)
    if application is not None:
        if application.status != "saved":
            raise HTTPException(
                status_code=409, detail="Job is tracked with another status"
            )
        session.delete(application)
        session.commit()
    return SavedState(job_id=job_id, saved=False)
