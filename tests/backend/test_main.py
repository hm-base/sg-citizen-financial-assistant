import numpy as np
from fastapi.testclient import TestClient

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


def test_api_config_returns_defaults():
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert "top_k" in body
    assert "similarity_threshold" in body
    assert "retrieval_mode" in body
