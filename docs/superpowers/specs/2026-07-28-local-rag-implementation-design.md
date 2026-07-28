---
title: SG Citizen Financial Assistant — Local RAG Implementation Design
version: 1.0
date: 2026-07-28
status: Approved for implementation planning
extends: requirements md/2026-07-27-rag-sgsubsidies-design.md, requirements md/2026-07-27-rag-sgsubsidies-profile-addendum.md
---

# SG Citizen Financial Assistant — Local RAG Implementation Design

This document adapts the team's already-approved spec (`2026-07-27-rag-sgsubsidies-design.md` and its profile addendum) to run as a **local Python project** instead of Google Colab + Drive, and adds **video as a third ingested modality**. It is the concrete build design for this repository; the earlier specs remain the source of truth for domain scope, prompt contracts, and evaluation methodology except where explicitly overridden below.

## 1. Deviations from the approved Colab-based spec

| Area | Approved spec (Colab) | This design (local) |
|---|---|---|
| Persistence | Google Drive (NFR-2) | `./data/` inside this repo — no cloud storage |
| Compute | Colab T4 GPU (required) | Local machine, GPU auto-detected and used if present, CPU fallback otherwise — same fixed embedding model either way so the resulting index is portable between machines |
| Modalities | Text + image (OCR) | Text + image (OCR) + **video** (Gemini multimodal transcription) |
| LLM provider | Gemini only | Pluggable: Gemini or Grok, selected via config |
| Demo | Colab notebook is primary | Local FastAPI backend + custom static frontend is primary; a thin Colab notebook is a secondary, optional demo path |
| UI | Gradio (`gr.Blocks`) | Custom static HTML/CSS/JS frontend calling a FastAPI backend — not constrained by Gradio's component styling |

Everything else (domain, schemes, chunking rationale, retrieval metrics, prompt rules, eval categories) is inherited unchanged from the approved spec.

## 2. Architecture

```
User → Browser (frontend/: static HTML/CSS/JS)
          ├── General Q&A mode      ──▶ POST /api/query
          └── Personal Profile mode ──▶ POST /api/profile-query
                    │
                    ▼
        FastAPI backend (backend/main.py)
                    │
                    ▼
        Retrieval (FAISS dense baseline, BM25+dense hybrid = improvement)
                    │
                    ▼
        Generation (pluggable LLM client: Gemini | Grok)
          - two-layer abstention gate
          - citation validation against retrieved chunk IDs
                    │
                    ▼
        JSON response → sources panel (title, section/page, excerpt, thumbnail) rendered in-browser

Ingestion (offline, run separately from the UI):
  data/raw/text  ──(pypdf/pdfplumber)──┐
  data/raw/images ─(pytesseract OCR)──┼─→ clean/normalize → chunk (~300-400 tok, ~50 overlap)
  data/raw/video ─(Gemini transcription)┘        → attach metadata → embed → FAISS + metadata store
  data/sources.yaml → optional fetch_sources.py → downloads into data/raw/*
```

Both UI modes share one retrieval index and one LLM client; the difference is the query-construction/re-ranking logic and the prompt template used (per §5 of this document).

## 3. Data & Ingestion Pipeline

### 3.1 Modalities and sources
- **Text:** official scheme PDFs/HTML pages, extracted via `pypdf`/`pdfplumber`.
- **Images:** infographics/eligibility tables, OCR'd via `pytesseract`.
- **Video:** scheme explainer videos, sent once (at ingestion time, not per query) to the active Gemini client with a prompt asking it to transcribe speech and describe on-screen graphics/flowcharts/tables as structured text.
- **Fetch module (`ingestion/fetch_sources.py`):** reads `data/sources.yaml` (rows of `{doc_id, url, modality, scheme_name, category}`), downloads each into `data/raw/<modality>/`, and records the retrieval date. This is optional — files can also be dropped into `data/raw/` manually by teammates.

### 3.2 Cleaning & chunking
- Clean: strip navigation/boilerplate, normalize whitespace, de-hyphenate line-wraps, collapse blank lines (applies uniformly to OCR and video-transcription output too).
- Chunk: recursive splitter, ~300–400 tokens per chunk with ~50-token overlap, preferring paragraph/section boundaries — inherited rationale from the approved spec (keeps one eligibility criterion/FAQ entry intact while avoiding pulling in unrelated sections).
- All three modalities converge on one unified chunk record so retrieval/generation code has no modality-specific branching.

