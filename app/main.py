"""Local FastAPI app. Binds to 127.0.0.1 only."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import documents, health, jobs, master, profile, refresh, tracker
from app.autosync import sync_forever
from app.db import init_db

HOST = "127.0.0.1"
PORT = 8000
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Background sync runs only when started with `python -m app.main`, never in tests."""
    init_db()
    task = (
        asyncio.create_task(sync_forever())
        if getattr(app.state, "autosync", False)
        else None
    )
    yield
    if task is not None:
        task.cancel()


app = FastAPI(title="Hidden Hire", lifespan=lifespan)
app.include_router(jobs.router)
app.include_router(tracker.router)
app.include_router(tracker.applied_router)
app.include_router(health.router)
app.include_router(profile.router)
app.include_router(documents.router)
app.include_router(master.router)
app.include_router(refresh.router)

# Built dashboard (npm run build). Mounted last so /api routes always win.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    app.state.autosync = True
    uvicorn.run(app, host=HOST, port=PORT)
