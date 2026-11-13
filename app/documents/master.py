"""Grow the master CV from plain notes or an uploaded CV: draft, fact-check, review, merge."""

import shutil
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.documents.cv import (
    MASTER_CV,
    Certification,
    CvData,
    DocumentError,
    Education,
    Experience,
    Header,
    Project,
    Reference,
    Research,
    SkillGroup,
    Volunteering,
    load_master,
)
from app.documents.factcheck import unsupported
from app.documents.textutil import clean, match
from app.llm.client import complete

PROMPT = (
    Path(__file__).resolve().parent.parent.parent
    / "config"
    / "prompts"
    / "cv_extract.md"
)
MAX_INPUT_CHARS = 12_000
DRAFT_MAX_TOKENS = 4000
BULLET_LIMITS = {"experience": 4, "projects": 3, "research": 3, "volunteering": 2}
FILE_NOTE = "# Master CV. Local only (profile/ is git-ignored). Edit facts here, never in generated CVs.\n"


class CvDraft(BaseModel):
    """Like CvData, but every section is optional because notes may cover only one thing."""

    header: Header | None = None
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    research: list[Research] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    volunteering: list[Volunteering] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)


def load_master_or_none() -> CvData | None:
    return load_master() if MASTER_CV.exists() else None


def _in_source(value: str, source: str) -> bool:
    return clean(value).lower().rstrip("/") in source.lower()


def check_draft(draft: CvDraft, source: str) -> tuple[CvDraft, list[str]]:
    """Remove anything the notes do not support: invented numbers, tools, links or contact details."""
    flags: list[str] = []
    for section, limit in BULLET_LIMITS.items():
        for item in getattr(draft, section):
            label = getattr(item, "name", None) or getattr(item, "title", "")
            kept = []
            for bullet in [clean(b) for b in item.bullets if b and b.strip()][:limit]:
                issues = unsupported(bullet, source)
                if issues:
                    flags.append(f"{label}: removed a bullet ({', '.join(issues)})")
                else:
                    kept.append(bullet)
            item.bullets = kept
            if hasattr(item, "links"):
                for link in [x for x in item.links if not _in_source(x.url, source)]:
                    flags.append(
                        f"{label}: removed link {link.url} (not in your notes)"
                    )
                item.links = [x for x in item.links if _in_source(x.url, source)]
            if hasattr(item, "stack"):
                item.stack = [tool for tool in item.stack if _in_source(tool, source)]
    for group in draft.skills:
        group.items = [item for item in group.items if _in_source(item, source)]
    draft.skills = [g for g in draft.skills if g.items]
    for cert in draft.certifications:
        if cert.url and not _in_source(cert.url, source):
            cert.url = ""
    if draft.header:
        for field in ("name", "email", "phone", "location"):
            if getattr(draft.header, field) and not _in_source(
                getattr(draft.header, field), source
            ):
                setattr(draft.header, field, "")
        draft.header.links = [
            x for x in draft.header.links if _in_source(x.url, source)
        ]
    return draft, flags


def draft_from_text(text: str) -> tuple[CvDraft, list[str]]:
    """Raises LLMError when the call fails and ValueError for an unusable reply."""
    text = text[:MAX_INPUT_CHARS]
    messages = [
        {"role": "system", "content": PROMPT.read_text(encoding="utf-8")},
        {"role": "user", "content": f"<notes>\n{text}\n</notes>"},
    ]
    raw = complete("documents", messages, json_output=True, max_tokens=DRAFT_MAX_TOKENS)
    try:
        draft = CvDraft.model_validate_json(raw)
    except ValidationError as exc:
        raise ValueError("invalid draft reply") from exc
    return check_draft(draft, text)


def parse_draft(data: dict) -> CvDraft:
    """The reviewed draft from the editor. Raises ValueError with a readable reason."""
    try:
        return CvDraft.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        place = ".".join(str(part) for part in first["loc"])
        raise ValueError(f"Check '{place}': {first['msg']}") from exc


def _merge_items(
    existing: list, new: list, name_of, section: str, report: list[str]
) -> list:
    """Append new items; skip ones whose name already exists."""
    result = list(existing)
    known = {name_of(item): item for item in existing}
    for item in new:
        name = name_of(item)
        if match(name, known):
            report.append(f"Skipped {section} '{name}' (already in your CV)")
        else:
            result.append(item)
            known[name] = item
            report.append(f"Added {section} '{name}'")
    return result


def _merge_skills(
    existing: list[SkillGroup], new: list[SkillGroup], report: list[str]
) -> list[SkillGroup]:
    groups = [g.model_copy(deep=True) for g in existing]
    by_name = {g.name: g for g in groups}
    for group in new:
        target = match(group.name, by_name)
        if target is None:
            groups.append(group)
            by_name[group.name] = group
            report.append(f"Added skill group '{group.name}'")
            continue
        added = [
            item
            for item in group.items
            if not match(item, {i: i for i in target.items})
        ]
        target.items += added
        if added:
            report.append(f"Added skills to '{target.name}': {', '.join(added)}")
    return groups


def merge(master: CvData | None, draft: CvDraft) -> tuple[CvData, list[str]]:
    """New items are added; the master's header and summary are never replaced."""
    if master is None:
        if draft.header is None or not draft.header.name:
            raise ValueError("A new master CV needs a header with your name.")
        return CvData.model_validate(draft.model_dump()), ["Created your master CV"]

    report: list[str] = []
    updates = {
        "skills": _merge_skills(master.skills, draft.skills, report),
        "experience": _merge_items(
            master.experience,
            draft.experience,
            lambda e: f"{e.title} at {e.organization}",
            "experience",
            report,
        ),
        "projects": _merge_items(
            master.projects, draft.projects, lambda p: p.name, "project", report
        ),
        "research": _merge_items(
            master.research, draft.research, lambda r: r.title, "research", report
        ),
        "education": _merge_items(
            master.education, draft.education, lambda e: e.degree, "education", report
        ),
        "certifications": _merge_items(
            master.certifications,
            draft.certifications,
            lambda c: c.name,
            "certification",
            report,
        ),
        "volunteering": _merge_items(
            master.volunteering,
            draft.volunteering,
            lambda v: v.name,
            "volunteering",
            report,
        ),
        "references": _merge_items(
            master.references, draft.references, lambda r: r.name, "reference", report
        ),
    }
    if not master.summary and draft.summary:
        updates["summary"] = draft.summary
    return master.model_copy(update=updates), report


def save_master(cv: CvData, path: Path = MASTER_CV) -> None:
    """Keep a backup of the previous version, then write the new one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copyfile(path, path.with_suffix(".yaml.bak"))
    body = yaml.safe_dump(
        cv.model_dump(exclude_defaults=True),
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )
    path.write_text(FILE_NOTE + body, encoding="utf-8")


def master_counts() -> dict[str, int] | None:
    try:
        master = load_master_or_none()
    except DocumentError:
        return None
    if master is None:
        return None
    return {
        section: len(getattr(master, section))
        for section in ("experience", "projects", "certifications", "skills")
    }
