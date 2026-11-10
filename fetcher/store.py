"""Write new jobs as JSON Lines, prune old data and write a source health report."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from fetcher.filters import RETENTION_DAYS
from fetcher.models import Job

SEEN_DAYS = 30  # longer than retention, so jobs without a posted date are not re-added


def _read_seen(path: Path) -> dict[str, date]:
    seen: dict[str, date] = {}
    if not path.exists():
        return seen
    for line in path.read_text(encoding="utf-8").splitlines():
        job_id, _, day = line.partition("\t")
        try:
            seen[job_id] = date.fromisoformat(day)
        except ValueError:
            continue
    return seen


def write_jobs(jobs: list[Job], out_dir: Path, now: datetime) -> int:
    """Append never-seen jobs to jobs/YYYY-MM-DD.jsonl. Returns how many were written."""
    today = now.date()
    seen_path = out_dir / "seen_ids.txt"
    seen = {
        job_id: day
        for job_id, day in _read_seen(seen_path).items()
        if (today - day).days <= SEEN_DAYS
    }

    new_jobs = []
    for job in jobs:
        if job.id not in seen:
            seen[job.id] = today
            new_jobs.append(job)

    jobs_path = out_dir / "jobs" / f"{today.isoformat()}.jsonl"
    jobs_path.parent.mkdir(parents=True, exist_ok=True)
    with jobs_path.open("a", encoding="utf-8") as f:
        f.writelines(job.model_dump_json() + "\n" for job in new_jobs)
    seen_path.write_text(
        "".join(f"{job_id}\t{day.isoformat()}\n" for job_id, day in seen.items()),
        encoding="utf-8",
    )
    return len(new_jobs)


def prune_job_files(out_dir: Path, now: datetime) -> int:
    """Delete daily job files older than the retention period. Returns how many were removed."""
    cutoff = now.date() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for path in (out_dir / "jobs").glob("*.jsonl"):
        try:
            file_day = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if file_day < cutoff:
            path.unlink()
            removed += 1
    return removed


def write_health(sources: list[dict], out_dir: Path, now: datetime) -> Path:
    """Write health/latest.json: run time and per-source counts and errors."""
    path = out_dir / "health" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {"run_at": now.isoformat(), "sources": sources}
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
