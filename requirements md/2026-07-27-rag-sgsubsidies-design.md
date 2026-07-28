---
title: RAG SG Subsidies Assistant — Technical & Functional Specification
version: 1.0
date: 2026-07-27
status: Approved for implementation planning
---

# RAG SG Subsidies Assistant
## Technical & Functional Specification

**Prepared for:** Group Mini-Project — Build and Evaluate a Practical RAG Assistant
**Domain:** Singapore Government Subsidies & Financial Assistance for Citizens
**Target compute:** Single NVIDIA Tesla T4 GPU (Google Colab)
**Timeline:** ~1 week build

---

## 1. Executive Summary

This document specifies a Retrieval-Augmented Generation (RAG) system that answers questions about Singapore government subsidy and financial assistance schemes (e.g. Baby Bonus, Silver Support, ComCare, Workfare) using only a curated knowledge base of official scheme documentation. The system retrieves relevant evidence from a two-modality knowledge base (official text/PDF pages and infographic/table images), generates a grounded answer via an external LLM API, cites its sources, and abstains when evidence is insufficient. The design is scoped to be built and evaluated by a 4-person team within one week, running entirely inside a Google Colab notebook on a single T4 GPU.

The system exists to answer one evaluation question with evidence, not opinion:

> **How effectively can this RAG system retrieve the right evidence and produce a grounded, attributable answer for the SG subsidies domain?**

Every design decision below is made in service of being able to answer that question with numbers (retrieval metrics, answer-quality scores) and named failure cases, not just a working demo.

---

## 2. Project Objective & Selected Domain

**Domain:** Public-sector information and service guides — specifically, Singapore government subsidy and financial assistance schemes for individuals/families/seniors.

**Intended users:** A Singaporean resident (or someone assisting one — e.g. a social worker, family member) who wants a plain-language answer to "am I eligible for X" or "how much is Y" questions, backed by a citation to the official scheme page/document, without having to search across many different agency websites.

**Why this domain fits the brief:**
- Content is public, official, and freely republishable for educational/demonstration use (no personal, confidential, or copyrighted material).
- Naturally produces two modalities: official scheme text pages and official infographic/payout-tier graphics.
- Naturally produces overlapping topics (e.g. several schemes target seniors, several target families), which is required for the "information appears in more than one document" evaluation question category.
- Bounded and small: ~8–10 schemes is enough to be "varied" without being unmanageable in a week.

---

## 3. Functional Requirements

Mapped directly from the project brief (Section 4), restated as system requirements:

| ID | Requirement | Source |
|----|---|---|
| FR-1 | Knowledge base must contain ≥2 modalities (text + image), each chunk traceable to a source document identity | Brief §4.1 |
| FR-2 | System must load, clean/normalize, chunk, and attach metadata to all source content | Brief §4.2 |
| FR-3 | System must embed chunks, store them in a vector index, embed queries, and retrieve top-k relevant chunks | Brief §4.3 |
| FR-4 | At least one retrieval parameter must be user/config-configurable (top_k, chunk size, overlap, or similarity threshold) | Brief §4.3 |
| FR-5 | Generation must be grounded strictly in retrieved evidence, and must abstain with a defined fallback message when evidence is insufficient | Brief §4.4 |
| FR-6 | Every answer must display at least one of: document title, source identifier, section/page, retrieved excerpt | Brief §4.5 |
| FR-7 | A ≥10-question test set must be created spanning factual, paraphrase, multi-document, unanswerable, and ambiguous question types, each with recorded expected answer, expected source, retrieved evidence, generated answer, evaluation result, and observation | Brief §4.6 |
| FR-8 | Evaluation must report ≥3 retrieval metrics and ≥1 answer-quality metric, plus ≥3 written failure-case analyses | Brief §4.6 |
| FR-9 | System must implement and evaluate ≥1 concrete improvement over baseline, using the same test set, with an explicit before/after comparison | Brief §5 |

---

## 4. Non-Functional Requirements

