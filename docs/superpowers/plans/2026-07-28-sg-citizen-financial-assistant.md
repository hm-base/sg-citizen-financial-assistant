# SG Citizen Financial Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, multi-modal RAG assistant that answers questions about Singapore government subsidy schemes and tax reliefs, grounded strictly in an ingested knowledge base (text + OCR'd images + Gemini-transcribed video), retrieved via a FAISS dense / BM25 hybrid index, generated via a pluggable Gemini/Grok LLM client with two-layer abstention, served through a FastAPI backend + custom static frontend (plus a minimal Gradio fallback), and evaluated against a labeled test set with retrieval + answer-quality metrics and a baseline-vs-hybrid comparison.

**Architecture:** Ingestion modules turn raw text/image/video files into a unified chunk+metadata schema, which is embedded (`all-MiniLM-L6-v2`, GPU-auto-detected) and indexed into FAISS (dense) and BM25 (keyword). A generation pipeline retrieves top-k chunks (dense-only baseline, or RRF-fused hybrid), applies a pre-LLM similarity gate, builds a grounded prompt, calls the active LLM provider, and validates citations. FastAPI exposes this pipeline over HTTP for a static HTML/CSS/JS frontend; a Gradio app reuses the same pipeline as a demo-day fallback. An evaluation runner replays a labeled question set through both retrieval modes and computes Hit Rate/Recall/MRR plus a human rubric.

**Tech Stack:** Python 3.11+, `faiss-cpu`, `sentence-transformers` + `torch`, `rank_bm25`, `pypdf`, `pdfplumber`, `beautifulsoup4`, `pytesseract` + Tesseract OCR binary, `google-generativeai` (Gemini), `openai` client pointed at xAI's Grok endpoint, `fastapi` + `uvicorn`, `gradio`, `python-dotenv`, `pandas`, `pytest`.

## Global Constraints

- Fallback abstention message (exact text, used verbatim everywhere it appears): `"The available knowledge base does not contain enough information to answer this question."`
- Embedding model is fixed regardless of hardware: `sentence-transformers/all-MiniLM-L6-v2` (384-dim) — never swapped for a bigger model on GPU machines, so the FAISS index stays portable across machines.
- Device auto-detection: use CUDA if `torch.cuda.is_available()`, else CPU — this only changes speed, never output vectors.
- Vector store: FAISS `IndexFlatIP` over L2-normalized vectors (cosine-equivalent). Persisted to `./data/faiss/index.faiss` + `./data/faiss/metadata.jsonl`. No cloud storage anywhere.
- Chunking: ~350 words per chunk, ~50-word overlap (`CHUNK_SIZE_WORDS = 350`, `CHUNK_OVERLAP_WORDS = 50` in `config.py`), matching the lecturer's word-based lab pattern.
- All retrieval/generation parameters (`TOP_K`, `SIMILARITY_THRESHOLD`, `CHUNK_SIZE_WORDS`, `CHUNK_OVERLAP_WORDS`, `LLM_PROVIDER`, `RETRIEVAL_MODE`) live in one `config.py`, loaded from `.env` via `python-dotenv` where secret/environment-specific.
- Only official, publicly published Singapore government content may be ingested — no personal, confidential, or copyrighted third-party material.
- Every citation surfaced to a user must reference `[scheme_name, section_or_page]` and be checked against the actually-retrieved chunk IDs before being trusted.
- No task may make a real network call to Gemini/Grok/Tesseract-download inside a test — all external calls are behind an injectable client/interface and tests use fakes.

---

## File Structure

```
sg-citizen-financial-assistant/
├── .env                          # GEMINI_API_KEY, GROK_API_KEY, LLM_PROVIDER (gitignored)
├── .env.example                  # documents the above with empty/placeholder values
├── .gitignore
├── config.py                     # all shared parameters, loads .env
├── requirements.txt
├── README.md
├── data/
│   ├── sources.yaml              # optional {doc_id, url, modality, scheme_name, category} rows
│   ├── raw/{text,images,video}/  # source files land here (manually or via fetch_sources.py)
│   ├── processed/                # cleaned/chunked JSON per doc_id
│   └── faiss/{index.faiss, metadata.jsonl}
├── ingestion/
│   ├── chunker.py                # word-based recursive chunking
│   ├── metadata.py               # chunk record schema + builder
│   ├── load_text.py              # PDF/HTML → cleaned text
│   ├── load_images_ocr.py        # image → OCR text
│   ├── load_video_gemini.py      # video → Gemini transcription (injectable client)
│   ├── fetch_sources.py          # data/sources.yaml → downloads into data/raw/
│   └── build_index.py            # orchestrates: load → chunk → embed → FAISS + BM25 persist
├── retrieval/
│   ├── embed.py                  # device-auto-detecting embedder wrapper
│   ├── faiss_index.py            # build/save/load/query FAISS IndexFlatIP
│   ├── bm25_index.py             # build/save/load/query BM25
│   ├── hybrid.py                 # reciprocal rank fusion of dense + BM25
│   └── profile_filter.py         # category-boost re-ranking for Personal Profile mode
├── generation/
│   ├── llm_client.py             # LLMClient protocol/interface
│   ├── gemini_client.py          # Gemini implementation
│   ├── grok_client.py            # Grok (OpenAI-compatible) implementation
│   ├── prompts.py                # General Q&A + Personal Profile prompt builders
│   └── pipeline.py               # retrieve → gate → prompt → generate → validate citations
├── backend/
│   ├── main.py                   # FastAPI: /api/query, /api/profile-query, /api/config
│   └── gradio_app.py             # minimal fallback UI, same pipeline
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── evaluation/
│   ├── test_set.json             # ≥12 labeled questions across all required categories
│   ├── metrics.py                # hit_rate, recall_at_k, mrr
│   ├── run_eval.py                # replays test_set.json through dense + hybrid, writes results
│   └── results/                  # CSV/JSON outputs land here
└── notebooks/
    └── colab_demo.ipynb           # thin: clone repo, pip install, run backend + pyngrok
```

---

### Task 1: Project Scaffolding & Config

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config.py`
- Create: `README.md`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.py` module-level constants — `CHUNK_SIZE_WORDS: int`, `CHUNK_OVERLAP_WORDS: int`, `EMBEDDING_MODEL: str`, `TOP_K: int`, `SIMILARITY_THRESHOLD: float`, `RETRIEVAL_MODE: str`, `LLM_PROVIDER: str`, `GEMINI_API_KEY: str | None`, `GROK_API_KEY: str | None`, `GEMINI_MODEL: str`, `GROK_MODEL: str`, `DATA_DIR: pathlib.Path`, `FAISS_INDEX_PATH: pathlib.Path`, `FAISS_METADATA_PATH: pathlib.Path`, `FALLBACK_MESSAGE: str`.

- [ ] **Step 1: Initialize the git repo and folder skeleton**

Run:
```bash
cd "c:/Users/drama/Desktop/sg citizen financial assistant"
git init
mkdir -p data/raw/text data/raw/images data/raw/video data/processed data/faiss
mkdir -p ingestion retrieval generation backend frontend evaluation/results notebooks tests
```
Expected: `.git/` directory created, all folders exist (verify with `ls data ingestion retrieval generation backend frontend evaluation tests`).

- [ ] **Step 2: Write `.gitignore`**

```
.env
__pycache__/
*.pyc
.venv/
venv/
data/raw/
data/processed/
data/faiss/
evaluation/results/
.pytest_cache/
```

- [ ] **Step 3: Write `requirements.txt`**

```
faiss-cpu==1.8.0
sentence-transformers==3.0.1
torch>=2.2
rank_bm25==0.2.2
pypdf==4.3.1
pdfplumber==0.11.4
beautifulsoup4==4.12.3
pytesseract==0.3.13
Pillow==10.4.0
google-generativeai==0.8.3
openai==1.51.0
fastapi==0.115.0
uvicorn==0.30.6
gradio==4.44.0
python-dotenv==1.0.1
pandas==2.2.2
pyyaml==6.0.2
requests==2.32.3
pytest==8.3.3
fpdf2==2.7.9
```

- [ ] **Step 4: Write `.env.example`**

```
# Copy this file to .env and fill in real values. Never commit .env.
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GROK_API_KEY=
```

- [ ] **Step 5: Write the failing test for config**

```python
# tests/test_config.py
import importlib
import os


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    import config
    importlib.reload(config)

    assert config.CHUNK_SIZE_WORDS == 350
    assert config.CHUNK_OVERLAP_WORDS == 50
    assert config.EMBEDDING_MODEL == "sentence-transformers/all-MiniLM-L6-v2"
    assert config.TOP_K == 5
    assert 0.0 <= config.SIMILARITY_THRESHOLD <= 1.0
    assert config.RETRIEVAL_MODE == "dense"
    assert config.LLM_PROVIDER == "gemini"
    assert config.FALLBACK_MESSAGE == (
        "The available knowledge base does not contain enough information "
        "to answer this question."
    )


def test_config_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "grok")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROK_API_KEY", "fake-grok-key")
    import config
    importlib.reload(config)

    assert config.LLM_PROVIDER == "grok"
    assert config.GEMINI_API_KEY == "fake-gemini-key"
    assert config.GROK_API_KEY == "fake-grok-key"
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 7: Write `config.py`**

```python
# config.py
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FAISS_INDEX_PATH = DATA_DIR / "faiss" / "index.faiss"
FAISS_METADATA_PATH = DATA_DIR / "faiss" / "metadata.jsonl"
SOURCES_YAML_PATH = DATA_DIR / "sources.yaml"

CHUNK_SIZE_WORDS = 350
CHUNK_OVERLAP_WORDS = 50

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 5
SIMILARITY_THRESHOLD = 0.35
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "dense")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-2-latest")

FALLBACK_MESSAGE = (
    "The available knowledge base does not contain enough information "
    "to answer this question."
)
```

- [ ] **Step 8: Run the test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Write a minimal `README.md` stub**

```markdown
# SG Citizen Financial Assistant

Local multi-modal RAG assistant for Singapore government subsidy schemes and tax reliefs.
See `docs/superpowers/specs/2026-07-28-local-rag-implementation-design.md` for the full design.

## Setup
1. `python -m venv .venv && .venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
2. `pip install -r requirements.txt`
3. Install Tesseract OCR separately (e.g. `winget install UB-Mannheim.TesseractOCR` on Windows) and ensure it's on PATH.
4. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and/or `GROK_API_KEY`.
5. Run `pytest` to verify the environment.
```

- [ ] **Step 10: Commit**

```bash
git add .gitignore requirements.txt .env.example config.py README.md tests/test_config.py
git commit -m "chore: scaffold project structure and shared config"
```

---

### Task 2: Chunker

**Files:**
- Create: `ingestion/chunker.py`
- Test: `tests/ingestion/test_chunker.py`

**Interfaces:**
- Consumes: `config.CHUNK_SIZE_WORDS`, `config.CHUNK_OVERLAP_WORDS`
- Produces: `chunk_text(text: str, chunk_size: int, overlap: int) -> list[dict]`, each dict has keys `chunk_index: int`, `word_start: int`, `word_end: int`, `text: str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_chunker.py
import pytest

from ingestion.chunker import chunk_text


def test_chunk_text_produces_overlapping_chunks():
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["word_start"] == 0
    assert chunks[0]["word_end"] == 100
    assert chunks[1]["word_start"] == 80  # step = chunk_size - overlap
    for chunk in chunks:
        assert chunk["text"].strip()
        assert chunk["word_start"] <= chunk["word_end"]


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size=10, overlap=10)


def test_chunk_text_rejects_empty_text():
    with pytest.raises(ValueError):
        chunk_text("   ", chunk_size=10, overlap=2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_chunker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion'`

- [ ] **Step 3: Write `ingestion/__init__.py` and `ingestion/chunker.py`**

```python
# ingestion/__init__.py
```

```python
# ingestion/chunker.py
def chunk_text(text: str, chunk_size: int, overlap: int) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    if not text.strip():
        raise ValueError("Cannot chunk empty text")

    words = text.split()
    step = chunk_size - overlap
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_value = " ".join(words[start:end]).strip()
        if chunk_value:
            chunks.append({
                "chunk_index": len(chunks),
                "word_start": start,
                "word_end": end,
                "text": chunk_value,
            })
        if end == len(words):
            break
        start += step
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_chunker.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add ingestion/__init__.py ingestion/chunker.py tests/ingestion/test_chunker.py
git commit -m "feat: add word-based recursive chunker"
```

---

### Task 3: Chunk Metadata Builder

**Files:**
- Create: `ingestion/metadata.py`
- Test: `tests/ingestion/test_metadata.py`

