"""One small wrapper for all LLM calls. Changing provider or model is a config change."""

import argparse
from functools import cache
from pathlib import Path
from typing import Literal

import litellm
import yaml
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
Task = Literal["scoring", "documents"]

litellm.suppress_debug_info = True


class LLMError(Exception):
    """The LLM call failed (no key, rate limit, network, provider error)."""


@cache
def load_settings() -> dict:
    """config/settings.yaml if present, otherwise the committed example."""
    load_dotenv()
    path = CONFIG_DIR / "settings.yaml"
    if not path.exists():
        path = CONFIG_DIR / "settings.example.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["llm"]


def complete(
    task: Task,
    messages: list[dict],
    *,
    json_output: bool = False,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Text of the model's reply. Raises LLMError so callers can fall back cleanly."""
    settings = load_settings()
    task_settings = settings[task]
    optional = {
        key: task_settings[key]
        for key in ("max_tokens", "reasoning_effort")
        if key in task_settings
    }
    if max_tokens is not None:
        optional["max_tokens"] = max_tokens
    try:
        response = litellm.completion(
            model=model or task_settings["model"],
            messages=messages,
            temperature=temperature,
            timeout=settings.get("timeout_seconds", 60),
            num_retries=2,
            response_format={"type": "json_object"} if json_output else None,
            **optional,
        )
    except Exception as exc:  # litellm maps every provider error to its own types; never log the message (may echo input)
        status = getattr(exc, "status_code", None)
        raise LLMError(
            f"{type(exc).__name__}{f' (HTTP {status})' if status else ''}"
        ) from exc
    content = response.choices[0].message.content
    if not content:
        raise LLMError("empty response")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send one test prompt to the configured LLM."
    )
    parser.add_argument("prompt")
    parser.add_argument("--task", choices=["scoring", "documents"], default="scoring")
    parser.add_argument("--model", help="override, e.g. groq/qwen/qwen3.8-27b")
    args = parser.parse_args()
    try:
        print(
            complete(
                args.task, [{"role": "user", "content": args.prompt}], model=args.model
            )
        )
    except LLMError as exc:
        raise SystemExit(f"LLM call failed: {exc}") from exc


if __name__ == "__main__":
    main()
