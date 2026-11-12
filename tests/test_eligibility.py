from types import SimpleNamespace

import pytest

from app.eligibility import eligibility


def job(**overrides):
    data = {
        "country": "DE",
        "work_type": "onsite",
        "remote_scope": "unknown",
        "title": "ML Engineer",
        "description": "Build models.",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"country": "BD"}, "bd"),
        ({"work_type": "remote", "remote_scope": "worldwide"}, "remote_worldwide"),
        ({"work_type": "remote", "remote_scope": "regions"}, "remote_regions"),
        (
            {"work_type": "remote", "remote_scope": "country", "country": "US"},
            "remote_country",
        ),
        ({"work_type": "remote"}, "remote_unknown"),
        (
            {"description": "We offer visa sponsorship and a relocation package."},
            "visa",
        ),
        ({"description": "Unfortunately we offer no visa sponsorship."}, "local_only"),
        (
            {
                "work_type": "hybrid",
                "description": "You must have the right to work in the UK.",
            },
            "local_only",
        ),
        ({}, "check_visa"),
    ],
)
def test_eligibility(overrides, expected):
    assert eligibility(job(**overrides)) == expected
