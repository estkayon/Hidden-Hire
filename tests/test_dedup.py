from fetcher.dedup import clean_company, dedup_jobs, is_same_job
from fetcher.models import Job


def make_job(
    job_id: str, source: str, title: str, company: str, country=None, description=""
) -> Job:
    return Job(
        id=job_id,
        source=source,
        title=title,
        company=company,
        country=country,
        description=description,
        source_url=f"https://{source}.example/{job_id}",
    )


def test_clean_company_drops_suffixes():
    assert clean_company("Acme GmbH") == clean_company("ACME Inc.") == "acme"


def test_same_job_ignores_case_and_brackets():
    a = make_job("1", "arbeitnow", "Data Engineer (m/w/d)", "Acme GmbH", "DE")
    b = make_job("2", "greenhouse", "data engineer", "Acme", "DE")
    assert is_same_job(a, b)


def test_different_country_or_title_not_same():
    base = make_job("1", "lever", "Data Engineer", "Acme", "DE")
    assert not is_same_job(base, make_job("2", "lever", "Data Engineer", "Acme", "GB"))
    assert not is_same_job(base, make_job("3", "lever", "Data Analyst", "Acme", "DE"))


def test_small_title_difference_not_same():
    a = make_job("1", "jobicy", "Machine Learning Engineer, TTS", "Cantina Labs")
    b = make_job("2", "jobicy", "Machine Learning Engineer, Ops", "Cantina Labs")
    assert not is_same_job(a, b)


def test_bracket_content_kept():
    a = make_job("1", "mcf", "Data Analyst (ETL, 1 Year)", "Recruit Express", "SG")
    b = make_job("2", "mcf", "Data Analyst", "Recruit Express", "SG")
    assert not is_same_job(a, b)


def test_merge_prefers_ats_and_lists_other_sources():
    board = make_job("1", "himalayas", "ML Engineer", "Acme", description="long " * 50)
    ats = make_job("2", "greenhouse", "ML Engineer", "Acme Inc", description="short")
    other = make_job("3", "lever", "Backend Developer", "Acme")

    result = dedup_jobs([board, ats, other])

    assert [job.id for job in result] == ["2", "3"]
    assert result[0].also_seen == ["himalayas: https://himalayas.example/1"]
    assert result[1].also_seen == []