- **NFR-1 (Compute):** All local compute (embedding, OCR, indexing) must run comfortably within a single T4's 16GB VRAM alongside the Python/Colab runtime overhead. Generation is offloaded to an external API specifically to preserve this headroom.
- **NFR-2 (Persistence):** Because Colab sessions are ephemeral, all durable artifacts (raw documents, processed chunks, FAISS index, metadata store, eval results) must be persisted to Google Drive, not left in the Colab VM's local disk.
- **NFR-3 (Reproducibility):** Retrieval parameters, model names/versions, and prompts must live in one shared `config.py` so baseline vs. improved runs are reproducible and diffable.
- **NFR-4 (Cost):** Total Gemini API spend must stay within free-tier limits for the expected call volume (≈12 test questions × 2 pipeline variants × a handful of iterations ≈ low hundreds of calls).
- **NFR-5 (Data permissibility):** Only official, publicly published Singapore government content may be ingested — no scraped personal data, no copyrighted third-party commentary/news.
- **NFR-6 (Latency):** A demo answer (retrieval + generation) should return in well under 10 seconds to be usable in a live 3-minute demo window.

---

## 5. System Architecture

### 5.1 Component diagram

```
                         ┌─────────────────────────┐
                         │   Google Drive (persist) │
                         │  raw docs / images /     │
                         │  FAISS index / metadata / │
                         │  eval logs                │
                         └────────────┬────────────┘
                                      │ mount
┌───────────────────────────── Colab Notebook (T4) ───────────────────────────┐
│                                                                              │
│  ┌───────────┐    ┌───────────────┐    ┌───────────────┐    ┌────────────┐ │
│  │ Ingestion │───▶│   Retrieval   │───▶│  Generation    │───▶│  Gradio UI │ │
│  │  module   │    │    module     │    │    module      │    │  (app.py)  │ │
│  │           │    │               │    │                │    │            │
│  │ load/clean│    │ bge embed +   │    │ Gemini API call │    │ question   │
│  │ /chunk/OCR│    │ FAISS + BM25  │    │ + grounding     │    │ box, answer│
│  │ /metadata │    │ (hybrid, v2)  │    │ prompt +        │    │ + sources  │
│  │           │    │               │    │ abstention gate │    │ panel      │
│  └───────────┘    └───────────────┘    └───────────────┘    └────────────┘ │
│                                                                              │
│                         ┌─────────────────────────┐                        │
│                         │   Evaluation module      │                        │
│                         │ test set runner, metrics,│                        │
│                         │ baseline-vs-improved diff│                        │
│                         └─────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                            External: Google Gemini API
```

### 5.2 Query-time sequence

1. User submits a question via Gradio.
2. Retrieval module embeds the question with `bge-small-en-v1.5`.
3. FAISS returns top-k candidates by cosine similarity (dense baseline) — or, in the improved pipeline, dense results are fused with BM25 keyword results via reciprocal rank fusion.
4. If the best candidate's similarity score is below `SIMILARITY_THRESHOLD`, or too few candidates clear the bar, the system short-circuits to the fallback message and skips the LLM call.
5. Otherwise, the retrieved chunks (with metadata) are formatted into the grounding prompt and sent to Gemini.
6. Gemini returns an answer with inline citations to `doc_id`/scheme name.
7. The UI renders the answer plus a sources panel (title, section/page, excerpt, thumbnail if image-derived).
8. Every call (question, retrieved chunk IDs + scores, prompt, raw model answer, latency) is logged to a run log used by the evaluation module.

---

## 6. Knowledge Base & Sourcing Plan

### 6.1 Scope

**8–10 household/individual-facing schemes**, chosen so several deliberately overlap in audience (seniors, families, lower-income) — this overlap is what makes genuine multi-document test questions possible.

| # | Scheme | Category | Text source | Image source (planned) |
|---|---|---|---|---|
| 1 | Baby Bonus Scheme | Family | Official scheme page/PDF | Payout schedule infographic |
| 2 | CDC Vouchers | Household/cost-of-living | Official scheme page | Voucher value/eligibility infographic |
| 3 | Silver Support Scheme | Seniors | Official scheme page | Payout-tier table graphic |
| 4 | ComCare Assistance | Lower-income | Official scheme page/FAQ | Eligibility criteria infographic |
| 5 | Workfare Income Supplement | Lower-income/employment | Official scheme page | Payout table by age/income graphic |
| 6 | GST Voucher (Cash/U-Save/MediSave) | Household | Official scheme page | Payout-tier infographic |
| 7 | HDB housing grants (e.g. Enhanced CPF Housing Grant) | Housing | Official scheme page | Grant amount table graphic |
| 8 | MediSave/MediShield subsidies | Healthcare | Official scheme page | Subsidy-tier infographic |
| 9 | CPF top-up / Matched Retirement Savings Scheme | Seniors/retirement | Official scheme page | Matching-grant table graphic |
| 10 | Home Caregiving Grant | Seniors/caregiving | Official scheme page | Eligibility/payout infographic |

