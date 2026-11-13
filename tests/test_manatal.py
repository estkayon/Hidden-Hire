import pytest

from fetcher.sources.manatal import ManatalSource

PAGE = """
<meta property="og:title" content="Backend Developer (Junior) - Talvette | Career Page" />
<meta property="og:description" content="Company Description
Our client is a Bangladesh-based fintech.
Employment Structure
Hybrid in Dhaka, Bangladesh | Full-time
Salary: BDT 30,000 - 45,000" />
"""


def _parse(page: str):
    item = {
        "id": "93X5YY5Y",
        "url": "https://www.careers-page.com/talvette/job/93X5YY5Y",
        "html": page,
    }
    return ManatalSource({}).parse(item, token="talvette", company="Talvette")


def test_parses_title_location_and_salary():
    job = _parse(PAGE)
    assert job.title == "Backend Developer (Junior)"
    assert job.work_type == "hybrid"
    assert job.location_raw == "Dhaka, Bangladesh"
    assert job.country == "BD"
    assert (job.salary_min, job.salary_max, job.salary_currency) == (
        30000,
        45000,
        "BDT",
    )


def test_missing_parts_stay_empty():
    page = (
        '<meta property="og:title" content="Data Analyst - Talvette | Career Page" />'
    )
    job = _parse(page)
    assert job.work_type == "unknown"
    assert job.country is None
    assert job.salary_min is None


def test_not_found_page_is_rejected():
    with pytest.raises(ValueError):
        _parse("<title>Manatal</title>")
