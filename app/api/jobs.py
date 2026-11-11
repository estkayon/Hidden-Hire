"""Job list, search, detail and paste endpoints."""

import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Job
from app.sync import naive_utc, to_row
from fetcher.models import Job as JobRecord
from fetcher.models import make_job_id
from fetcher.normalize import country_tier, normalize_job

NEW_HOURS = 48
MAIN_VIEW_DAYS = 7
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+\w")
URL = re.compile(r"https?://[^\s<>\"')\]]+")

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
SessionDep = Annotated[Session, Depends(get_session)]


class JobSummary(BaseModel):
    id: str
    title: str
    company: str
    location_raw: str
    country: str | None
    city: str | None
    work_type: str
    remote_scope: str
    source: str
    seniority: str | None
    also_seen: list[str]
    posted_at: datetime | None
    deadline: date | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    salary_period: str | None
    is_new: bool
    country_tier: int


class JobDetail(JobSummary):
    description: str
    source_url: str | None
    apply_url: str | None
    apply_email: str | None
    tags: list[str]


class JobList(BaseModel):
    total: int
    jobs: list[JobSummary]


class PasteJob(BaseModel):
    """A job posting pasted by the owner (Facebook post, email, message)."""

    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=20, max_length=20_000)
    location: str = Field(default="", max_length=200)
    url: str | None = Field(default=None, max_length=2_000, pattern=r"^https?://")


def _to_model[T: JobSummary](job: Job, model: type[T], now: datetime) -> T:
    seen_at = (job.posted_at or job.fetched_at).replace(tzinfo=UTC)
    data = {
        name: getattr(job, name) for name in model.model_fields if hasattr(job, name)
    }
    data["posted_at"] = job.posted_at.replace(tzinfo=UTC) if job.posted_at else None
    data["is_new"] = now - seen_at <= timedelta(hours=NEW_HOURS)
    data["country_tier"] = country_tier(job.country)
    return model(**data)


@router.get("", response_model=JobList)
def list_jobs(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    country: Annotated[list[str] | None, Query()] = None,
    work_type: Annotated[list[str] | None, Query()] = None,
    source: Annotated[list[str] | None, Query()] = None,
    posted_within_hours: Annotated[int | None, Query(ge=1, le=240)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobList:
    """Newest first. Without a search query, only the last 7 days are shown."""
    now = datetime.now(UTC)
    seen_at = func.coalesce(Job.posted_at, Job.fetched_at)
    stmt = select(Job)

    if q:
        stmt = stmt.where(
            or_(
                Job.title.icontains(q, autoescape=True),
                Job.company.icontains(q, autoescape=True),
                Job.description.icontains(q, autoescape=True),
            )
        )
    if posted_within_hours:
        stmt = stmt.where(
            seen_at >= naive_utc(now - timedelta(hours=posted_within_hours))
        )
    elif not q:
        stmt = stmt.where(seen_at >= naive_utc(now - timedelta(days=MAIN_VIEW_DAYS)))
    if country:
        stmt = stmt.where(Job.country.in_([c.upper() for c in country]))
    if work_type:
        stmt = stmt.where(Job.work_type.in_(work_type))
    if source:
        stmt = stmt.where(Job.source.in_(source))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(stmt.order_by(seen_at.desc()).limit(limit).offset(offset))
    return JobList(total=total, jobs=[_to_model(job, JobSummary, now) for job in rows])


@router.post("/paste", response_model=JobDetail, status_code=201)
def paste_job(body: PasteJob, session: SessionDep) -> JobDetail:
    """Save a pasted job. Pasting the same text again returns the saved job."""
    now = datetime.now(UTC)
    job_id = make_job_id("paste", body.text)
    existing = session.get(Job, job_id)
    if existing is not None:
        return _to_model(existing, JobDetail, now)

    email = EMAIL.search(body.text)
    link = URL.search(body.text)
    record = normalize_job(
        JobRecord(
            id=job_id,
            source="paste",
            title=body.title,
            company=body.company,
            description=body.text.strip(),
            location_raw=body.location,
            apply_url=body.url or (link.group(0).rstrip(".,;:!?") if link else None),
            apply_email=email.group(0) if email else None,
            posted_at=now,
            fetched_at=now,
        )
    )
    row = to_row(record)
    session.add(row)
    session.commit()
    return _to_model(row, JobDetail, now)


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, session: SessionDep) -> JobDetail:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_model(job, JobDetail, datetime.now(UTC))