**Candidate official sources** (general destinations, not specific deep links — the data & ingestion owner should locate and record the exact current URL for each scheme at collection time): Supportgowhere (life.gov.sg), Ministry of Social and Family Development (msf.gov.sg), CPF Board (cpf.gov.sg), gov.sg, Ministry of Finance Budget microsite (mof.gov.sg / Budget site), HDB (hdb.gov.sg).

Total expected corpus: ~10 text documents + ~10–20 images ≈ 20–30 source files, chunking to an estimated 150–350 chunks — small enough to fully re-index in minutes on a T4, varied enough to support 12 meaningful test questions.

### 6.2 Document identity

Every ingested source is assigned a stable `doc_id` (e.g. `baby-bonus-scheme`) and recorded with: scheme name, category, modality, source file path, official source URL, and date retrieved. This satisfies the "record the source or document identity" requirement and is the join key between the vector index and the metadata store.

### 6.3 Compliance

Only official government-published material is used. No personal data, no scraped news commentary, no copyrighted third-party material. This is recorded explicitly in the report's "Description of the knowledge base" section.

---

## 7. Data Processing Pipeline

### 7.1 Text pipeline

1. **Load:** PDF/HTML scheme pages via a PDF/HTML text extractor.
2. **Clean:** strip navigation/boilerplate, normalize whitespace, de-hyphenate broken line-wraps, collapse repeated blank lines.
3. **Chunk:** recursive splitter, **target ~300–400 tokens per chunk with ~50-token overlap**, preferring to break on paragraph/section boundaries rather than mid-sentence.
   - **Rationale:** scheme documents are organized around discrete eligibility criteria, payout amounts, and FAQ entries. A ~300–400 token chunk is large enough to keep one such unit intact (avoiding split-criterion answers) but small enough that top-k retrieval doesn't pull in unrelated scheme sections, which matters for precision on the "correct evidence" evaluation question.
4. **Metadata attach:** each chunk inherits `doc_id`, `scheme_name`, `category`, `modality: text`, `source_file`, `section_or_page`, `source_url`.

### 7.2 Image pipeline

1. **Load:** infographic/table images (PNG/JPG) collected per scheme.
2. **OCR:** `pytesseract` (Tesseract) extracts raw text — CPU-only, zero VRAM cost, keeping the T4 free for embeddings/generation-side work.
3. **Clean:** OCR output normalized the same way as text (whitespace, common OCR artifacts).
4. **Chunk:** treated identically to text chunks (same splitter, same size target), tagged `modality: image`, plus a stored `thumbnail_path` for UI display.
5. **Metadata attach:** same schema as text chunks, with `modality: image`.

**Design choice — OCR over CLIP embeddings:** a CLIP-based joint image/text embedding space was considered (see §14 Limitations) but rejected for the baseline because it introduces a second embedding space that must be fused/ranked against the text space, adding evaluation complexity without a clear payoff at this corpus size and timeline. OCR keeps the entire system on **one** retrieval pipeline, which is simpler to build, debug, and evaluate within a week.

### 7.3 Unified metadata schema

| Field | Type | Example |
|---|---|---|
| `chunk_id` | string | `baby-bonus-scheme_txt_003` |
| `doc_id` | string | `baby-bonus-scheme` |
| `scheme_name` | string | `Baby Bonus Scheme` |
| `category` | string | `Family` |
| `modality` | enum | `text` \| `image` |
| `source_file` | string | `data/raw/baby_bonus.pdf` |
| `section_or_page` | string | `Eligibility, p.2` |
| `source_url` | string | official scheme URL |
| `thumbnail_path` | string (image only) | `data/raw/images/baby_bonus_infographic.png` |
| `text` | string | chunk content |

---

## 8. Retrieval Design

### 8.1 Embedding model

`BAAI/bge-small-en-v1.5` (fallback to `bge-base-en-v1.5` if VRAM headroom allows and quality needs a boost). Chosen for strong MTEB retrieval performance at small size (~130MB), fast enough to embed the full corpus in seconds on a T4, and light enough to coexist with the rest of the pipeline in VRAM.

### 8.2 Vector store

