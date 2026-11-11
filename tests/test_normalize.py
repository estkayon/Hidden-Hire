import pytest

from fetcher.models import Job
from fetcher.normalize import (
    detect_location,
    detect_remote_scope,
    detect_seniority,
    detect_work_type,
    html_to_text,
    normalize_job,
)


def test_html_to_text_keeps_structure_and_drops_tags():
    raw = "<h2>About</h2><p>Hello <b>world</b></p><script>alert(1)</script><ul><li>Python</li></ul>"
    assert html_to_text(raw) == "## About\nHello world\n• Python"


def test_html_to_text_handles_double_escaped_html():
    assert html_to_text("&lt;p&gt;Hi &amp;amp; bye&lt;/p&gt;") == "Hi & bye"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Bangalore, India", ("IN", "Bangalore")),
        ("San Francisco, CA", ("US", "San Francisco")),
        ("London", ("GB", "London")),
        ("Remote, Germany", ("DE", None)),
        ("Remote, Canada; Remote, United States", ("US", None)),
        ("Remote", (None, None)),
        ("Wilmington, DE", (None, None)),
    ],
)
def test_detect_location(raw, expected):
    assert detect_location(raw) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Remote, Poland", "remote"),
        ("Hybrid - Berlin", "hybrid"),
        ("On-site, Dhaka", "onsite"),
        ("Berlin, Germany", "unknown"),
    ],
)
def test_detect_work_type(text, expected):
    assert detect_work_type(text) == expected


@pytest.mark.parametrize(
    "location, country, expected",
    [
        ("Remote, Anywhere", None, "worldwide"),
        ("Remote, EMEA", None, "regions"),
        ("Remote, Poland", "PL", "country"),
        ("Remote", None, "unknown"),
    ],
)
def test_detect_remote_scope(location, country, expected):
    assert detect_remote_scope(location, country) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Junior Backend Developer", "Junior"),
        ("Graduate Data Engineer", "Junior"),
        ("Data Analyst Intern", "Intern"),
        ("mid_level", "Mid-level"),
        ("Entry-Level, Junior", "Junior"),
        (["Mid-level"], "Mid-level"),
        ("Machine Learning Engineer", None),
    ],
)
def test_detect_seniority(text, expected):
    assert detect_seniority(text) == expected


def test_normalize_job_keeps_source_values():
    job = Job(
        id="x",
        source="test",
        title="ML Engineer",
        company="Acme",
        location_raw="Remote, Poland",
        country="DE",
    )
    result = normalize_job(job)
    assert result.country == "DE"
    assert result.work_type == "remote"
    assert result.remote_scope == "country"
