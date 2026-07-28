# SG Citizen Financial Assistant

Local multi-modal RAG assistant for Singapore government subsidy schemes and tax reliefs.
See `docs/superpowers/specs/2026-07-28-local-rag-implementation-design.md` for the full design.

## Setup
1. Install [uv](https://docs.astral.sh/uv/) if you don't have it.
2. `uv venv .venv` to create the virtual environment.
3. `uv pip install -r requirements.txt --python .venv` (add `--system-certs` if you're behind a network that intercepts TLS, e.g. a corporate proxy).
4. Install Tesseract OCR separately (e.g. `winget install UB-Mannheim.TesseractOCR` on Windows) and ensure it's on PATH.
5. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and/or `GROK_API_KEY`.
6. Run `.venv\Scripts\pytest` (Windows) or `.venv/bin/pytest` (Unix) to verify the environment.

## Ingesting the Knowledge Base
1. Drop official scheme PDFs/HTML into `data/raw/text/`, infographic images into `data/raw/images/`, and videos into `data/raw/video/`; or list URLs in `data/sources.yaml` and run `python -m ingestion.fetch_sources`.
2. Run `python -m ingestion.build_index` to chunk, embed, and persist the FAISS index + metadata under `data/faiss/`.

## Running the App
- Custom UI: `uvicorn backend.main:app --reload`, then open `http://127.0.0.1:8000/`.
- Fallback UI: `python backend/gradio_app.py`.

## Running Evaluation
`python -m evaluation.run_eval` — replays `evaluation/test_set.json` through both dense and hybrid retrieval, writing results to `evaluation/results/`.

## GPU
Embedding and OCR auto-detect a local CUDA GPU if available and fall back to CPU otherwise — no configuration needed. The FAISS index built on one machine is portable to any other (e.g. Colab's T4) since the embedding model is fixed.
