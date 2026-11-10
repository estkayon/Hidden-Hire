"""Common interfaces for all job sources."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial

import httpx
from pydantic import ValidationError

from fetcher.models import Job

log = logging.getLogger(__name__)

PARSE_ERRORS = (KeyError, TypeError, ValueError, ValidationError)


@dataclass
class FetchResult:
    jobs: list[Job] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self, client: httpx.Client) -> FetchResult:
        """Fetch jobs. Must not raise: failures go into FetchResult.errors."""


class FeedSource(Source):
    """Job board with a single feed for all its jobs."""

    @abstractmethod
    def fetch_items(self, client: httpx.Client) -> list[dict]:
        """Raw job items from the feed."""

    @abstractmethod
    def parse(self, item: dict) -> Job:
        """Turn one raw item into a Job."""

    def fetch(self, client: httpx.Client) -> FetchResult:
        result = FetchResult()
        try:
            items = self.fetch_items(client)
        except (httpx.HTTPError, ValueError) as exc:
            _record_error(result, f"{self.name}: {describe_error(exc)}")
            return result
        _parse_items(result, items, self.parse, self.name)
        return result


class BoardSource(Source):
    """ATS source with one public job board per company."""

    def __init__(self, boards: dict[str, str]) -> None:
        """boards: board token -> company display name."""
        self.boards = boards

    @abstractmethod
    def fetch_items(self, client: httpx.Client, token: str) -> list[dict]:
        """Raw job items for one board."""

    @abstractmethod
    def parse(self, item: dict, token: str, company: str) -> Job:
        """Turn one raw item into a Job."""

    def fetch(self, client: httpx.Client) -> FetchResult:
        result = FetchResult()
        for token, company in self.boards.items():
            label = f"{self.name}/{token}"
            try:
                items = self.fetch_items(client, token)
            except (httpx.HTTPError, ValueError) as exc:
                _record_error(result, f"{label}: {describe_error(exc)}")
                continue
            parse = partial(self.parse, token=token, company=company)
            _parse_items(result, items, parse, label)
        return result


def _record_error(result: FetchResult, error: str) -> None:
    log.warning(error)
    result.errors.append(error)


def _parse_items(
    result: FetchResult, items: list[dict], parse: Callable[[dict], Job], label: str
) -> None:
    for item in items:
        try:
            result.jobs.append(parse(item))
        except PARSE_ERRORS as exc:
            result.errors.append(f"{label}: bad job ({describe_error(exc)})")


def describe_error(exc: Exception) -> str:
    """Short error text without URLs, so API keys in query params never reach logs."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__
