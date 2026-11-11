import pytest
from fastapi.testclient import TestClient

from app import profile as store
from app.main import app

CV_TEXT = "Machine learning engineer. Python, PyTorch, Docker and FastAPI. " * 10


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PROFILE_DIR", tmp_path)
    monkeypatch.setattr(store, "extract_pdf_text", lambda data: CV_TEXT)
    return TestClient(app)


def test_detect_skills_whole_words_only():
    found = store.detect_skills(
        "Built APIs with FastAPI and React.js; used scikit-learn. Good communicator."
    )
    assert {"FastAPI", "React", "scikit-learn"} <= set(found)
    assert "Go" not in found


def test_extract_personal_from_cv_text():
    text = (
        "Jane Rahman\n"
        "Dhaka | jane.r@example.com | +880 1712-345678\n"
        "github.com/janer | linkedin.com/in/jane-r | https://janer.dev\n"
        "Education 2022-2026\n"
    )
    info = store.extract_personal(text)
    assert info.full_name == "Jane Rahman"
    assert info.email == "jane.r@example.com"
    assert info.phone == "+880 1712-345678"
    assert info.github == "https://github.com/janer"
    assert info.linkedin == "https://linkedin.com/in/jane-r"
    assert info.portfolio == "https://janer.dev"
    assert info.location == ""


def test_merge_keeps_owner_edits():
    current = store.PersonalInfo(full_name="Jane R.", location="Dhaka")
    found = store.PersonalInfo(full_name="Jane Rahman", email="j@example.com")
    merged = store.merge_personal(current, found)
    assert merged.full_name == "Jane R."
    assert merged.email == "j@example.com"
    assert merged.location == "Dhaka"


def test_extract_rejects_non_pdf():
    with pytest.raises(ValueError):
        store.extract_pdf_text(b"hello")


def test_upload_creates_profile_with_detected_skills(client):
    response = client.post(
        "/api/profile/cv",
        files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 200
    state = response.json()
    assert state["has_cv"] is True
    assert {"Python", "PyTorch", "Docker", "FastAPI"} <= set(state["profile"]["skills"])


def test_update_cleans_values_and_delete_removes_everything(client):
    client.post(
        "/api/profile/cv",
        files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    body = {
        "skills": [" Python ", "python", "MLOps", ""],
        "target_roles": ["MLOps Engineer"],
        "years_experience": 1,
    }
    profile = client.put("/api/profile", json=body).json()["profile"]
    assert profile["skills"] == ["Python", "MLOps"]
    assert profile["target_roles"] == ["MLOps Engineer"]

    state = client.delete("/api/profile/cv").json()
    assert state == {"has_cv": False, "profile": None, "detected_skills": []}


def test_update_without_cv_is_rejected(client):
    assert client.put("/api/profile", json={"skills": []}).status_code == 409
