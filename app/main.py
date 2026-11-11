"""Local FastAPI app. Binds to 127.0.0.1 only."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api import health, jobs, tracker
from app.db import init_db

HOST = "127.0.0.1"
PORT = 8000


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Hidden Hire", lifespan=lifespan)
app.include_router(jobs.router)
app.include_router(tracker.router)
app.include_router(health.router)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
