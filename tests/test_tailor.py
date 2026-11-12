from app.documents.cv import CvData
from app.documents.factcheck import unsupported
from app.documents.tailor import TailorPlan, apply_plan

MASTER = CvData.model_validate(
    {
        "header": {"name": "Jane"},
        "summary": "ML engineer with Python and Docker.",
        "skills": [
            {"name": "Programming", "items": ["Python", "SQL"]},
            {"name": "Tools", "items": ["Docker", "Git"]},
        ],
        "experience": [
            {
                "title": "Intern",
                "dates": "2026",
                "organization": "Acme",
                "bullets": ["Built 3 internal apps with Python.", "Wrote SQL reports."],
            }
        ],
        "projects": [
            {
                "name": "Pinned A",
                "pinned": True,
                "bullets": ["Reached 5.68% MAPE with Python."],
            },
            {"name": "Pinned B", "pinned": True, "bullets": ["Built a Docker API."]},
            {"name": "Option C", "bullets": ["Built a SQL tool."]},
            {"name": "Option D", "bullets": ["Built a Git helper."]},
            {"name": "Option E", "bullets": ["Built a Python CLI."]},
        ],
    }
)


def test_unsupported_finds_new_numbers_and_skills():
    assert unsupported(
        "Reached 99% accuracy with Kubernetes.", "Reached 5.68% MAPE with Python."
    ) == [
        "number 99",
        "skill Kubernetes",
    ]
    assert (
        unsupported(
            "Reached 5.68% MAPE using Python.", "Reached 5.68% MAPE with Python."
        )
        == []
    )


def test_pinned_projects_first_and_two_optional_chosen():
    plan = TailorPlan(
        projects=[
            {"name": "Option E", "bullets": []},
            {"name": "Made Up", "bullets": []},
        ]
    )
    result = apply_plan(MASTER, plan)
    assert [p.name for p in result.cv.projects] == [
        "Pinned A",
        "Pinned B",
        "Option E",
        "Option C",
    ]
    assert any("Made Up" in flag for flag in result.flags)


def test_invented_facts_fall_back_to_master():
    plan = TailorPlan(
        summary="ML engineer with 10 years of Kubernetes.",
        experience=[
            {
                "index": 0,
                "bullets": [
                    "Built 30 internal apps with Python.",
                    "Wrote SQL reports for managers.",
                ],
            }
        ],
        projects=[{"name": "Pinned A", "bullets": ["Reached 1% MAPE."]}],
    )
    result = apply_plan(MASTER, plan)
    assert result.cv.summary == MASTER.summary
    assert result.cv.experience[0].bullets == MASTER.experience[0].bullets
    assert result.cv.projects[0].bullets == ["Reached 5.68% MAPE with Python."]
    assert len(result.flags) == 4


def test_shorter_bullets_keep_master_detail():
    plan = TailorPlan(projects=[{"name": "Pinned A", "bullets": ["Used Python."]}])
    result = apply_plan(MASTER, plan)
    assert result.cv.projects[0].bullets == ["Reached 5.68% MAPE with Python."]
    assert any("lost detail" in flag for flag in result.flags)


def test_reworded_bullets_with_same_detail_are_used():
    plan = TailorPlan(
        projects=[
            {
                "name": "Pinned A",
                "bullets": ["Achieved 5.68% MAPE in forecasting with Python."],
            }
        ]
    )
    result = apply_plan(MASTER, plan)
    assert result.cv.projects[0].bullets == [
        "Achieved 5.68% MAPE in forecasting with Python."
    ]


def test_project_names_match_despite_odd_hyphens_and_typos():
    plan = TailorPlan(
        projects=[
            {
                "name": "Pinned\u2011A",
                "bullets": ["Achieved 5.68% MAPE in forecasting with Python."],
            },
            {"name": "option  d", "bullets": []},
        ]
    )
    result = apply_plan(MASTER, plan)
    assert [p.name for p in result.cv.projects] == [
        "Pinned A",
        "Pinned B",
        "Option D",
        "Option C",
    ]
    assert result.cv.projects[0].bullets == [
        "Achieved 5.68% MAPE in forecasting with Python."
    ]
    assert not [flag for flag in result.flags if "project" in flag or "Pinned" in flag]


def test_skills_reordered_without_new_items():
    plan = TailorPlan(skills=[{"name": "Tools", "items": ["Git", "Terraform"]}])
    result = apply_plan(MASTER, plan)
    assert [g.name for g in result.cv.skills] == ["Tools", "Programming"]
    assert result.cv.skills[0].items == ["Git", "Docker"]
    assert any("Terraform" in flag for flag in result.flags)
