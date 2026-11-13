from app import profile as store
from app.documents.cv import CvData
from app.documents.master import save_master
from app.scoring.source import candidate, has_source, master_as_text

MASTER = CvData.model_validate(
    {
        "header": {"name": "Jane", "email": "jane@example.com"},
        "summary": "ML engineer.",
        "projects": [
            {
                "name": "Flood model",
                "stack": ["XGBoost", "FastAPI"],
                "bullets": ["Built a flood model."],
            }
        ],
    }
)


def test_master_text_has_projects_and_tools_but_no_contacts():
    text = master_as_text(MASTER)
    assert "Project: Flood model" in text
    assert "Tools: XGBoost, FastAPI" in text
    assert "jane@example.com" not in text


def test_candidate_prefers_master_and_adds_its_skills(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PROFILE_DIR", tmp_path)
    assert not has_source()
    assert candidate() is None

    (tmp_path / "cv.txt").write_text("Uploaded CV with Python.", encoding="utf-8")
    store.save_profile(store.Profile(skills=["Python"], target_roles=["ML Engineer"]))
    assert candidate()[1] == "Uploaded CV with Python."

    save_master(MASTER, tmp_path / "master_cv.yaml")
    profile, text = candidate()
    assert "Flood model" in text
    assert {"Python", "XGBoost", "FastAPI"} <= set(profile.skills)
    assert profile.target_roles == ["ML Engineer"]
