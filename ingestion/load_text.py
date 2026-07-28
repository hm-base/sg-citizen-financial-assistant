import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup


def extract_pdf_text(path: Path) -> str:
    parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            parts.append(page_text)
    return "\n".join(parts)


def extract_html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["nav", "script", "style", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def load_text_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix in (".html", ".htm"):
        return extract_html_text(path)
    raise ValueError(f"Unsupported text source suffix: {suffix}")


def clean_text(text: str) -> str:
    text = text.replace("­", "")  # soft hyphen
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