**FAISS**, flat (exact) index — the corpus (a few hundred chunks) is small enough that approximate indexing (IVF/HNSW) would add complexity with no measurable speed benefit. Index is serialized to a file and persisted on Google Drive; a parallel metadata store (a simple JSON/SQLite file keyed by `chunk_id`, matching §7.3) travels alongside it since FAISS itself only stores vectors.

### 8.3 Configurable retrieval parameters

All live in `config.py`, overridable at query time from the Gradio sidebar for live demo purposes:

| Parameter | Baseline default | Purpose |
|---|---|---|
| `TOP_K` | 5 | Number of chunks retrieved per query (primary required configurable parameter) |
| `SIMILARITY_THRESHOLD` | tuned during baseline eval | Minimum score to accept a chunk as evidence; below this, triggers abstention |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 350 / 50 tokens | Set at ingestion time; changing requires re-chunking + re-indexing |

### 8.4 Baseline vs. improved retrieval

- **Baseline:** dense-only — embed query, FAISS top-k by cosine similarity.
- **Improved (required experiment, see §10):** hybrid — BM25 (`rank_bm25`) keyword scores fused with dense cosine scores via reciprocal rank fusion, re-ranking the merged candidate set before taking top-k.

---

## 9. Grounded Generation Design

### 9.1 LLM

Google Gemini API (Flash tier). Chosen over a locally-hosted quantized model to preserve all T4 VRAM for the retrieval-side pipeline (embeddings + OCR) and because a hosted frontier-class model gives materially better instruction-following for strict grounding/citation/abstention behavior than a 4-bit quantized 7–8B local model would.

### 9.2 Prompt contract (system prompt, summarized)

> You are an assistant that answers questions about Singapore government subsidy schemes using ONLY the context passages provided below. Each passage is labeled with a source ID. Rules:
> 1. Answer only using facts present in the provided passages. Do not use outside knowledge.
> 2. For every factual claim, cite the source ID(s) it came from.
> 3. If the passages do not contain enough information to answer, respond with exactly: "The available knowledge base does not contain enough information to answer this question." Do not guess.
> 4. Keep answers concise and in plain language suitable for a member of the public.

### 9.3 Two-layer abstention

1. **Pre-LLM gate:** if the top retrieved similarity score is below `SIMILARITY_THRESHOLD`, skip the LLM call entirely and return the fallback message — this also saves API cost on clearly unanswerable questions.
2. **In-prompt instruction:** even when the gate passes, the model is explicitly instructed to abstain if the retrieved passages don't actually answer the question (handles cases where retrieval returns topically-similar but non-answering chunks).

### 9.4 Citation format

Generated answers reference sources as `[scheme_name, section_or_page]`; the UI cross-references this back to the full metadata record (title, source identifier, section/page, excerpt, thumbnail).

---

## 10. Improvement Experiment Design

**Change:** introduce hybrid (BM25 + dense) retrieval in place of dense-only retrieval.

**Problem it targets:** dense embeddings can under-rank chunks containing exact scheme names, dollar amounts, or acronyms (e.g. "$3,000", "CPF", "GST-V") because semantic similarity doesn't weight exact-term overlap — this directly threatens Hit Rate/Recall/MRR on straightforward factual questions, and BM25 is a well-known complement.

**Method:**
1. Run the full 12-question test set through the baseline (dense-only) pipeline; record all retrieval + answer-quality metrics.
2. Swap in the hybrid retriever (same embedding model, same FAISS index, plus a BM25 index over the same chunks; combine rankings via reciprocal rank fusion) with everything else (chunking, prompt, LLM) held constant.
3. Run the identical 12 questions through the improved pipeline.
4. Report, per the brief's required 5-point comparison: what changed, what problem it targeted, which metrics improved, which regressed/stayed flat, and what trade-offs were introduced (e.g. added latency/complexity, possible over-weighting of keyword matches on paraphrase-style questions).

This is a controlled, single-variable experiment — only the retrieval mechanism changes between baseline and improved runs, so any metric delta is attributable to that one change.

---

## 11. Evaluation Framework

### 11.1 Test set (12 questions)

| Category | Count | Purpose |
|---|---|---|
| Straightforward factual | 3 | Basic retrieval sanity (e.g. "What is the payout amount for X?") |
| Paraphrase / semantic matching | 3 | Tests embedding quality vs. keyword-only matching |
| Multi-document (answer spans >1 scheme) | 2 | Tests retrieval breadth and answer synthesis across sources |
| Unanswerable (not in KB) | 2 | Tests abstention behavior — required minimum met |
| Ambiguous / difficult | 2 | Stress-tests grounding discipline and citation accuracy |

