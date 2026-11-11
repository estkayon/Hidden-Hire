"""Profile endpoints: upload the master CV, confirm skills and preferences, delete everything."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import profile as store
from app.profile import MAX_CV_BYTES, Profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileState(BaseModel):
    has_cv: bool
    profile: Profile | None
    detected_skills: list[str]


class ProfileUpdate(BaseModel):
    skills: list[str] = Field(default_factory=list, max_length=150)
    target_roles: list[str] = Field(default_factory=list, max_length=20)
    years_experience: float | None = Field(default=None, ge=0, le=60)


def _clean(values: list[str], max_len: int = 60) -> list[str]:
    """Trim, drop empties and duplicates, keep the given order."""
    seen: dict[str, str] = {}
    for value in values:
        value = value.strip()[:max_len]
        if value and value.lower() not in seen:
            seen[value.lower()] = value
    return list(seen.values())


def _state() -> ProfileState:
    text = store.cv_text()
    return ProfileState(
        has_cv=text is not None,
        profile=store.load_profile(),
        detected_skills=store.detect_skills(text) if text else [],
    )


@router.get("", response_model=ProfileState)
def get_profile() -> ProfileState:
    return _state()


@router.post("/cv", response_model=ProfileState)
async def upload_cv(file: UploadFile) -> ProfileState:
    data = await file.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(status_code=413, detail="The CV must be 5 MB or smaller.")
    try:
        store.save_cv(data, Path(file.filename or "cv.pdf").name[:120])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _state()


@router.put("", response_model=ProfileState)
def update_profile(body: ProfileUpdate) -> ProfileState:
    current = store.load_profile()
    if current is None:
        raise HTTPException(status_code=409, detail="Upload your CV first.")
    store.save_profile(
        current.model_copy(
            update={
                "skills": _clean(body.skills),
                "target_roles": _clean(body.target_roles, max_len=80),
                "years_experience": body.years_experience,
            }
        )
    )
    return _state()


@router.delete("/cv", response_model=ProfileState)
def delete_cv() -> ProfileState:
    store.delete_cv()
    return _state()
