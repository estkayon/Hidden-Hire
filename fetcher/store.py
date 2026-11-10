"""Write new jobs as JSON Lines and a source health report."""

import json
from datetime import datetime
from pathlib import Path

from fetcher.models import Job


def _read_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def write_jobs(jobs: list[Job], out_dir: Path, now: datetime) -> int:
    """Append never-seen jobs to jobs/YYYY-MM-DD.jsonl. Returns how many were written."""
    seen_path = out_dir / "seen_ids.txt"
    jobs_path = out_dir / "jobs" / f"{now:%Y-%m-%d}.jsonl"
    jobs_path.parent.mkdir(parents=True, exist_ok=True)

    seen = _read_seen(seen_path)
    new_jobs = []
    for job in jobs:
        if job.id not in seen:
            seen.add(job.id)
            new_jobs.append(job)

    with jobs_path.open("a", encoding="utf-8") as f:
        f.writelines(job.model_dump_json() + "\n" for job in new_jobs)
    with seen_path.open("a", encoding="utf-8") as f:
        f.writelines(job.id + "\n" for job in new_jobs)
    return len(new_jobs)


def write_health(sources: list[dict], out_dir: Path, now: datetime) -> Path:
    """Write health/latest.json: run time and per-source counts and errors."""
    path = out_dir / "health" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {"run_at": now.isoformat(), "sources": sources}
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
