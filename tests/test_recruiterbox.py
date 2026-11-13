from fetcher.sources.recruiterbox import RecruiterboxSource

ITEM = {
    "id": "fk0xn86",
    "title": "Associate Oncall Engineer",
    "description": "<p>Troubleshoot <b>production</b> issues.</p>",
    "location": {"city": "Dhaka", "state": "Dhaka Division", "country": "Bangladesh"},
    "hosted_url": "https://therap.hire.trakstar.com/jobs/fk0xn86/",
    "allows_remote": False,
}


def _parse(item: dict):
    return RecruiterboxSource({}).parse(item, token="therap", company="Therap (BD)")


def test_parses_recruiterbox_opening():
    job = _parse(ITEM)
    assert job.title == "Associate Oncall Engineer"
    assert "production" in job.description
    assert job.location_raw == "Dhaka, Bangladesh"
    assert job.country == "BD"
    assert job.work_type == "unknown"
    assert job.apply_url == ITEM["hosted_url"]


def test_remote_allowed_means_hybrid():
    assert _parse({**ITEM, "allows_remote": True}).work_type == "hybrid"


def test_other_country_is_not_marked_bd():
    job = _parse({**ITEM, "location": {"city": "Toronto", "country": "Canada"}})
    assert job.country is None
    assert job.location_raw == "Toronto, Canada"