**Interfaces:**
- Consumes: chunk dicts from `ingestion.chunker.chunk_text` (`chunk_index`, `word_start`, `word_end`, `text`)
- Produces: `build_chunk_records(chunks: list[dict], *, doc_id: str, scheme_name: str, category: str, modality: str, source_file: str, section_or_page: str, source_url: str = "", thumbnail_path: str = "") -> list[dict]`. Each output record has keys: `chunk_id`, `doc_id`, `scheme_name`, `category`, `modality`, `source_file`, `section_or_page`, `source_url`, `thumbnail_path`, `text`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_metadata.py
from ingestion.metadata import build_chunk_records


def test_build_chunk_records_attaches_all_fields():
    chunks = [
        {"chunk_index": 0, "word_start": 0, "word_end": 5, "text": "Baby Bonus is a scheme."},
        {"chunk_index": 1, "word_start": 3, "word_end": 8, "text": "It gives cash payouts."},
    ]

    records = build_chunk_records(
        chunks,
        doc_id="baby-bonus-scheme",
        scheme_name="Baby Bonus Scheme",
        category="Family",
        modality="text",
        source_file="data/raw/text/baby_bonus.pdf",
        section_or_page="Eligibility, p.2",
        source_url="https://example.gov.sg/baby-bonus",
    )

    assert len(records) == 2
    assert records[0]["chunk_id"] == "baby-bonus-scheme_text_000"
    assert records[1]["chunk_id"] == "baby-bonus-scheme_text_001"
    for record in records:
        assert record["doc_id"] == "baby-bonus-scheme"
        assert record["scheme_name"] == "Baby Bonus Scheme"
        assert record["category"] == "Family"
        assert record["modality"] == "text"
        assert record["source_file"] == "data/raw/text/baby_bonus.pdf"
        assert record["section_or_page"] == "Eligibility, p.2"
        assert record["source_url"] == "https://example.gov.sg/baby-bonus"
        assert record["thumbnail_path"] == ""
        assert record["text"]


def test_build_chunk_records_image_modality_keeps_thumbnail():
    chunks = [{"chunk_index": 0, "word_start": 0, "word_end": 4, "text": "Payout tiers table."}]

    records = build_chunk_records(
        chunks,
        doc_id="cdc-vouchers",
        scheme_name="CDC Vouchers",
        category="Household",
        modality="image",
        source_file="data/raw/images/cdc.png",
        section_or_page="Infographic",
        thumbnail_path="data/raw/images/cdc.png",
    )

    assert records[0]["chunk_id"] == "cdc-vouchers_image_000"
    assert records[0]["thumbnail_path"] == "data/raw/images/cdc.png"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_metadata.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.metadata'`

- [ ] **Step 3: Write `ingestion/metadata.py`**

```python
# ingestion/metadata.py
def build_chunk_records(
    chunks: list[dict],
    *,
    doc_id: str,
    scheme_name: str,
    category: str,
    modality: str,
    source_file: str,
    section_or_page: str,
    source_url: str = "",
    thumbnail_path: str = "",
) -> list[dict]:
    records = []
    for chunk in chunks:
        chunk_id = f"{doc_id}_{modality}_{chunk['chunk_index']:03d}"
        records.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "scheme_name": scheme_name,
            "category": category,
            "modality": modality,
            "source_file": source_file,
            "section_or_page": section_or_page,
            "source_url": source_url,
            "thumbnail_path": thumbnail_path,
            "text": chunk["text"],
        })
    return records
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_metadata.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ingestion/metadata.py tests/ingestion/test_metadata.py
git commit -m "feat: add chunk metadata builder"
```

---

### Task 4: Text Loader (PDF/HTML)

**Files:**
- Create: `ingestion/load_text.py`
- Test: `tests/ingestion/test_load_text.py`

**Interfaces:**
- Produces: `extract_pdf_text(path: pathlib.Path) -> str`, `extract_html_text(path: pathlib.Path) -> str`, `load_text_file(path: pathlib.Path) -> str` (dispatches on suffix), `clean_text(text: str) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_load_text.py
from pathlib import Path

import pytest
from fpdf import FPDF

from ingestion.load_text import clean_text, extract_html_text, extract_pdf_text, load_text_file


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_load_text.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.load_text'`

- [ ] **Step 3: Write `ingestion/load_text.py`**

```python
# ingestion/load_text.py
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
    text = text.replace("\u00ad", "")  # soft hyphen
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_load_text.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add ingestion/load_text.py tests/ingestion/test_load_text.py
git commit -m "feat: add PDF/HTML text loader and cleaner"
```

---

### Task 5: Image OCR Loader

**Files:**
- Create: `ingestion/load_images_ocr.py`
- Test: `tests/ingestion/test_load_images_ocr.py`

**Interfaces:**
- Produces: `extract_image_text(path: pathlib.Path) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_load_images_ocr.py
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from ingestion.load_images_ocr import extract_image_text


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    image = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 60), "SILVER SUPPORT SCHEME", fill="black", font=ImageFont.load_default())
    path = tmp_path / "sample.png"
    image.save(path)
    return path


def test_extract_image_text_finds_rendered_words(sample_image):
    text = extract_image_text(sample_image)
    assert "SILVER" in text.upper() or "SUPPORT" in text.upper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_load_images_ocr.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.load_images_ocr'`

- [ ] **Step 3: Write `ingestion/load_images_ocr.py`**

```python
# ingestion/load_images_ocr.py
from pathlib import Path

import pytesseract
from PIL import Image


def extract_image_text(path: Path) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_load_images_ocr.py -v`
Expected: PASS (1 test). Requires the Tesseract binary installed and on PATH — if this fails with `TesseractNotFoundError`, install it first (see README) before re-running.

- [ ] **Step 5: Commit**

```bash
git add ingestion/load_images_ocr.py tests/ingestion/test_load_images_ocr.py
git commit -m "feat: add image OCR loader"
```

---

### Task 6: Video Transcription Loader (Gemini)

**Files:**
- Create: `ingestion/load_video_gemini.py`
- Test: `tests/ingestion/test_load_video_gemini.py`

**Interfaces:**
- Consumes: any object implementing `transcribe(video_path: pathlib.Path, prompt: str) -> str` (the real implementation will use the Gemini client from Task 13, but this module only depends on that narrow protocol so it's testable without network calls)
- Produces: `VideoTranscriptionClient` protocol, `transcribe_video(path: pathlib.Path, client: VideoTranscriptionClient) -> str`, `VIDEO_TRANSCRIPTION_PROMPT: str` constant.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_load_video_gemini.py
from pathlib import Path

from ingestion.load_video_gemini import transcribe_video


class FakeClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def transcribe(self, video_path: Path, prompt: str) -> str:
        self.calls.append((video_path, prompt))
        return self.response


def test_transcribe_video_delegates_to_client(tmp_path):
    video_path = tmp_path / "baby_bonus_explainer.mp4"
    video_path.write_bytes(b"fake video bytes")
    client = FakeClient("Baby Bonus gives $8,000 to $10,000 per child.")

    result = transcribe_video(video_path, client)

    assert result == "Baby Bonus gives $8,000 to $10,000 per child."
    assert client.calls[0][0] == video_path
    assert "transcribe" in client.calls[0][1].lower() or "describe" in client.calls[0][1].lower()


def test_transcribe_video_rejects_missing_file(tmp_path):
    import pytest

    missing = tmp_path / "missing.mp4"
    client = FakeClient("irrelevant")
    with pytest.raises(FileNotFoundError):
        transcribe_video(missing, client)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_load_video_gemini.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.load_video_gemini'`

- [ ] **Step 3: Write `ingestion/load_video_gemini.py`**

```python
# ingestion/load_video_gemini.py
from pathlib import Path
from typing import Protocol

VIDEO_TRANSCRIPTION_PROMPT = (
    "Transcribe all spoken speech in this video, and separately describe any "
    "on-screen graphics, flowcharts, or tables (eligibility criteria, payout "
    "amounts, steps) in structured plain text. Do not add commentary."
)


class VideoTranscriptionClient(Protocol):
    def transcribe(self, video_path: Path, prompt: str) -> str: ...


def transcribe_video(path: Path, client: VideoTranscriptionClient) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")
    return client.transcribe(path, VIDEO_TRANSCRIPTION_PROMPT)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_load_video_gemini.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ingestion/load_video_gemini.py tests/ingestion/test_load_video_gemini.py
git commit -m "feat: add video transcription loader with injectable client"
```

---

### Task 7: Fetch Sources Module

**Files:**
- Create: `ingestion/fetch_sources.py`
- Test: `tests/ingestion/test_fetch_sources.py`

**Interfaces:**
- Consumes: any object implementing `get(url: str) -> bytes` (the real implementation will use `requests.get(url).content`, tests use a fake)
- Produces: `SourceEntry` (a `dict` with keys `doc_id`, `url`, `modality`, `scheme_name`, `category`), `load_sources_yaml(path: pathlib.Path) -> list[SourceEntry]`, `fetch_sources(entries: list[SourceEntry], raw_dir: pathlib.Path, downloader) -> list[pathlib.Path]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_fetch_sources.py
from pathlib import Path

import pytest

from ingestion.fetch_sources import fetch_sources, load_sources_yaml


@pytest.fixture
def sources_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text(
        "- doc_id: baby-bonus-scheme\n"
        "  url: https://example.gov.sg/baby-bonus.pdf\n"
        "  modality: text\n"
        "  scheme_name: Baby Bonus Scheme\n"
        "  category: Family\n"
        "- doc_id: cdc-vouchers\n"
        "  url: https://example.gov.sg/cdc.png\n"
        "  modality: image\n"
        "  scheme_name: CDC Vouchers\n"
        "  category: Household\n",
        encoding="utf-8",
    )
    return path


class FakeDownloader:
    def __init__(self):
        self.requested = []

    def get(self, url: str) -> bytes:
        self.requested.append(url)
        return f"content-of-{url}".encode("utf-8")


def test_load_sources_yaml_parses_entries(sources_yaml):
    entries = load_sources_yaml(sources_yaml)
    assert len(entries) == 2
    assert entries[0]["doc_id"] == "baby-bonus-scheme"
    assert entries[1]["modality"] == "image"


def test_fetch_sources_downloads_into_modality_folders(sources_yaml, tmp_path):
    entries = load_sources_yaml(sources_yaml)
    downloader = FakeDownloader()
    raw_dir = tmp_path / "raw"

    saved_paths = fetch_sources(entries, raw_dir, downloader)

    assert len(saved_paths) == 2
    assert (raw_dir / "text" / "baby-bonus-scheme.pdf").exists()
    assert (raw_dir / "images" / "cdc-vouchers.png").exists()
    assert downloader.requested == [
        "https://example.gov.sg/baby-bonus.pdf",
        "https://example.gov.sg/cdc.png",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_fetch_sources.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.fetch_sources'`

- [ ] **Step 3: Write `ingestion/fetch_sources.py`**

```python
# ingestion/fetch_sources.py
from pathlib import Path
from typing import Protocol

import yaml


class Downloader(Protocol):
    def get(self, url: str) -> bytes: ...


def load_sources_yaml(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or []


def fetch_sources(entries: list[dict], raw_dir: Path, downloader: Downloader) -> list[Path]:
    modality_subdir = {"text": "text", "image": "images", "video": "video"}
    saved_paths = []
    for entry in entries:
        subdir = modality_subdir[entry["modality"]]
        folder = raw_dir / subdir
        folder.mkdir(parents=True, exist_ok=True)
        suffix = Path(entry["url"]).suffix or ".bin"
        target = folder / f"{entry['doc_id']}{suffix}"
        target.write_bytes(downloader.get(entry["url"]))
        saved_paths.append(target)
    return saved_paths
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_fetch_sources.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Write a thin real `requests`-based downloader for actual use (not covered by unit tests, exercised manually)**

```python
# append to ingestion/fetch_sources.py
import requests


class RequestsDownloader:
    def get(self, url: str) -> bytes:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content


if __name__ == "__main__":
    import config

    entries = load_sources_yaml(config.SOURCES_YAML_PATH)
    paths = fetch_sources(entries, config.DATA_DIR / "raw", RequestsDownloader())
    print(f"Downloaded {len(paths)} sources into {config.DATA_DIR / 'raw'}")
```

- [ ] **Step 6: Commit**

```bash
git add ingestion/fetch_sources.py tests/ingestion/test_fetch_sources.py
git commit -m "feat: add optional source-fetching module"
```

---

### Task 8: Embedding Module with Device Auto-Detection

**Files:**
- Create: `retrieval/embed.py`
- Test: `tests/retrieval/test_embed.py`

**Interfaces:**
- Consumes: `config.EMBEDDING_MODEL`
- Produces: `get_device() -> str` (`"cuda"` or `"cpu"`), `load_embedder(model_name: str, device: str | None = None) -> sentence_transformers.SentenceTransformer`, `embed_texts(texts: list[str], embedder) -> numpy.ndarray` (shape `(n, 384)`, `float32`, L2-normalized).

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/test_embed.py
import numpy as np

from retrieval.embed import embed_texts, get_device, load_embedder


def test_get_device_returns_cpu_or_cuda():
    assert get_device() in ("cpu", "cuda")


def test_embed_texts_returns_normalized_float32_matrix():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    texts = ["Baby Bonus gives cash gifts.", "CDC vouchers help with groceries."]

    vectors = embed_texts(texts, embedder)

    assert vectors.shape == (2, 384)
    assert vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/retrieval/test_embed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retrieval'`

- [ ] **Step 3: Write `retrieval/__init__.py` and `retrieval/embed.py`**

```python
# retrieval/__init__.py
```

```python
# retrieval/embed.py
import numpy as np
import torch
from sentence_transformers import SentenceTransformer


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_embedder(model_name: str, device: str | None = None) -> SentenceTransformer:
    return SentenceTransformer(model_name, device=device or get_device())


def embed_texts(texts: list[str], embedder: SentenceTransformer) -> np.ndarray:
    vectors = embedder.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/retrieval/test_embed.py -v`
Expected: PASS (2 tests). First run downloads the ~80MB model from Hugging Face — requires internet once; cached afterward.

- [ ] **Step 5: Commit**

```bash
git add retrieval/__init__.py retrieval/embed.py tests/retrieval/test_embed.py
git commit -m "feat: add device-auto-detecting embedding wrapper"
```

---

### Task 9: FAISS Index Module

**Files:**
- Create: `retrieval/faiss_index.py`
- Test: `tests/retrieval/test_faiss_index.py`

**Interfaces:**
- Consumes: `numpy.ndarray` vectors from `retrieval.embed.embed_texts`
- Produces: `build_faiss_index(vectors: numpy.ndarray) -> faiss.IndexFlatIP`, `save_faiss_index(index, path: pathlib.Path) -> None`, `load_faiss_index(path: pathlib.Path) -> faiss.IndexFlatIP`, `search_faiss_index(index, query_vector: numpy.ndarray, top_k: int) -> list[tuple[int, float]]` (list of `(row_index, score)`, best first).

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/test_faiss_index.py
import numpy as np

from retrieval.faiss_index import build_faiss_index, load_faiss_index, save_faiss_index, search_faiss_index


def _unit_vectors():
    raw = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.9, 0.1, 0.0]],
        dtype=np.float32,
    )
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    return (raw / norms).astype(np.float32)


