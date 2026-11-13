"""Master CV data, LaTeX rendering and PDF compile with Tectonic."""

import argparse
import os
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
MASTER_CV = ROOT / "profile" / "master_cv.yaml"
OUTPUT_DIR = ROOT / "output" / "cv"
COMPILE_TIMEOUT = 180

LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
URL_SCHEMES = ("https://", "http://", "mailto:")


class DocumentError(Exception):
    """Rendering or compiling a document failed."""


class Link(BaseModel):
    label: str
    url: str


class Header(BaseModel):
    name: str
    location: str = ""
    phone: str = ""
    email: str = ""
    links: list[Link] = Field(default_factory=list)


class SkillGroup(BaseModel):
    name: str
    items: list[str]


class Experience(BaseModel):
    title: str
    dates: str
    organization: str
    location: str = ""
    stack: list[str] = Field(
        default_factory=list
    )  # tools really used; not printed, used for fact checks
    bullets: list[str]


class Project(BaseModel):
    name: str
    pinned: bool = False  # always shown first in tailored CVs
    tracks: list[str] = Field(
        default_factory=list
    )  # job kinds an optional project is chosen for
    links: list[Link] = Field(default_factory=list)
    stack: list[str] = Field(
        default_factory=list
    )  # tools really used; not printed, used for fact checks
    bullets: list[str]


class Research(BaseModel):
    title: str
    links: list[Link] = Field(default_factory=list)
    subtitle: str = ""
    tools: str = ""
    bullets: list[str]


class Education(BaseModel):
    degree: str
    dates: str
    institution: str
    grade: str = ""
    location: str = ""


class Certification(BaseModel):
    name: str
    issuer: str = ""
    url: str = ""


class Volunteering(BaseModel):
    name: str
    date: str = ""
    url: str = ""
    bullets: list[str] = Field(default_factory=list)


class SectionItem(BaseModel):
    """One line of a custom section, with an optional link shown as "View"."""

    text: str
    url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _from_plain_text(cls, value):
        return {"text": value} if isinstance(value, str) else value


class CustomSection(BaseModel):
    """Any extra section such as Awards, Publications or Languages: a title and one line per item."""

    title: str
    items: list[SectionItem]


class Reference(BaseModel):
    name: str
    lines: list[str] = Field(default_factory=list)
    phone: str = ""
    email: str = ""


class CvData(BaseModel):
    header: Header
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    research: list[Research] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    volunteering: list[Volunteering] = Field(default_factory=list)
    other_sections: list[CustomSection] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)


class Latex(str):
    """Text that is already safe LaTeX and must not be escaped again."""


def latex_escape(text: str) -> str:
    return "".join(LATEX_SPECIAL.get(char, char) for char in text)


def latex_url(url: str) -> Latex:
    """A link target for \\href. Only plain web or mail links are allowed."""
    url = url.strip()
    if not url.startswith(URL_SCHEMES) or any(c in url for c in " \\{}\n\t"):
        raise DocumentError(f"unsafe link: {url[:60]}")
    return Latex(url.replace("%", r"\%").replace("#", r"\#"))


def display_url(url: str) -> str:
    """Visible link text without the scheme, so ATS parsers can read the address."""
    for scheme in URL_SCHEMES:
        url = url.removeprefix(scheme)
    return url.rstrip("/")


def _finalize(value: object) -> str:
    return value if isinstance(value, Latex) else latex_escape(str(value))


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((#",
        comment_end_string="#))",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        finalize=_finalize,
        undefined=StrictUndefined,
    )
    env.filters["url"] = latex_url
    env.filters["display_url"] = display_url
    return env


def load_master(path: Path = MASTER_CV) -> CvData:
    try:
        return CvData.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise DocumentError(f"master CV not found at {path}") from exc
    except (yaml.YAMLError, ValueError) as exc:
        raise DocumentError(f"master CV is invalid: {exc}") from exc


def render_tex(cv: CvData) -> str:
    return _environment().get_template("cv.tex.j2").render(cv=cv)


def tectonic_command() -> str:
    """TECTONIC_PATH, else the project's tools/ copy, else tectonic on PATH."""
    local = ROOT / "tools" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    return os.environ.get("TECTONIC_PATH") or (
        str(local) if local.exists() else "tectonic"
    )


def compile_pdf(tex: str, name: str, out_dir: Path = OUTPUT_DIR) -> Path:
    """Write name.tex and compile it. Tectonic keeps shell-escape off by default."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / f"{name}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    cmd = [
        tectonic_command(),
        "--chatter",
        "minimal",
        "--outdir",
        str(out_dir),
        str(tex_path),
    ]
    try:
        subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=COMPILE_TIMEOUT
        )
    except FileNotFoundError as exc:
        raise DocumentError(
            "Tectonic not found. Put it in tools/ or set TECTONIC_PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DocumentError("Tectonic timed out") from exc
    except subprocess.CalledProcessError as exc:
        tail = "\n".join((exc.stderr or exc.stdout or "").strip().splitlines()[-8:])
        raise DocumentError(f"LaTeX compile failed:\n{tail}") from exc
    return out_dir / f"{name}.pdf"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render and compile the master CV.")
    parser.add_argument("--name", default="master")
    args = parser.parse_args()
    try:
        pdf = compile_pdf(render_tex(load_master()), args.name)
    except DocumentError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Wrote {pdf}")


if __name__ == "__main__":
    main()
