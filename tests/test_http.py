import httpx
import pytest

from fetcher import http


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda _: None)


def client_with(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_retries_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) < 3 else 200, json={"ok": True})

    response = http.get(client_with(handler), "https://example.com/jobs")
    assert response.json() == {"ok": True}
    assert len(calls) == 3


def test_retries_network_error():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200)

    assert http.get(client_with(handler), "https://example.com").status_code == 200
    assert len(calls) == 2


def test_raises_after_max_attempts():
    with pytest.raises(httpx.HTTPStatusError):
        http.get(client_with(lambda r: httpx.Response(500)), "https://example.com")


def test_no_retry_on_404():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(404)

    with pytest.raises(httpx.HTTPStatusError):
        http.get(client_with(handler), "https://example.com")
    assert len(calls) == 1
