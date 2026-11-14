"""Master CV builder: draft entries from notes or the uploaded CV, merge them, and edit the whole CV."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.jobs import SessionDep
from app.documents.cv import CvData
from app.profile import cv_text

router = APIRouter(prefix="/api/master", tags=["master"])


class MasterSummary(BaseModel):
    exists: bool
    counts: dict[str, int]


class DraftRequest(BaseModel):
    text: str = Field(min_length=20, max_length=12_000)


class Draft(BaseModel):
    draft: dict
    flags: list[str]


class MergeRequest(BaseModel):
    draft: dict


class MergeResult(BaseModel):
    report: list[str]


class ExtractedText(BaseModel):
    text: str


def _reset_reviews(session) -> None:
    """Saved recruiter views were built from the old CV, so they are removed."""
    from app.scoring.llm_score import reset_recruiter_views

    reset_recruiter_views(session)
    session.commit()


def _rescore() -> None:
    """Recompute Stage 1 match scores after the master CV changes (runs after the response)."""
    try:
        from app.scoring.run import run_scoring
    except ImportError:
        return
    run_scoring()


def _draft(text: str) -> Draft:
    from app.documents.master import draft_from_text
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
    return Draft(draft=draft.model_dump(), flags=flags)


@router.get("", response_model=MasterSummary)
def get_master() -> MasterSummary:
    from app.documents.master import master_counts

    counts = master_counts()
    return MasterSummary(exists=counts is not None, counts=counts or {})


@router.post("/draft", response_model=Draft)
def draft_from_notes(body: DraftRequest) -> Draft:
    return _draft(body.text)


@router.post("/extract-text", response_model=ExtractedText)
async def extract_uploaded_text(file: UploadFile) -> ExtractedText:
    """Text from a PDF, Word, .txt or .md file, for the notes box. Nothing is saved."""
    from app.documents.upload_text import MAX_FILE_BYTES, MAX_TEXT_CHARS, extract_text

    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413, detail="The file is too large. Keep it under 5 MB."
        )
    try:
        text = extract_text(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ExtractedText(text=text[:MAX_TEXT_CHARS])


@router.post("/draft-from-cv", response_model=Draft)
def draft_from_uploaded_cv() -> Draft:
    text = cv_text()
    if text is None:
        raise HTTPException(status_code=409, detail="Upload your CV first.")
    return _draft(text)


@router.post("/merge", response_model=MergeResult)
def merge_draft(
    body: MergeRequest, background: BackgroundTasks, session: SessionDep
) -> MergeResult:
    from app.documents.cv import DocumentError
    from app.documents.master import (
        load_master_or_none,
        merge,
        parse_draft,
        save_master,
    )

    try:
        draft = parse_draft(body.draft)
        cv, report = merge(load_master_or_none(), draft)
    except (ValueError, DocumentError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    save_master(cv)
    _reset_reviews(session)
    background.add_task(_rescore)
    return MergeResult(report=report)


@router.get("/cv", response_model=CvData)
def get_master_cv() -> CvData:
    from app.documents.cv import DocumentError
    from app.documents.master import load_master_or_none

    try:
        master = load_master_or_none()
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if master is None:
        raise HTTPException(status_code=404, detail="No master CV yet.")
    return master


@router.put("/cv", response_model=CvData)
def save_master_cv(
    cv: CvData, background: BackgroundTasks, session: SessionDep
) -> CvData:
    """Save the CV from the editor. Rendering first rejects unsafe links."""
    from app.documents.cv import DocumentError, render_tex
    from app.documents.master import save_master

    try:
        render_tex(cv)
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    save_master(cv)
    _reset_reviews(session)
    background.add_task(_rescore)
    return cv


@router.delete("/cv", status_code=204)
def delete_master_cv(background: BackgroundTasks, session: SessionDep) -> None:
    """Delete the master CV and its backup. Tailored CVs in output/ are kept."""
    from app.documents.master import delete_master

    if not delete_master():
        raise HTTPException(status_code=404, detail="No master CV yet.")
    _reset_reviews(session)
    background.add_task(_rescore)
