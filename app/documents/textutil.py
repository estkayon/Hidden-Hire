"""Small text helpers shared by CV tailoring and the master CV builder."""

import re
import unicodedata

from rapidfuzz import fuzz, process

NAME_MATCH_SCORE = 90
ODD_HYPHENS = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2212": "-"})


def clean(text: str) -> str:
    """Plain hyphens and single spaces, so the PDF font can show every character."""
    return re.sub(r"\s+", " ", text.translate(ODD_HYPHENS)).strip()


def key(name: str) -> str:
    return re.sub(
        r"[^a-z0-9]+", " ", unicodedata.normalize("NFKC", name).lower()
    ).strip()


def match[T](name: str, options: dict[str, T]) -> T | None:
    """Find an item by its full or short name (the part before a dash), tolerating small differences."""
    keyed = {}
    for option, value in options.items():
        keyed[key(option)] = value
        short = re.split(r"\s[–-]\s", option, maxsplit=1)[0]
        keyed.setdefault(key(short), value)
    found = process.extractOne(
        key(name), list(keyed), scorer=fuzz.ratio, score_cutoff=NAME_MATCH_SCORE
    )
    return keyed[found[0]] if found else None