For every question, the run log records: expected answer/criteria, expected source document(s), actual retrieved evidence (chunk IDs + scores), generated answer, evaluation result, and a short observation — exactly as required by the brief.

### 11.2 Retrieval metrics (3 required, all computed per-question against hand-labeled relevant chunk IDs)

- **Hit Rate@k:** did at least one relevant chunk appear in the top-k results? (binary per question, averaged)
- **Recall@k:** fraction of all known-relevant chunks for that question that appear in the top-k results.
- **MRR (Mean Reciprocal Rank):** 1 / (rank of first relevant chunk), averaged across questions — rewards ranking relevant evidence higher, not just present.

### 11.3 Answer-quality metric

A structured human rubric, scored 0–2 on each of:
- **Correctness:** does the answer match the expected answer/criteria?
- **Faithfulness/groundedness:** is every claim actually supported by the retrieved evidence (no hallucinated facts)?
- **Citation accuracy:** do the cited sources actually correspond to where the claim came from?

Chosen over an automated framework (e.g. RAGAS) because at 12 questions, manual scoring is fast to execute, fully transparent, and produces a defensible written rationale per question for the report — automated LLM-as-judge scoring can be added later as a cross-check if time permits, but is not load-bearing for the required metric.

### 11.4 Failure analysis

The 3 lowest-scoring questions (by combined rubric score) get a short written causal explanation — e.g. "retrieval returned the correct scheme but the wrong section (payout table instead of eligibility), so the answer cited the right document but the wrong facts."

---

## 12. Application (UI) Design

**Framework:** Gradio (`gr.Blocks`), launched inline in the Colab notebook with `share=True` for a public demo link — no separate hosting/tunnel needed.

**Layout:**
- Question input box + submit button.
- Answer panel: generated answer text.
- Sources panel: for each cited chunk — scheme/document title, source identifier, section/page, retrieved excerpt, and a thumbnail image when the evidence is image-derived.
- Sidebar: live-adjustable `top_k` and `similarity_threshold` sliders, and a toggle between baseline (dense) and improved (hybrid) retrieval mode, so the demo can visibly show the before/after comparison from §10.

---

## 13. Team Structure & Repository Organization

Mapped 1:1 to the brief's suggested roles (4-person team):

| Role | Owner | Repo module |
|---|---|---|
| Data & Ingestion | Member A | `ingestion/` (loaders, cleaning, chunking, OCR, metadata) |
| Retrieval | Member B | `retrieval/` (embedding, FAISS index build/query, BM25, hybrid fusion) |
| Generation & Application | Member C | `generation/` (prompt templates, Gemini client, abstention logic), `app.py` (Gradio UI) |
| Evaluation & Testing | Member D | `evaluation/` (test set, metric computation, rubric scoring, baseline-vs-improved report generator) |

**Repository layout:**

```
rag-sgsubsidies/
├── config.py                 # shared parameters (chunk size, top_k, threshold, model names)
├── requirements.txt
├── README.md
├── data/
│   ├── raw/                  # source PDFs/images, mirrored to Drive
│   └── processed/            # cleaned/chunked outputs, metadata store
├── ingestion/
│   ├── load_text.py
│   ├── load_images_ocr.py
│   ├── chunker.py
│   └── metadata.py
├── retrieval/
│   ├── embed.py
│   ├── faiss_index.py
│   ├── bm25_index.py
│   └── hybrid.py
├── generation/
│   ├── prompts.py
│   └── gemini_client.py
├── app.py
├── evaluation/
│   ├── test_set.json
│   ├── metrics.py
│   ├── run_eval.py
│   └── results/
└── notebooks/
    └── integration.ipynb     # mounts Drive, clones repo, runs end-to-end in Colab
```

**Workflow:** code lives in a shared GitHub repo (not scattered notebooks); the Colab integration notebook clones the repo and mounts Drive at the start of each session, satisfying the brief's explicit requirement to integrate lab work into "one coherent system rather than several disconnected notebooks."

---

## 14. Tech Stack Summary

