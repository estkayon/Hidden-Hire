import zipfile
from io import BytesIO

import pytest

from app.documents.upload_text import extract_docx_text, extract_text

DOC = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hidden Hire</w:t></w:r><w:r><w:tab/><w:t>Python, FastAPI</w:t></w:r></w:p>
    <w:p><w:r><w:t>Built a job search agent.</w:t></w:r></w:p>
  </w:body>
</w:document>"""


def make_docx(document_xml: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_docx_paragraphs_and_tabs():
    assert (
        extract_docx_text(make_docx(DOC))
        == "Hidden Hire\tPython, FastAPI\nBuilt a job search agent."
    )


def test_broken_docx_raises_value_error():
    with pytest.raises(ValueError):
        extract_docx_text(b"not a zip file")


def test_text_files_are_decoded():
    assert extract_text("notes.md", b"  Project | Python \n") == "Project | Python"


@pytest.mark.parametrize("name", ["old.doc", "photo.png"])
def test_unsupported_files_are_rejected(name):
    with pytest.raises(ValueError):
        extract_text(name, b"data")