def test_build_and_search_faiss_index_ranks_by_similarity():
    vectors = _unit_vectors()
    index = build_faiss_index(vectors)

    query = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    results = search_faiss_index(index, query, top_k=2)

    assert results[0][0] == 0  # most similar to itself
    assert results[1][0] == 2  # second-closest is the near-duplicate
    assert results[0][1] > results[1][1]


def test_save_and_load_faiss_index_roundtrips(tmp_path):
    vectors = _unit_vectors()
    index = build_faiss_index(vectors)
    path = tmp_path / "index.faiss"

    save_faiss_index(index, path)
    loaded = load_faiss_index(path)

    assert loaded.ntotal == index.ntotal
    assert loaded.d == index.d
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/retrieval/test_faiss_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retrieval.faiss_index'`

- [ ] **Step 3: Write `retrieval/faiss_index.py`**

```python
# retrieval/faiss_index.py
from pathlib import Path

import faiss
import numpy as np


def build_faiss_index(vectors: np.ndarray) -> faiss.IndexFlatIP:
    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)
    return index


def save_faiss_index(index: faiss.IndexFlatIP, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_faiss_index(path: Path) -> faiss.IndexFlatIP:
    return faiss.read_index(str(path))


def search_faiss_index(
    index: faiss.IndexFlatIP, query_vector: np.ndarray, top_k: int
) -> list[tuple[int, float]]:
    safe_k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, safe_k)
    return [
        (int(idx), float(score))
        for idx, score in zip(indices[0], scores[0])
        if idx != -1
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/retrieval/test_faiss_index.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add retrieval/faiss_index.py tests/retrieval/test_faiss_index.py
git commit -m "feat: add FAISS flat index build/save/load/search"
```

---

### Task 10: BM25 Index Module

**Files:**
- Create: `retrieval/bm25_index.py`
- Test: `tests/retrieval/test_bm25_index.py`

**Interfaces:**
- Produces: `build_bm25_index(chunk_texts: list[str]) -> rank_bm25.BM25Okapi`, `search_bm25_index(index, query: str, top_k: int) -> list[tuple[int, float]]` (list of `(row_index, score)`, best first).

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/test_bm25_index.py
from retrieval.bm25_index import build_bm25_index, search_bm25_index


def test_search_bm25_index_ranks_exact_keyword_matches_first():
    chunk_texts = [
        "The GST Voucher gives eligible households up to $850.",
        "Baby Bonus gives parents cash gifts for each child.",
        "GST Voucher amounts depend on Annual Value of the home.",
    ]
    index = build_bm25_index(chunk_texts)

    results = search_bm25_index(index, "GST Voucher amount", top_k=2)

    result_indices = [idx for idx, _ in results]
    assert 0 in result_indices
    assert 2 in result_indices
    assert 1 not in result_indices
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/retrieval/test_bm25_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retrieval.bm25_index'`

- [ ] **Step 3: Write `retrieval/bm25_index.py`**

```python
# retrieval/bm25_index.py
from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def build_bm25_index(chunk_texts: list[str]) -> BM25Okapi:
    tokenized = [_tokenize(text) for text in chunk_texts]
    return BM25Okapi(tokenized)


def search_bm25_index(index: BM25Okapi, query: str, top_k: int) -> list[tuple[int, float]]:
    scores = index.get_scores(_tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    return [(idx, float(score)) for idx, score in ranked[:top_k] if score > 0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/retrieval/test_bm25_index.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add retrieval/bm25_index.py tests/retrieval/test_bm25_index.py
git commit -m "feat: add BM25 keyword index"
```

---

### Task 11: Hybrid Retrieval (Reciprocal Rank Fusion)

**Files:**
- Create: `retrieval/hybrid.py`
- Test: `tests/retrieval/test_hybrid.py`

**Interfaces:**
- Consumes: `list[tuple[int, float]]` result lists from `search_faiss_index` and `search_bm25_index` (same shape, `(row_index, score)`)
- Produces: `reciprocal_rank_fusion(result_lists: list[list[tuple[int, float]]], k: int = 60) -> list[tuple[int, float]]` (fused, sorted best-first by fused score; row indices are the same corpus row indices used by both underlying searches).

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/test_hybrid.py
from retrieval.hybrid import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_boosts_items_ranked_high_in_both_lists():
    dense_results = [(2, 0.9), (0, 0.8), (1, 0.5)]
    bm25_results = [(0, 5.0), (2, 4.0), (3, 1.0)]

    fused = reciprocal_rank_fusion([dense_results, bm25_results])

    fused_indices = [idx for idx, _ in fused]
    # 0 and 2 each appear in both lists near the top, so they should fuse to the top two.
    assert set(fused_indices[:2]) == {0, 2}
    # 1 only appears in dense results, 3 only in bm25 — both should still be present, ranked lower.
    assert set(fused_indices) == {0, 1, 2, 3}


def test_reciprocal_rank_fusion_handles_empty_list():
    fused = reciprocal_rank_fusion([[], [(0, 1.0)]])
    assert fused == [(0, 1.0 / 61)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/retrieval/test_hybrid.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retrieval.hybrid'`

- [ ] **Step 3: Write `retrieval/hybrid.py`**

```python
# retrieval/hybrid.py
def reciprocal_rank_fusion(
    result_lists: list[list[tuple[int, float]]], k: int = 60
) -> list[tuple[int, float]]:
    fused_scores: dict[int, float] = {}
    for results in result_lists:
        for rank, (row_index, _score) in enumerate(results):
            fused_scores[row_index] = fused_scores.get(row_index, 0.0) + 1.0 / (k + rank + 1)

    ranked = sorted(fused_scores.items(), key=lambda pair: pair[1], reverse=True)
    return [(idx, score) for idx, score in ranked]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/retrieval/test_hybrid.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add retrieval/hybrid.py tests/retrieval/test_hybrid.py
git commit -m "feat: add reciprocal rank fusion for hybrid retrieval"
```

---

### Task 12: Profile Category Re-Ranking

**Files:**
- Create: `retrieval/profile_filter.py`
- Test: `tests/retrieval/test_profile_filter.py`

**Interfaces:**
- Consumes: candidate list of `(row_index, score)` plus a `chunk_records: list[dict]` (same row-indexed order as the corpus, each with a `"category"` key from Task 3)
- Produces: `PROFILE_CATEGORY_MAP: dict[str, list[str]]` (profile signal → preferred categories, per the addendum), `infer_preferred_categories(profile: dict) -> set[str]`, `rerank_by_category(candidates: list[tuple[int, float]], chunk_records: list[dict], preferred_categories: set[str], top_k: int) -> list[tuple[int, float]]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/test_profile_filter.py
from retrieval.profile_filter import infer_preferred_categories, rerank_by_category


def test_infer_preferred_categories_maps_senior_age():
    categories = infer_preferred_categories({"age": 68, "life_stage_tags": []})
    assert "Seniors" in categories


def test_infer_preferred_categories_maps_young_children_tag():
    categories = infer_preferred_categories({"age": 32, "life_stage_tags": ["Has young child(ren)"]})
    assert "Family" in categories


def test_infer_preferred_categories_defaults_to_empty_when_no_signals():
    categories = infer_preferred_categories({"age": 40, "life_stage_tags": []})
    assert categories == set()


def test_rerank_by_category_promotes_preferred_categories_without_dropping_others():
    candidates = [(0, 0.9), (1, 0.85), (2, 0.8), (3, 0.75)]
    chunk_records = [
        {"category": "Housing"},
        {"category": "Seniors"},
        {"category": "Family"},
        {"category": "Seniors"},
    ]

    reranked = rerank_by_category(candidates, chunk_records, {"Seniors"}, top_k=2)

    reranked_indices = [idx for idx, _ in reranked]
    assert reranked_indices == [1, 3]


def test_rerank_by_category_falls_back_when_not_enough_preferred_hits():
    candidates = [(0, 0.9), (1, 0.85)]
    chunk_records = [{"category": "Housing"}, {"category": "Family"}]

    reranked = rerank_by_category(candidates, chunk_records, {"Seniors"}, top_k=2)

    assert [idx for idx, _ in reranked] == [0, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/retrieval/test_profile_filter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retrieval.profile_filter'`

- [ ] **Step 3: Write `retrieval/profile_filter.py`**

```python
# retrieval/profile_filter.py
PROFILE_CATEGORY_MAP = {
    "senior_age": ["Seniors", "Healthcare"],
    "young_children": ["Family"],
    "caregiver": ["Seniors/caregiving", "Healthcare"],
    "lower_income_employed": ["Lower-income/employment"],
    "hdb_housing": ["Housing", "Household/cost-of-living"],
}


def infer_preferred_categories(profile: dict) -> set[str]:
    preferred: set[str] = set()

    if profile.get("age") is not None and profile["age"] >= 65:
        preferred.update(PROFILE_CATEGORY_MAP["senior_age"])

    tags = profile.get("life_stage_tags") or []
    if "Has young child(ren)" in tags:
        preferred.update(PROFILE_CATEGORY_MAP["young_children"])
    if "Caregiver" in tags:
        preferred.update(PROFILE_CATEGORY_MAP["caregiver"])

    if profile.get("employment") == "Employed" and profile.get("monthly_income_band") in (
        "<$1.5k",
        "$1.5-3k",
    ):
        preferred.update(PROFILE_CATEGORY_MAP["lower_income_employed"])

    if profile.get("housing") == "HDB":
        preferred.update(PROFILE_CATEGORY_MAP["hdb_housing"])

    return preferred


def rerank_by_category(
    candidates: list[tuple[int, float]],
    chunk_records: list[dict],
    preferred_categories: set[str],
    top_k: int,
) -> list[tuple[int, float]]:
    if not preferred_categories:
        return candidates[:top_k]

    preferred = [c for c in candidates if chunk_records[c[0]]["category"] in preferred_categories]
    if len(preferred) < top_k:
        return candidates[:top_k]

    others = [c for c in candidates if chunk_records[c[0]]["category"] not in preferred_categories]
    return (preferred + others)[:top_k]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/retrieval/test_profile_filter.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add retrieval/profile_filter.py tests/retrieval/test_profile_filter.py
git commit -m "feat: add profile-based category re-ranking"
```

---

### Task 13: LLM Client Interface + Gemini Client

**Files:**
- Create: `generation/llm_client.py`
- Create: `generation/gemini_client.py`
- Test: `tests/generation/test_llm_client.py`

**Interfaces:**
- Produces: `LLMClient` protocol with `generate(self, prompt: str) -> str`; `GeminiClient` implementing it, constructed as `GeminiClient(api_key: str, model_name: str, sdk_client=None)` where `sdk_client` (optional, for tests) must expose `generate_content(model: str, contents: str) -> object with .text`; also `GeminiClient.transcribe(video_path: pathlib.Path, prompt: str) -> str` satisfying Task 6's `VideoTranscriptionClient` protocol.

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_llm_client.py
from pathlib import Path

from generation.gemini_client import GeminiClient


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeGenAIClient:
    def __init__(self, text_response: str):
        self.text_response = text_response
        self.calls = []

    def generate_content(self, model: str, contents):
        self.calls.append((model, contents))
        return FakeResponse(self.text_response)


def test_gemini_client_generate_returns_response_text():
    fake_sdk = FakeGenAIClient("Answer: [Baby Bonus Scheme, p.2]")
    client = GeminiClient(api_key="fake-key", model_name="gemini-1.5-flash", sdk_client=fake_sdk)

    result = client.generate("What is Baby Bonus?")

    assert result == "Answer: [Baby Bonus Scheme, p.2]"
    assert fake_sdk.calls[0][0] == "gemini-1.5-flash"


def test_gemini_client_transcribe_passes_video_and_prompt(tmp_path):
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"fake bytes")
    fake_sdk = FakeGenAIClient("Transcript: scheme explainer content.")
    client = GeminiClient(api_key="fake-key", model_name="gemini-1.5-flash", sdk_client=fake_sdk)

    result = client.transcribe(video_path, "Transcribe this video.")

    assert result == "Transcript: scheme explainer content."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_llm_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generation'`

