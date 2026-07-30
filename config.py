import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
# Chroma persists its own on-disk state under this directory; metadata.jsonl
# (chunk_records, used for BM25 + display) still lives alongside it rather
# than inside Chroma, since it's also the source the backend/evaluation code
# reads chunk records from directly.
CHROMA_PATH = DATA_DIR / "chroma"
CHROMA_METADATA_PATH = DATA_DIR / "chroma" / "metadata.jsonl"
CHROMA_COLLECTION_NAME = "sg_financial_assistant"
SOURCES_YAML_PATH = DATA_DIR / "sources.yaml"

CHUNK_SIZE_WORDS = 350
CHUNK_OVERLAP_WORDS = 50

# BGE-M3 (dense embeddings only -- see docs/superpowers/specs/2026-07-29-
# chromadb-context-chunking-design.md's "Non-goals" for why sparse/hybrid
# BGE-M3 was ruled out). Loads via the same sentence_transformers API as the
# old all-MiniLM-L6-v2 model; ~2.3GB on first download.
EMBEDDING_MODEL = "BAAI/bge-m3"

# Contextual chunking: prepend a short LLM-generated "where this chunk sits"
# sentence before embedding. Costs one LLM call per chunk (hundreds for a
# full corpus rebuild), so it's independently skippable -- set False when API
# budget is tight, rather than burning a provider's daily quota mid-run.
ENABLE_CONTEXTUAL_CHUNKING = os.getenv("ENABLE_CONTEXTUAL_CHUNKING", "true").lower() == "true"
# Deliberately separate from LLM_PROVIDER: contextualization is a one-time
# bulk job at ingestion time (hundreds of calls in one run), fundamentally
# different in shape from live-query generation (a few calls per question,
# spread over a demo). Routing both through the same provider risks the bulk
# job burning through the same daily quota the live demo needs -- this
# project has hit Groq's 100K-tokens/day cap once already. OpenAI has no
# such daily cap (pay-as-you-go), so it is the safer default for the bulk job.
CONTEXTUAL_CHUNKING_LLM_PROVIDER = os.getenv("CONTEXTUAL_CHUNKING_LLM_PROVIDER", "openai")
# After this many consecutive contextualization failures (rate limit/quota
# errors), stop calling the LLM for the rest of the run and fall back to
# plain structure-aware chunks for everything remaining -- see the spec's
# "Contextual chunking is optional" section.
CONTEXTUALIZE_CIRCUIT_BREAKER_THRESHOLD = int(
    os.getenv("CONTEXTUALIZE_CIRCUIT_BREAKER_THRESHOLD", "5")
)

TOP_K = 5
SIMILARITY_THRESHOLD = 0.35
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "dense")
# Default true: rewriting only ever helps recall (see generation.pipeline's
# fail-open contract) and is the main lever for the required retrieval-quality
# comparison, so it should be on unless a request explicitly opts out.
ENABLE_QUERY_REWRITE = os.getenv("ENABLE_QUERY_REWRITE", "true").lower() == "true"
# A real LLM round-trip (even fast providers like Groq) routinely takes
# 500ms-1.5s depending on prompt size and load. 500ms sounded reasonable on
# paper but meant the rewrite lost the race almost every time in practice,
# fail-opening to the raw query and making rewriting look broken. 3s keeps a
# hard ceiling (still fails open past that) while giving a real call room to
# finish.
REWRITE_TIMEOUT_SECONDS = float(os.getenv("REWRITE_TIMEOUT_SECONDS", "15.0"))

# In-session chat: max prior turns sent with each request (user+assistant
# pairs). Caps prompt size / cost while still resolving follow-ups like
# "how much is that?". Frontend also caps what it stores in sessionStorage.
CHAT_HISTORY_MAX_TURNS = int(os.getenv("CHAT_HISTORY_MAX_TURNS", "4"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Groq (groq.com, fast open-model inference) is the fallback provider -- not
# to be confused with xAI's Grok. An earlier version of this project pointed
# at xAI's API by mistake; the key actually configured was always a Groq key.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# OpenAI (api.openai.com) -- a third pluggable provider, useful as a fallback
# when Groq's daily token quota is exhausted (this project has hit that limit
# before). Not used for video transcription; that stays on Gemini.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Pinned Gemini generation names get retired out from under this project:
# gemini-1.5-flash now 404s ("not found for API version v1beta") and even
# gemini-2.5-flash 404s for keys created after its cutoff ("no longer available
# to new users"). Note that models.list() still advertises names that
# generate_content rejects, so listing is not a safe way to pick one.
# `gemini-flash-latest` is a stable, non-preview alias that Google re-points at
# the current Flash model, so it is the only default immune to that failure
# mode. Pin a specific version via the GEMINI_MODEL env var when reproducibility
# matters more than availability (e.g. gemini-3.6-flash, gemini-3.5-flash-lite).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

FALLBACK_MESSAGE = (
    "The available knowledge base does not contain enough information "
    "to answer this question."
)
