"""Owner profile: master CV (PDF) and confirmed profile data. Stored only in profile/ (git-ignored)."""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from fetcher.normalize import has_any, load_config

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profile"
MAX_CV_BYTES = 5 * 1024 * 1024
MIN_CV_CHARS = 200


class Profile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    cv_file: str | None = None
    cv_uploaded_at: datetime | None = None


def _path(name: str) -> Path:
    return PROFILE_DIR / name


def extract_pdf_text(data: bytes) -> str:
    """Text of a PDF. Raises ValueError for non-PDFs, unreadable or scanned (image-only) files."""
    if not data.startswith(b"%PDF"):
        raise ValueError("The file is not a PDF.")
    try:
        reader = PdfReader(BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except (PdfReadError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("The PDF could not be read.") from exc
    if len(text) < MIN_CV_CHARS:
        raise ValueError(
            "No text found in the PDF. Is it a scanned image? Export it as a text PDF."
        )
    return text


def detect_skills(text: str) -> list[str]:
    """Skills from config/skills.yaml that the text mentions."""
    found = []
    for item in load_config("skills.yaml")["skills"]:
        if has_any(text, [item["name"], *item.get("aliases", [])]):
            found.append(item["name"])
    return found


def load_profile() -> Profile | None:
    path = _path("profile.yaml")
    if not path.exists():
        return None
    try:
        return Profile.model_validate(
            yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        )
    except (OSError, yaml.YAMLError, ValidationError):
        return None


def save_profile(profile: Profile) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    _path("profile.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def cv_text() -> str | None:
    path = _path("cv.txt")
    return path.read_text(encoding="utf-8") if path.exists() else None


def save_cv(data: bytes, filename: str) -> tuple[Profile, list[str]]:
    """Store the CV and its text. A new profile starts with the detected skills."""
    text = extract_pdf_text(data)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _path("cv.pdf").write_bytes(data)
    _path("cv.txt").write_text(text, encoding="utf-8")

    detected = detect_skills(text)
    profile = load_profile() or Profile(skills=detected)
    profile = profile.model_copy(
        update={"cv_file": filename, "cv_uploaded_at": datetime.now(UTC)}
    )
    save_profile(profile)
    return profile, detected


def delete_cv() -> None:
    for name in ("cv.pdf", "cv.txt", "profile.yaml"):
        _path(name).unlink(missing_ok=True)