- [ ] **Step 3: Write `generation/__init__.py` and `generation/llm_client.py`**

```python
# generation/__init__.py
```

```python
# generation/llm_client.py
from typing import Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...
```

- [ ] **Step 4: Write `generation/gemini_client.py`**

```python
# generation/gemini_client.py
from pathlib import Path

import google.generativeai as genai


class GeminiClient:
    def __init__(self, api_key: str, model_name: str, sdk_client=None):
        self.model_name = model_name
        if sdk_client is not None:
            self._sdk_client = sdk_client
        else:
            genai.configure(api_key=api_key)
            self._sdk_client = _RealGenAIAdapter()

    def generate(self, prompt: str) -> str:
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text

    def transcribe(self, video_path: Path, prompt: str) -> str:
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text


class _RealGenAIAdapter:
    def generate_content(self, model: str, contents):
        return genai.GenerativeModel(model).generate_content(contents)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/generation/test_llm_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add generation/__init__.py generation/llm_client.py generation/gemini_client.py tests/generation/test_llm_client.py
git commit -m "feat: add LLM client interface and Gemini implementation"
```

---

### Task 14: Grok Client

**Files:**
- Create: `generation/grok_client.py`
- Test: `tests/generation/test_grok_client.py`

**Interfaces:**
- Consumes: `generation.llm_client.LLMClient` protocol
- Produces: `GrokClient(api_key: str, model_name: str, sdk_client=None)` where `sdk_client` (optional, for tests) exposes `chat_completions_create(model: str, messages: list[dict]) -> object with .choices[0].message.content`.

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_grok_client.py
from generation.grok_client import GrokClient


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeGrokSDK:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def chat_completions_create(self, model: str, messages: list[dict]):
        self.calls.append((model, messages))
        return FakeCompletion(self.content)


def test_grok_client_generate_returns_message_content():
    fake_sdk = FakeGrokSDK("Answer: [Silver Support Scheme, Eligibility]")
    client = GrokClient(api_key="fake-key", model_name="grok-2-latest", sdk_client=fake_sdk)

    result = client.generate("What is Silver Support?")

    assert result == "Answer: [Silver Support Scheme, Eligibility]"
    model, messages = fake_sdk.calls[0]
    assert model == "grok-2-latest"
    assert messages[0]["content"] == "What is Silver Support?"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_grok_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generation.grok_client'`

- [ ] **Step 3: Write `generation/grok_client.py`**

```python
# generation/grok_client.py
from openai import OpenAI

GROK_BASE_URL = "https://api.x.ai/v1"


class GrokClient:
    def __init__(self, api_key: str, model_name: str, sdk_client=None):
        self.model_name = model_name
        self._sdk_client = sdk_client or _RealOpenAIAdapter(api_key)

    def generate(self, prompt: str) -> str:
        completion = self._sdk_client.chat_completions_create(
            self.model_name, [{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content


class _RealOpenAIAdapter:
    def __init__(self, api_key: str):
        self._client = OpenAI(api_key=api_key, base_url=GROK_BASE_URL)

    def chat_completions_create(self, model: str, messages: list[dict]):
        return self._client.chat.completions.create(model=model, messages=messages)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_grok_client.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add generation/grok_client.py tests/generation/test_grok_client.py
git commit -m "feat: add Grok client via OpenAI-compatible API"
```

---

### Task 15: Prompt Templates

**Files:**
- Create: `generation/prompts.py`
- Test: `tests/generation/test_prompts.py`

