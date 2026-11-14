"""Plain text from files loaded into the master CV builder: PDF, Word (.docx), .txt and .md."""

import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from app.profile import extract_pdf_text

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_XML_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 12_000
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_text(data: bytes) -> str:
    """Paragraph text from word/document.xml. Raises ValueError for unreadable files."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_XML_BYTES:
                raise ValueError("The Word file is too large.")
            root = ET.fromstring(archive.read(info))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError(
            "The Word file could not be read. Save it as .docx and try again."
        ) from exc

    paragraphs = []
    for paragraph in root.iter(f"{W}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{W}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{W}tab":
                parts.append("\t")
            elif node.tag in (f"{W}br", f"{W}cr"):
                parts.append("\n")
        paragraphs.append("".join(parts))
    text = "\n".join(paragraphs).strip()
    if not text:
        raise ValueError("No text found in the Word file.")
    return text


def extract_text(filename: str, data: bytes) -> str:
    """Text of an uploaded file, chosen by its extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(data)
    if name.endswith(".docx"):
        return extract_docx_text(data)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace").strip()
    if name.endswith(".doc"):
        raise ValueError("Old .doc files are not supported. Save it as .docx or PDF.")
    raise ValueError("Please choose a PDF, Word (.docx), .txt or .md file.")
