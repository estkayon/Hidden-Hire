"""Tailor the master CV to one job with an LLM, then fact-check every change."""

import argparse
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.documents.cv import (
    OUTPUT_DIR,
    CvData,
    DocumentError,
    compile_pdf,
    load_master,
    render_tex,
)
from app.documents.factcheck import unsupported
from app.documents.textutil import clean as _clean
from app.documents.textutil import match as _match
from app.llm.client import LLMError, complete
from app.models import Job

PROMPT = (
    Path(__file__).resolve().parent.parent.parent
    / "config"
    / "prompts"
    / "cv_tailor.md"
)
OPTIONAL_PROJECTS = 2
MAX_EXPERIENCE_BULLETS = 4
MAX_PROJECT_BULLETS = 3
MAX_SUMMARY_CHARS = 700
MAX_JOB_CHARS = 3500
MAX_KEYWORDS = 10
DEFAULT_TOTAL_PROJECTS = 5
MIN_LENGTH_RATIO = 0.75  # a tailored item shorter than this has lost detail

log = logging.getLogger("tailor")


class PlanSkills(BaseModel):
    name: str
    items: list[str] = Field(default_factory=list)


class PlanExperience(BaseModel):
    index: int
    bullets: list[str] = Field(default_factory=list)


class PlanProject(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)


class TailorPlan(BaseModel):
    role_type: str = ""
    keywords: list[str] = Field(default_factory=list)
    optional_projects: list[str] = Field(default_factory=list)
    summary: str = ""
    skills: list[PlanSkills] = Field(default_factory=list)
    experience: list[PlanExperience] = Field(default_factory=list)
    projects: list[PlanProject] = Field(default_factory=list)


@dataclass
class TailorResult:
    cv: CvData
    flags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


