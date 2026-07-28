import numpy as np

from generation.pipeline import RagIndex, answer_general_question, answer_profile_question
from retrieval.bm25_index import build_bm25_index
from retrieval.faiss_index import build_faiss_index


class FakeEmbedder:
    """Deterministic fake: maps known strings to fixed unit vectors."""

    VECTORS = {
        "gst voucher amount": np.array([1.0, 0.0], dtype=np.float32),
        "unrelated pet question": np.array([0.0, 1.0], dtype=np.float32),
    }

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        return np.array([self.VECTORS.get(text.lower(), [0.0, 0.0]) for text in texts], dtype=np.float32)


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def _build_rag_index():
    chunk_records = [
        {
            "chunk_id": "gst-voucher_text_000",
            "scheme_name": "GST Voucher",
            "category": "Household",
            "section_or_page": "FAQ",
            "text": "GST Voucher gives eligible households up to $850 in cash.",
        },
    ]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    faiss_index = build_faiss_index(vectors)
    bm25_index = build_bm25_index([record["text"] for record in chunk_records])
    return RagIndex(
        faiss_index=faiss_index,
        bm25_index=bm25_index,
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )


def test_answer_general_question_returns_grounded_answer_above_threshold():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get up to $850 [GST Voucher, FAQ].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is False
    assert result["answer"] == "You may get up to $850 [GST Voucher, FAQ]."
    assert result["sources"][0]["scheme_name"] == "GST Voucher"
    assert result["citation_warning"] == []


def test_answer_general_question_abstains_below_threshold_without_calling_llm():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("should never be returned")

    result = answer_general_question(
        "unrelated pet question",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is True
    assert "does not contain enough information" in result["answer"]
    assert llm_client.last_prompt is None


def test_answer_general_question_flags_citation_not_in_retrieved_sources():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get funds [Made Up Scheme, Nowhere].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["citation_warning"] == [("Made Up Scheme", "Nowhere")]


def test_answer_general_question_hybrid_mode_does_not_abstain_on_relevant_query():
    """Regression test: RRF-fused scores (~<=0.033) must not be compared directly
    against similarity_threshold (calibrated for raw dense cosine scores ~0.0-1.0).
    The abstention gate must use the dense score even in hybrid mode."""
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get up to $850 [GST Voucher, FAQ].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="hybrid",
    )

    assert result["abstained"] is False
    assert result["answer"] == "You may get up to $850 [GST Voucher, FAQ]."


def test_answer_profile_question_returns_grounded_shortlist():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("Possibly eligible: GST Voucher [GST Voucher, FAQ].")

    result = answer_profile_question(
        {"age": 68, "life_stage_tags": [], "monthly_income_band": "<$1.5k"},
        rag_index,
        llm_client,
        free_text_question="gst voucher amount",
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is False
    assert "Possibly eligible" in result["answer"]
