"""SQLite engine and sessions for the local app."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "hidden_hire.db"


class Base(DeclarativeBase):
    pass


def create_db_engine(path: Path = DB_PATH) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _record) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    """Create all tables that do not exist yet."""
    from app import models  # noqa: F401  registers the tables

    Base.metadata.create_all(engine)
