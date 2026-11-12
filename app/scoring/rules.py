"""Stage 1 match score: rule and keyword checks plus an embedding similarity. No LLM."""

from dataclasses import dataclass
from typing import Protocol

from rapidfuzz import fuzz

from app.profile import Profile, detect_skills
from fetcher.normalize import country_tier

# Starting weights; tune after real use.
WEIGHTS = {
    "skills": 0.45,
    "semantic": 0.25,
    "role": 0.15,
    "seniority": 0.10,
    "location": 0.05,
}
UNKNOWN = 0.5
FULL_CONFIDENCE_SKILLS = 4  # a job naming fewer known skills says less about the fit
SENIORITY_FIT = {"Intern": 0.9, "Junior": 1.0, "Mid-level": 0.7, "Senior": 0.2}
TIER_FIT = {1: 1.0, 2: 0.8, 3: 0.5}


class JobLike(Protocol):
    title: str
    description: str
    tags: list
    seniority: str | None
    work_type: str
    remote_scope: str
    country: str | None


@dataclass
class Stage1Result:
    score: int
    breakdown: dict


def skill_fit(
    job_text: str, profile_skills: list[str]
) -> tuple[float, list[str], list[str]]:
    """Share of the job's known skills the profile has, pulled toward neutral when the job names few."""
    job_skills = detect_skills(job_text)
    if not job_skills:
        return UNKNOWN, [], []
    have = {skill.lower() for skill in profile_skills}
    matched = [s for s in job_skills if s.lower() in have]
    missing = [s for s in job_skills if s.lower() not in have]
    share = len(matched) / len(job_skills)
    confidence = min(1.0, len(job_skills) / FULL_CONFIDENCE_SKILLS)
    return confidence * share + (1 - confidence) * UNKNOWN, matched, missing


def semantic_fit(cosine: float) -> float:
    """MiniLM cosine values for related texts sit roughly between 0.15 and 0.6."""
    return min(1.0, max(0.0, (cosine - 0.15) / 0.45))


def role_fit(title: str, target_roles: list[str]) -> float:
    if not target_roles:
        return UNKNOWN
    return (
        max(fuzz.token_set_ratio(title.lower(), role.lower()) for role in target_roles)
        / 100
    )


def seniority_fit(level: str | None, years: float | None) -> float:
    if level == "Mid-level" and years is not None and years >= 2:
        return 0.9
    return SENIORITY_FIT.get(level or "", 0.75)


def location_fit(job: JobLike) -> float:
    if job.country == "BD":
        return 1.0
    if job.work_type == "remote":
        return {"worldwide": 1.0, "regions": 0.8, "country": 0.4}.get(
            job.remote_scope, 0.7
        )
    return TIER_FIT[country_tier(job.country)]


def stage1_score(job: JobLike, profile: Profile, cosine: float) -> Stage1Result:
    text = " ".join([job.title, job.description, *map(str, job.tags or [])])
    skills, matched, missing = skill_fit(text, profile.skills)
    parts = {
        "skills": skills,
        "semantic": semantic_fit(cosine),
        "role": role_fit(job.title, profile.target_roles),
        "seniority": seniority_fit(job.seniority, profile.years_experience),
        "location": location_fit(job),
    }
    score = round(100 * sum(WEIGHTS[name] * value for name, value in parts.items()))
    breakdown = {name: round(value, 2) for name, value in parts.items()}
    breakdown |= {"matched_skills": matched, "missing_skills": missing}
    return Stage1Result(score=score, breakdown=breakdown)
