"""Owner profile: master CV (PDF) and confirmed profile data. Stored only in profile/ (git-ignored)."""

import re
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

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s\-()]{8,}\d")
GITHUB = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9-]+", re.IGNORECASE)
LINKEDIN = re.compile(
    r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_%-]+", re.IGNORECASE
)
PORTFOLIO = re.compile(
    r"(?:https?://)?[\w-]+\.github\.io(?:/[\w./-]*)?|https?://[^\s,;)]+", re.IGNORECASE
)
NAME_LINE = re.compile(r"^[A-Za-z][A-Za-z.' -]{2,60}$")


class PersonalInfo(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    github: str = ""
    linkedin: str = ""
    portfolio: str = ""


class Profile(BaseModel):
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
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
        links = _link_uris(reader)
    except (PdfReadError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("The PDF could not be read.") from exc
    if links:
        text = f"{text}\n\nLinks:\n" + "\n".join(links)
    if len(text) < MIN_CV_CHARS:
        raise ValueError(
            "No text found in the PDF. Is it a scanned image? Export it as a text PDF."
        )
    return text


def _link_uris(reader: PdfReader) -> list[str]:
    """URLs of clickable links (link annotations), which page text often hides behind a word."""
    uris: list[str] = []
    for page in reader.pages:
        for annot in page.get("/Annots") or []:
            action = annot.get_object().get("/A") or {}
            uri = action.get("/URI")
            if (
                isinstance(uri, str)
                and uri.startswith(("http://", "https://"))
                and uri not in uris
            ):
                uris.append(uri)
    return uris


def detect_skills(text: str) -> list[str]:
    """Skills from config/skills.yaml that the text mentions."""
    found = []
    for item in load_config("skills.yaml")["skills"]:
        if has_any(text, [item["name"], *item.get("aliases", [])]):
            found.append(item["name"])
    return found


def _url(match: re.Match | None) -> str:
    if match is None:
        return ""
    value = match.group(0).rstrip("./")
    return value if value.lower().startswith("http") else f"https://{value}"


def _phone(text: str) -> str:
    for match in PHONE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 10 <= len(digits) <= 15:
            return match.group(0).strip()
    return ""


def _name(text: str) -> str:
    """First short line that looks like a person's name."""
    for line in text.splitlines()[:5]:
        line = line.strip()
        if NAME_LINE.match(line) and 2 <= len(line.split()) <= 6:
            return line
    return ""


def extract_personal(text: str) -> PersonalInfo:
    """Contact details written in the CV text. Location is left for the owner to fill in."""
    email = EMAIL.search(text)
    portfolio = next(
        (
            m
            for m in PORTFOLIO.finditer(text)
            if not GITHUB.fullmatch(m.group(0))
            and "linkedin.com" not in m.group(0).lower()
        ),
        None,
    )
    return PersonalInfo(
        full_name=_name(text),
        email=email.group(0) if email else "",
        phone=_phone(text),
        github=_url(GITHUB.search(text)),
        linkedin=_url(LINKEDIN.search(text)),
        portfolio=_url(portfolio),
    )


def merge_personal(current: PersonalInfo, found: PersonalInfo) -> PersonalInfo:
    """Fill only empty fields, so the owner's edits are never overwritten."""
    return PersonalInfo(
        **{
            field: getattr(current, field) or getattr(found, field)
            for field in PersonalInfo.model_fields
        }
    )


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
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def has_cv() -> bool:
    return _path("cv.txt").exists()


def cv_text() -> str | None:
    path = _path("cv.txt")
    return path.read_text(encoding="utf-8") if path.exists() else None


def save_cv(data: bytes, filename: str) -> tuple[Profile, list[str]]:
    """Store the CV and its text. New profiles start with detected skills; empty contact fields are filled."""
    text = extract_pdf_text(data)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _path("cv.pdf").write_bytes(data)
    _path("cv.txt").write_text(text, encoding="utf-8")

    detected = detect_skills(text)
    profile = load_profile() or Profile(skills=detected)
    profile = profile.model_copy(
        update={
            "personal": merge_personal(profile.personal, extract_personal(text)),
            "cv_file": filename,
            "cv_uploaded_at": datetime.now(UTC),
        }
    )
    save_profile(profile)
    return profile, detected


def delete_cv() -> None:
    for name in ("cv.pdf", "cv.txt", "profile.yaml"):
        _path(name).unlink(missing_ok=True)
