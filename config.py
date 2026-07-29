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
# Default true: rewriting only ever helps recall (see generation.pipeline's
# fail-open contract) and is the main lever for the required retrieval-quality
# comparison, so it should be on unless a request explicitly opts out.
ENABLE_QUERY_REWRITE = os.getenv("ENABLE_QUERY_REWRITE", "true").lower() == "true"
REWRITE_TIMEOUT_SECONDS = float(os.getenv("REWRITE_TIMEOUT_SECONDS", "0.5"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Groq (groq.com, fast open-model inference) is the fallback provider -- not
# to be confused with xAI's Grok. An earlier version of this project pointed
# at xAI's API by mistake; the key actually configured was always a Groq key.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
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

FALLBACK_MESSAGE = (
    "The available knowledge base does not contain enough information "
    "to answer this question."
)
