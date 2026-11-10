import pytest

from fetcher.filters import is_tech, is_too_senior


@pytest.mark.parametrize(
    "title",
    [
        "Machine Learning Engineer",
        "Junior Backend Developer",
        "Data Analyst Intern",
        "MLOps Engineer",
    ],
)
def test_tech_titles_kept(title):
    assert is_tech(title)


@pytest.mark.parametrize(
    "title",
    [
        "Account Executive",
        "Benefits Analyst",
        "AI Sales Specialist",
        "Technical Recruiter",
    ],
)
def test_non_tech_titles_dropped(title):
    assert not is_tech(title)


@pytest.mark.parametrize(
    "title", ["Senior Data Engineer", "Staff ML Engineer", "Engineering Manager"]
)
def test_senior_titles_flagged(title):
    assert is_too_senior(title)


def test_junior_title_not_senior():
    assert not is_too_senior("Associate Software Engineer")
