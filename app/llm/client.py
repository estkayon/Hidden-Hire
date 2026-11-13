"""One small wrapper for all LLM calls, with a fallback chain of models per task."""

import argparse
import logging
import os
from functools import cache
from pathlib import Path
from typing import Literal

import litellm
import yaml
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
Task = Literal["scoring", "documents"]
REASONING_MODELS = ("gpt-oss",)  # only these accept reasoning_effort

litellm.suppress_debug_info = True
litellm.drop_params = (
    True  # skip options a provider does not support instead of failing
)

log = logging.getLogger("llm")


class LLMError(Exception):
    """Every configured model failed (no key, rate limit, network, provider error)."""


@cache
def load_settings() -> dict:
    """config/settings.yaml if present, otherwise the committed example."""
    load_dotenv()
    path = CONFIG_DIR / "settings.yaml"
    if not path.exists():
        path = CONFIG_DIR / "settings.example.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["llm"]


def _describe(exc: Exception) -> str:
    """Error type and HTTP status only; the message may echo the prompt (CV text)."""
    status = getattr(exc, "status_code", None)
    return f"{type(exc).__name__}{f' (HTTP {status})' if status else ''}"


def _strip_fence(text: str) -> str:
    """Some models wrap JSON in a ```json code block; return just the JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _model_options(entry: str | dict) -> dict:
    """LiteLLM arguments for one configured model."""
    if isinstance(entry, str):
        return {"model": entry}
    options = {"model": entry["model"]}
    if "api_base" in entry:
        options["api_base"] = entry["api_base"].format_map(os.environ)
    if "api_key_env" in entry:
        options["api_key"] = os.environ.get(entry["api_key_env"], "")
    return options


def model_entries(task: Task) -> list:
    task_settings = load_settings()[task]
    return task_settings.get("models") or [task_settings["model"]]


def complete(
    task: Task,
    messages: list[dict],
    *,
    json_output: bool = False,
    model: str | dict | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Text of the first model that answers. Raises LLMError when all of them fail."""
    settings = load_settings()
    task_settings = settings[task]
    failures = []
    for entry in [model] if model else model_entries(task):
        name = entry if isinstance(entry, str) else entry.get("model", "?")
        try:
            options = _model_options(entry)
            if "reasoning_effort" in task_settings and any(
                m in name for m in REASONING_MODELS
            ):
                options["reasoning_effort"] = task_settings["reasoning_effort"]
            response = litellm.completion(
                messages=messages,
                temperature=temperature,
                timeout=settings.get("timeout_seconds", 60),
                num_retries=1,
                max_tokens=max_tokens or task_settings.get("max_tokens"),
                response_format={"type": "json_object"} if json_output else None,
                **options,
            )
            content = response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001 - any provider error moves on to the next model
            failures.append(f"{name}: {_describe(exc)}")
            log.warning("LLM model failed, trying the next one: %s", failures[-1])
            continue
        if content:
            return _strip_fence(content) if json_output else content
        failures.append(f"{name}: empty response")
    raise LLMError("; ".join(failures) or "no model configured")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send one test prompt to the configured LLM."
    )
    parser.add_argument("prompt")
    parser.add_argument("--task", choices=["scoring", "documents"], default="scoring")
    parser.add_argument(
        "--position", type=int, help="test only the Nth model of the task (1 = first)"
    )
    parser.add_argument("--json", action="store_true", help="ask for a JSON object")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )

    model = model_entries(args.task)[args.position - 1] if args.position else None
    try:
        print(
            complete(
                args.task,
                [{"role": "user", "content": args.prompt}],
                model=model,
                json_output=args.json,
            )
        )
    except LLMError as exc:
        raise SystemExit(f"LLM call failed: {exc}") from exc


if __name__ == "__main__":
    main()