**Interfaces:**
- Consumes: `chunk_records: list[dict]` (from Task 3's schema, subset that was retrieved) and `config.FALLBACK_MESSAGE`
- Produces: `build_general_qa_prompt(question: str, retrieved: list[dict]) -> str`, `build_profile_prompt(profile: dict, retrieved: list[dict], free_text_question: str = "") -> str`, `extract_cited_scheme_labels(answer: str) -> list[tuple[str, str]]` (list of `(scheme_name, section_or_page)` pairs found in `[scheme_name, section_or_page]` citations).

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_prompts.py
from generation.prompts import build_general_qa_prompt, build_profile_prompt, extract_cited_scheme_labels

SAMPLE_CHUNKS = [
    {
        "scheme_name": "Baby Bonus Scheme",
        "section_or_page": "Eligibility, p.2",
        "text": "Parents receive a cash gift for each Singaporean child.",
    },
    {
        "scheme_name": "CDC Vouchers",
        "section_or_page": "FAQ",
        "text": "Vouchers can be spent at participating hawkers and merchants.",
    },
]


def test_build_general_qa_prompt_includes_question_and_labeled_passages():
    prompt = build_general_qa_prompt("What is Baby Bonus?", SAMPLE_CHUNKS)

    assert "What is Baby Bonus?" in prompt
    assert "[Baby Bonus Scheme, Eligibility, p.2]" in prompt
    assert "Parents receive a cash gift" in prompt
    assert "does not contain enough information" in prompt  # abstention instruction present


def test_build_profile_prompt_includes_profile_and_three_section_contract():
    profile = {"citizenship": "Singapore Citizen", "age": 68, "monthly_income_band": "<$1.5k"}
    prompt = build_profile_prompt(profile, SAMPLE_CHUNKS, free_text_question="")

    assert "Singapore Citizen" in prompt
    assert "Possibly eligible" in prompt
    assert "Likely not eligible" in prompt
    assert "Not assessed" in prompt


def test_extract_cited_scheme_labels_parses_bracketed_citations():
    answer = "You may get a cash gift [Baby Bonus Scheme, Eligibility, p.2] and vouchers [CDC Vouchers, FAQ]."

    labels = extract_cited_scheme_labels(answer)

    assert ("Baby Bonus Scheme", "Eligibility, p.2") in labels
    assert ("CDC Vouchers", "FAQ") in labels
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_prompts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generation.prompts'`

- [ ] **Step 3: Write `generation/prompts.py`**

```python
# generation/prompts.py
import re

from config import FALLBACK_MESSAGE

GENERAL_QA_SYSTEM_RULES = f"""You are an assistant that answers questions about Singapore \
government subsidy schemes and tax reliefs using ONLY the context passages provided below. \
Each passage is labeled with a source ID.

Rules:
1. Answer only using facts present in the provided passages. Do not use outside knowledge.
2. For every factual claim, cite the source ID(s) it came from, in the form [scheme_name, section_or_page].
3. If the passages do not contain enough information to answer, respond with exactly: \
"{FALLBACK_MESSAGE}" Do not guess.
4. Keep answers concise and in plain language suitable for a member of the public.
"""

PROFILE_SYSTEM_RULES = f"""You help a Singapore resident understand which schemes in the provided \
passages they may be eligible for.

Rules:
1. Use ONLY the numbered context passages. No outside knowledge.
2. Output three sections only:
   - Possibly eligible - scheme name, why (criteria quoted/paraphrased from passages), \
amount/tier only if stated in passages, citations.
   - Likely not eligible / unclear - scheme appears in context but a stated criterion conflicts \
with the profile, or a required criterion is missing from passages.
   - Not assessed - do not invent schemes that are absent from the passages.
3. Never say "you are approved" or "you will receive." Use "based on the documents, you may be \
eligible if ..."
4. If income/age/citizenship thresholds are not in the passages, say so and put the scheme under \
Likely not eligible / unclear, even if thematically relevant.
5. Every factual claim must cite [scheme_name, section_or_page].
6. If passages are insufficient for any shortlist, respond exactly with: "{FALLBACK_MESSAGE}"
"""


def _format_passages(retrieved: list[dict]) -> str:
    lines = []
    for chunk in retrieved:
        label = f"[{chunk['scheme_name']}, {chunk['section_or_page']}]"
        lines.append(f"{label}\n{chunk['text']}")
    return "\n\n".join(lines)


def build_general_qa_prompt(question: str, retrieved: list[dict]) -> str:
    return (
        f"{GENERAL_QA_SYSTEM_RULES}\n\n"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )


def build_profile_prompt(profile: dict, retrieved: list[dict], free_text_question: str = "") -> str:
    question_line = free_text_question or "What can I get and roughly how much?"
    return (
        f"{PROFILE_SYSTEM_RULES}\n\n"
        f"User profile (bands only): {profile}\n\n"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question_line}\n"
        f"Answer:"
    )


def extract_cited_scheme_labels(answer: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\[\],]+),\s*([^\[\]]+)\]", answer)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_prompts.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add generation/prompts.py tests/generation/test_prompts.py
git commit -m "feat: add General Q&A and Personal Profile prompt templates"
```

---

### Task 16: RAG Pipeline Orchestration (Retrieval + Abstention + Generation + Citation Validation)

**Files:**
- Create: `generation/pipeline.py`
- Test: `tests/generation/test_pipeline.py`

**Interfaces:**
- Consumes: `retrieval.faiss_index.search_faiss_index`, `retrieval.bm25_index.search_bm25_index`, `retrieval.hybrid.reciprocal_rank_fusion`, `retrieval.profile_filter.{infer_preferred_categories, rerank_by_category}`, `generation.prompts.{build_general_qa_prompt, build_profile_prompt, extract_cited_scheme_labels}`, `generation.llm_client.LLMClient`, `config.{TOP_K, SIMILARITY_THRESHOLD, FALLBACK_MESSAGE}`
- Produces:
  - `RagIndex` — a small dataclass bundling `faiss_index`, `bm25_index`, `chunk_records: list[dict]`, `embedder` (an object with `.encode` used only via `retrieval.embed.embed_texts`), so callers pass one object instead of four.
  - `answer_general_question(question: str, rag_index: RagIndex, llm_client, *, top_k: int, similarity_threshold: float, retrieval_mode: str) -> dict` returning `{"answer": str, "sources": list[dict], "abstained": bool, "citation_warning": list[tuple[str, str]] | None}`.
  - `answer_profile_question(profile: dict, rag_index: RagIndex, llm_client, *, free_text_question: str = "", top_k: int, similarity_threshold: float, retrieval_mode: str) -> dict` (same return shape).

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_pipeline.py
import numpy as np

from generation.pipeline import RagIndex, answer_general_question, answer_profile_question
from retrieval.bm25_index import build_bm25_index
from retrieval.faiss_index import build_faiss_index


class FakeEmbedder:
    """Deterministic fake: maps known strings to fixed unit vectors."""

    VECTORS = {
        "gst voucher amount": np.array([1.0, 0.0], dtype=np.float32),
        "unrelated pet question": np.array([0.0, 1.0], dtype=np.float32),
    }

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        return np.array([self.VECTORS.get(text.lower(), [0.0, 0.0]) for text in texts], dtype=np.float32)


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def _build_rag_index():
    chunk_records = [
        {
            "chunk_id": "gst-voucher_text_000",
            "scheme_name": "GST Voucher",
            "category": "Household",
            "section_or_page": "FAQ",
            "text": "GST Voucher gives eligible households up to $850 in cash.",
        },
    ]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    faiss_index = build_faiss_index(vectors)
    bm25_index = build_bm25_index([record["text"] for record in chunk_records])
    return RagIndex(
        faiss_index=faiss_index,
        bm25_index=bm25_index,
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )


def test_answer_general_question_returns_grounded_answer_above_threshold():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get up to $850 [GST Voucher, FAQ].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is False
    assert result["answer"] == "You may get up to $850 [GST Voucher, FAQ]."
    assert result["sources"][0]["scheme_name"] == "GST Voucher"
    assert result["citation_warning"] == []


def test_answer_general_question_abstains_below_threshold_without_calling_llm():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("should never be returned")

    result = answer_general_question(
        "unrelated pet question",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is True
    assert "does not contain enough information" in result["answer"]
    assert llm_client.last_prompt is None


def test_answer_general_question_flags_citation_not_in_retrieved_sources():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get funds [Made Up Scheme, Nowhere].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["citation_warning"] == [("Made Up Scheme", "Nowhere")]


def test_answer_profile_question_returns_grounded_shortlist():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("Possibly eligible: GST Voucher [GST Voucher, FAQ].")

    result = answer_profile_question(
        {"age": 68, "life_stage_tags": [], "monthly_income_band": "<$1.5k"},
        rag_index,
        llm_client,
        free_text_question="gst voucher amount",
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is False
    assert "Possibly eligible" in result["answer"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generation.pipeline'`

- [ ] **Step 3: Write `generation/pipeline.py`**

```python
# generation/pipeline.py
from dataclasses import dataclass

from retrieval.bm25_index import search_bm25_index
from retrieval.embed import embed_texts
from retrieval.faiss_index import search_faiss_index
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.profile_filter import infer_preferred_categories, rerank_by_category

from config import FALLBACK_MESSAGE
from generation.prompts import build_general_qa_prompt, build_profile_prompt, extract_cited_scheme_labels


@dataclass
class RagIndex:
    faiss_index: object
    bm25_index: object
    chunk_records: list[dict]
    embedder: object


def _retrieve(query: str, rag_index: RagIndex, top_k: int, retrieval_mode: str) -> list[tuple[int, float]]:
    query_vector = embed_texts([query], rag_index.embedder)
    dense_results = search_faiss_index(rag_index.faiss_index, query_vector, top_k)

    if retrieval_mode == "dense":
        return dense_results

    bm25_results = search_bm25_index(rag_index.bm25_index, query, top_k)
    fused = reciprocal_rank_fusion([dense_results, bm25_results])
    return fused[:top_k]


def _abstain_result() -> dict:
    return {"answer": FALLBACK_MESSAGE, "sources": [], "abstained": True, "citation_warning": None}


def _generate_result(prompt: str, retrieved_records: list[dict], llm_client) -> dict:
    answer = llm_client.generate(prompt)
    cited = extract_cited_scheme_labels(answer)
    allowed = {(r["scheme_name"], r["section_or_page"]) for r in retrieved_records}
    warnings = [pair for pair in cited if (pair[0].strip(), pair[1].strip()) not in allowed]
    return {
        "answer": answer,
        "sources": retrieved_records,
        "abstained": False,
        "citation_warning": warnings,
    }


def answer_general_question(
    question: str,
    rag_index: RagIndex,
    llm_client,
    *,
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
) -> dict:
    results = _retrieve(question, rag_index, top_k, retrieval_mode)
    if not results or results[0][1] < similarity_threshold:
        return _abstain_result()

    retrieved_records = [rag_index.chunk_records[idx] for idx, _ in results]
    prompt = build_general_qa_prompt(question, retrieved_records)
    return _generate_result(prompt, retrieved_records, llm_client)


def answer_profile_question(
    profile: dict,
    rag_index: RagIndex,
    llm_client,
    *,
    free_text_question: str = "",
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
) -> dict:
    query = free_text_question or (
        f"Singapore subsidy eligibility and payout amounts for profile: {profile}"
    )
    candidate_pool_size = max(top_k * 3, 15)
    candidates = _retrieve(query, rag_index, candidate_pool_size, retrieval_mode)
    if not candidates or candidates[0][1] < similarity_threshold:
        return _abstain_result()

    preferred_categories = infer_preferred_categories(profile)
    reranked = rerank_by_category(candidates, rag_index.chunk_records, preferred_categories, top_k)

    retrieved_records = [rag_index.chunk_records[idx] for idx, _ in reranked]
    prompt = build_profile_prompt(profile, retrieved_records, free_text_question)
    return _generate_result(prompt, retrieved_records, llm_client)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_pipeline.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add generation/pipeline.py tests/generation/test_pipeline.py
git commit -m "feat: add RAG pipeline with two-layer abstention and citation validation"
```

---

### Task 17: Ingestion Build-Index Script

**Files:**
- Create: `ingestion/build_index.py`
- Test: `tests/ingestion/test_build_index.py`

**Interfaces:**
- Consumes: `ingestion.chunker.chunk_text`, `ingestion.metadata.build_chunk_records`, `retrieval.embed.{load_embedder, embed_texts}`, `retrieval.faiss_index.{build_faiss_index, save_faiss_index}`, `retrieval.bm25_index.build_bm25_index`, `config.{CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS, FAISS_INDEX_PATH, FAISS_METADATA_PATH}`
- Produces: `build_index_from_documents(documents: list[dict], embedder) -> tuple[faiss.IndexFlatIP, list[dict]]` where each input `dict` has keys `text, doc_id, scheme_name, category, modality, source_file, section_or_page, source_url, thumbnail_path`; `persist_index(faiss_index, chunk_records: list[dict], faiss_path: pathlib.Path, metadata_path: pathlib.Path) -> None`; `load_metadata(metadata_path: pathlib.Path) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_build_index.py
import json

from ingestion.build_index import build_index_from_documents, load_metadata, persist_index
from retrieval.embed import load_embedder


def test_build_index_from_documents_chunks_embeds_and_indexes_all_docs():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [
        {
            "text": "Baby Bonus gives cash gifts to parents of Singaporean children. " * 30,
            "doc_id": "baby-bonus-scheme",
            "scheme_name": "Baby Bonus Scheme",
            "category": "Family",
            "modality": "text",
            "source_file": "data/raw/text/baby_bonus.pdf",
            "section_or_page": "Overview",
            "source_url": "",
            "thumbnail_path": "",
        },
    ]

    faiss_index, chunk_records = build_index_from_documents(documents, embedder)

    assert faiss_index.ntotal == len(chunk_records)
    assert faiss_index.ntotal > 1  # long text should split into multiple chunks
    assert all(record["doc_id"] == "baby-bonus-scheme" for record in chunk_records)


def test_persist_index_and_load_metadata_roundtrip(tmp_path):
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [
        {
            "text": "Silver Support gives quarterly payouts to eligible seniors. " * 30,
            "doc_id": "silver-support",
            "scheme_name": "Silver Support Scheme",
            "category": "Seniors",
            "modality": "text",
            "source_file": "data/raw/text/silver_support.pdf",
            "section_or_page": "Overview",
            "source_url": "",
            "thumbnail_path": "",
        },
    ]
    faiss_index, chunk_records = build_index_from_documents(documents, embedder)
    faiss_path = tmp_path / "index.faiss"
    metadata_path = tmp_path / "metadata.jsonl"

    persist_index(faiss_index, chunk_records, faiss_path, metadata_path)
    loaded_records = load_metadata(metadata_path)

    assert faiss_path.exists()
    assert len(loaded_records) == len(chunk_records)
    assert loaded_records[0]["chunk_id"] == chunk_records[0]["chunk_id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_build_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.build_index'`

- [ ] **Step 3: Write `ingestion/build_index.py`**

```python
# ingestion/build_index.py
import json
from pathlib import Path

from config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS
from ingestion.chunker import chunk_text
from ingestion.metadata import build_chunk_records
from retrieval.embed import embed_texts
from retrieval.faiss_index import build_faiss_index, save_faiss_index


def build_index_from_documents(documents: list[dict], embedder):
    all_records: list[dict] = []
    for doc in documents:
        chunks = chunk_text(doc["text"], CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS)
        records = build_chunk_records(
            chunks,
            doc_id=doc["doc_id"],
            scheme_name=doc["scheme_name"],
            category=doc["category"],
            modality=doc["modality"],
            source_file=doc["source_file"],
            section_or_page=doc["section_or_page"],
            source_url=doc.get("source_url", ""),
            thumbnail_path=doc.get("thumbnail_path", ""),
        )
        all_records.extend(records)

    vectors = embed_texts([record["text"] for record in all_records], embedder)
    faiss_index = build_faiss_index(vectors)
    return faiss_index, all_records


def persist_index(faiss_index, chunk_records: list[dict], faiss_path: Path, metadata_path: Path) -> None:
    save_faiss_index(faiss_index, faiss_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as handle:
        for record in chunk_records:
            handle.write(json.dumps(record) + "\n")


def load_metadata(metadata_path: Path) -> list[dict]:
    with open(metadata_path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_build_index.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Write the end-to-end CLI entry point (manually exercised, not unit-tested — depends on real files in `data/raw/`)**

```python
# append to ingestion/build_index.py
if __name__ == "__main__":
    import config
    from ingestion.load_images_ocr import extract_image_text
    from ingestion.load_text import clean_text, load_text_file
    from retrieval.embed import get_device, load_embedder

    def _discover_documents() -> list[dict]:
        docs = []
        text_dir = config.DATA_DIR / "raw" / "text"
        for path in text_dir.glob("*"):
            if path.suffix.lower() in (".pdf", ".html", ".htm"):
                docs.append({
                    "text": clean_text(load_text_file(path)),
                    "doc_id": path.stem,
                    "scheme_name": path.stem.replace("-", " ").title(),
                    "category": "Uncategorized",
                    "modality": "text",
                    "source_file": str(path),
                    "section_or_page": "Full document",
                    "source_url": "",
                    "thumbnail_path": "",
                })

        image_dir = config.DATA_DIR / "raw" / "images"
        for path in image_dir.glob("*"):
            docs.append({
                "text": clean_text(extract_image_text(path)),
                "doc_id": path.stem,
                "scheme_name": path.stem.replace("-", " ").title(),
                "category": "Uncategorized",
                "modality": "image",
                "source_file": str(path),
                "section_or_page": "Infographic",
                "source_url": "",
                "thumbnail_path": str(path),
            })
        return [doc for doc in docs if doc["text"].strip()]

    print(f"Using device: {get_device()}")
    embedder = load_embedder(config.EMBEDDING_MODEL)
    documents = _discover_documents()
    print(f"Discovered {len(documents)} documents under data/raw/")

    faiss_index, chunk_records = build_index_from_documents(documents, embedder)
    persist_index(faiss_index, chunk_records, config.FAISS_INDEX_PATH, config.FAISS_METADATA_PATH)
    print(f"Indexed {len(chunk_records)} chunks into {config.FAISS_INDEX_PATH}")
```

- [ ] **Step 6: Commit**

```bash
git add ingestion/build_index.py tests/ingestion/test_build_index.py
git commit -m "feat: add end-to-end ingestion build-index pipeline"
```

---

### Task 18: FastAPI Backend

**Files:**
- Create: `backend/main.py`
- Test: `tests/backend/test_main.py`

**Interfaces:**
- Consumes: `generation.pipeline.{RagIndex, answer_general_question, answer_profile_question}`, `generation.llm_client.LLMClient`, `config.{TOP_K, SIMILARITY_THRESHOLD, RETRIEVAL_MODE}`
- Produces: FastAPI `app` object with dependency-overridable `get_rag_index()` and `get_llm_client()` providers, `POST /api/query`, `POST /api/profile-query`, `GET /api/config`.

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_main.py
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app, get_llm_client, get_rag_index
from generation.pipeline import RagIndex
from retrieval.bm25_index import build_bm25_index
from retrieval.faiss_index import build_faiss_index


class FakeEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


def _fake_rag_index():
    chunk_records = [{
        "chunk_id": "gst-voucher_text_000",
        "scheme_name": "GST Voucher",
        "category": "Household",
        "section_or_page": "FAQ",
        "text": "GST Voucher gives eligible households up to $850 in cash.",
    }]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    return RagIndex(
        faiss_index=build_faiss_index(vectors),
        bm25_index=build_bm25_index([chunk_records[0]["text"]]),
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )


def test_api_query_returns_grounded_answer():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?"})

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert "GST Voucher" in body["answer"]
    assert body["sources"][0]["scheme_name"] == "GST Voucher"
    app.dependency_overrides.clear()


def test_api_profile_query_returns_shortlist():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(
        "Possibly eligible: GST Voucher [GST Voucher, FAQ]."
    )
    client = TestClient(app)

    response = client.post(
        "/api/profile-query",
        json={"profile": {"age": 68, "life_stage_tags": []}, "free_text_question": "GST voucher amount"},
    )

    assert response.status_code == 200
    assert "Possibly eligible" in response.json()["answer"]
    app.dependency_overrides.clear()


def test_api_config_returns_defaults():
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert "top_k" in body
    assert "similarity_threshold" in body
    assert "retrieval_mode" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend'`

- [ ] **Step 3: Write `backend/__init__.py` and `backend/main.py`**

```python
# backend/__init__.py
```

```python
# backend/main.py
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from generation.gemini_client import GeminiClient
from generation.grok_client import GrokClient
from generation.pipeline import RagIndex, answer_general_question, answer_profile_question
from ingestion.build_index import load_metadata
from retrieval.embed import load_embedder
from retrieval.faiss_index import load_faiss_index
from retrieval.bm25_index import build_bm25_index

app = FastAPI(title="SG Citizen Financial Assistant")

_rag_index_cache: RagIndex | None = None


def get_rag_index() -> RagIndex:
    global _rag_index_cache
    if _rag_index_cache is None:
        chunk_records = load_metadata(config.FAISS_METADATA_PATH)
        _rag_index_cache = RagIndex(
            faiss_index=load_faiss_index(config.FAISS_INDEX_PATH),
            bm25_index=build_bm25_index([record["text"] for record in chunk_records]),
            chunk_records=chunk_records,
            embedder=load_embedder(config.EMBEDDING_MODEL),
        )
    return _rag_index_cache


def get_llm_client():
    if config.LLM_PROVIDER == "grok":
        return GrokClient(api_key=config.GROK_API_KEY, model_name=config.GROK_MODEL)
    return GeminiClient(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL)


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None
    similarity_threshold: float | None = None
    retrieval_mode: str | None = None


class ProfileQueryRequest(BaseModel):
    profile: dict
    free_text_question: str = ""
    top_k: int | None = None
    similarity_threshold: float | None = None
    retrieval_mode: str | None = None


@app.post("/api/query")
def query(
    request: QueryRequest,
    rag_index: RagIndex = Depends(get_rag_index),
    llm_client=Depends(get_llm_client),
):
    return answer_general_question(
        request.question,
        rag_index,
        llm_client,
        top_k=request.top_k or config.TOP_K,
        similarity_threshold=request.similarity_threshold or config.SIMILARITY_THRESHOLD,
        retrieval_mode=request.retrieval_mode or config.RETRIEVAL_MODE,
    )


@app.post("/api/profile-query")
def profile_query(
    request: ProfileQueryRequest,
    rag_index: RagIndex = Depends(get_rag_index),
    llm_client=Depends(get_llm_client),
):
    return answer_profile_question(
        request.profile,
        rag_index,
        llm_client,
        free_text_question=request.free_text_question,
        top_k=request.top_k or config.TOP_K,
        similarity_threshold=request.similarity_threshold or config.SIMILARITY_THRESHOLD,
        retrieval_mode=request.retrieval_mode or config.RETRIEVAL_MODE,
    )


@app.get("/api/config")
def get_config():
    return {
        "top_k": config.TOP_K,
        "similarity_threshold": config.SIMILARITY_THRESHOLD,
        "retrieval_mode": config.RETRIEVAL_MODE,
        "llm_provider": config.LLM_PROVIDER,
    }


_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_main.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/__init__.py backend/main.py tests/backend/test_main.py
git commit -m "feat: add FastAPI backend exposing the RAG pipeline"
```

---

### Task 19: Gradio Fallback App

**Files:**
- Create: `backend/gradio_app.py`

**Interfaces:**
- Consumes: `backend.main.{get_rag_index, get_llm_client}`, `generation.pipeline.{answer_general_question, answer_profile_question}`, `config.{TOP_K, SIMILARITY_THRESHOLD, RETRIEVAL_MODE}`
- Produces: a runnable script (`python backend/gradio_app.py`) that launches a minimal `gr.Blocks` demo. This is a manually-verified demo artifact, not unit tested (it wraps already-tested pipeline functions with no new logic of its own).

- [ ] **Step 1: Write `backend/gradio_app.py`**

```python
# backend/gradio_app.py
import gradio as gr

import config
from backend.main import get_llm_client, get_rag_index
from generation.pipeline import answer_general_question, answer_profile_question


def general_qa(question: str) -> str:
    rag_index = get_rag_index()
    llm_client = get_llm_client()
    result = answer_general_question(
        question,
        rag_index,
        llm_client,
        top_k=config.TOP_K,
        similarity_threshold=config.SIMILARITY_THRESHOLD,
        retrieval_mode=config.RETRIEVAL_MODE,
    )
    sources = "\n".join(f"- {s['scheme_name']} ({s['section_or_page']})" for s in result["sources"])
    return f"{result['answer']}\n\nSources:\n{sources}"


def profile_shortlist(citizenship, age, income_band, housing, employment, free_text) -> str:
    rag_index = get_rag_index()
    llm_client = get_llm_client()
    profile = {
        "citizenship": citizenship,
        "age": age,
        "monthly_income_band": income_band,
        "housing": housing,
        "employment": employment,
        "life_stage_tags": [],
    }
    result = answer_profile_question(
        profile,
        rag_index,
        llm_client,
        free_text_question=free_text,
        top_k=config.TOP_K,
        similarity_threshold=config.SIMILARITY_THRESHOLD,
        retrieval_mode=config.RETRIEVAL_MODE,
    )
    sources = "\n".join(f"- {s['scheme_name']} ({s['section_or_page']})" for s in result["sources"])
    return f"{result['answer']}\n\nSources:\n{sources}"


with gr.Blocks(title="SG Citizen Financial Assistant (fallback)") as demo:
    gr.Markdown("# SG Citizen Financial Assistant — fallback demo UI")
    with gr.Tab("General Q&A"):
        question_box = gr.Textbox(label="Question")
        qa_output = gr.Textbox(label="Answer", lines=8)
        gr.Button("Ask").click(general_qa, inputs=question_box, outputs=qa_output)
    with gr.Tab("Personal Profile"):
        citizenship = gr.Dropdown(["Singapore Citizen", "PR", "Other"], label="Citizenship")
        age = gr.Number(label="Age")
        income_band = gr.Dropdown(["<$1.5k", "$1.5-3k", "$3-6k", ">$6k", "Prefer not to say"], label="Income band")
        housing = gr.Dropdown(["HDB", "Private", "Rental", "Other", "Prefer not to say"], label="Housing")
        employment = gr.Dropdown(["Employed", "Self-employed", "Unemployed", "Retired", "Student"], label="Employment")
        free_text = gr.Textbox(label="Optional question")
        profile_output = gr.Textbox(label="Shortlist", lines=10)
        gr.Button("Get shortlist").click(
            profile_shortlist,
            inputs=[citizenship, age, income_band, housing, employment, free_text],
            outputs=profile_output,
        )

if __name__ == "__main__":
    demo.launch()
```

- [ ] **Step 2: Manually verify it launches (after Task 17's ingestion has produced a real index)**

Run: `python backend/gradio_app.py`
Expected: Terminal prints a local URL (e.g. `http://127.0.0.1:7860`); opening it shows both tabs and a working "Ask" button once a FAISS index exists at `config.FAISS_INDEX_PATH`.

- [ ] **Step 3: Commit**

```bash
git add backend/gradio_app.py
git commit -m "feat: add minimal Gradio fallback UI for demo-day risk reduction"
```

---

### Task 20: Frontend (Custom Static UI)

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/style.css`
- Create: `frontend/app.js`

**Interfaces:**
- Consumes: `POST /api/query`, `POST /api/profile-query`, `GET /api/config` (from Task 18)
- Produces: a static site served by `backend/main.py`'s `StaticFiles` mount. Manually verified in-browser (UI behavior, not unit-testable business logic).

- [ ] **Step 1: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SG Citizen Financial Assistant</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="app-header">
    <h1>SG Citizen Financial Assistant</h1>
    <div class="mode-toggle" role="tablist">
      <button class="mode-btn active" data-mode="general" role="tab">General Q&amp;A</button>
      <button class="mode-btn" data-mode="profile" role="tab">Personal Eligibility Shortlist</button>
    </div>
  </header>

  <main class="layout">
    <section class="input-panel">
      <div id="general-panel" class="mode-panel">
        <label for="question-input">Ask a question about subsidies or tax reliefs</label>
        <textarea id="question-input" rows="3" placeholder="e.g. How much CDC Voucher will a household get?"></textarea>
        <button id="ask-button" class="primary-btn">Ask</button>
      </div>

      <div id="profile-panel" class="mode-panel hidden">
        <label>Citizenship
          <select id="profile-citizenship">
            <option>Singapore Citizen</option>
            <option>PR</option>
            <option>Other</option>
          </select>
        </label>
        <label>Age <input id="profile-age" type="number" min="0" max="120" /></label>
        <label>Household size <input id="profile-household-size" type="number" min="1" max="20" /></label>
        <label>Monthly income band
          <select id="profile-income-band">
            <option>&lt;$1.5k</option>
            <option>$1.5-3k</option>
            <option>$3-6k</option>
            <option>&gt;$6k</option>
            <option>Prefer not to say</option>
          </select>
        </label>
        <label>Housing
          <select id="profile-housing">
            <option>HDB</option>
            <option>Private</option>
            <option>Rental</option>
            <option>Other</option>
            <option>Prefer not to say</option>
          </select>
        </label>
        <label>Employment
          <select id="profile-employment">
            <option>Employed</option>
            <option>Self-employed</option>
            <option>Unemployed</option>
            <option>Retired</option>
            <option>Student</option>
          </select>
        </label>
        <fieldset class="tags">
          <legend>Life stage</legend>
          <label><input type="checkbox" value="Has young child(ren)" class="life-stage-tag" /> Has young child(ren)</label>
          <label><input type="checkbox" value="Caregiver" class="life-stage-tag" /> Caregiver</label>
          <label><input type="checkbox" value="Senior (65+)" class="life-stage-tag" /> Senior (65+)</label>
          <label><input type="checkbox" value="PWD in household" class="life-stage-tag" /> PWD in household</label>
        </fieldset>
        <label for="profile-question">Optional question</label>
        <textarea id="profile-question" rows="2" placeholder="Leave blank for a general shortlist"></textarea>
        <button id="profile-button" class="primary-btn">Get shortlist</button>
      </div>

      <details class="advanced-panel">
        <summary>Advanced (demo controls)</summary>
        <label>Top K <input id="control-top-k" type="number" min="1" max="20" value="5" /></label>
        <label>Similarity threshold <input id="control-threshold" type="number" step="0.05" min="0" max="1" value="0.35" /></label>
        <label>Retrieval mode
          <select id="control-mode">
            <option value="dense">Dense (baseline)</option>
            <option value="hybrid">Hybrid (improved)</option>
          </select>
        </label>
      </details>
    </section>

    <section class="answer-panel">
      <div id="answer-abstained-badge" class="abstained-badge hidden">Not enough evidence</div>
      <div id="answer-text" class="answer-text" aria-live="polite"></div>
      <h2>Sources</h2>
      <ul id="sources-list" class="sources-list"></ul>
    </section>
  </main>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `frontend/style.css`**

```css
:root {
  --sg-red: #b0242a;
  --ink: #1c2733;
  --muted: #5b6b7a;
  --bg: #f6f7f9;
  --panel-bg: #ffffff;
  --border: #d8dee5;
  --possibly: #1a7f4e;
  --unclear: #a3660c;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--ink);
}

.app-header {
  background: var(--sg-red);
  color: white;
  padding: 1rem 1.5rem;
}

.app-header h1 {
  margin: 0 0 0.75rem 0;
  font-size: 1.25rem;
}

.mode-toggle {
  display: flex;
  gap: 0.5rem;
}

.mode-btn {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  padding: 0.4rem 1rem;
  cursor: pointer;
}

.mode-btn.active {
  background: white;
  color: var(--sg-red);
  font-weight: 600;
}

.layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  padding: 1rem;
  max-width: 1100px;
  margin: 0 auto;
}

@media (min-width: 900px) {
  .layout {
    grid-template-columns: minmax(320px, 1fr) minmax(320px, 1.2fr);
  }
}

.input-panel, .answer-panel {
  background: var(--panel-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
}

.mode-panel.hidden { display: none; }

.mode-panel label {
  display: block;
  margin: 0.75rem 0 0.25rem;
  font-weight: 600;
  font-size: 0.9rem;
}

textarea, select, input[type="number"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  font: inherit;
}

.tags {
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-top: 0.75rem;
  padding: 0.5rem 0.75rem;
}

.tags label {
  font-weight: 400;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.primary-btn {
  margin-top: 1rem;
  background: var(--sg-red);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.6rem 1.2rem;
  font-weight: 600;
  cursor: pointer;
}

.advanced-panel {
  margin-top: 1.25rem;
  border-top: 1px dashed var(--border);
  padding-top: 0.75rem;
  color: var(--muted);
  font-size: 0.85rem;
}

.answer-text {
  white-space: pre-wrap;
  line-height: 1.5;
}

.abstained-badge {
  display: inline-block;
  background: #fdecea;
  color: var(--sg-red);
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
}

.abstained-badge.hidden { display: none; }

.sources-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
}

.sources-list li {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
  margin-bottom: 0.5rem;
}

.sources-list .scheme-name {
  font-weight: 700;
}

.sources-list .section {
  color: var(--muted);
  font-size: 0.85rem;
}
```

- [ ] **Step 3: Write `frontend/app.js`**

```javascript
const state = { mode: "general" };

const generalPanel = document.getElementById("general-panel");
const profilePanel = document.getElementById("profile-panel");
const modeButtons = document.querySelectorAll(".mode-btn");

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    modeButtons.forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    state.mode = button.dataset.mode;
    generalPanel.classList.toggle("hidden", state.mode !== "general");
    profilePanel.classList.toggle("hidden", state.mode !== "profile");
  });
});

function readControls() {
  return {
    top_k: parseInt(document.getElementById("control-top-k").value, 10),
    similarity_threshold: parseFloat(document.getElementById("control-threshold").value),
    retrieval_mode: document.getElementById("control-mode").value,
  };
}

function renderResult(result) {
  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);

  document.getElementById("answer-text").textContent = result.answer;

  const list = document.getElementById("sources-list");
  list.innerHTML = "";
  (result.sources || []).forEach((source) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="scheme-name">${source.scheme_name}</div>
      <div class="section">${source.section_or_page}</div>
      <div class="excerpt">${source.text}</div>
    `;
    list.appendChild(item);
  });
}

document.getElementById("ask-button").addEventListener("click", async () => {
  const question = document.getElementById("question-input").value.trim();
  if (!question) return;

  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, ...readControls() }),
  });
  renderResult(await response.json());
});

document.getElementById("profile-button").addEventListener("click", async () => {
  const tags = Array.from(document.querySelectorAll(".life-stage-tag:checked")).map((el) => el.value);
  const profile = {
    citizenship: document.getElementById("profile-citizenship").value,
    age: parseInt(document.getElementById("profile-age").value, 10) || null,
    household_size: parseInt(document.getElementById("profile-household-size").value, 10) || null,
    monthly_income_band: document.getElementById("profile-income-band").value,
    housing: document.getElementById("profile-housing").value,
    employment: document.getElementById("profile-employment").value,
    life_stage_tags: tags,
  };
  const free_text_question = document.getElementById("profile-question").value.trim();

  const response = await fetch("/api/profile-query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, free_text_question, ...readControls() }),
  });
  renderResult(await response.json());
});
```

- [ ] **Step 4: Manually verify in-browser**

Run: `uvicorn backend.main:app --reload` then open `http://127.0.0.1:8000/`
Expected: page loads, mode toggle switches panels, "Ask" and "Get shortlist" call the API and render an answer + sources list (once a real FAISS index exists from Task 17's ingestion run).

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/style.css frontend/app.js
git commit -m "feat: add custom static frontend for General Q&A and Personal Profile modes"
```

---

### Task 21: Evaluation Metrics

**Files:**
- Create: `evaluation/metrics.py`
- Test: `tests/evaluation/test_metrics.py`

**Interfaces:**
- Produces: `hit_rate(retrieved_ids: list[str], relevant_ids: set[str]) -> float` (0 or 1 for a single question), `recall_at_k(retrieved_ids: list[str], relevant_ids: set[str]) -> float`, `reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float`, `mean_of(values: list[float]) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# tests/evaluation/test_metrics.py
from evaluation.metrics import hit_rate, mean_of, reciprocal_rank, recall_at_k


def test_hit_rate_true_when_any_relevant_chunk_retrieved():
    assert hit_rate(["a", "b", "c"], {"c", "z"}) == 1.0


def test_hit_rate_false_when_no_relevant_chunk_retrieved():
    assert hit_rate(["a", "b"], {"z"}) == 0.0


def test_recall_at_k_computes_fraction_of_relevant_found():
    assert recall_at_k(["a", "b"], {"a", "b", "c"}) == pytest_approx(2 / 3)


def pytest_approx(value):
    return value  # simple helper since exact fractions are used in these fixtures


def test_reciprocal_rank_rewards_earlier_rank():
    assert reciprocal_rank(["z", "a"], {"a"}) == 0.5
    assert reciprocal_rank(["a", "z"], {"a"}) == 1.0
    assert reciprocal_rank(["z", "y"], {"a"}) == 0.0


def test_mean_of_averages_a_list():
    assert mean_of([1.0, 0.0, 1.0]) == pytest_approx(2 / 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/evaluation/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evaluation'`

- [ ] **Step 3: Write `evaluation/__init__.py` and `evaluation/metrics.py`**

```python
# evaluation/__init__.py
```

```python
# evaluation/metrics.py
def hit_rate(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    return 1.0 if any(rid in relevant_ids for rid in retrieved_ids) else 0.0


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    if not relevant_ids:
        raise ValueError("relevant_ids must not be empty")
    found = sum(1 for rid in relevant_ids if rid in retrieved_ids)
    return found / len(relevant_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_of(values: list[float]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/evaluation/test_metrics.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add evaluation/__init__.py evaluation/metrics.py tests/evaluation/test_metrics.py
git commit -m "feat: add retrieval evaluation metrics (hit rate, recall@k, MRR)"
```

---

### Task 22: Evaluation Test Set

**Files:**
- Create: `evaluation/test_set.json`

**Interfaces:**
- Produces: a JSON array of question objects, each with keys `id`, `category` (one of `factual`, `paraphrase`, `multi_document`, `unanswerable`, `ambiguous`, `profile`), `question` (or `profile` object for profile-category entries), `expected_answer_criteria`, `expected_source_doc_ids: list[str]`, `expected_relevant_chunk_ids: list[str]` (filled in with real `chunk_id`s once Task 17's ingestion has run against the team's actual collected documents — see note below).

- [ ] **Step 1: Write `evaluation/test_set.json`**

```json
[
  {
    "id": "F1",
    "category": "factual",
    "question": "How much does each eligible Singaporean household get from CDC Vouchers, and where can they be spent?",
    "expected_answer_criteria": "States the voucher value per household and that they can be spent at participating hawkers/heartland merchants/supermarkets.",
    "expected_source_doc_ids": ["cdc-vouchers"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "F2",
    "category": "factual",
    "question": "What is the maximum claimable cap for total personal income tax reliefs?",
    "expected_answer_criteria": "States the $80,000 overall personal income tax relief cap.",
    "expected_source_doc_ids": ["iras-tax-reliefs"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "F3",
    "category": "factual",
    "question": "What is the Silver Support Scheme payout frequency?",
    "expected_answer_criteria": "States that payouts are quarterly, and mentions the eligibility tiers by Assessable Income/AV/household support.",
    "expected_source_doc_ids": ["silver-support"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "P1",
    "category": "paraphrase",
    "question": "My mother lives with me and has no job. Can I reduce my tax bill because of her?",
    "expected_answer_criteria": "Identifies Parent Relief as the relevant relief and states its qualifying conditions (e.g. income/age of dependent, cohabitation).",
    "expected_source_doc_ids": ["iras-tax-reliefs"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "P2",
    "category": "paraphrase",
    "question": "I'm a working mum with a young kid — is there a tax break for that?",
    "expected_answer_criteria": "Identifies Working Mother's Child Relief (WMCR) and its qualifying conditions.",
    "expected_source_doc_ids": ["iras-tax-reliefs"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "P3",
    "category": "paraphrase",
    "question": "I put extra money into my CPF for retirement — do I get anything back on tax?",
    "expected_answer_criteria": "Identifies CPF top-up / SRS-related relief and its qualifying conditions.",
    "expected_source_doc_ids": ["iras-tax-reliefs", "cpf-matched-retirement-savings"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "M1",
    "category": "multi_document",
    "question": "What financial support (cash payouts and tax savings) can a working mother with a young child get from the government?",
    "expected_answer_criteria": "Combines Assurance Package/GST Voucher cash payouts with Working Mother's Child Relief and Child Relief, citing both a Govbenefits-style scheme doc and the IRAS reliefs doc.",
    "expected_source_doc_ids": ["gst-voucher", "iras-tax-reliefs"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "M2",
    "category": "multi_document",
    "question": "What can a low-income retired senior living in a rental flat get from the government?",
    "expected_answer_criteria": "Combines Silver Support Scheme and ComCare Assistance, citing both scheme docs.",
    "expected_source_doc_ids": ["silver-support", "comcare-assistance"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "U1",
    "category": "unanswerable",
    "question": "Can I use my CDC vouchers to pay for my IRAS income tax bill?",
    "expected_answer_criteria": "Must trigger the exact fallback: \"The available knowledge base does not contain enough information to answer this question.\"",
    "expected_source_doc_ids": [],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "U2",
    "category": "unanswerable",
    "question": "Can I claim tax relief for taking care of my pet dog?",
    "expected_answer_criteria": "Must trigger the exact fallback: \"The available knowledge base does not contain enough information to answer this question.\"",
    "expected_source_doc_ids": [],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "A1",
    "category": "ambiguous",
    "question": "How much money will I get from the government this year?",
    "expected_answer_criteria": "Should not fabricate a single number; should ask for or note the missing inputs it needs (age, income, property AV, citizenship) before giving a number, or abstain/qualify heavily.",
    "expected_source_doc_ids": [],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "A2",
    "category": "ambiguous",
    "question": "Am I eligible for Workfare?",
    "expected_answer_criteria": "Should note that eligibility depends on age, income, and employment type, and not assert a definite yes/no without those inputs.",
    "expected_source_doc_ids": ["workfare-income-supplement"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "PR1",
    "category": "profile",
    "profile": {
      "citizenship": "Singapore Citizen",
      "age": 68,
      "monthly_income_band": "<$1.5k",
      "housing": "HDB",
      "employment": "Retired",
      "life_stage_tags": ["Senior (65+)"]
    },
    "expected_answer_criteria": "Shortlist should surface Silver Support and cost-of-living schemes as 'Possibly eligible', citing amounts only if stated in evidence.",
    "expected_source_doc_ids": ["silver-support", "gst-voucher"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "PR2",
    "category": "profile",
    "profile": {
      "citizenship": "Singapore Citizen",
      "age": 32,
      "monthly_income_band": "$3-6k",
      "housing": "HDB",
      "employment": "Employed",
      "life_stage_tags": ["Has young child(ren)"]
    },
    "expected_answer_criteria": "Shortlist should surface Baby Bonus / family-oriented schemes as 'Possibly eligible' and not assert senior schemes as eligible.",
    "expected_source_doc_ids": ["baby-bonus-scheme"],
    "expected_relevant_chunk_ids": []
  },
  {
    "id": "PR3",
    "category": "profile",
    "profile": {
      "citizenship": "PR",
      "age": 40,
      "monthly_income_band": "Prefer not to say",
      "housing": "Private",
      "employment": "Employed",
      "life_stage_tags": []
    },
    "expected_answer_criteria": "Heavy 'Likely not eligible / unclear' due to PR status and undisclosed income on citizen-only/income-gated schemes.",
    "expected_source_doc_ids": [],
    "expected_relevant_chunk_ids": []
  }
]
```

> **Note for the Data & Ingestion owner:** `expected_source_doc_ids` above use placeholder `doc_id`s matching the scheme list in the approved spec (§6.1). Once real documents are ingested (Task 17), open each question, run it through `evaluation/run_eval.py` (Task 23), inspect the actual retrieved `chunk_id`s, and fill in `expected_relevant_chunk_ids` by hand-labeling which of the retrieved (or known-correct) chunks are truly relevant — this hand-labeling step is inherent to the brief's evaluation methodology and cannot be automated.

- [ ] **Step 2: Commit**

```bash
git add evaluation/test_set.json
git commit -m "feat: add 15-question evaluation test set covering all required categories"
```

---

### Task 23: Evaluation Runner + Baseline-vs-Hybrid Comparison

**Files:**
- Create: `evaluation/run_eval.py`
- Test: `tests/evaluation/test_run_eval.py`

**Interfaces:**
- Consumes: `evaluation.metrics.{hit_rate, recall_at_k, reciprocal_rank, mean_of}`, `generation.pipeline.{RagIndex, answer_general_question, answer_profile_question}`
- Produces: `run_single_question(question_entry: dict, rag_index: RagIndex, llm_client, *, retrieval_mode: str, top_k: int, similarity_threshold: float) -> dict` (returns a per-question log row: `id, category, retrieved_chunk_ids, generated_answer, abstained`); `compute_aggregate_metrics(rows: list[dict], test_set: list[dict]) -> dict` (returns `{"hit_rate": float, "recall_at_k": float, "mrr": float}` over questions that have non-empty `expected_relevant_chunk_ids`); `run_comparison(test_set: list[dict], rag_index: RagIndex, llm_client) -> dict` (returns `{"dense": {...}, "hybrid": {...}}`, each containing `rows` and aggregate metrics).

- [ ] **Step 1: Write the failing test**

```python
# tests/evaluation/test_run_eval.py
import numpy as np

from evaluation.run_eval import compute_aggregate_metrics, run_comparison, run_single_question
from generation.pipeline import RagIndex
from retrieval.bm25_index import build_bm25_index
from retrieval.faiss_index import build_faiss_index


class FakeEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


class FakeLLMClient:
    def generate(self, prompt: str) -> str:
        return "You may get up to $850 [GST Voucher, FAQ]."


def _rag_index():
    chunk_records = [{
        "chunk_id": "gst-voucher_text_000",
        "scheme_name": "GST Voucher",
        "category": "Household",
        "section_or_page": "FAQ",
        "text": "GST Voucher gives eligible households up to $850 in cash.",
    }]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    return RagIndex(
        faiss_index=build_faiss_index(vectors),
        bm25_index=build_bm25_index([chunk_records[0]["text"]]),
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )


def test_run_single_question_returns_log_row():
    question_entry = {"id": "F1", "category": "factual", "question": "GST voucher amount"}
    row = run_single_question(
        question_entry, _rag_index(), FakeLLMClient(),
        retrieval_mode="dense", top_k=3, similarity_threshold=0.3,
    )
    assert row["id"] == "F1"
    assert row["retrieved_chunk_ids"] == ["gst-voucher_text_000"]
    assert row["abstained"] is False


def test_compute_aggregate_metrics_skips_questions_without_labels():
    rows = [{"id": "F1", "retrieved_chunk_ids": ["gst-voucher_text_000"]}]
    test_set = [{"id": "F1", "expected_relevant_chunk_ids": ["gst-voucher_text_000"]}]

    metrics = compute_aggregate_metrics(rows, test_set)

    assert metrics["hit_rate"] == 1.0
    assert metrics["recall_at_k"] == 1.0
    assert metrics["mrr"] == 1.0


def test_run_comparison_runs_both_retrieval_modes():
    test_set = [{"id": "F1", "category": "factual", "question": "GST voucher amount", "expected_relevant_chunk_ids": ["gst-voucher_text_000"]}]

    comparison = run_comparison(test_set, _rag_index(), FakeLLMClient())

    assert set(comparison.keys()) == {"dense", "hybrid"}
    assert comparison["dense"]["metrics"]["hit_rate"] == 1.0
    assert comparison["hybrid"]["metrics"]["hit_rate"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/evaluation/test_run_eval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evaluation.run_eval'`

- [ ] **Step 3: Write `evaluation/run_eval.py`**

```python
# evaluation/run_eval.py
import json
from pathlib import Path

from evaluation.metrics import hit_rate, mean_of, reciprocal_rank, recall_at_k
from generation.pipeline import RagIndex, answer_general_question, answer_profile_question


def run_single_question(
    question_entry: dict,
    rag_index: RagIndex,
    llm_client,
    *,
    retrieval_mode: str,
    top_k: int,
    similarity_threshold: float,
) -> dict:
    if question_entry["category"] == "profile":
        result = answer_profile_question(
            question_entry["profile"],
            rag_index,
            llm_client,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            retrieval_mode=retrieval_mode,
        )
    else:
        result = answer_general_question(
            question_entry["question"],
            rag_index,
            llm_client,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            retrieval_mode=retrieval_mode,
        )

    return {
        "id": question_entry["id"],
        "category": question_entry["category"],
        "retrieved_chunk_ids": [source["chunk_id"] for source in result["sources"]],
        "generated_answer": result["answer"],
        "abstained": result["abstained"],
    }


def compute_aggregate_metrics(rows: list[dict], test_set: list[dict]) -> dict:
    labeled_by_id = {
        entry["id"]: set(entry["expected_relevant_chunk_ids"])
        for entry in test_set
        if entry.get("expected_relevant_chunk_ids")
    }
    rows_by_id = {row["id"]: row for row in rows}

    hit_rates, recalls, rr_values = [], [], []
    for question_id, relevant_ids in labeled_by_id.items():
        retrieved_ids = rows_by_id[question_id]["retrieved_chunk_ids"]
        hit_rates.append(hit_rate(retrieved_ids, relevant_ids))
        recalls.append(recall_at_k(retrieved_ids, relevant_ids))
        rr_values.append(reciprocal_rank(retrieved_ids, relevant_ids))

    if not hit_rates:
        return {"hit_rate": None, "recall_at_k": None, "mrr": None}

    return {
        "hit_rate": mean_of(hit_rates),
        "recall_at_k": mean_of(recalls),
        "mrr": mean_of(rr_values),
    }


def run_comparison(test_set: list[dict], rag_index: RagIndex, llm_client, *, top_k: int = 5, similarity_threshold: float = 0.35) -> dict:
    comparison = {}
    for mode in ("dense", "hybrid"):
        rows = [
            run_single_question(
                entry, rag_index, llm_client,
                retrieval_mode=mode, top_k=top_k, similarity_threshold=similarity_threshold,
            )
            for entry in test_set
        ]
        comparison[mode] = {"rows": rows, "metrics": compute_aggregate_metrics(rows, test_set)}
    return comparison


def save_comparison(comparison: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for mode, payload in comparison.items():
        with open(output_dir / f"{mode}_results.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/evaluation/test_run_eval.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the CLI entry point (manually exercised against the real index and API key)**

```python
# append to evaluation/run_eval.py
if __name__ == "__main__":
    import config
    from backend.main import get_llm_client, get_rag_index

    with open(Path(__file__).parent / "test_set.json", encoding="utf-8") as handle:
        test_set = json.load(handle)

    rag_index = get_rag_index()
    llm_client = get_llm_client()
    comparison = run_comparison(test_set, rag_index, llm_client, top_k=config.TOP_K, similarity_threshold=config.SIMILARITY_THRESHOLD)
    save_comparison(comparison, Path(__file__).parent / "results")

    for mode, payload in comparison.items():
        print(f"{mode}: {payload['metrics']}")
```

- [ ] **Step 6: Commit**

```bash
git add evaluation/run_eval.py tests/evaluation/test_run_eval.py
git commit -m "feat: add evaluation runner with baseline-vs-hybrid comparison"
```

---

### Task 24: Colab Demo Notebook

**Files:**
- Create: `notebooks/colab_demo.ipynb`

**Interfaces:**
- Consumes: the published GitHub repo URL (team fills in after first push), `backend/main.py`, `frontend/`
- Produces: a notebook that clones the repo, installs dependencies, and launches the backend with a public tunnel. Manually verified by running it in Colab; not unit tested (infrastructure glue, no new logic).

- [ ] **Step 1: Write `notebooks/colab_demo.ipynb`**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": ["# SG Citizen Financial Assistant \u2014 Colab Demo\n", "Clones the repo, installs dependencies, and runs the FastAPI backend + static frontend with a public tunnel for live demos.\n", "The FAISS index must already exist under `data/faiss/` in the repo (built locally beforehand, per Task 17) \u2014 this notebook does not re-run ingestion."]
  },
  {
   "cell_type": "code",
   "metadata": {},
   "source": ["!git clone https://github.com/YOUR_ORG/sg-citizen-financial-assistant.git\n", "%cd sg-citizen-financial-assistant\n", "!pip install -q -r requirements.txt pyngrok"],
   "execution_count": null,
   "outputs": []
  },
  {
   "cell_type": "code",
   "metadata": {},
   "source": ["from google.colab import userdata\n", "import os\n", "os.environ['GEMINI_API_KEY'] = userdata.get('GEMINI_API_KEY')\n", "os.environ['GROK_API_KEY'] = userdata.get('GROK_API_KEY') if userdata.get('GROK_API_KEY') else ''\n", "os.environ['LLM_PROVIDER'] = 'gemini'"],
   "execution_count": null,
   "outputs": []
  },
  {
   "cell_type": "code",
   "metadata": {},
   "source": ["import subprocess\n", "from pyngrok import ngrok\n", "\n", "server = subprocess.Popen(['uvicorn', 'backend.main:app', '--host', '0.0.0.0', '--port', '8000'])\n", "public_url = ngrok.connect(8000)\n", "print('Public demo URL:', public_url)"],
   "execution_count": null,
   "outputs": []
  },
  {
   "cell_type": "code",
   "metadata": {},
   "source": ["# Run at the end of the demo to stop the server and tunnel\n", "server.terminate()\n", "ngrok.disconnect(public_url)"],
   "execution_count": null,
   "outputs": []
  }
 ],
 "metadata": {
  "kernelspec": {"display_name": "Python 3", "name": "python3"},
  "language_info": {"name": "python"}
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/colab_demo.ipynb
git commit -m "docs: add thin Colab demo notebook for optional public sharing"
```

---

### Task 25: README Finalization

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Expand `README.md` with run instructions**

```markdown
# SG Citizen Financial Assistant

Local multi-modal RAG assistant for Singapore government subsidy schemes and tax reliefs.
Full design: `docs/superpowers/specs/2026-07-28-local-rag-implementation-design.md`.
Implementation plan: `docs/superpowers/plans/2026-07-28-sg-citizen-financial-assistant.md`.

## Setup
1. `python -m venv .venv && .venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
2. `pip install -r requirements.txt`
3. Install Tesseract OCR separately (e.g. `winget install UB-Mannheim.TesseractOCR` on Windows) and ensure it's on PATH.
4. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and/or `GROK_API_KEY`.
5. Run `pytest` to verify the environment.

## Ingesting the knowledge base
1. Drop official scheme PDFs/HTML into `data/raw/text/`, infographic images into `data/raw/images/`, and videos into `data/raw/video/` \u2014 or list URLs in `data/sources.yaml` and run `python -m ingestion.fetch_sources`.
2. Run `python -m ingestion.build_index` to chunk, embed, and persist the FAISS index + metadata under `data/faiss/`.

## Running the app
- Custom UI: `uvicorn backend.main:app --reload`, then open `http://127.0.0.1:8000/`.
- Fallback UI: `python backend/gradio_app.py`.

## Running evaluation
`python -m evaluation.run_eval` \u2014 replays `evaluation/test_set.json` through both dense and hybrid retrieval, writing results to `evaluation/results/`.

## GPU
Embedding and OCR auto-detect a local CUDA GPU if available and fall back to CPU otherwise \u2014 no configuration needed. The FAISS index built on one machine is portable to any other (e.g. Colab's T4) since the embedding model is fixed.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: finalize README with setup, ingestion, run, and eval instructions"
```

---

## Self-Review Notes

- **Spec coverage:** §1 (device auto-detect + portable index) → Task 8; §3 (ingestion, all 3 modalities + fetch module) → Tasks 2–7, 17; §4 (retrieval: embedding, FAISS, BM25, hybrid, profile re-rank) → Tasks 8–12; §5 (pluggable LLM, abstention, prompts, citation validation) → Tasks 13–16; §6 (FastAPI + custom frontend + Gradio fallback + UI brief) → Tasks 18–20; §7 (evaluation: metrics, test set, baseline-vs-hybrid) → Tasks 21–23; §8 (repo layout, persistence) → all tasks collectively, verified against the file tree above; notebook → Task 24.
- **Type consistency checked:** `RagIndex` (Task 16) is constructed identically in Tasks 18, 19, 23 tests (`faiss_index`, `bm25_index`, `chunk_records`, `embedder`); `chunk_id` format `f"{doc_id}_{modality}_{chunk_index:03d}"` (Task 3) is what Task 17's `load_metadata`/`persist_index` and Task 23's `retrieved_chunk_ids` all rely on unchanged; `LLMClient.generate(prompt: str) -> str` signature (Task 13) is what Tasks 14, 16, 18, 19, 23 all call identically.
- **No placeholders:** all code blocks are complete and runnable; the one deliberately-deferred value (`expected_relevant_chunk_ids` in Task 22's test set) is flagged with an explicit note explaining why it's blocked on the team's real document collection (an external dependency, not a plan gap) and exactly how to fill it in once unblocked.
