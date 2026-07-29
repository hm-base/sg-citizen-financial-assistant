import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup


def extract_pdf_pages(path: Path) -> list[str]:
    """Extract text page by page, so chunk citations can carry real page numbers."""
    with pdfplumber.open(str(path)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def extract_pdf_text(path: Path) -> str:
    return "\n".join(extract_pdf_pages(path))


def extract_html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["nav", "script", "style", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def extract_markdown_text(path: Path) -> str:
    """Load a team .md source; strip YAML frontmatter (kept in sidecar / headers)."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    return text.strip()


def load_text_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix in (".html", ".htm"):
        return extract_html_text(path)
    if suffix in (".md", ".markdown"):
        return extract_markdown_text(path)
    raise ValueError(f"Unsupported text source suffix: {suffix}")


def clean_text(text: str) -> str:
    text = text.replace("­", "")  # soft hyphen
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
