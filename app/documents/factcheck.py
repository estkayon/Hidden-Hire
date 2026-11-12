"""Checks that generated text claims nothing the master CV does not contain."""

import re

from app.profile import detect_skills

NUMBER = re.compile(r"\d+(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    return set(NUMBER.findall(text))


def unsupported(text: str, source: str) -> list[str]:
    """Numbers and known tech skills in text that the source never mentions."""
    issues = [f"number {n}" for n in sorted(numbers(text) - numbers(source))]
    issues += [
        f"skill {s}"
        for s in sorted(set(detect_skills(text)) - set(detect_skills(source)))
    ]
    return issues
