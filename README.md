# SG Citizen Financial Assistant

Local multi-modal RAG assistant for Singapore government subsidy schemes and tax reliefs.
See `docs/superpowers/specs/2026-07-28-local-rag-implementation-design.md` for the full design.

## Setup
1. Install [uv](https://docs.astral.sh/uv/) if you don't have it.
2. `uv venv .venv` to create the virtual environment.
3. `uv pip install -r requirements.txt --python .venv` (add `--system-certs` if you're behind a network that intercepts TLS, e.g. a corporate proxy).
4. Install Tesseract OCR separately (e.g. `winget install UB-Mannheim.TesseractOCR` on Windows) and ensure it's on PATH.
5. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and/or `GROQ_API_KEY` (Groq — fast open-model inference at groq.com, not xAI's Grok).
6. Run `.venv\Scripts\pytest` (Windows) or `.venv/bin/pytest` (Unix) to verify the environment.

## Ingesting the Knowledge Base
1. Drop official scheme PDFs/HTML into `data/raw/text/<category>/`, infographic images into `data/raw/images/<category>/`, and videos into `data/raw/video/<category>/`; or list URLs in `data/sources.yaml` and run `python -m ingestion.fetch_sources`.
2. Sub-folder names drive the `category` metadata that the personal-profile re-ranker matches on (see `CATEGORY_BY_FOLDER` in `ingestion/build_index.py`, e.g. `elderly` → `Seniors`, `comcare` → `Lower-income/employment`). Files dropped straight into `data/raw/text/` get `Uncategorized` and are never boosted for a profile.
3. Run `python -m ingestion.build_index` to chunk, embed, and persist the FAISS index + metadata under `data/faiss/`. Discovery is recursive, PDF chunks are cited by real page number, and `data/raw/video/*.mp4` is transcribed through the configured LLM provider (Gemini) before indexing.

## Running the App
- Custom UI: `uvicorn backend.main:app --reload`, then open `http://127.0.0.1:8000/`.
- Fallback UI: `python backend/gradio_app.py`.

## Running Evaluation
`python -m evaluation.run_eval` — replays `evaluation/test_set.json` through both dense and hybrid retrieval, writing `<mode>_results.json` and `<mode>_results.csv` to `evaluation/results/`.

Each result row carries `retrieved_chunk_ids`, `retrieved_scores`, the generated answer, and three blank human-rubric columns — `correctness_score`, `faithfulness_score`, `citation_accuracy_score` — to be scored 0-2 each by a human reviewer in the CSV. Nothing is scored automatically.

### Hand-labelling retrieval ground truth
`hit_rate`, `recall_at_k` and `mrr` are reported as `null` until relevance labels exist, and the runner prints `WARNING: 0 of 15 questions have labeled expected_relevant_chunk_ids; retrieval metrics unavailable.` Chunk IDs only exist after a real index is built, so labelling has to happen afterwards:
1. Build the index (`python -m ingestion.build_index`) — this writes `data/faiss/metadata.jsonl`, one JSON record per chunk with its `chunk_id`.
2. Run the evaluation once and read `evaluation/results/dense_results.csv` to see which chunks each question actually retrieved.
3. For each question in `evaluation/test_set.json` (under the `questions` key), inspect the candidate chunks' text in `metadata.jsonl` and copy the `chunk_id`s that genuinely answer the question into that question's `expected_relevant_chunk_ids` list.
4. Re-run `python -m evaluation.run_eval`; the warning disappears and retrieval metrics are computed over the labelled subset.

## GPU
Embedding and OCR auto-detect a local CUDA GPU if available and fall back to CPU otherwise — no configuration needed. The FAISS index built on one machine is portable to any other (e.g. Colab's T4) since the embedding model is fixed.
