"""Master CV builder: draft entries from notes or the uploaded CV, then merge the reviewed YAML."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.profile import cv_text

router = APIRouter(prefix="/api/master", tags=["master"])


class MasterSummary(BaseModel):
    exists: bool
    counts: dict[str, int]


class DraftRequest(BaseModel):
    text: str = Field(min_length=20, max_length=12_000)


class Draft(BaseModel):
    yaml: str
    flags: list[str]


class MergeRequest(BaseModel):
    yaml: str = Field(min_length=1, max_length=60_000)


class MergeResult(BaseModel):
    report: list[str]


def _draft(text: str) -> Draft:
    from app.documents.master import draft_from_text, draft_to_yaml
    from app.llm.client import LLMError

    try:
        draft, flags = draft_from_text(text)
    except LLMError as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy or unavailable. Try again in a minute.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="The model gave an unusable answer. Try again."
        ) from exc
    return Draft(yaml=draft_to_yaml(draft), flags=flags)


@router.get("", response_model=MasterSummary)
def get_master() -> MasterSummary:
    from app.documents.master import master_counts

    counts = master_counts()
    return MasterSummary(exists=counts is not None, counts=counts or {})


@router.post("/draft", response_model=Draft)
def draft_from_notes(body: DraftRequest) -> Draft:
    return _draft(body.text)


@router.post("/draft-from-cv", response_model=Draft)
def draft_from_uploaded_cv() -> Draft:
    text = cv_text()
    if text is None:
        raise HTTPException(status_code=409, detail="Upload your CV first.")
    return _draft(text)


@router.post("/merge", response_model=MergeResult)
def merge_draft(body: MergeRequest) -> MergeResult:
    from app.documents.cv import DocumentError
    from app.documents.master import (
        load_master_or_none,
        merge,
        parse_draft,
        save_master,
    )

    try:
        draft = parse_draft(body.yaml)
        cv, report = merge(load_master_or_none(), draft)
    except (ValueError, DocumentError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    save_master(cv)
    return MergeResult(report=report)
