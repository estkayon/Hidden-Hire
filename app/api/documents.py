"""Tailored CV: generate on request, report status, download PDF or LaTeX source."""

import re
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.jobs import SessionDep
from app.models import Job

router = APIRouter(prefix="/api/jobs", tags=["documents"])

JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MEDIA_TYPES = {"pdf": "application/pdf", "tex": "application/x-tex"}


class CvStatus(BaseModel):
    exists: bool
    generated_at: datetime | None
    flags: list[str]


def _job_or_404(job_id: str, session) -> Job:
    job = session.get(Job, job_id) if JOB_ID.match(job_id) else None
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _file_stem(name: str, company: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", f"{name} CV {company}").strip("_")[:90]


@router.get("/{job_id}/cv", response_model=CvStatus)
def get_cv_status(job_id: str, session: SessionDep) -> CvStatus:
    from app.documents.tailor import cv_status

    job = _job_or_404(job_id, session)
    return CvStatus(**cv_status(job.id))


@router.post("/{job_id}/cv", response_model=CvStatus)
def create_cv(job_id: str, session: SessionDep) -> CvStatus:
    """Tailor the master CV to this job. Takes around half a minute."""
    from app.documents.cv import DocumentError
    from app.documents.tailor import cv_status, generate_cv
    from app.llm.client import LLMError

    job = _job_or_404(job_id, session)
    try:
        generate_cv(job)
    except LLMError as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy or unavailable. Try again in a minute.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="The model gave an unusable answer. Try again."
        ) from exc
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CvStatus(**cv_status(job.id))


@router.get("/{job_id}/cv.{kind}")
def download_cv(
    job_id: str, kind: Literal["pdf", "tex"], session: SessionDep, inline: bool = False
) -> FileResponse:
    """inline=true shows the file in the browser (used for the preview) instead of downloading it."""
    from app.documents.cv import load_master
    from app.documents.tailor import cv_files

    job = _job_or_404(job_id, session)
    path = cv_files(job.id)[kind]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generate the CV first.")
    stem = _file_stem(load_master().header.name, job.company)
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[kind],
        filename=f"{stem}.{kind}",
        content_disposition_type="inline" if inline else "attachment",
    )
