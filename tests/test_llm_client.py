from types import SimpleNamespace

import pytest

from app.llm import client


def fake_response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_complete_uses_task_model_and_returns_text(monkeypatch):
    calls = {}

    def fake_completion(**kwargs):
        calls.update(kwargs)
        return fake_response("hello")

    monkeypatch.setattr(client.litellm, "completion", fake_completion)
    text = client.complete(
        "documents", [{"role": "user", "content": "hi"}], json_output=True
    )

    assert text == "hello"
    assert calls["model"] == client.load_settings()["documents"]["model"]
    assert calls["response_format"] == {"type": "json_object"}


def test_complete_wraps_provider_errors(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("rate limited, prompt was: secret cv text")

    monkeypatch.setattr(client.litellm, "completion", boom)
    with pytest.raises(client.LLMError) as info:
        client.complete("scoring", [{"role": "user", "content": "hi"}])
    assert "secret" not in str(info.value)


def test_empty_reply_is_an_error(monkeypatch):
    monkeypatch.setattr(
        client.litellm, "completion", lambda **kwargs: fake_response("")
    )
    with pytest.raises(client.LLMError):
        client.complete("scoring", [{"role": "user", "content": "hi"}])
