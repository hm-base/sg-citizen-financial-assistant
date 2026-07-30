import chromadb
import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.main
from backend.main import app, get_llm_client, get_llm_clients, get_rag_index
from generation.pipeline import RagIndex
from retrieval.bm25_index import build_bm25_index
from retrieval.chroma_index import build_chroma_collection, upsert_chunks


def _chroma_collection_from(chunk_records: list[dict], vectors: np.ndarray):
    client = chromadb.EphemeralClient()
    collection = build_chroma_collection(client, "test-collection")
    upsert_chunks(
        collection,
        [record["chunk_id"] for record in chunk_records],
        vectors,
        documents=[record.get("text", "") for record in chunk_records],
        metadatas=[{"doc_id": record.get("chunk_id", "")} for record in chunk_records],
    )
    return collection


class FakeEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False, **kwargs):
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


def _fake_rag_index():
    chunk_records = [{
        "chunk_id": "gst-voucher_text_000",
        "scheme_name": "GST Voucher",
        "category": "Household",
        "section_or_page": "FAQ",
        "text": "GST Voucher gives eligible households up to $850 in cash.",
    }]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    return RagIndex(
        chroma_collection=_chroma_collection_from(chunk_records, vectors),
        bm25_index=build_bm25_index([chunk_records[0]["text"]]),
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )


def test_api_query_returns_grounded_answer():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )]
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?"})

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert "GST Voucher" in body["answer"]
    assert body["sources"][0]["scheme_name"] == "GST Voucher"
    app.dependency_overrides.clear()


def test_api_query_accepts_history_and_reports_history_turns():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )]
    client = TestClient(app)

    response = client.post("/api/query", json={
        "question": "How much is that?",
        "history": [
            {"role": "user", "content": "Tell me about GST Voucher"},
            {"role": "assistant", "content": "GST Voucher gives cash to eligible households."},
        ],
    })

    assert response.status_code == 200
    body = response.json()
    assert body["diagnostics"]["history_turns"] == 2
    app.dependency_overrides.clear()


def test_api_config_includes_chat_history_max_turns():
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["chat_history_max_turns"] >= 1


def test_api_profile_query_returns_shortlist():
    import json

    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient(json.dumps([
        {
            "scheme": "GST Voucher",
            "reason": "Citizenship and income band match the stated criteria.",
            "amount": "$850",
            "conditions": [{"label": "Singapore Citizen", "state": "met"}],
            "changer": "A higher home annual value would reduce the amount.",
            "citation_chunk_ids": ["gst-voucher_text_000"],
        },
    ]))]
    client = TestClient(app)

    response = client.post(
        "/api/profile-query",
        json={"profile": {"age": 68, "life_stage_tags": []}, "free_text_question": "GST voucher amount"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["shortlist"][0]["scheme"] == "GST Voucher"
    assert body["shortlist"][0]["group"] == "eligible"
    app.dependency_overrides.clear()


def test_api_profile_query_returns_502_when_llm_never_returns_valid_json():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient("not json, sorry")]
    client = TestClient(app)

    response = client.post(
        "/api/profile-query",
        json={"profile": {"age": 68, "life_stage_tags": []}, "free_text_question": "GST voucher amount"},
    )

    assert response.status_code == 502
    app.dependency_overrides.clear()


class RaisingLLMClient:
    """Simulates a provider SDK raising its own exception type on generate()."""

    def __init__(self, exc: Exception):
        self.exc = exc

    def generate(self, prompt: str) -> str:
        raise self.exc


def _groq_rate_limit_error():
    import httpx
    from openai import APIStatusError

    response = httpx.Response(
        429, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    )
    return APIStatusError("rate limited", response=response, body=None)


def _gemini_quota_error():
    from google.genai.errors import ClientError

    return ClientError(429, {"error": {"message": "quota exceeded"}})


@pytest.mark.parametrize("make_error", [_groq_rate_limit_error, _gemini_quota_error])
def test_api_query_returns_503_when_all_llm_providers_error(make_error):
    """A provider-side rate limit/quota error must surface as a clear 503, not
    an unhandled 500 with a raw traceback and no actionable message, once
    every configured provider has failed the same way."""
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [RaisingLLMClient(make_error())]
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?"})

    assert response.status_code == 503
    assert "rate limit or quota" in response.json()["detail"]
    app.dependency_overrides.clear()


def test_api_profile_query_returns_503_when_all_llm_providers_error():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [RaisingLLMClient(_groq_rate_limit_error())]
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/profile-query",
        json={"profile": {"age": 68, "life_stage_tags": []}, "free_text_question": "GST voucher amount"},
    )

    assert response.status_code == 503
    assert "rate limit or quota" in response.json()["detail"]
    app.dependency_overrides.clear()


