# ChromaDB + BGE-M3 + Context-Aware Chunking Design

## Goal

Replace the current FAISS vector store, `all-MiniLM-L6-v2` embedding model, and
naive fixed-word-count chunker with ChromaDB, BGE-M3 dense embeddings, and a
structure-aware chunker that prepends an LLM-generated context sentence to
each chunk before embedding — while keeping the rest of the system (BM25
keyword search, generation, backend API, evaluation harness) unchanged.

## Motivation

The team wants to align with ChromaDB (the vector store named in the original
project requirements doc) and improve retrieval quality via "context
chunking" — both structure-aware splitting and contextual-summary
prepending, decided during brainstorming on 2026-07-29.

## Non-goals

- Replacing BM25 with BGE-M3's sparse embeddings. BGE-M3 supports dense,
  sparse, and multi-vector embeddings in one model, but fusing dense+sparse
  requires the `FlagEmbedding` library and custom score-fusion code that
  Chroma doesn't provide natively. Given this is a course mini-project with a
  working dense-vs-hybrid evaluation harness already built around BM25, the
  team chose the lower-risk **dense-only** BGE-M3 swap. BM25 keeps running
  exactly as it does today.
- Changing the external API of `RagIndex`, `answer_general_question`, or
  `answer_profile_question`. Generation and the backend consume the same
  shapes as before.
- Semantic chunking (splitting on sentence-embedding similarity drops instead
  of headings/word-count). Considered during brainstorming and left out: most
  of this corpus is well-structured government FAQ/scheme pages with clear
  heading boundaries, so structure-aware splitting alone likely captures most
  of the benefit, and semantic chunking adds real implementation cost
  (sentence segmentation, threshold tuning, variable-size chunks) for an
  uncertain gain on already-structured text.

## Architecture

Three isolated swaps, each behind the interface it currently sits behind:

