"""Pull the data repo, import new jobs into the local database, then score them.

Jobs come from the data repo (filled by GitHub Actions) and from data/jobs, where a local
fetch writes. When the newest fetch in either place is older than STALE_HOURS, a local
fetch runs first, so jobs stay fresh even when GitHub skips scheduled runs.
"""

import json
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import chain
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import Application, Job, SourceRun
from fetcher.dedup import clean_company, is_same_job
from fetcher.filters import RETENTION_DAYS, is_fresh
from fetcher.models import Job as JobRecord
from fetcher.normalize import normalize_job

ROOT = Path(__file__).resolve().parent.parent
REPO_DIR = ROOT / "data" / "repo"
LOCAL_DIR = REPO_DIR.parent
GIT_TIMEOUT = 120
FETCH_TIMEOUT = 900
STALE_HOURS = 6

log = logging.getLogger("sync")


@dataclass
class SyncResult:
    added: int
    removed: int
    runs: int
    fetched_locally: bool
    last_fetch_at: datetime | None


def naive_utc(value: datetime | None) -> datetime | None:
    """SQLite keeps no time zone, so all datetimes are stored as naive UTC."""
    return value.astimezone(UTC).replace(tzinfo=None) if value else None


def pull_data_repo(repo_url: str, repo_dir: Path = REPO_DIR) -> None:
    if (repo_dir / ".git").exists():
        cmd = ["git", "-C", str(repo_dir), "pull", "--ff-only", "--quiet"]
    else:
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--quiet", repo_url, str(repo_dir)]
    subprocess.run(cmd, check=True, timeout=GIT_TIMEOUT)


def read_run_at(directory: Path) -> datetime | None:
    """Time of the fetch run recorded in directory/health/latest.json."""
    try:
        report = json.loads(
            (directory / "health" / "latest.json").read_text(encoding="utf-8")
        )
        run_at = datetime.fromisoformat(report["run_at"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return run_at if run_at.tzinfo else run_at.replace(tzinfo=UTC)


def latest_fetch_at(directories: list[Path]) -> datetime | None:
    return max((t for t in map(read_run_at, directories) if t), default=None)


def is_stale(last_fetch: datetime | None, now: datetime) -> bool:
    return last_fetch is None or now - last_fetch > timedelta(hours=STALE_HOURS)


def fetch_locally() -> bool:
    """Run the fetcher on this PC, writing to data/jobs. Takes a few minutes."""
    cmd = [sys.executable, "-m", "fetcher.run", "--out", str(LOCAL_DIR)]
    try:
        subprocess.run(cmd, check=True, timeout=FETCH_TIMEOUT, cwd=ROOT)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        log.error("local fetch failed (%s)", type(exc).__name__)
        return False
    return True


def read_records(repo_dir: Path) -> Iterator[JobRecord]:
    """Validated jobs from all daily files. Invalid lines are skipped."""
    for path in sorted((repo_dir / "jobs").glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    yield JobRecord.model_validate_json(line)
                except ValidationError:
                    log.warning("skipped invalid line in %s", path.name)


def to_row(record: JobRecord) -> Job:
    data = record.model_dump()
    data["posted_at"] = naive_utc(record.posted_at)
    data["fetched_at"] = naive_utc(record.fetched_at)
    return Job(**data)


def import_jobs(session: Session, records: Iterator[JobRecord], now: datetime) -> int:
    """Add unseen, fresh jobs. A job already stored from another source only adds to also_seen."""
    known_ids = set(session.scalars(select(Job.id)))
    by_company: dict[str, list[Job]] = {}
    for job in session.scalars(select(Job)):
        by_company.setdefault(clean_company(job.company), []).append(job)

    added = 0
    for record in records:
        if record.id in known_ids or not is_fresh(record, now):
            continue
        known_ids.add(record.id)
        key = clean_company(record.company)
        twin = next(
            (job for job in by_company.get(key, []) if is_same_job(job, record)), None
        )
        if twin is not None:
            entry = f"{record.source}: {record.source_url or record.apply_url or ''}"
            if entry not in twin.also_seen:
                twin.also_seen = [*twin.also_seen, entry]
            continue
        row = to_row(normalize_job(record))
        session.add(row)
        by_company.setdefault(key, []).append(row)
        added += 1
    return added


def delete_old_jobs(session: Session, now: datetime) -> int:
    """Delete jobs past the retention period, except jobs in the application tracker."""
    cutoff = naive_utc(now) - timedelta(days=RETENTION_DAYS)
    is_old = or_(
        Job.posted_at < cutoff, and_(Job.posted_at.is_(None), Job.fetched_at < cutoff)
    )
    tracked = select(Application.job_id)
    result = session.execute(delete(Job).where(is_old, Job.id.not_in(tracked)))
    return result.rowcount


def import_health(session: Session, repo_dir: Path) -> int:
    """Record the latest fetch run per source, once."""
    try:
        report = json.loads(
            (repo_dir / "health" / "latest.json").read_text(encoding="utf-8")
        )
        run_at = naive_utc(datetime.fromisoformat(report["run_at"]))
        sources = report["sources"]
    except (OSError, ValueError, KeyError, TypeError):
        log.warning("health report missing or invalid in %s", repo_dir.name)
        return 0
    if session.scalar(select(SourceRun.id).where(SourceRun.run_at == run_at).limit(1)):
        return 0
    rows = [
        SourceRun(
            source=s.get("source", "unknown"),
            run_at=run_at,
            jobs_found=s.get("jobs_found", 0),
            jobs_kept=s.get("jobs_kept", 0),
            errors=s.get("errors", []),
        )
        for s in sources
        if isinstance(s, dict)
    ]
    session.add_all(rows)
    return len(rows)


def score_jobs() -> None:
    """Stage 1 scoring after import. Stage 2 (LLM) runs only on request from a job's page."""
    try:
        from app.scoring.run import run_scoring  # heavy ML import, only when installed
    except ImportError:
        log.warning("scoring skipped: install requirements-ml.txt")
        return
    scored = run_scoring()
    if scored is not None:
        log.info("scored %d jobs", scored)


def sync_once(now: datetime | None = None) -> SyncResult:
    """Pull, fetch locally if the data is stale, import, clean up and score."""
    now = now or datetime.now(UTC)
    repo_url = os.environ.get("DATA_REPO_URL")
    if repo_url:
        try:
            pull_data_repo(repo_url)
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            OSError,
        ) as exc:
            log.error(
                "git pull failed (%s); using what is already on disk",
                type(exc).__name__,
            )
    else:
        log.warning("DATA_REPO_URL is not set; using local fetch only")

    fetched = False
    if is_stale(latest_fetch_at([REPO_DIR, LOCAL_DIR]), now):
        log.info(
            "newest fetch is older than %d hours; fetching on this PC", STALE_HOURS
        )
        fetched = fetch_locally()

    init_db()
    with SessionLocal.begin() as session:
        records = chain(read_records(REPO_DIR), read_records(LOCAL_DIR))
        added = import_jobs(session, records, now)
        removed = delete_old_jobs(session, now)
        runs = import_health(session, REPO_DIR) + import_health(session, LOCAL_DIR)
    log.info(
        "imported %d new jobs, deleted %d old jobs, recorded %d source runs",
        added,
        removed,
        runs,
    )
    score_jobs()
    return SyncResult(
        added, removed, runs, fetched, latest_fetch_at([REPO_DIR, LOCAL_DIR])
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    load_dotenv()
    sync_once()


if __name__ == "__main__":
    main()