def test_api_query_falls_back_to_next_provider_when_first_is_rate_limited():
    """The whole point of the fallback list: a rate-limited/quota-exhausted
    first provider must not fail the request when a later one can serve it."""
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [
        RaisingLLMClient(_groq_rate_limit_error()),
        FakeLLMClient("You may get up to $850 [GST Voucher, FAQ]."),
    ]
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?"})

    assert response.status_code == 200
    assert "GST Voucher" in response.json()["answer"]
    app.dependency_overrides.clear()


def test_get_llm_clients_orders_configured_provider_first_and_skips_missing_keys(monkeypatch):
    monkeypatch.setattr(backend.main.config, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(backend.main.config, "GROQ_API_KEY", "groq-key")
    monkeypatch.setattr(backend.main.config, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(backend.main.config, "OPENAI_API_KEY", None)

    clients = get_llm_clients()

    assert [type(c).__name__ for c in clients] == ["GroqClient", "GeminiClient"]


def test_get_rag_index_raises_503_when_index_files_are_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backend.main, "_rag_index_cache", None)
    monkeypatch.setattr(backend.main.config, "CHROMA_METADATA_PATH", tmp_path / "missing.jsonl")

    with pytest.raises(HTTPException) as excinfo:
        get_rag_index()

    assert excinfo.value.status_code == 503
    assert "ingestion.build_index" in excinfo.value.detail


def test_api_query_returns_503_when_index_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backend.main, "_rag_index_cache", None)
    monkeypatch.setattr(backend.main.config, "CHROMA_METADATA_PATH", tmp_path / "missing.jsonl")
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient("never used")]
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?"})

    assert response.status_code == 503
    assert "Knowledge base index not found" in response.json()["detail"]
    app.dependency_overrides.clear()


def test_api_config_returns_defaults():
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert "top_k" in body
    assert "similarity_threshold" in body
    assert "retrieval_mode" in body
    assert "rewrite_query" in body


def test_api_config_prefers_build_info_json_over_metadata_mtime(tmp_path, monkeypatch):
    """Regression test: index_built_at used to be metadata.jsonl's mtime,
    which a git checkout, file copy, or Drive resync resets without
    anything having actually been rebuilt -- making the stale-index banner
    lie. build_info.json (written by ingestion.build_index) is authoritative
    when present."""
    metadata_path = tmp_path / "chroma" / "metadata.jsonl"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text("", encoding="utf-8")
    (metadata_path.parent / "build_info.json").write_text(
        '{"built_at": "2026-01-01T00:00:00+00:00"}', encoding="utf-8"
    )
    monkeypatch.setattr(backend.main.config, "CHROMA_METADATA_PATH", metadata_path)

    client = TestClient(app)
    response = client.get("/api/config")

    assert response.json()["index_built_at"] == "2026-01-01T00:00:00+00:00"


def test_api_config_falls_back_to_mtime_when_build_info_json_is_absent(tmp_path, monkeypatch):
    """An index built before build_info.json existed must still report a
    timestamp, not None."""
    metadata_path = tmp_path / "chroma" / "metadata.jsonl"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(backend.main.config, "CHROMA_METADATA_PATH", metadata_path)

    client = TestClient(app)
    response = client.get("/api/config")

    assert response.json()["index_built_at"] is not None


