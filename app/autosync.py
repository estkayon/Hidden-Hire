"""Background sync for the running app: once at start, then every few hours, or on request."""

import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from dotenv import load_dotenv

from app.sync import sync_once

INTERVAL_HOURS = 3

log = logging.getLogger("autosync")


@dataclass
class SyncStatus:
    running: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_fetch_at: datetime | None = None
    added: int = 0
    fetched_locally: bool = False
    error: str | None = None


status = SyncStatus()
_lock = threading.Lock()


def run_sync() -> None:
    """One sync. Skipped if another sync is already running."""
    if not _lock.acquire(blocking=False):
        return
    status.running = True
    status.started_at = datetime.now(UTC)
    status.error = None
    try:
        load_dotenv()
        result = sync_once()
        status.added = result.added
        status.fetched_locally = result.fetched_locally
        status.last_fetch_at = result.last_fetch_at
    except Exception as exc:  # noqa: BLE001 - a failed sync must never stop the app
        log.error("sync failed (%s)", type(exc).__name__)
        status.error = type(exc).__name__
    finally:
        status.running = False
        status.finished_at = datetime.now(UTC)
        _lock.release()


def start_now() -> bool:
    """Start a sync in a background thread. False if one is already running."""
    if _lock.locked():
        return False
    threading.Thread(target=run_sync, daemon=True).start()
    return True


async def sync_forever() -> None:
    while True:
        await asyncio.to_thread(run_sync)
        await asyncio.sleep(INTERVAL_HOURS * 3600)
