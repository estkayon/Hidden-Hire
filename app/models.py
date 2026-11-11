"""Local database tables. All datetimes are stored in UTC."""

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, index=True)
    source_job_id: Mapped[str | None] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(String)

    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    location_raw: Mapped[str] = mapped_column(String, default="")
    country: Mapped[str | None] = mapped_column(String(2), index=True)
    city: Mapped[str | None] = mapped_column(String)
    work_type: Mapped[str] = mapped_column(String, default="unknown")
    remote_scope: Mapped[str] = mapped_column(String, default="unknown")

    apply_url: Mapped[str | None] = mapped_column(String)
    apply_email: Mapped[str | None] = mapped_column(String)

    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_period: Mapped[str | None] = mapped_column(String)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    deadline: Mapped[date | None] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    seniority: Mapped[str | None] = mapped_column(String)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    also_seen: Mapped[list] = mapped_column(JSON, default=list)


class Score(Base):
    __tablename__ = "scores"

    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    stage1_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    justification: Mapped[str] = mapped_column(Text, default="")
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    model: Mapped[str | None] = mapped_column(String)


class Application(Base):
    """Tracked jobs. The foreign key has no cascade, so a tracked job can never be deleted."""

    __tablename__ = "applications"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, default="saved")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str] = mapped_column(Text, default="")
    cv_path: Mapped[str | None] = mapped_column(String)
    letter_path: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )


class CompanyPref(Base):
    __tablename__ = "companies_prefs"

    company: Mapped[str] = mapped_column(String, primary_key=True)
    preference: Mapped[str] = mapped_column(String)  # "watch" or "block"


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, index=True)
    run_at: Mapped[datetime] = mapped_column(DateTime)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_kept: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
