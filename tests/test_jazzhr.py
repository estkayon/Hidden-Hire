import pytest

from fetcher.sources.jazzhr import JazzHRSource, jobs_from_xml

FEED = b"""<?xml version="1.0"?>
<jobs>
  <publisher>JazzHR</publisher>
  <job>
    <id>job_1</id><status>Open</status><title>Software Engineer</title>
    <url>https://palmpaylimited.applytojob.com/apply/AAA/Software-Engineer</url>
    <city>Dhaka</city><state></state><country>Bangladesh</country>
    <description>&lt;p&gt;Build &lt;b&gt;payment&lt;/b&gt; APIs.&lt;/p&gt;</description>
  </job>
  <job>
    <id>job_2</id><status>Open</status><title>Credit Analyst</title>
    <url>https://palmpaylimited.applytojob.com/apply/BBB/Credit-Analyst</url>
    <city>Ikeja</city><state>Lagos</state><country>Nigeria</country>
  </job>
  <job>
    <id>job_3</id><status>Closed</status><title>Old Role</title><country>Bangladesh</country>
  </job>
</jobs>"""


def test_country_filter_keeps_only_open_bangladesh_jobs():
    jobs = jobs_from_xml(FEED, "Bangladesh")
    assert [job["id"] for job in jobs] == ["job_1"]


def test_without_country_keeps_all_open_jobs():
    assert [job["id"] for job in jobs_from_xml(FEED)] == ["job_1", "job_2"]


def test_bad_xml_raises_value_error():
    with pytest.raises(ValueError):
        jobs_from_xml(b"<jobs><job>")


def test_parses_job():
    item = jobs_from_xml(FEED, "Bangladesh")[0]
    job = JazzHRSource({}).parse(
        item, token="palmpaylimited:Bangladesh", company="PalmPay Bangladesh"
    )
    assert job.title == "Software Engineer"
    assert "payment" in job.description
    assert job.location_raw == "Dhaka, Bangladesh"
    assert job.country == "BD"
    assert job.apply_url.endswith("Software-Engineer")