def master_text(cv: CvData) -> str:
    """All factual text of the master CV, used as the fact-check source."""
    data = cv.model_dump(
        include={"summary", "skills", "experience", "projects", "research", "education"}
    )
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _master_for_llm(cv: CvData) -> str:
    """Compact master CV without contact details or links."""
    data = {
        "summary": cv.summary,
        "skills": [g.model_dump() for g in cv.skills],
        "experience": [
            {
                "index": i,
                "title": e.title,
                "organization": e.organization,
                "dates": e.dates,
                "stack": e.stack,
                "bullets": e.bullets,
            }
            for i, e in enumerate(cv.experience)
        ],
        "pinned_projects": [
            {"name": p.name, "stack": p.stack, "bullets": p.bullets}
            for p in cv.projects
            if p.pinned
        ],
        "optional_projects": [
            {"name": p.name, "stack": p.stack, "bullets": p.bullets}
            for p in cv.projects
            if not p.pinned
        ],
        "research": [{"title": r.title, "bullets": r.bullets} for r in cv.research],
        "education": [
            {"degree": e.degree, "institution": e.institution} for e in cv.education
        ],
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def build_messages(
    job: Job, cv: CvData, optional_count: int = OPTIONAL_PROJECTS
) -> list[dict]:
    system = PROMPT.read_text(encoding="utf-8").replace(
        "{optional_count}", str(optional_count)
    )

    posting = f"Title: {job.title}\nCompany: {job.company}\n\n{job.description[:MAX_JOB_CHARS]}"
    posting = posting.replace("</job_posting>", "").replace("<job_posting>", "")
    user = f"Master CV (YAML):\n{_master_for_llm(cv)}\n<job_posting>\n{posting}\n</job_posting>"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def request_plan(
    job: Job, cv: CvData, optional_count: int = OPTIONAL_PROJECTS
) -> TailorPlan:
    """Raises LLMError when the call fails and ValueError for an unusable reply."""
    raw = complete(
        "documents", build_messages(job, cv, optional_count), json_output=True
    )
    try:
        return TailorPlan.model_validate_json(raw)
    except ValidationError as exc:
        raise ValueError("invalid tailoring reply") from exc


def _checked_bullets(
    new: list[str],
    original: list[str],
    source: str,
    limit: int,
    label: str,
    flags: list[str],
) -> list[str]:
    """Keep supported bullets; an unsupported one is replaced by the master bullet in the same place.
    Use all master bullets when the result has fewer or much shorter bullets."""
    master = original[:limit]
    kept = []
    for index, bullet in enumerate([_clean(b) for b in new if b and b.strip()][:limit]):
        issues = unsupported(bullet, source)
        if not issues:
            kept.append(bullet)
        elif index < len(master):
            flags.append(
                f"{label}: used the master version of a bullet ({', '.join(issues)})"
            )
            kept.append(master[index])
        else:
            flags.append(f"{label}: dropped a bullet ({', '.join(issues)})")
    if not kept:
        return master
    if len(kept) < len(master) or len(" ".join(kept)) < MIN_LENGTH_RATIO * len(
        " ".join(master)
    ):
        flags.append(f"{label}: kept the master bullets (tailored version lost detail)")
        return master
    return kept


def _skills(master: CvData, plan: TailorPlan, flags: list[str]) -> list:
    """Reordered master skills. Items not in the master are dropped, missing ones are kept at the end."""
    groups = {g.name: g for g in master.skills}
    all_items = {item for g in master.skills for item in g.items}
    ordered, seen_groups = [], set()
    for planned in plan.skills:
        group = _match(planned.name, groups)
        if group is None or group.name in seen_groups:
            continue
        known = {item: item for item in group.items}
        items = []
        for item in planned.items:
            match = _match(item, known)
            if match is None:
                if _match(item, {i: i for i in all_items}) is None:
                    flags.append(f"skills: dropped '{item}' (not in master CV)")
            elif match not in items:
                items.append(match)
        items += [item for item in group.items if item not in items]
        ordered.append(group.model_copy(update={"items": items}))
        seen_groups.add(group.name)
    return ordered + [g for g in master.skills if g.name not in seen_groups]


def _projects(
    master: CvData, plan: TailorPlan, flags: list[str], optional_count: int
) -> list:
    """Pinned projects first, then optional projects for this kind of role, each fact-checked."""
    pinned = [p for p in master.projects if p.pinned]
    optional = {p.name: p for p in master.projects if not p.pinned}
    every = {p.name: p for p in master.projects}

    planned = {}
    for item in plan.projects:
        project = _match(item.name, every)
        if project is None:
            flags.append(f"projects: ignored unknown project '{item.name}'")
        else:
            planned[project.name] = item

    role_type = plan.role_type.strip().lower()
    chosen = [p for p in optional.values() if role_type in p.tracks][:optional_count]
    for name in plan.optional_projects or [item.name for item in plan.projects]:
        project = _match(name, optional)
        if (
            project is not None
            and project not in chosen
            and len(chosen) < optional_count
        ):
            chosen.append(project)
    if len(chosen) < optional_count:
        given = ", ".join(plan.optional_projects) or "none"
        flags.append(
            f"projects: the model chose too few optional projects (gave: {given}); filled from the master order"
        )
        chosen += [p for p in optional.values() if p not in chosen][
            : optional_count - len(chosen)
        ]

    result = []
    for project in [*pinned, *chosen]:
        source = "\n".join([project.name, *project.stack, *project.bullets])
        new = planned.get(project.name)
        bullets = _checked_bullets(
            new.bullets if new else [],
            project.bullets,
            source,
            MAX_PROJECT_BULLETS,
            project.name,
            flags,
        )
        result.append(project.model_copy(update={"bullets": bullets}))
    return result


def apply_plan(
    master: CvData, plan: TailorPlan, optional_count: int = OPTIONAL_PROJECTS
) -> TailorResult:
    """Build the tailored CV from the master, keeping only changes the master supports."""
    flags: list[str] = []
    source = master_text(master)

    summary = _clean(plan.summary)[:MAX_SUMMARY_CHARS]
    issues = unsupported(summary, source) if summary else ["empty"]
    if issues:
        flags.append(f"summary: kept the master summary ({', '.join(issues)})")
        summary = master.summary

    planned_experience = {e.index: e.bullets for e in plan.experience}
    experience = []
    for index, job in enumerate(master.experience):
        job_source = "\n".join([job.title, job.organization, *job.stack, *job.bullets])
        bullets = _checked_bullets(
            planned_experience.get(index, []),
            job.bullets,
            job_source,
            MAX_EXPERIENCE_BULLETS,
            job.title,
            flags,
        )
        experience.append(job.model_copy(update={"bullets": bullets}))

    cv = master.model_copy(
        update={
            "summary": summary,
            "skills": _skills(master, plan, flags),
            "experience": experience,
            "projects": _projects(master, plan, flags, optional_count),
        }
    )
    lower_source = source.lower()
    keywords = [
        _clean(k)
        for k in plan.keywords
        if k.strip() and _clean(k).lower() in lower_source
    ]
    return TailorResult(cv=cv, flags=flags, keywords=keywords[:MAX_KEYWORDS])


def cv_files(job_id: str) -> dict[str, Path]:
    base = OUTPUT_DIR / f"cv_{job_id}"
    return {
        "pdf": base.with_suffix(".pdf"),
        "tex": base.with_suffix(".tex"),
        "meta": base.with_suffix(".json"),
    }


def cv_status(job_id: str) -> dict:
    """Whether a tailored CV exists for the job, when it was made, its fact-check notes and keywords."""
    files = cv_files(job_id)
    if not files["pdf"].exists():
        return {"exists": False, "generated_at": None, "flags": [], "keywords": []}
    try:
        meta = json.loads(files["meta"].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    return {
        "exists": True,
        "generated_at": meta.get("generated_at"),
        "flags": meta.get("flags", []),
        "keywords": meta.get("keywords", []),
    }


def optional_count_for(master: CvData, total_projects: int | None) -> int:
    """How many optional projects to add so the CV shows total_projects (pinned ones always stay)."""
    pinned = sum(p.pinned for p in master.projects)
    available = len(master.projects) - pinned
    total = DEFAULT_TOTAL_PROJECTS if total_projects is None else total_projects
    return max(0, min(total - pinned, available))


def delete_cv(job_id: str) -> None:
    for path in cv_files(job_id).values():
        path.unlink(missing_ok=True)


def generate_cv(job: Job, total_projects: int | None = None) -> tuple[Path, list[str]]:
    """Tailored CV PDF for one job. Raises LLMError, ValueError or DocumentError."""
    master = load_master()
    optional_count = optional_count_for(master, total_projects)
    result = apply_plan(
        master, request_plan(job, master, optional_count), optional_count
    )
    pdf = compile_pdf(render_tex(result.cv), name=f"cv_{job.id}")
    meta = {
        "generated_at": datetime.now(UTC).isoformat(),
        "flags": result.flags,
        "keywords": result.keywords,
    }
    cv_files(job.id)["meta"].write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return pdf, result.flags


def main() -> None:
    from app.db import SessionLocal

    parser = argparse.ArgumentParser(description="Generate a tailored CV for one job.")
    parser.add_argument("job_id")
    parser.add_argument(
        "--projects", type=int, help="total projects in the CV, pinned ones included"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    for noisy in ("httpx", "httpx2", "LiteLLM"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    with SessionLocal() as session:
        job = session.get(Job, args.job_id)
        if job is None:
            raise SystemExit("Job not found")
        try:
            pdf, flags = generate_cv(job, args.projects)
        except (LLMError, ValueError, DocumentError) as exc:
            raise SystemExit(f"CV generation failed: {exc}") from exc
    print(f"Wrote {pdf}")
    for flag in flags:
        print(f"- {flag}")
    print(f"Keywords: {', '.join(cv_status(args.job_id)['keywords'])}")


if __name__ == "__main__":
    main()
