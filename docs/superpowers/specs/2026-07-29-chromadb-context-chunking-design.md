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
     Green Scheme page"), using the existing pluggable Gemini/Groq client
     (`get_llm_client()` in `backend/main.py`, reused at ingestion time) — no
     new LLM provider.

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

The contextualization LLM call at ingestion time is **fail-open**, following
the same convention as query rewriting (`generation/rewrite.py`): on a
provider error or timeout, log it and embed the chunk's raw text with no
prepended context, rather than blocking or failing the whole ingestion run
over one bad chunk. This mirrors the existing
`ops: [{"kind": "failed"}]` pattern used for rewrite failures.

## Testing

- `tests/retrieval/test_chroma_index.py` (new): build/persist/load/query,
  mirroring the structure of today's `tests/retrieval/test_faiss_index.py`.
- `tests/ingestion/test_chunker.py` (extended): structure-aware splitting
  cases — heading/paragraph boundaries respected, oversized sections still
  fall back to word-count splitting.
- `tests/ingestion/test_contextualize.py` (new): the LLM-prepend step,
  including the fail-open path (provider error/timeout falls back to raw
  chunk text).
- `tests/retrieval/test_hybrid.py` (updated): reciprocal rank fusion keyed by
  `chunk_id` string instead of row index.
- `evaluation/run_eval.py`: no code change required, since it consumes the
  same `RagIndex` interface as before.

## Migration

The existing FAISS index at `data/faiss/` and its build code
(`retrieval/faiss_index.py`) are removed once the Chroma path is verified
end-to-end — no dual-write period, since this is a from-scratch rebuild of
the index (`python -m ingestion.build_index`), not a live-data migration.
