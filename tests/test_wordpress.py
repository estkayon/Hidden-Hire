import pytest

from fetcher.sources.wordpress import WordPressSource

TOKEN = "https://www.bracits.com/wp-json/wp/v2/awsm_job_openings"
ITEM = {
    "id": 19997,
    "date_gmt": "2026-11-12T07:30:34",
    "link": "https://www.bracits.com/jobs/devops-engineer-2/",
    "title": {"rendered": "Data Engineer &#8211; SSIS"},
    "content": {"rendered": "<p>Build <b>pipelines</b>.</p>"},
    "class_list": ["post-19997", "job-location-dhaka", "job-type-full-time"],
}


def _parse(item: dict):
    return WordPressSource({}).parse(item, token=TOKEN, company="BRAC IT")


def test_parses_wordpress_job():
    job = _parse(ITEM)
    assert job.title == "Data Engineer \u2013 SSIS"
    assert "pipelines" in job.description
    assert job.location_raw == "Dhaka, Bangladesh"
    assert job.country == "BD"
    assert job.apply_url == ITEM["link"]


def test_location_falls_back_to_country():
    job = _parse({**ITEM, "class_list": ["post-1"]})
    assert job.location_raw == "Bangladesh"


def test_job_without_title_is_rejected():
    with pytest.raises(ValueError):
        _parse({**ITEM, "title": {"rendered": ""}})
