import json
from datetime import UTC, datetime, timedelta

from app.sync import is_stale, latest_fetch_at

NOW = datetime(2026, 11, 14, 6, 0, tzinfo=UTC)


def write_health(directory, run_at: str) -> None:
    (directory / "health").mkdir(parents=True)
    (directory / "health" / "latest.json").write_text(
        json.dumps({"run_at": run_at, "sources": []})
    )


def test_latest_fetch_picks_the_newest_run(tmp_path):
    repo, local, empty = tmp_path / "repo", tmp_path / "local", tmp_path / "empty"
    write_health(repo, "2026-11-14T01:00:00+00:00")
    write_health(local, "2026-11-14T04:30:00Z")
    assert latest_fetch_at([repo, local, empty]) == datetime(
        2026, 11, 14, 4, 30, tzinfo=UTC
    )


def test_no_health_report_means_stale(tmp_path):
    assert latest_fetch_at([tmp_path]) is None
    assert is_stale(None, NOW)


def test_stale_only_after_six_hours():
    assert not is_stale(NOW - timedelta(hours=5), NOW)
    assert is_stale(NOW - timedelta(hours=7), NOW)
