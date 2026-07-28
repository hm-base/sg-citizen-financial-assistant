import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.main
from backend.main import app, get_llm_client, get_rag_index
from generation.pipeline import RagIndex
from retrieval.bm25_index import build_bm25_index
from retrieval.faiss_index import build_faiss_index


class FakeEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
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
        faiss_index=build_faiss_index(vectors),
        bm25_index=build_bm25_index([chunk_records[0]["text"]]),
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )


def test_api_query_returns_grounded_answer():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?"})

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert "GST Voucher" in body["answer"]
    assert body["sources"][0]["scheme_name"] == "GST Voucher"
    app.dependency_overrides.clear()


def test_api_profile_query_returns_shortlist():
    app.dependency_overrides[get_rag_index] = _fake_rag_index
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(
        "Possibly eligible: GST Voucher [GST Voucher, FAQ]."
    )
    client = TestClient(app)

    response = client.post(
        "/api/profile-query",
        json={"profile": {"age": 68, "life_stage_tags": []}, "free_text_question": "GST voucher amount"},
    )

    assert response.status_code == 200
    assert "Possibly eligible" in response.json()["answer"]
    app.dependency_overrides.clear()


def test_get_rag_index_raises_503_when_index_files_are_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backend.main, "_rag_index_cache", None)
    monkeypatch.setattr(backend.main.config, "FAISS_INDEX_PATH", tmp_path / "missing.faiss")
    monkeypatch.setattr(backend.main.config, "FAISS_METADATA_PATH", tmp_path / "missing.jsonl")

    with pytest.raises(HTTPException) as excinfo:
        get_rag_index()

    assert excinfo.value.status_code == 503
    assert "ingestion.build_index" in excinfo.value.detail


def test_api_query_returns_503_when_index_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backend.main, "_rag_index_cache", None)
    monkeypatch.setattr(backend.main.config, "FAISS_INDEX_PATH", tmp_path / "missing.faiss")
    monkeypatch.setattr(backend.main.config, "FAISS_METADATA_PATH", tmp_path / "missing.jsonl")
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient("never used")
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
        faiss_index=build_faiss_index(np.array([[1.0, 0.0]], dtype=np.float32)),
        bm25_index=build_bm25_index([chunk_records[0]["text"]]),
        chunk_records=chunk_records,
        embedder=LowSimilarityEmbedder(),
    )


def test_explicit_zero_similarity_threshold_is_not_replaced_by_the_default():
    """threshold=0 means "never abstain" and must not be read as "unset"."""
    app.dependency_overrides[get_rag_index] = _fake_low_similarity_rag_index
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(
        "You may get up to $850 [GST Voucher, FAQ]."
    )
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
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient("never used")
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "How much is GST Voucher?", "top_k": 0})

    # top_k=0 retrieves nothing, so the pipeline must abstain rather than
    # silently fall back to config.TOP_K and answer.
    assert response.json()["abstained"] is True
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
