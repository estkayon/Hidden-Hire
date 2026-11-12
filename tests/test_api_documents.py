import pytest

from app.api.documents import JOB_ID, _file_stem


def test_file_stem_is_safe():
    assert _file_stem("Md. Jane Doe", "Acme / Labs") == "Md_Jane_Doe_CV_Acme_Labs"


@pytest.mark.parametrize("job_id", ["../secret", "a b", "x" * 65, ""])
def test_bad_job_ids_are_rejected(job_id):
    assert not JOB_ID.match(job_id)


def test_normal_job_id_is_accepted():
    assert JOB_ID.match("19f69ac89a317ebb")
