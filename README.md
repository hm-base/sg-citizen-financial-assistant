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
