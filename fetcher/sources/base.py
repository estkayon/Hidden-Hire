"""Common interface for all job sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from fetcher.models import Job


@dataclass
class FetchResult:
    jobs: list[Job] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self, client: httpx.Client) -> FetchResult:
        """Fetch jobs. Must not raise: failures go into FetchResult.errors."""


def describe_error(exc: Exception) -> str:
    """Short error text without URLs, so API keys in query params never reach logs."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__
