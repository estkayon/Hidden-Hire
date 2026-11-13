import pytest

from app.documents.cv import (
    CvData,
    DocumentError,
    display_url,
    latex_escape,
    latex_url,
    render_tex,
)

CV = CvData.model_validate(
    {
        "header": {
            "name": "Jane Doe",
            "location": "Dhaka",
            "email": "jane@example.com",
            "links": [{"label": "GitHub", "url": "https://github.com/jane"}],
        },
        "summary": "Built 3 tools with 95% accuracy & C# code.",
        "skills": [{"name": "AI & ML", "items": ["PyTorch", "C#"]}],
        "projects": [
            {
                "name": "Tool",
                "links": [],
                "bullets": [r"\input{secret.txt} should stay plain text"],
            }
        ],
    }
)


def test_escape_special_characters():
    assert latex_escape(r"50% & C# \x_{y}") == r"50\% \& C\# \textbackslash{}x\_\{y\}"


def test_url_rules():
    assert latex_url("https://a.com/x%20y#top") == r"https://a.com/x\%20y\#top"
    assert display_url("https://github.com/jane/") == "github.com/jane"
    with pytest.raises(DocumentError):
        latex_url(r"https://a.com/\input{x}")
    with pytest.raises(DocumentError):
        latex_url("javascript:alert(1)")


def test_render_escapes_all_values():
    tex = render_tex(CV)
    assert r"95\% accuracy \& C\# code" in tex
    assert r"\textbf{AI \& ML:} & PyTorch, C\#" in tex
    assert r"\textbackslash{}input\{secret.txt\}" in tex
    assert r"\input{secret.txt}" not in tex
    assert r"\href{https://github.com/jane}{github.com/jane}" in tex


def test_other_sections_are_rendered_and_escaped():
    cv = CvData.model_validate(
        {
            **CV.model_dump(),
            "other_sections": [
                {
                    "title": "Awards & Honours",
                    "items": [
                        "Top 5% in contest",
                        {"text": "Hackathon winner", "url": "https://x.com/award"},
                    ],
                }
            ],
        }
    )
    tex = render_tex(cv)
    assert r"\section{Awards \& Honours}" in tex
    assert r"\item Top 5\% in contest" in tex
    assert r"\item Hackathon winner \;|\; \href{https://x.com/award}{View}" in tex


def test_section_order_is_followed_and_completed():
    cv = CvData.model_validate(
        {
            **CV.model_dump(),
            "education": [{"degree": "BSc", "dates": "2026", "institution": "AIUB"}],
            "experience": [
                {
                    "title": "Intern",
                    "dates": "2026",
                    "organization": "Acme",
                    "bullets": ["Built apps."],
                }
            ],
            "section_order": ["education", "made_up", "experience"],
        }
    )
    assert cv.section_order[:2] == ["education", "experience"]
    assert "made_up" not in cv.section_order
    assert len(cv.section_order) == 10
    tex = render_tex(cv)
    assert tex.index(r"\section{Education}") < tex.index(
        r"\section{Professional Experience}"
    )
