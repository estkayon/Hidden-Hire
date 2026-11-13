"""What the candidate is matched on: the master CV when it exists, otherwise the uploaded CV."""

from app import profile as store
from app.profile import Profile, cv_text, detect_skills

MASTER_FILE = "master_cv.yaml"


def _master_path():
    return store.PROFILE_DIR / MASTER_FILE


def has_source() -> bool:
    return _master_path().exists() or store.has_cv()


def master_as_text(cv) -> str:
    """Compact plain text of the master CV, without contact details or links."""
    lines: list[str] = []
    if cv.summary:
        lines += ["Summary:", cv.summary]
    if cv.skills:
        lines.append("Skills:")
        lines += [f"{g.name}: {', '.join(g.items)}" for g in cv.skills]
    for e in cv.experience:
        lines.append(f"Experience: {e.title}, {e.organization} ({e.dates})")
        if e.stack:
            lines.append(f"Tools: {', '.join(e.stack)}")
        lines += [f"- {b}" for b in e.bullets]
    for p in cv.projects:
        lines.append(f"Project: {p.name}")
        if p.stack:
            lines.append(f"Tools: {', '.join(p.stack)}")
        lines += [f"- {b}" for b in p.bullets]
    for r in cv.research:
        lines.append(f"Research: {r.title}")
        lines += [f"- {b}" for b in r.bullets]
    for ed in cv.education:
        lines.append(
            f"Education: {ed.degree}, {ed.institution} ({ed.dates}) {ed.grade}".strip()
        )
    for c in cv.certifications:
        lines.append(f"Certification: {c.name}" + (f", {c.issuer}" if c.issuer else ""))
    return "\n".join(lines)


def candidate_text() -> str | None:
    path = _master_path()
    if path.exists():
        from app.documents.cv import (  # LaTeX packages load only when needed
            DocumentError,
            load_master,
        )

        try:
            return master_as_text(load_master(path))
        except DocumentError:
            pass  # an invalid master CV falls back to the uploaded CV
    return cv_text()


def candidate() -> tuple[Profile, str] | None:
    """Profile preferences plus every known skill in the candidate text, and the text itself."""
    text = candidate_text()
    if text is None:
        return None
    profile = store.load_profile() or Profile()
    skills = list(dict.fromkeys([*profile.skills, *detect_skills(text)]))
    return profile.model_copy(update={"skills": skills}), text
