"""Source health: the latest fetch run per source."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.api.jobs import SessionDep
from app.models import SourceRun

router = APIRouter(prefix="/api/health", tags=["health"])

Status = Literal["ok", "partial", "empty", "failing"]


class SourceStatus(BaseModel):
    source: str
    run_at: datetime
    jobs_found: int
    jobs_kept: int
    errors: list[str]
    status: Status


class HealthReport(BaseModel):
    last_run_at: datetime | None
    sources: list[SourceStatus]


def source_status(jobs_found: int, errors: list[str]) -> Status:
    if errors:
        return "partial" if jobs_found else "failing"
    return "ok" if jobs_found else "empty"


@router.get("", response_model=HealthReport)
def get_health(session: SessionDep) -> HealthReport:
    latest = (
        select(SourceRun.source, func.max(SourceRun.run_at).label("run_at"))
        .group_by(SourceRun.source)
        .subquery()
    )
    runs = session.scalars(
        select(SourceRun)
        .join(
            latest,
            and_(
                SourceRun.source == latest.c.source, SourceRun.run_at == latest.c.run_at
            ),
        )
        .order_by(SourceRun.source)
    ).all()

    sources = [
        SourceStatus(
            source=run.source,
            run_at=run.run_at.replace(tzinfo=UTC),
            jobs_found=run.jobs_found,
            jobs_kept=run.jobs_kept,
            errors=run.errors or [],
            status=source_status(run.jobs_found, run.errors or []),
        )
        for run in runs
    ]
    last_run_at = max((s.run_at for s in sources), default=None)
    return HealthReport(last_run_at=last_run_at, sources=sources)