| Layer | Choice | Why |
|---|---|---|
| Compute environment | Google Colab (T4 GPU) | User-specified constraint |
| Text extraction | `pypdf` / `pdfplumber` | Standard, lightweight PDF text extraction |
| OCR | `pytesseract` (Tesseract) | CPU-only, zero VRAM cost, mature |
| Chunking | LangChain `RecursiveCharacterTextSplitter` (or equivalent hand-rolled splitter) | Battle-tested boundary-aware splitting |
| Embedding model | `BAAI/bge-small-en-v1.5` | Strong MTEB retrieval score at small footprint |
| Vector store | FAISS (`faiss-cpu`) | No server, file-based persistence, simple top-k API |
| Keyword search (improvement) | `rank_bm25` | Lightweight, no external service |
| Generation LLM | Google Gemini API (Flash tier) | Strong grounding/instruction-following, free-tier friendly, frees T4 VRAM |
| UI | Gradio | Colab-native `share=True` public demo link |
| Metadata store | JSON or SQLite | Simple, no server, easy to inspect/debug |
| Evaluation | Custom Python scripts + structured rubric (spreadsheet/CSV export) | Transparent, fast at this scale |

---

## 15. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Official scheme pages change/move during the project week | Snapshot each source (save PDF/HTML copy) at collection time; record retrieval date |
| OCR quality on infographics is poor (stylized fonts, low contrast) | Manually spot-check OCR output per image during ingestion; hand-correct if a given image is unreadable rather than dropping the modality requirement |
| Gemini free-tier rate limits during heavy eval runs | Batch/space out evaluation calls; cache generated answers per question so re-runs of unchanged config don't re-call the API |
| Colab session disconnects mid-build | All artifacts persisted to Drive; code in GitHub, not notebook-local state |
| Hybrid search regresses some question categories | Explicitly reported in §10 comparison as "trade-offs introduced" — an honest regression is acceptable and expected content for the report |

---

## 16. Limitations & Future Work (for report §10)

- Image modality is handled via OCR rather than true multimodal (CLIP-style) embeddings; a genuinely image-native retrieval path is a natural next step if extended beyond this course project.
- FAISS flat index does not scale past a small corpus; a larger production deployment would need an approximate index (IVF/HNSW) or a managed vector DB.
- Answer-quality evaluation is manually scored at this scale (12 questions); a larger deployment would benefit from an automated LLM-as-judge cross-check (e.g. RAGAS) to scale evaluation without proportional human effort.
- No user authentication/personalization — the system answers generically, not based on an individual's actual eligibility profile (a real deployment would need to handle personal data, which is explicitly out of scope here).

---

## 17. Deliverables Mapping

This spec's sections map directly onto the required project report structure, so the report can largely follow this document's ordering:

| Report section | Spec section |
|---|---|
| 1. Project objective and selected domain | §2 |
| 2. Description of the knowledge base | §6 |
| 3. RAG architecture | §5 |
| 4. Document processing and chunking strategy | §7 |
| 5. Embedding and retrieval approach | §8 |
| 6. Prompt and answer-generation approach | §9 |
| 7. Evaluation dataset and metrics | §11 |
| 8. Baseline results | (populated after baseline run, using §11 framework) |
| 9. Improvement experiment | §10 |
| 10. Limitations and recommended next steps | §16 |
| 11. Contributions of each group member | §13 |

---

## 18. Assumptions & Decisions Log

Recorded for traceability — these were explicitly decided with the project owner rather than assumed unilaterally:

- Domain confirmed as SG subsidies/financial assistance for citizens (household/individual focus).
- Modalities: text + image (not audio/video), via OCR rather than CLIP embeddings for the baseline.
- Compute: Google Colab T4; generation offloaded to Google Gemini API rather than a local quantized LLM.
- Vector store: FAISS; embedding model: BAAI/bge-small-en-v1.5.
- Required improvement experiment: hybrid (BM25 + dense) retrieval.
- UI: Gradio with `share=True`.
- Team: 4 people, one per suggested role.
- Knowledge base scope: ~8–10 schemes, ~20–30 source files.
- Timeline: ~1 week.

**Still open / to confirm during build (not architecturally blocking):**
- Exact final list of 8–10 schemes and their current official source URLs (to be finalized by the Data & Ingestion owner at collection time).
- Exact `SIMILARITY_THRESHOLD` value — to be tuned empirically once real embedding score distributions are observed on the actual corpus, not fixed in advance.
- Whether `bge-small` or `bge-base` is used — decide after a quick VRAM/quality check once OCR + FAISS + Gemini client are all loaded together.
