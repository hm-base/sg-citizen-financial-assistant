import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from google.genai.errors import ClientError as GeminiClientError
from openai import APIStatusError as GroqAPIStatusError
from pydantic import BaseModel

import config
from generation.gemini_client import GeminiClient
from generation.groq_client import GroqClient
from generation.openai_client import OpenAIClient
from generation.pipeline import (
    RagIndex,
    ShortlistFormatError,
    answer_general_question,
    answer_profile_question,
)
from ingestion.build_index import load_metadata
from retrieval.bm25_index import build_bm25_index
from retrieval.chroma_index import get_chroma_client, get_or_create_chroma_collection
from retrieval.embed import load_embedder

app = FastAPI(title="SG Citizen Financial Assistant")

_rag_index_cache: RagIndex | None = None


INDEX_MISSING_DETAIL = (
    "Knowledge base index not found — run `python -m ingestion.build_index` first"
)

# Both LLM SDKs raise their own exception type for 4xx/5xx responses (rate
# limits, exhausted daily quota, transient outages). Left uncaught, these
# propagate past FastAPI as a bare 500 with no actionable detail -- a
# resident (or demo audience) sees "Something went wrong: HTTP 500" instead
# of "try again shortly" or "switch provider."
LLM_PROVIDER_ERRORS = (GeminiClientError, GroqAPIStatusError)
LLM_PROVIDER_ERROR_DETAIL = (
    "The assistant's LLM providers are all temporarily unavailable (rate "
    "limit or quota exceeded). Please try again in a few minutes."
)


def _call_with_llm_fallback(fn, *args, llm_clients: list, **kwargs):
    """Try each client in turn, moving to the next only on a provider-side
    rate-limit/quota error. Raises the last such error once every client has
    been exhausted, so the caller's except clause still fires."""
    if not llm_clients:
        raise RuntimeError("No LLM provider is configured (all API keys are unset).")
    last_error = None
    for client in llm_clients:
        try:
            return fn(*args, client, **kwargs)
        except LLM_PROVIDER_ERRORS as exc:
            last_error = exc
    raise last_error


def get_rag_index() -> RagIndex:
    global _rag_index_cache
    if _rag_index_cache is None:
        if not Path(config.CHROMA_METADATA_PATH).exists():
            raise HTTPException(status_code=503, detail=INDEX_MISSING_DETAIL)
        chunk_records = load_metadata(config.CHROMA_METADATA_PATH)
        chroma_client = get_chroma_client(config.CHROMA_PATH)
        collection = get_or_create_chroma_collection(chroma_client, config.CHROMA_COLLECTION_NAME)
        if collection.count() == 0:
            raise HTTPException(status_code=503, detail=INDEX_MISSING_DETAIL)
        _rag_index_cache = RagIndex(
            chroma_collection=collection,
            bm25_index=build_bm25_index([record["embed_text"] for record in chunk_records]),
            chunk_records=chunk_records,
            embedder=load_embedder(config.EMBEDDING_MODEL),
        )
    return _rag_index_cache


def get_llm_client(provider: str | None = None):
    provider = provider or config.LLM_PROVIDER
    if provider == "groq":
        return GroqClient(api_key=config.GROQ_API_KEY, model_name=config.GROQ_MODEL)
    if provider == "openai":
        return OpenAIClient(api_key=config.OPENAI_API_KEY, model_name=config.OPENAI_MODEL)
    return GeminiClient(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL)


_PROVIDER_API_KEYS = {
    "gemini": lambda: config.GEMINI_API_KEY,
    "groq": lambda: config.GROQ_API_KEY,
    "openai": lambda: config.OPENAI_API_KEY,
}


def get_llm_clients() -> list:
    """Clients for every configured provider, tried in this order: the
    provider set in LLM_PROVIDER first, then the other two (skipping any
    without an API key). A rate-limited/quota-exhausted provider then just
    falls through to the next one instead of failing the whole request."""
    primary = config.LLM_PROVIDER if config.LLM_PROVIDER in _PROVIDER_API_KEYS else "gemini"
    order = [primary, *[p for p in _PROVIDER_API_KEYS if p != primary]]
    return [get_llm_client(provider) for provider in order if _PROVIDER_API_KEYS[provider]()]


def _override(requested, default):
    """Use a caller-supplied value whenever one was actually supplied.

    `requested or default` would silently discard an explicit 0 / 0.0 — a
    similarity_threshold of 0 ("never abstain") is a legitimate experiment
    setting, not an absent one.
    """
    return default if requested is None else requested


