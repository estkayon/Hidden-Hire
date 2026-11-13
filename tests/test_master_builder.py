import pytest

from app.documents.cv import CvData
from app.documents.master import CvDraft, check_draft, merge, parse_draft, save_master

NOTES = """New project: PriceRadar. Commodity price anomaly detection for 6 commodities using LightGBM and
Prophet, Z-score and Isolation Forest, Streamlit dashboard, 42 pytest tests.
GitHub: https://github.com/jane/priceradar"""

MASTER = CvData.model_validate(
    {
        "header": {"name": "Jane"},
        "summary": "ML engineer.",
        "skills": [{"name": "Programming", "items": ["Python"]}],
        "projects": [
            {"name": "Hidden Hire – Job Agent", "bullets": ["Built a job agent."]}
        ],
    }
)


def test_check_draft_removes_invented_facts():
    draft = CvDraft.model_validate(
        {
            "projects": [
                {
                    "name": "PriceRadar",
                    "stack": ["LightGBM", "Kubernetes"],
                    "links": [
                        {
                            "label": "GitHub",
                            "url": "https://github.com/jane/priceradar",
                        },
                        {"label": "Demo", "url": "https://made-up.app"},
                    ],
                    "bullets": [
                        "Tracked 6 commodities with LightGBM and Prophet.",
                        "Served 10,000 users with Kubernetes.",
                    ],
                }
            ],
            "header": {"name": "John Smith", "email": "john@made-up.com"},
        }
    )
    checked, flags = check_draft(draft, NOTES)
    project = checked.projects[0]
    assert project.bullets == ["Tracked 6 commodities with LightGBM and Prophet."]
    assert project.stack == ["LightGBM"]
    assert [link.url for link in project.links] == [
        "https://github.com/jane/priceradar"
    ]
    assert checked.header.name == ""
    assert len(flags) == 2


def test_merge_adds_new_items_and_skips_duplicates():
    draft = CvDraft.model_validate(
        {
            "skills": [
                {"name": "programming", "items": ["Python", "SQL"]},
                {"name": "Tools", "items": ["Git"]},
            ],
            "projects": [
                {"name": "Hidden Hire", "bullets": ["Duplicate."]},
                {"name": "PriceRadar", "bullets": ["Built a price anomaly detector."]},
            ],
        }
    )
    cv, report = merge(MASTER, draft)
    assert [p.name for p in cv.projects] == ["Hidden Hire – Job Agent", "PriceRadar"]
    assert cv.skills[0].items == ["Python", "SQL"]
    assert cv.skills[1].name == "Tools"
    assert cv.summary == "ML engineer."
    assert any("Skipped project 'Hidden Hire'" in line for line in report)


def test_merge_without_master_needs_a_name():
    with pytest.raises(ValueError):
        merge(None, CvDraft())
    cv, report = merge(None, CvDraft.model_validate({"header": {"name": "Jane"}}))
    assert cv.header.name == "Jane"
    assert report == ["Created your master CV"]


def test_parse_draft_reports_readable_errors():
    with pytest.raises(ValueError, match="indentation"):
        parse_draft("projects: [\n  - name: x")
    with pytest.raises(ValueError, match="projects"):
        parse_draft("projects:\n  - links: []\n")


def test_save_keeps_a_backup(tmp_path):
    path = tmp_path / "master_cv.yaml"
    save_master(MASTER, path)
    save_master(MASTER, path)
    assert path.with_suffix(".yaml.bak").exists()
    assert path.read_text(encoding="utf-8").startswith("# Master CV")
