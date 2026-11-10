"""Fetcher entry point: fetch all sources, normalize, filter and store."""

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from fetcher.filters import keep_job
from fetcher.http import create_client
from fetcher.normalize import load_config, normalize_job
from fetcher.sources.ashby import AshbySource
from fetcher.sources.base import FetchResult, Source, describe_error
from fetcher.sources.greenhouse import GreenhouseSource
from fetcher.sources.lever import LeverSource
from fetcher.sources.recruitee import RecruiteeSource
from fetcher.sources.smartrecruiters import SmartRecruitersSource
from fetcher.sources.workable import WorkableSource
from fetcher.store import prune_job_files, write_health, write_jobs

log = logging.getLogger("fetcher")


def build_sources() -> list[Source]:
    companies = load_config("companies.yaml")
    return [
        GreenhouseSource(companies.get("greenhouse") or {}),
        LeverSource(companies.get("lever") or {}),
        AshbySource(companies.get("ashby") or {}),
        WorkableSource(companies.get("workable") or {}),
        RecruiteeSource(companies.get("recruitee") or {}),
        SmartRecruitersSource(companies.get("smartrecruiters") or {}),
    ]


def run_source(source: Source, client: httpx.Client) -> FetchResult:
    try:
        return source.fetch(client)
    except Exception as exc:  # noqa: BLE001 - a broken source must never stop the others
        error = f"{source.name}: {describe_error(exc)}"
        log.error(error)
        return FetchResult(errors=[error])


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch tech jobs from all sources.")
    parser.add_argument("--out", type=Path, default=Path("data"), help="output folder")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(
        logging.WARNING
    )  # httpx logs full URLs incl. API keys

    now = datetime.now(UTC)
    kept: list = []
    health: list[dict] = []
    with create_client() as client:
        for source in build_sources():
            result = run_source(source, client)
            jobs = [
                job for job in map(normalize_job, result.jobs) if keep_job(job, now)
            ]
            kept.extend(jobs)
            health.append(
                {
                    "source": source.name,
                    "jobs_found": len(result.jobs),
                    "jobs_kept": len(jobs),
                    "errors": result.errors,
                }
            )
            log.info(
                "%s: %d found, %d kept, %d errors",
                source.name,
                len(result.jobs),
                len(jobs),
                len(result.errors),
            )

    written = write_jobs(kept, args.out, now)
    removed = prune_job_files(args.out, now)
    write_health(health, args.out, now)
    log.info(
        "wrote %d new jobs, removed %d old files in %s", written, removed, args.out
    )


if __name__ == "__main__":
    main()
