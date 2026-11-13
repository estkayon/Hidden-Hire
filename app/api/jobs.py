"""Job list, search, detail, paste and recruiter-view endpoints."""

import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.eligibility import Eligibility, eligibility
from app.models import Application, Job, Score
from app.scoring.source import candidate, has_source
from app.sync import naive_utc, to_row
from fetcher.models import Job as JobRecord
from fetcher.models import make_job_id
from fetcher.normalize import country_tier, html_to_text, normalize_job

NEW_HOURS = 48
MAIN_VIEW_DAYS = 7
RELEVANT_THRESHOLD = 60
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+\w")
URL = re.compile(r"https?://[^\s<>\"')\]]+")
HTML_TAG = re.compile(r"</?[a-z][^>]*>", re.IGNORECASE)

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
    saved: bool
    applied_at: datetime | None
    match: int | None
    eligibility: Eligibility


class JobDetail(JobSummary):
    description: str
    source_url: str | None
    apply_url: str | None
    apply_email: str | None
    tags: list[str]
    recruiter_view: dict | None


class JobList(BaseModel):
    total: int
    jobs: list[JobSummary]


class Facet(BaseModel):
    value: str
    count: int


class Facets(BaseModel):
    countries: list[Facet]
    sources: list[Facet]


class PasteJob(BaseModel):
    """A job posting pasted by the owner (Facebook post, email, message)."""

    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=20, max_length=20_000)
    location: str = Field(default="", max_length=200)
    url: str | None = Field(default=None, max_length=2_000, pattern=r"^https?://")


def _to_model[T: JobSummary](
    job: Job,
    model: type[T],
    now: datetime,
    application: Application | None,
    score: Score | None,
) -> T:
    seen_at = (job.posted_at or job.fetched_at).replace(tzinfo=UTC)
    applied = application is not None and application.status == "applied"
    data = {
        name: getattr(job, name) for name in model.model_fields if hasattr(job, name)
    }
    data["posted_at"] = job.posted_at.replace(tzinfo=UTC) if job.posted_at else None
    data["is_new"] = now - seen_at <= timedelta(hours=NEW_HOURS)
    data["country_tier"] = country_tier(job.country)
    data["saved"] = application is not None and application.status == "saved"
    data["applied_at"] = (
        application.applied_at.replace(tzinfo=UTC)
        if applied and application.applied_at
        else None
    )
    data["eligibility"] = eligibility(job)
    data["match"] = (
        round(score.final_score) if score and score.final_score is not None else None
    )
    if "recruiter_view" in model.model_fields:
        data["recruiter_view"] = (
            (score.breakdown or {}).get("stage2") if score else None
        )
    if HTML_TAG.search(data.get("description") or ""):
        data["description"] = html_to_text(
            data["description"]
        )  # older imports kept raw HTML
    return model(**data)


def _score_of(session: Session, job_id: str) -> Score | None:
    return session.get(Score, job_id) if has_source() else None


@router.get("", response_model=JobList)
def list_jobs(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    country: Annotated[list[str] | None, Query()] = None,
    work_type: Annotated[list[str] | None, Query()] = None,
    source: Annotated[list[str] | None, Query()] = None,
    posted_within_hours: Annotated[int | None, Query(ge=1, le=240)] = None,
    saved: bool = False,
    applied: bool = False,
    relevance: Literal["relevant", "other"] | None = None,
    min_match: Annotated[int | None, Query(ge=0, le=100)] = None,
    sort: Literal["newest", "match"] = "newest",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobList:
    """Without a search query, the saved or the applied filter, only the last 7 days are shown.
    Match filters and sorting apply only when a CV is uploaded."""
    now = datetime.now(UTC)
    scored = has_source()
    seen_at = func.coalesce(Job.posted_at, Job.fetched_at)
    stmt = select(Job, Score).outerjoin(Score, Score.job_id == Job.id)

    if saved:
        stmt = stmt.where(
            Job.id.in_(select(Application.job_id).where(Application.status == "saved"))
        )
    if applied:
        stmt = stmt.join(Application, Application.job_id == Job.id).where(
            Application.status == "applied"
        )
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
    elif not q and not saved and not applied:
        stmt = stmt.where(seen_at >= naive_utc(now - timedelta(days=MAIN_VIEW_DAYS)))
    if country:
        stmt = stmt.where(Job.country.in_([c.upper() for c in country]))
    if work_type:
        stmt = stmt.where(Job.work_type.in_(work_type))
    if source:
        stmt = stmt.where(Job.source.in_(source))
    if scored and relevance == "relevant":
        stmt = stmt.where(Score.final_score >= RELEVANT_THRESHOLD)
    elif scored and relevance == "other":
        stmt = stmt.where(
            or_(Score.final_score < RELEVANT_THRESHOLD, Score.final_score.is_(None))
        )
    if scored and min_match is not None:
        stmt = stmt.where(Score.final_score >= min_match)

    order = [seen_at.desc()]
    if applied:
        order = [Application.applied_at.desc()]
    elif scored and sort == "match":
        order = [Score.final_score.desc().nulls_last(), seen_at.desc()]

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.execute(stmt.order_by(*order).limit(limit).offset(offset)).all()
    ids = [job.id for job, _ in rows]
    applications = {
        a.job_id: a
        for a in session.scalars(select(Application).where(Application.job_id.in_(ids)))
    }
    return JobList(
        total=total,
        jobs=[
            _to_model(
                job,
                JobSummary,
                now,
                applications.get(job.id),
                score if scored else None,
            )
            for job, score in rows
        ],
    )


@router.get("/facets", response_model=Facets)
def get_facets(session: SessionDep) -> Facets:
    """Countries and sources present in the database, for filter menus."""

    def counts(column) -> list[Facet]:
        rows = session.execute(
            select(column, func.count())
            .where(column.is_not(None))
            .group_by(column)
            .order_by(func.count().desc())
        )
        return [Facet(value=value, count=count) for value, count in rows]

    return Facets(countries=counts(Job.country), sources=counts(Job.source))


@router.post("/paste", response_model=JobDetail, status_code=201)
def paste_job(body: PasteJob, session: SessionDep) -> JobDetail:
    """Save a pasted job. Pasting the same text again returns the saved job."""
    now = datetime.now(UTC)
    job_id = make_job_id("paste", body.text)
    existing = session.get(Job, job_id)
    if existing is not None:
        return _to_model(
            existing,
            JobDetail,
            now,
            session.get(Application, job_id),
            _score_of(session, job_id),
        )

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
    return _to_model(row, JobDetail, now, application=None, score=None)


@router.post("/{job_id}/recruiter-view", response_model=JobDetail)
def create_recruiter_view(job_id: str, session: SessionDep) -> JobDetail:
    """Run the Stage 2 (LLM) judgment for one job the owner picked."""
    from app.llm.client import LLMError  # LLM packages load only when used
    from app.scoring import llm_score

    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    found = candidate()
    if found is None:
        raise HTTPException(status_code=409, detail="Add your CV first.")
    profile, cv = found
    try:
        total, details = llm_score.judge(job, profile, cv)
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="The model gave an unusable answer. Try again."
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy or unavailable. Try again in a minute.",
        ) from exc
    llm_score.save_judgment(session, job.id, total, details)
    session.commit()
    return get_job(job_id, session)


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, session: SessionDep) -> JobDetail:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_model(
        job,
        JobDetail,
        datetime.now(UTC),
        session.get(Application, job_id),
        _score_of(session, job_id),
    )