1. **Vector store**: `retrieval/faiss_index.py` is replaced by
   `retrieval/chroma_index.py`, backed by `chromadb.PersistentClient` at
   `data/chroma/` (pinned to `chromadb==1.5.9` per the team's requirement).
2. **Embedding model**: `config.EMBEDDING_MODEL` changes from
   `sentence-transformers/all-MiniLM-L6-v2` to `BAAI/bge-m3`. BGE-M3 loads via
   the same `sentence_transformers.SentenceTransformer` API, so
   `retrieval/embed.py` needs no code change — only the config value changes.
   GPU auto-detection in `retrieval/embed.py` continues to work unmodified.
3. **Chunking**: `ingestion/chunker.py`'s fixed word-count splitter (currently
   350 words / 50-word overlap, no boundary awareness) is replaced by a
   two-stage chunker:
   - **Structure-aware splitting**: split on natural document boundaries
     (headings, paragraph breaks) first; only fall back to the existing
     fixed-word-count logic for any resulting section that still exceeds the
     configured chunk size.
   - **Contextual prepending**: before embedding, prepend a short
     LLM-generated sentence describing where the chunk sits in its source
     document (e.g. "This chunk is from the Eligibility section of the CHAS
     Green Scheme page"). This step is independently skippable — see
     "Contextual chunking is optional" below — since it costs one extra LLM
     call per chunk (measured at 475 chunks for the current corpus; see
     "Cost and time estimate").

### Contextualization uses its own LLM provider, separate from live queries

Contextualization is a one-time bulk job at ingestion time (475 calls in one
run), fundamentally different in shape from live-query generation (a few
calls per user question, spread over the demo). Routing both through the
same `LLM_PROVIDER` risks the ingestion job burning through the same daily
quota the live demo needs — exactly the failure this project already hit
once with Groq's 100K-tokens/day cap.

**New config**: `CONTEXTUAL_CHUNKING_LLM_PROVIDER` (default `"openai"`),
independent of `LLM_PROVIDER` (which stays whatever's configured for live
generation — Gemini or Groq). `ingestion/build_index.py` builds its LLM
client from this dedicated setting via the same `OpenAIClient`/`GroqClient`/
`GeminiClient` classes `backend/main.py` already uses, just picked by a
different config key.

### Cost and time estimate (measured against the current corpus)

A dry run of `discover_documents` + the existing chunker over all of
`data/raw/` (text only — images/video excluded, see below) gives real
numbers to plan against:

- 100 documents, 132,145 words → **475 chunks** at 350 words/50-word overlap.
  (11 videos and all images aren't counted here: Tesseract isn't installed
  locally and no transcription client was passed to the dry run, so those
  chunks don't exist yet — the real final count will be somewhat higher.)
- Contextualization = 475 LLM calls. Estimating ~600 input tokens (chunk +
  doc metadata + instruction) and ~50 output tokens per call: **~309,000
  tokens total** (~285K input, ~24K output).
- **Groq free tier**: the 100K-tokens/day cap this project already hit would
  be exceeded by contextualization alone — confirms `CONTEXTUAL_CHUNKING_LLM_PROVIDER=openai`
  is the right default rather than reusing Groq.
- **OpenAI (`gpt-5.4-mini`)**: using comparable current mini-tier pricing as
  a reference (~$0.15/1M input, ~$0.60/1M output) — **≈ $0.06 total**.
  Verify the actual `gpt-5.4-mini` rate before relying on this figure.
- **Time**: at ~0.5-1.5s per call, sequential ≈ 8-12 minutes for all 475
  calls; running several concurrently (bounded by the provider's
  requests-per-minute cap) could bring this down to a few minutes.

### Contextual chunking is optional

Structure-aware splitting always runs — it's local, free, and has no
external dependency. The **contextual-prepending** half is the one that
costs LLM calls, so it's controlled independently, at two levels:

1. **Upfront opt-out**: a new `config.ENABLE_CONTEXTUAL_CHUNKING` flag
   (default `True`). Set it `False` before running
   `python -m ingestion.build_index` when you know API budget is tight —
   every chunk is then embedded from its raw structure-aware text only, no
   LLM calls made, no risk to the day's quota.
2. **Mid-run circuit breaker**: even with the flag on, if N consecutive
   contextualization calls fail with the same `LLM_PROVIDER_ERRORS` types
   `backend/main.py` already handles (rate limit / quota exhausted — e.g.
   `GroqAPIStatusError`, `GeminiClientError`, or an OpenAI equivalent),
   ingestion stops calling the LLM for the *remainder* of the run and falls
   back to raw-text chunks for everything after that point, logging a
   one-line summary of how many chunks got contextualized vs. fell back.
   This avoids two failure modes observed in practice this project: (a)
   burning through an already-exhausted quota chunk-by-chunk across a
   multi-hundred-chunk corpus, and (b) an ingestion run silently taking far
   longer than necessary retrying/timing out on every remaining chunk one at
   a time.

Either way, a chunk that never got contextualized is not a broken chunk —
it's exactly what today's chunker already produces, so "contextual chunking
off" degrades to the pre-existing baseline, never to a failure.

## Chunk identity: from array position to `chunk_id`

Today, FAISS row *i*, `chunk_records[i]`, and BM25's corpus index *i* are all
positionally aligned, and `retrieval/hybrid.py`'s reciprocal rank fusion
merges lists of `(row_index, score)` tuples on that assumption. ChromaDB
returns string IDs, not positional indices, so this alignment breaks.

**Change**: `chunk_id` (already generated per chunk during ingestion, e.g.
`gst-voucher_text_000`) becomes the join key across both retrievers.
`RagIndex` gains a `chunk_id -> index` map so BM25's positional results can be
translated to the same key space Chroma already uses natively.
`reciprocal_rank_fusion` in `retrieval/hybrid.py` changes its signature from
`list[list[tuple[int, float]]]` (row index) to
`list[list[tuple[str, float]]]` (chunk ID); its ranking algorithm is
unaffected, only the key type.

## Data flow

**Ingestion** (`ingestion/build_index.py`):
`discover_documents` → structure-aware chunk → contextualize (LLM prepend,
fail-open) → embed with BGE-M3 → `chroma_collection.upsert(ids=[chunk_id],
embeddings=[...], documents=[chunk_text], metadatas=[...])`.

The per-chunk metadata payload upserted into Chroma is exactly the
`chroma_flat_metadata_template` shape already present in every file under
`data/metadata/*.json` (both Jony's docs and `metadata_hm_base.json`) — this
is what that field was prepared for. `build_index.py` looks up each chunk's
parent document by `doc_id` in these metadata files and fills in the
chunk-specific fields (`chunk_index`, `chunk_total`, `section`) that the
per-document template leaves as placeholders.

**Query** (`retrieval/hybrid.py`, consumed by `generation/pipeline.py`):
externally unchanged. Internally, `RagIndex` queries Chroma for dense hits
and BM25 for keyword hits, fuses results by `chunk_id` via
`reciprocal_rank_fusion`, and returns results in the same `chunk_records`
shape generation already expects — `generation/pipeline.py` and
`backend/main.py` require no changes.

## Error handling

The contextualization LLM call at ingestion time is **fail-open per chunk**,
following the same convention as query rewriting (`generation/rewrite.py`):
on a provider error or timeout, log it and embed that chunk's raw text with
no prepended context, rather than blocking or failing the whole ingestion
run over one bad chunk. This mirrors the existing
`ops: [{"kind": "failed"}]` pattern used for rewrite failures. Layered on
top of that per-chunk fallback is the run-level circuit breaker described
above ("Contextual chunking is optional") for the case where failures are
sustained (quota exhaustion) rather than one-off.

## Testing

- `tests/retrieval/test_chroma_index.py` (new): build/persist/load/query,
  mirroring the structure of today's `tests/retrieval/test_faiss_index.py`.
- `tests/ingestion/test_chunker.py` (extended): structure-aware splitting
  cases — heading/paragraph boundaries respected, oversized sections still
  fall back to word-count splitting.
- `tests/ingestion/test_contextualize.py` (new): the LLM-prepend step,
  including the per-chunk fail-open path (provider error/timeout falls back
  to raw chunk text), the `ENABLE_CONTEXTUAL_CHUNKING=False` upfront-skip
  path, the mid-run circuit breaker (N consecutive quota/rate-limit errors
  disables contextualization for the rest of the run), and that the client
  built for contextualization respects `CONTEXTUAL_CHUNKING_LLM_PROVIDER`
  independently of `LLM_PROVIDER`.
- `tests/retrieval/test_hybrid.py` (updated): reciprocal rank fusion keyed by
  `chunk_id` string instead of row index.
- `evaluation/run_eval.py`: no code change required, since it consumes the
  same `RagIndex` interface as before.

## Migration

The existing FAISS index at `data/faiss/` and its build code
(`retrieval/faiss_index.py`) are removed once the Chroma path is verified
end-to-end — no dual-write period, since this is a from-scratch rebuild of
the index (`python -m ingestion.build_index`), not a live-data migration.
