import json
from datetime import UTC, datetime, timedelta

from fetcher.models import Job
from fetcher.store import prune_job_files, write_health, write_jobs

NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def make_job(job_id: str) -> Job:
    return Job(id=job_id, source="test", title="ML Engineer", company="Acme")


def test_write_jobs_skips_seen_ids(tmp_path):
    assert write_jobs([make_job("a"), make_job("b"), make_job("a")], tmp_path, NOW) == 2
    assert write_jobs([make_job("b"), make_job("c")], tmp_path, NOW) == 1

    lines = (
        (tmp_path / "jobs" / "2026-11-10.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert [json.loads(line)["id"] for line in lines] == ["a", "b", "c"]


def test_seen_ids_expire(tmp_path):
    write_jobs([make_job("a")], tmp_path, NOW)
    assert write_jobs([make_job("a")], tmp_path, NOW + timedelta(days=29)) == 0
    assert write_jobs([make_job("a")], tmp_path, NOW + timedelta(days=31)) == 1


def test_prune_removes_only_old_files(tmp_path):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    for name in [
        "2026-10-30.jsonl",
        "2026-10-31.jsonl",
        "2026-11-09.jsonl",
        "notes.jsonl",
    ]:
        (jobs_dir / name).write_text("", encoding="utf-8")

    assert prune_job_files(tmp_path, NOW) == 1
    assert sorted(p.name for p in jobs_dir.iterdir()) == [
        "2026-10-31.jsonl",
        "2026-11-09.jsonl",
        "notes.jsonl",
    ]


def test_write_health(tmp_path):
    sources = [{"source": "greenhouse", "jobs_found": 5, "jobs_kept": 2, "errors": []}]
    report = json.loads(
        write_health(sources, tmp_path, NOW).read_text(encoding="utf-8")
    )
    assert report["run_at"] == NOW.isoformat()
    assert report["sources"] == sources