def _fake_low_similarity_rag_index():
    """Index whose only chunk sits at cosine 0.3 — below the 0.35 default gate."""
    chunk_records = [{
        "chunk_id": "gst-voucher_text_000",
        "scheme_name": "GST Voucher",
        "category": "Household",
        "section_or_page": "FAQ",
        "text": "GST Voucher gives eligible households up to $850 in cash.",
    }]

    class LowSimilarityEmbedder:
        def encode(self, texts, **kwargs):
            unit = np.array([0.3, np.sqrt(1 - 0.3**2)], dtype=np.float32)
            return np.array([unit for _ in texts], dtype=np.float32)

    return RagIndex(
        chroma_collection=_chroma_collection_from(
            chunk_records, np.array([[1.0, 0.0]], dtype=np.float32)
        ),
        bm25_index=build_bm25_index([chunk_records[0]["text"]]),
        chunk_records=chunk_records,
        embedder=LowSimilarityEmbedder(),
    )


def test_explicit_zero_similarity_threshold_is_not_replaced_by_the_default():
    """threshold=0 means "never abstain" and must not be read as "unset"."""
    app.dependency_overrides[get_rag_index] = _fake_low_similarity_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )]
    client = TestClient(app)

    defaulted = client.post("/api/query", json={"question": "How much is GST Voucher?"})
    explicit_zero = client.post(
        "/api/query",
        json={"question": "How much is GST Voucher?", "similarity_threshold": 0.0},
    )

    # The default 0.35 gate abstains at cosine 0.3 ...
    assert defaulted.json()["abstained"] is True
    # ... so an explicit 0.0 being honoured is observable.
    assert explicit_zero.json()["abstained"] is False
    app.dependency_overrides.clear()


def test_explicit_zero_top_k_is_not_replaced_by_the_default():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient("never used")]
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?", "top_k": 0})

    # top_k=0 retrieves nothing, so the pipeline must abstain rather than
    # silently fall back to config.TOP_K and answer.
    assert response.json()["abstained"] is True
    app.dependency_overrides.clear()


class QueuedLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def test_explicit_rewrite_query_flag_calls_the_llm_for_rewriting_first():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    llm_client = QueuedLLMClient(["GST Voucher", "You may get up to $850 [GST Voucher, FAQ]."])
    app.dependency_overrides[get_llm_clients] = lambda: [llm_client]
    client = TestClient(app)

    response = client.post(
        "/api/query",
        json={"question": "how much is that gst thing", "rewrite_query": True},
    )

    assert response.status_code == 200
    assert response.json()["abstained"] is False
    assert len(llm_client.prompts) == 2
    app.dependency_overrides.clear()


def test_diagnostics_full_query_param_computes_gain():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_clients] = lambda: [FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )]
    client = TestClient(app)

    without_gain = client.post("/api/query", json={"question": "GST voucher amount"})
    with_gain = client.post(
        "/api/query?diagnostics=full", json={"question": "GST voucher amount"}
    )

    assert without_gain.json()["diagnostics"]["gain"] is None
    assert with_gain.json()["diagnostics"]["gain"] is not None
    assert "top1SimRaw" in with_gain.json()["diagnostics"]["gain"]
    app.dependency_overrides.clear()


def test_media_mount_serves_images_but_not_source_pdfs_or_videos(tmp_path):
    from fastapi import FastAPI

    from backend.main import mount_media

    raw_dir = tmp_path / "raw"
    (raw_dir / "images").mkdir(parents=True)
    (raw_dir / "text").mkdir(parents=True)
    (raw_dir / "video").mkdir(parents=True)
    (raw_dir / "images" / "comcare-steps.png").write_bytes(b"fake png bytes")
    (raw_dir / "text" / "internal-source.pdf").write_bytes(b"fake pdf bytes")
    (raw_dir / "video" / "briefing.mp4").write_bytes(b"fake mp4 bytes")

    scoped_app = FastAPI()
    assert mount_media(scoped_app, raw_dir) is True
    client = TestClient(scoped_app)

    assert client.get("/media/images/comcare-steps.png").content == b"fake png bytes"
    # The rest of the corpus must not be reachable as static files at all.
    assert client.get("/media/text/internal-source.pdf").status_code == 404
    assert client.get("/media/video/briefing.mp4").status_code == 404


def test_media_mount_is_skipped_when_the_corpus_has_not_been_ingested(tmp_path):
    """A fresh clone with no data/raw/ must still start rather than raise."""
    from fastapi import FastAPI

    from backend.main import mount_media

    scoped_app = FastAPI()

    assert mount_media(scoped_app, tmp_path / "does-not-exist") is False
    assert TestClient(scoped_app).get("/media/images/anything.png").status_code == 404
