"""Shared HTTP client: timeouts, retries and user agent for all sources."""

import logging
import time
from typing import Any

import httpx

USER_AGENT = (
    "HiddenHire/0.1 (personal job search; +https://github.com/estkayon/Hidden-Hire)"
)
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2.0

log = logging.getLogger(__name__)


def create_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
    )


def get(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """GET with retries on network errors and 429/5xx. Raises after the last attempt."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.get(url, params=params, headers=headers)
        except httpx.TransportError as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            reason = type(exc).__name__
        else:
            if response.status_code not in RETRY_STATUS or attempt == MAX_ATTEMPTS:
                response.raise_for_status()
                return response
            reason = f"HTTP {response.status_code}"

        # Log only the base URL: query params may contain API keys.
        log.warning(
            "GET %s failed (%s), retry %d/%d", url, reason, attempt, MAX_ATTEMPTS - 1
        )
        time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))

    raise RuntimeError("unreachable")
