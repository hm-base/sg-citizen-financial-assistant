from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from generation.gemini_client import GeminiClient
from generation.grok_client import GrokClient
from generation.pipeline import RagIndex, answer_general_question, answer_profile_question
from ingestion.build_index import load_metadata
from retrieval.bm25_index import build_bm25_index
from retrieval.embed import load_embedder
from retrieval.faiss_index import load_faiss_index

app = FastAPI(title="SG Citizen Financial Assistant")

_rag_index_cache: RagIndex | None = None


INDEX_MISSING_DETAIL = (
    "Knowledge base index not found — run `python -m ingestion.build_index` first"
)


def get_rag_index() -> RagIndex:
    global _rag_index_cache
    if _rag_index_cache is None:
        missing = [
            path
            for path in (config.FAISS_INDEX_PATH, config.FAISS_METADATA_PATH)
            if not Path(path).exists()
        ]
        if missing:
            raise HTTPException(status_code=503, detail=INDEX_MISSING_DETAIL)
        chunk_records = load_metadata(config.FAISS_METADATA_PATH)
        _rag_index_cache = RagIndex(
            faiss_index=load_faiss_index(config.FAISS_INDEX_PATH),
            bm25_index=build_bm25_index([record["text"] for record in chunk_records]),
            chunk_records=chunk_records,
            embedder=load_embedder(config.EMBEDDING_MODEL),
        )
    return _rag_index_cache


def get_llm_client():
    if config.LLM_PROVIDER == "grok":
        return GrokClient(api_key=config.GROK_API_KEY, model_name=config.GROK_MODEL)
    return GeminiClient(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL)


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None
    similarity_threshold: float | None = None
    retrieval_mode: str | None = None


class ProfileQueryRequest(BaseModel):
    profile: dict
    free_text_question: str = ""
    top_k: int | None = None
    similarity_threshold: float | None = None
    retrieval_mode: str | None = None


@app.post("/api/query")
def query(
    request: QueryRequest,
    rag_index: RagIndex = Depends(get_rag_index),
    llm_client=Depends(get_llm_client),
):
    return answer_general_question(
        request.question,
        rag_index,
        llm_client,
        top_k=request.top_k or config.TOP_K,
        similarity_threshold=request.similarity_threshold or config.SIMILARITY_THRESHOLD,
        retrieval_mode=request.retrieval_mode or config.RETRIEVAL_MODE,
    )


@app.post("/api/profile-query")
def profile_query(
    request: ProfileQueryRequest,
    rag_index: RagIndex = Depends(get_rag_index),
    llm_client=Depends(get_llm_client),
):
    return answer_profile_question(
        request.profile,
        rag_index,
        llm_client,
        free_text_question=request.free_text_question,
        top_k=request.top_k or config.TOP_K,
        similarity_threshold=request.similarity_threshold or config.SIMILARITY_THRESHOLD,
        retrieval_mode=request.retrieval_mode or config.RETRIEVAL_MODE,
    )


@app.get("/api/config")
def get_config():
    return {
        "top_k": config.TOP_K,
        "similarity_threshold": config.SIMILARITY_THRESHOLD,
        "retrieval_mode": config.RETRIEVAL_MODE,
        "llm_provider": config.LLM_PROVIDER,
    }


_raw_dir = config.DATA_DIR / "raw"
if _raw_dir.exists():
    # Serves source infographics so the sources panel can show thumbnails.
    app.mount("/media", StaticFiles(directory=str(_raw_dir)), name="media")

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
