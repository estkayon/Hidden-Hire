"""Find which supported ATS a company uses.

Usage: python -m fetcher.probe doctolib qonto glovo
"""

import sys

import httpx

from fetcher.http import create_client
from fetcher.sources.ashby import AshbySource
from fetcher.sources.base import PARSE_ERRORS, BoardSource
from fetcher.sources.greenhouse import GreenhouseSource
from fetcher.sources.lever import LeverSource
from fetcher.sources.personio import PersonioSource
from fetcher.sources.recruitee import RecruiteeSource
from fetcher.sources.teamtailor import TeamtailorSource
from fetcher.sources.workable import WorkableSource

SOURCES: list[type[BoardSource]] = [
    GreenhouseSource,
    LeverSource,
    AshbySource,
    WorkableSource,
    RecruiteeSource,
    PersonioSource,
    TeamtailorSource,
]


def _token(source: type[BoardSource], name: str) -> str:
    return f"{name}.teamtailor.com" if source is TeamtailorSource else name


def probe(client: httpx.Client, name: str) -> None:
    for source_cls in SOURCES:
        source = source_cls({})
        token = _token(source_cls, name)
        try:
            items = source.fetch_items(client, token)
        except (httpx.HTTPError, ValueError):
            continue
        if not items:
            continue
        try:
            sample = source.parse(items[0], token, name)
            example = f"{sample.title} | {sample.location_raw}"
        except PARSE_ERRORS:
            example = "(could not parse sample)"
        print(f"{name}: {source.name} token={token} jobs={len(items)} e.g. {example}")


def main() -> None:
    with create_client() as client:
        for name in sys.argv[1:]:
            probe(client, name.lower())


if __name__ == "__main__":
    main()
