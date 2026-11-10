"""Common interface for all job sources."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from pydantic import ValidationError

from fetcher.models import Job

log = logging.getLogger(__name__)


@dataclass
class FetchResult:
    jobs: list[Job] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self, client: httpx.Client) -> FetchResult:
        """Fetch jobs. Must not raise: failures go into FetchResult.errors."""


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
            try:
                items = self.fetch_items(client, token)
            except (httpx.HTTPError, ValueError) as exc:
                error = f"{self.name}/{token}: {describe_error(exc)}"
                log.warning(error)
                result.errors.append(error)
                continue

            for item in items:
                try:
                    result.jobs.append(self.parse(item, token, company))
                except (KeyError, TypeError, ValueError, ValidationError) as exc:
                    result.errors.append(
                        f"{self.name}/{token}: bad job ({describe_error(exc)})"
                    )
        return result


def describe_error(exc: Exception) -> str:
    """Short error text without URLs, so API keys in query params never reach logs."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__
