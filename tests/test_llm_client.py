from types import SimpleNamespace

import pytest

from app.llm import client

SETTINGS = {
    "timeout_seconds": 5,
    "scoring": {
        "max_tokens": 100,
        "reasoning_effort": "low",
        "models": [
            "groq/openai/gpt-oss-20b",
            "groq/qwen/qwen3.8-27b",
            {
                "model": "openai/@cf/x",
                "api_base": "https://cf.test/{CF_ACCOUNT}/v1",
                "api_key_env": "CF_KEY",
            },
        ],
    },
}


def fake_response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(client, "load_settings", lambda: SETTINGS)
    monkeypatch.setenv("CF_ACCOUNT", "acc123")
    monkeypatch.setenv("CF_KEY", "secret-key")


def test_first_model_answers_with_json_and_reasoning(monkeypatch):
    calls = []
    monkeypatch.setattr(
        client.litellm,
        "completion",
        lambda **kw: calls.append(kw) or fake_response("hello"),
    )
    assert (
        client.complete(
            "scoring", [{"role": "user", "content": "hi"}], json_output=True
        )
        == "hello"
    )
    assert calls[0]["model"] == "groq/openai/gpt-oss-20b"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["reasoning_effort"] == "low"


def test_falls_back_and_fills_api_base(monkeypatch):
    calls = []

    def completion(**kw):
        calls.append(kw)
        if kw["model"].startswith("groq/"):
            raise RuntimeError("rate limited")
        return fake_response("from cloudflare")

    monkeypatch.setattr(client.litellm, "completion", completion)
    assert (
        client.complete("scoring", [{"role": "user", "content": "hi"}])
        == "from cloudflare"
    )
    assert [c["model"] for c in calls] == [
        "groq/openai/gpt-oss-20b",
        "groq/qwen/qwen3.8-27b",
        "openai/@cf/x",
    ]
    assert "reasoning_effort" not in calls[1]
    assert calls[2]["api_base"] == "https://cf.test/acc123/v1"
    assert calls[2]["api_key"] == "secret-key"


def test_all_models_fail_without_leaking_messages(monkeypatch):
    def boom(**kw):
        raise RuntimeError("prompt was: secret cv text")

    monkeypatch.setattr(client.litellm, "completion", boom)
    with pytest.raises(client.LLMError) as info:
        client.complete("scoring", [{"role": "user", "content": "hi"}])
    assert "secret" not in str(info.value)
    assert str(info.value).count("RuntimeError") == 3


def test_empty_reply_moves_to_next_model(monkeypatch):
    replies = iter(["", "ok"])
    monkeypatch.setattr(
        client.litellm, "completion", lambda **kw: fake_response(next(replies))
    )
    assert client.complete("scoring", [{"role": "user", "content": "hi"}]) == "ok"


def test_json_code_fence_is_removed(monkeypatch):
    monkeypatch.setattr(
        client.litellm,
        "completion",
        lambda **kw: fake_response('```json\n{"a": 1}\n```'),
    )
    assert (
        client.complete(
            "scoring", [{"role": "user", "content": "hi"}], json_output=True
        )
        == '{"a": 1}'
    )
