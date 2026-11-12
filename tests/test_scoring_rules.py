from types import SimpleNamespace

import pytest

from app.profile import Profile
from app.scoring.rules import (
    location_fit,
    role_fit,
    semantic_fit,
    seniority_fit,
    skill_fit,
    stage1_score,
)


def make_job(**overrides):
    data = {
        "title": "Junior MLOps Engineer",
        "description": "We use Python, Docker, Kubernetes and Terraform.",
        "tags": [],
        "seniority": "Junior",
        "work_type": "remote",
        "remote_scope": "worldwide",
        "country": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


PROFILE = Profile(
    skills=["Python", "Docker", "Kubernetes"],
    target_roles=["MLOps Engineer"],
    years_experience=1,
)


def test_skill_fit_counts_matched_and_missing():
    share, matched, missing = skill_fit(
        "Python, Docker, Kubernetes and Terraform", PROFILE.skills
    )
    assert matched == ["Python", "Docker", "Kubernetes"]
    assert missing == ["Terraform"]
    assert share == pytest.approx(0.75)


def test_skill_fit_few_skills_moves_toward_neutral():
    share, matched, _ = skill_fit("Must know Python.", PROFILE.skills)
    assert matched == ["Python"]
    assert share == pytest.approx(0.25 * 1.0 + 0.75 * 0.5)


def test_skill_fit_unknown_when_no_known_skills():
    assert skill_fit("Great team, nice office.", PROFILE.skills) == (0.5, [], [])


@pytest.mark.parametrize("cosine, expected", [(0.0, 0.0), (0.6, 1.0), (0.375, 0.5)])
def test_semantic_fit_scales(cosine, expected):
    assert semantic_fit(cosine) == pytest.approx(expected)


def test_role_fit_prefers_matching_titles():
    assert role_fit("Senior MLOps Engineer", ["MLOps Engineer"]) > role_fit(
        "Accountant", ["MLOps Engineer"]
    )
    assert role_fit("Anything", []) == 0.5


def test_seniority_and_location():
    assert seniority_fit("Junior", 0) > seniority_fit("Senior", 0)
    assert seniority_fit("Mid-level", 3) > seniority_fit("Mid-level", 0)
    assert location_fit(make_job()) == 1.0
    assert location_fit(make_job(remote_scope="country", country="US")) == 0.4
    assert location_fit(make_job(work_type="onsite", country="BD")) == 1.0


def test_good_job_scores_higher_than_bad_job():
    good = stage1_score(make_job(), PROFILE, cosine=0.5)
    bad = stage1_score(
        make_job(
            title="Senior Accountant",
            description="QuickBooks and Excel.",
            seniority="Senior",
            work_type="onsite",
            remote_scope="unknown",
            country="BR",
        ),
        PROFILE,
        cosine=0.05,
    )
    assert good.score > 70
    assert bad.score < 40
    assert good.breakdown["missing_skills"] == ["MLOps", "Terraform"]