### 3.3 Metadata schema

| Field | Type | Notes |
|---|---|---|
| `chunk_id` | string | e.g. `baby-bonus-scheme_txt_003` |
| `doc_id` | string | stable per source document |
| `scheme_name` | string | |
| `category` | string | e.g. `Family`, `Seniors`, `Lower-income` |
| `modality` | enum | `text` \| `image` \| `video` |
| `source_file` | string | path under `data/raw/` |
| `section_or_page` | string | or timestamp range for video |
| `source_url` | string | official source, if fetched |
| `thumbnail_path` | string (image only) | for UI display |
| `text` | string | chunk content |

## 4. Retrieval Design

- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim; matches the lecturer's baseline lab), fixed regardless of hardware — this keeps the vector space identical across machines so results are reproducible and the FAISS index is portable (see GPU note below).
- **Device auto-detection:** `retrieval/embed.py` checks `torch.cuda.is_available()` at runtime and loads the embedding model onto GPU if present (your local machine, or Colab's T4), otherwise CPU. This only affects embedding/OCR speed, not the resulting vectors — same model, same output either way (deterministic modulo negligible floating-point noise), so index files built on one device load and query correctly on another.
- **Portable index:** because the embedding model is fixed, `data/faiss/index.faiss` + `data/faiss/metadata.jsonl` built locally (fast, on your GPU) can be copied as-is into the optional Colab demo notebook (or Drive) and queried directly on T4 — no re-ingestion/re-embedding needed there.
- **Vector store:** FAISS `IndexFlatIP` over L2-normalized vectors (cosine-equivalent), persisted to `./data/faiss/index.faiss`. A parallel `./data/faiss/metadata.jsonl` keyed by `chunk_id` stores the metadata table from §3.3.
- **Baseline retrieval:** dense-only, FAISS top-k by similarity.
- **Improved retrieval (required experiment):** BM25 (`rank_bm25`) over the same chunk texts, fused with FAISS dense results via reciprocal rank fusion. A config flag (`RETRIEVAL_MODE = "dense" | "hybrid"`) switches between the two so the same test set can be run both ways.
- **Configurable parameters** (all in `config.py`, overridable live from the frontend's controls panel via `/api/query`): `TOP_K` (default 5), `SIMILARITY_THRESHOLD` (tuned empirically once real score distributions are observed), `CHUNK_SIZE`/`CHUNK_OVERLAP` (350/50 tokens; requires re-ingestion to change).
- **Profile-mode retrieval:** fetch a candidate pool of `max(TOP_K*3, 15)`, soft re-rank so chunks whose `category` matches the profile's inferred preferred categories (senior/family/lower-income/etc., per the mapping table in the profile addendum §B.1) rise to the top, then truncate to `TOP_K`. Never hard-drops non-preferred categories unless the pool still has ≥`TOP_K` preferred hits, to avoid empty retrieval.

## 5. Generation & Abstention

### 5.1 Pluggable LLM provider
- `generation/llm_client.py` defines a minimal interface: `generate(prompt: str) -> str`.
- `generation/gemini_client.py` and `generation/grok_client.py` implement it.
- `LLM_PROVIDER` in `config.py`/`.env` selects the active client; only the corresponding API key needs to be set at runtime.
- Both keys are declared in one `.env` file (see §8), loaded via `python-dotenv`.

### 5.2 Two-layer abstention (inherited from approved spec)
1. **Pre-LLM gate:** if the top retrieved similarity score is below `SIMILARITY_THRESHOLD`, skip the LLM call and return the fallback message directly — saves API cost on clearly out-of-scope questions.
2. **In-prompt instruction:** even when the gate passes, the model is instructed to abstain if the retrieved passages don't actually answer the question.
3. **Fallback message (exact text):** "The available knowledge base does not contain enough information to answer this question."

### 5.3 Prompt templates (`generation/prompts.py`)
- **General Q&A:** answer only from numbered context passages; cite `[scheme_name, section_or_page]` per factual claim; use the exact fallback sentence when insufficient; concise, plain language.
- **Personal Profile shortlist:** takes retrieved chunks + profile JSON + optional free-text question; outputs exactly three sections — **Possibly eligible** / **Likely not eligible / unclear** / **Not assessed**; never asserts approval or a guaranteed payout; defaults a scheme to "unclear" if a stated threshold isn't present in evidence even when thematically relevant; every claim cited.

### 5.4 Citation validation
After generation, a post-check (same pattern as the lecturer's lab) extracts cited chunk IDs from the answer and flags any that weren't actually retrieved, surfaced as a warning in logs/UI.

## 6. Application (UI) Design

**Decision:** dropped Gradio in favor of a fully custom UI, so styling isn't constrained by Gradio's default component library.

**Stack:**
- **Backend:** FastAPI (`backend/main.py`) exposes the retrieval/generation pipeline as a small JSON API:
  - `POST /api/query` — General Q&A: `{question, top_k?, similarity_threshold?, retrieval_mode?}` → `{answer, sources[], abstained}`
  - `POST /api/profile-query` — Personal Profile shortlist: `{profile, free_text_question?}` → `{answer, sources[], abstained}`
  - `GET /api/config` — current default retrieval params, for the frontend to initialize its controls
  - Backend is a thin HTTP wrapper around the same `retrieval/` and `generation/` modules used elsewhere — no logic duplicated between this and any batch/eval scripts.
- **Frontend:** a static site (`frontend/index.html`, `frontend/style.css`, `frontend/app.js`) served by FastAPI's static-files support (or any static server) — no build step, no framework, fully custom CSS.
  - Mode toggle: **General Q&A** | **Personal eligibility shortlist**.
  - General Q&A: question input, submit, answer panel, sources panel (title, section/page, excerpt, thumbnail for image/video-derived evidence).
  - Personal Profile: profile form (citizenship, age, household size, income band, housing, employment, life-stage tags) + optional free-text question, same answer/sources rendering, styled per the 3-section prompt contract (Possibly eligible / Unclear / Not assessed shown as distinct visual blocks).
  - Controls panel (both modes): `top_k` / `similarity_threshold` inputs, dense↔hybrid retrieval toggle, active LLM provider indicator — calls `/api/query` or `/api/profile-query` with the chosen values.
- **Visual design:** before building the frontend, invoke the `frontend-design` skill (or hand off the brief in §6.1 below) to produce a polished, Singapore-government-appropriate look — clean, accessible, trustworthy — rather than hand-rolling ad hoc CSS.
- **Demo sharing:** since Gradio's `share=True` no longer applies, the optional Colab notebook instead runs the FastAPI backend + static frontend together and exposes a public URL via `pyngrok` (or Colab's own port-forwarding) if a shareable link is needed live.
- **Demo-day fallback:** `backend/gradio_app.py` — a minimal, unstyled Gradio `gr.Blocks` app reusing the exact same `retrieval/` and `generation/` modules (and both prompt templates) as the custom UI, covering General Q&A and Personal Profile modes with plain components (no custom CSS). Only a fallback if the custom frontend isn't demo-ready or breaks close to presentation day — not part of the primary user experience, not covered by the UI design brief below, and not a second thing to keep visually polished.

### 6.1 UI design brief (for the frontend-design skill / handoff prompt)

> Design a clean, trustworthy web UI for a Singapore government subsidies & tax reliefs assistant, aimed at everyday residents (not developers). Two modes, switchable via a top-level toggle: (1) **General Q&A** — a single question box, a submit button, a generated-answer area, and a "Sources" panel listing each cited scheme with its section/page, an excerpt, and a thumbnail when the evidence is an image or video frame; (2) **Personal Eligibility Shortlist** — a short profile form (citizenship, age, household size, income band, housing type, employment status, life-stage tags as checkboxes) plus an optional free-text question, producing a results view with three clearly distinct sections: "Possibly eligible", "Likely not eligible / unclear", and "Not assessed" — each entry shows the scheme name, a plain-language reason, an amount/tier only if the source states one, and a citation. Include a compact "Advanced" panel for `top_k`, similarity threshold, and a baseline/hybrid retrieval toggle, meant for the team's own demo use rather than end users. Visual tone: SG public-service style — calm, legible, high contrast, no dark patterns, mobile-friendly single column that expands to two columns (question/profile on the left, answer/sources on the right) on wider screens. Avoid anything that looks like it's promising a guaranteed payout — the "Possibly eligible" language and citations must stay visually prominent, not fine print.

## 7. Evaluation Framework

- **Test set** (`evaluation/test_set.json`), ~12–15 questions: 3 factual, 3 paraphrase/semantic, 2 multi-document, 2 unanswerable, 2 ambiguous, plus 3 profile-style questions (senior/low-income retiree; young family; PR with undisclosed income) exercising the Profile mode — per the addendum §D.
- Each entry records: expected answer/criteria, expected source document(s), retrieved evidence (chunk IDs + scores), generated answer, evaluation result, short observation.
- **Retrieval metrics (≥3, computed against hand-labeled relevant chunk IDs):** Hit Rate@k, Recall@k, MRR.
- **Answer-quality metric:** structured 0–2 human rubric — Correctness, Faithfulness/groundedness, Citation accuracy.
- **Baseline vs. improved comparison:** run the full test set through dense-only, then hybrid, with everything else held constant; report per the brief's 5-point structure (what changed / problem targeted / what improved / what regressed / trade-offs).
- **Failure analysis:** written causal explanation for the 3 lowest-scoring questions.
- Results persisted under `evaluation/results/` (CSV/JSON) for the report.

## 8. Repository Layout & Persistence

```
sg-citizen-financial-assistant/
├── .env                          # GEMINI_API_KEY, GROK_API_KEY, LLM_PROVIDER
├── .env.example
├── .gitignore
├── config.py
├── requirements.txt
├── README.md
├── data/
│   ├── sources.yaml
│   ├── raw/
│   │   ├── text/
│   │   ├── images/
│   │   └── video/
│   ├── processed/
│   └── faiss/
│       ├── index.faiss           # ← local vector embeddings persisted here
│       └── metadata.jsonl        # chunk_id → metadata, joined to FAISS results
├── ingestion/
│   ├── fetch_sources.py
│   ├── load_text.py
│   ├── load_images_ocr.py
│   ├── load_video_gemini.py
│   ├── chunker.py
│   └── metadata.py
├── retrieval/
│   ├── embed.py
│   ├── faiss_index.py
│   ├── bm25_index.py
│   └── hybrid.py
├── generation/
│   ├── prompts.py
│   ├── llm_client.py
│   ├── gemini_client.py
│   └── grok_client.py
├── backend/
│   ├── main.py                    # FastAPI app: /api/query, /api/profile-query, /api/config; serves frontend/ as static files
│   └── gradio_app.py              # minimal demo-day fallback UI, same retrieval/generation modules, no custom styling
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── evaluation/
│   ├── test_set.json
│   ├── metrics.py
│   ├── run_eval.py
│   └── results/
└── notebooks/
    └── colab_demo.ipynb           # optional: clones repo, pip installs, runs backend/main.py + frontend/ in Colab, exposed via pyngrok if a public demo link is needed
```

**Local vector embeddings persist at `./data/faiss/index.faiss` + `./data/faiss/metadata.jsonl`**, entirely inside the project directory, surviving across script runs without any cloud storage or desktop GUI app.

## 9. Non-Functional Requirements (adapted from approved spec)

- **Compute:** all local processing (embedding, OCR) auto-detects and uses a local GPU if available, falling back to CPU otherwise; no GPU is required at this corpus size, but one is used opportunistically for faster ingestion when present.
- **Persistence:** all durable artifacts (raw documents, processed chunks, FAISS index, metadata store, eval results) live under `./data/` and `./evaluation/results/` in this repo.
- **Reproducibility:** retrieval parameters, model names, provider selection, and prompts live in `config.py`/`.env` so baseline vs. improved runs are diffable.
- **Cost:** Gemini/Grok API spend limited to generation calls and one-off video ingestion calls; no per-query image/video re-processing.
- **Data permissibility:** only official, publicly published Singapore government content; no personal, confidential, or copyrighted third-party material.
- **Latency:** a demo answer (retrieval + generation) should return well under 10 seconds.

## 10. Team Structure (unchanged from approved spec)

| Role | Repo module |
|---|---|
| Data & Ingestion | `ingestion/`, `data/sources.yaml` |
| Retrieval | `retrieval/` |
| Generation & Application | `generation/`, `backend/`, `frontend/` |
| Evaluation & Testing | `evaluation/` |

## 11. Open Items (not architecturally blocking)

- Exact final list of 8–10 schemes and their current official source URLs — to be finalized by the Data & Ingestion owner, optionally via `fetch_sources.py` once URLs are collected.
- Exact `SIMILARITY_THRESHOLD` — tuned empirically once real embedding score distributions are observed on the actual corpus.
- Whether any videos are actually available per scheme; if none are collected, the video pipeline module still exists but simply has no input files to process.