class ChatTurn(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    question: str
    history: list[ChatTurn] | None = None
    sticky_profile: dict | None = None
    top_k: int | None = None
    similarity_threshold: float | None = None
    retrieval_mode: str | None = None
    rewrite_query: bool | None = None


class ProfileQueryRequest(BaseModel):
    profile: dict
    free_text_question: str = ""
    history: list[ChatTurn] | None = None
    top_k: int | None = None
    similarity_threshold: float | None = None
    retrieval_mode: str | None = None
    rewrite_query: bool | None = None


def _history_payload(turns: list[ChatTurn] | None) -> list[dict] | None:
    if not turns:
        return None
    return [{"role": turn.role, "content": turn.content} for turn in turns]


@app.post("/api/query")
def query(
    request: QueryRequest,
    diagnostics: str | None = None,
    rag_index: RagIndex = Depends(get_rag_index),
    llm_clients: list = Depends(get_llm_clients),
):
    try:
        return _call_with_llm_fallback(
            answer_general_question,
            request.question,
            rag_index,
            llm_clients=llm_clients,
            top_k=_override(request.top_k, config.TOP_K),
            similarity_threshold=_override(request.similarity_threshold, config.SIMILARITY_THRESHOLD),
            retrieval_mode=_override(request.retrieval_mode, config.RETRIEVAL_MODE),
            rewrite_query=_override(request.rewrite_query, config.ENABLE_QUERY_REWRITE),
            diagnostics_full=diagnostics == "full",
            history=_history_payload(request.history),
            sticky_profile=request.sticky_profile,
        )
    except LLM_PROVIDER_ERRORS:
        raise HTTPException(status_code=503, detail=LLM_PROVIDER_ERROR_DETAIL)


@app.post("/api/profile-query")
def profile_query(
    request: ProfileQueryRequest,
    diagnostics: str | None = None,
    rag_index: RagIndex = Depends(get_rag_index),
    llm_clients: list = Depends(get_llm_clients),
):
    try:
        return _call_with_llm_fallback(
            answer_profile_question,
            request.profile,
            rag_index,
            llm_clients=llm_clients,
            free_text_question=request.free_text_question,
            top_k=_override(request.top_k, config.TOP_K),
            similarity_threshold=_override(request.similarity_threshold, config.SIMILARITY_THRESHOLD),
            retrieval_mode=_override(request.retrieval_mode, config.RETRIEVAL_MODE),
            rewrite_query=_override(request.rewrite_query, config.ENABLE_QUERY_REWRITE),
            diagnostics_full=diagnostics == "full",
            history=_history_payload(request.history),
        )
    except ShortlistFormatError:
        raise HTTPException(
            status_code=502,
            detail="The assistant returned an invalid response; please try again.",
        )
    except LLM_PROVIDER_ERRORS:
        raise HTTPException(status_code=503, detail=LLM_PROVIDER_ERROR_DETAIL)


def _index_built_at() -> str | None:
    """Prefers the real timestamp ingestion.build_index writes at build time
    (data/chroma/build_info.json) over metadata.jsonl's mtime, which a git
    checkout, file copy, or Drive resync can reset without anything having
    actually been rebuilt -- making the stale-index banner lie either way.
    Falls back to mtime only for an index built before this file existed."""
    build_info_path = Path(config.CHROMA_METADATA_PATH).parent / "build_info.json"
    if build_info_path.exists():
        try:
            return json.loads(build_info_path.read_text(encoding="utf-8"))["built_at"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    metadata_path = Path(config.CHROMA_METADATA_PATH)
    if metadata_path.exists():
        return datetime.fromtimestamp(metadata_path.stat().st_mtime, tz=timezone.utc).isoformat()
    return None


@app.get("/api/config")
def get_config():
    index_built_at = _index_built_at()
    return {
        "top_k": config.TOP_K,
        "similarity_threshold": config.SIMILARITY_THRESHOLD,
        "retrieval_mode": config.RETRIEVAL_MODE,
        "llm_provider": config.LLM_PROVIDER,
        "rewrite_query": config.ENABLE_QUERY_REWRITE,
        "index_built_at": index_built_at,
        "chat_history_max_turns": config.CHAT_HISTORY_MAX_TURNS,
    }


def mount_media(target_app: FastAPI, raw_dir: Path) -> bool:
    """Mount only data/raw/images/ so the sources panel can show thumbnails.

    Scoped to the images subtree on purpose: mounting all of data/raw/ would
    publish the whole corpus — source PDFs and videos included — as arbitrary
    static downloads, when the UI only ever requests infographic thumbnails.

    Mounted at /media/images so the on-disk-path-to-URL mapping in
    frontend/app.js (`.../raw/<rest>` -> `/media/<rest>`) still resolves, while
    any non-image path under it simply has no route and 404s.

    Returns whether the mount was registered; a machine that has not ingested
    anything yet has no data/raw/ and must still start.
    """
    images_dir = Path(raw_dir) / "images"
    if not images_dir.exists():
        return False
    target_app.mount("/media/images", StaticFiles(directory=str(images_dir)), name="media")
    return True


mount_media(app, config.DATA_DIR / "raw")

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
