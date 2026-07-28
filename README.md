# SG Citizen Financial Assistant

Local multi-modal RAG assistant for Singapore government subsidy schemes and tax reliefs.
See `docs/superpowers/specs/2026-07-28-local-rag-implementation-design.md` for the full design.

## Setup
1. `python -m venv .venv && .venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
2. `pip install -r requirements.txt`
3. Install Tesseract OCR separately (e.g. `winget install UB-Mannheim.TesseractOCR` on Windows) and ensure it's on PATH.
4. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and/or `GROK_API_KEY`.
5. Run `pytest` to verify the environment.
