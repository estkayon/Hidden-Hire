"""Job model shared by the fetcher and the local app."""

import hashlib
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkType = Literal["remote", "hybrid", "onsite", "unknown"]
RemoteScope = Literal["worldwide", "regions", "country", "unknown"]
SalaryPeriod = Literal["hour", "day", "week", "month", "year"]


def make_job_id(source: str, key: str) -> str:
    """Stable id from the source name and its job id (or apply URL)."""
    raw = f"{source.strip().lower()}:{key.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def utc_now() -> datetime:
    return datetime.now(UTC)


class Job(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_job_id: str | None = None
    source_url: str | None = None

    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    description: str = ""

    location_raw: str = ""
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    city: str | None = None
    work_type: WorkType = "unknown"
    remote_scope: RemoteScope = "unknown"

    apply_url: str | None = None
    apply_email: str | None = None

    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    salary_period: SalaryPeriod | None = None

    posted_at: datetime | None = None
    deadline: date | None = None
    fetched_at: datetime = Field(default_factory=utc_now)

    seniority: str | None = None  # only when the posting states it
    tags: list[str] = Field(default_factory=list)
    also_seen: list[str] = Field(
        default_factory=list
    )  # "source: url" of merged duplicates

    @field_validator("posted_at", "fetched_at")
    @classmethod
    def to_utc(cls, value: datetime | None) -> datetime | None:
        """Store all timestamps in UTC; naive values are treated as UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
