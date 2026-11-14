"""Sync status and the refresh button."""

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app import autosync

router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncStatusOut(BaseModel):
    running: bool
    started_at: datetime | None
    finished_at: datetime | None
    last_fetch_at: datetime | None
    added: int
    fetched_locally: bool
    error: str | None


@router.get("", response_model=SyncStatusOut)
def get_status() -> dict:
    return asdict(autosync.status)


@router.post("", response_model=SyncStatusOut, status_code=202)
def refresh() -> dict:
    autosync.start_now()
    return asdict(autosync.status)
