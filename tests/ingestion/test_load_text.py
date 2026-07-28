from pathlib import Path

import pytest
from fpdf import FPDF

from ingestion.load_text import (
    clean_text,
    extract_html_text,
    extract_pdf_pages,
    extract_pdf_text,
    load_text_file,
)


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, "Baby Bonus Scheme gives cash gifts to parents.")
    path = tmp_path / "sample.pdf"
    pdf.output(str(path))
    return path


@pytest.fixture
def sample_html(tmp_path: Path) -> Path:
    path = tmp_path / "sample.html"
    path.write_text(
        "<html><body><nav>Skip nav</nav>"
        "<p>CDC Vouchers help with daily expenses.</p></body></html>",
        encoding="utf-8",
    )
    return path


def test_extract_pdf_text_returns_content(sample_pdf):
    text = extract_pdf_text(sample_pdf)
    assert "Baby Bonus" in text


def test_extract_pdf_pages_returns_one_entry_per_page(tmp_path):
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for page_text in ("Page one about ComCare.", "Page two about Silver Support."):
        pdf.add_page()
        pdf.multi_cell(0, 10, page_text)
    path = tmp_path / "two_pages.pdf"
    pdf.output(str(path))

    pages = extract_pdf_pages(path)

    assert len(pages) == 2
    assert "ComCare" in pages[0]
    assert "Silver Support" in pages[1]


def test_extract_html_text_strips_tags(sample_html):
    text = extract_html_text(sample_html)
    assert "CDC Vouchers help with daily expenses." in text
    assert "<p>" not in text


def test_load_text_file_dispatches_by_suffix(sample_pdf, sample_html):
    assert "Baby Bonus" in load_text_file(sample_pdf)
    assert "CDC Vouchers" in load_text_file(sample_html)


def test_load_text_file_rejects_unknown_suffix(tmp_path):
    path = tmp_path / "sample.docx"
    path.write_text("irrelevant", encoding="utf-8")
    with pytest.raises(ValueError):
        load_text_file(path)


def test_clean_text_normalizes_whitespace():
    dirty = "Line one.\n\n\n\nLine   two.   "
    assert clean_text(dirty) == "Line one.\nLine two."
