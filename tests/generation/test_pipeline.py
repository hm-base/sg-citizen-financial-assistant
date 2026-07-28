import logging

import numpy as np

from generation.pipeline import (
    RagIndex,
    answer_general_question,
    answer_profile_question,
    dense_score_for_chunk,
)
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


class ThreeChunkEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


def _build_fusion_rag_index():
    """Index where BM25 promotes a chunk that dense ranks third.

    Dense cosine scores against the query vector [1, 0] are 1.0 / 0.9 / 0.85 for
    rows 0 / 1 / 2. Only rows 1 and 2 share vocabulary with the query, so BM25
    ranks row 2 first and RRF fusion puts row 2 at the top overall.
    """
    chunk_records = [
        {
            "chunk_id": "household-support_text_000",
            "scheme_name": "Household Support",
            "category": "Household",
            "section_or_page": "p.1",
            "text": "Household support scheme pays cash to families every quarter.",
        },
        {
            "chunk_id": "gst-voucher_text_001",
            "scheme_name": "GST Voucher",
            "category": "Household",
            "section_or_page": "p.2",
            "text": "Voucher amount depends on annual value of the home.",
        },
        {
            "chunk_id": "gst-voucher_text_002",
            "scheme_name": "GST Voucher",
            "category": "Household",
            "section_or_page": "p.3",
            "text": "GST Voucher amount table lists each gst voucher amount payout tier.",
        },
    ]
    vectors = np.array(
        [[1.0, 0.0], [0.9, np.sqrt(1 - 0.9**2)], [0.85, np.sqrt(1 - 0.85**2)]],
        dtype=np.float32,
    )
    return RagIndex(
        faiss_index=build_faiss_index(vectors),
        bm25_index=build_bm25_index([record["text"] for record in chunk_records]),
        chunk_records=chunk_records,
        embedder=ThreeChunkEmbedder(),
    )


def test_hybrid_gate_uses_dense_score_of_the_top_ranked_fused_chunk():
    """The gate must follow the chunk that actually leads the generated context.

    Dense top-1 (row 0, cosine 1.0) is not what fusion puts first — row 2
    (cosine 0.85) is — so with a 0.9 threshold dense mode answers while hybrid
    mode abstains, because the chunk carrying the answer is below threshold.
    """
    rag_index = _build_fusion_rag_index()

    dense_result = answer_general_question(
        "gst voucher amount",
        rag_index,
        FakeLLMClient("Dense answer [Household Support, p.1]."),
        top_k=3,
        similarity_threshold=0.9,
        retrieval_mode="dense",
    )
    hybrid_result = answer_general_question(
        "gst voucher amount",
        rag_index,
        FakeLLMClient("Hybrid answer [GST Voucher, p.3]."),
        top_k=3,
        similarity_threshold=0.9,
        retrieval_mode="hybrid",
    )

    assert dense_result["abstained"] is False
    assert dense_result["sources"][0]["chunk_id"] == "household-support_text_000"
    assert hybrid_result["abstained"] is True


def test_hybrid_mode_answers_when_the_fused_top_chunk_clears_the_threshold():
    """Same fusion ordering, threshold below the fused top-1's own cosine score."""
    rag_index = _build_fusion_rag_index()
    llm_client = FakeLLMClient("The amount table is here [GST Voucher, p.3].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.8,
        retrieval_mode="hybrid",
    )

    assert result["abstained"] is False
    assert result["sources"][0]["chunk_id"] == "gst-voucher_text_002"
    assert result["citation_warning"] == []


def test_dense_score_for_chunk_returns_cosine_of_that_specific_row():
    rag_index = _build_fusion_rag_index()
    query_vector = np.array([[1.0, 0.0]], dtype=np.float32)

    assert dense_score_for_chunk(rag_index.faiss_index, query_vector, 2) == np.float32(0.85)


def test_dense_score_for_chunk_returns_negative_infinity_when_unreconstructable():
    class NoReconstructIndex:
        def reconstruct(self, row_index):
            raise RuntimeError("reconstruct not supported")

    query_vector = np.array([[1.0, 0.0]], dtype=np.float32)

    assert dense_score_for_chunk(NoReconstructIndex(), query_vector, 0) == float("-inf")


def test_answer_general_question_attaches_retrieval_scores_to_sources():
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

    assert result["sources"][0]["score"] == 1.0
    # Source dicts must be copies, so the shared index metadata stays clean.
    assert "score" not in rag_index.chunk_records[0]


def test_citation_warning_is_logged_as_a_server_warning(caplog):
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get funds [Made Up Scheme, Nowhere].")

    with caplog.at_level(logging.WARNING, logger="generation.pipeline"):
        answer_general_question(
            "gst voucher amount",
            rag_index,
            llm_client,
            top_k=3,
            similarity_threshold=0.3,
            retrieval_mode="dense",
        )

    assert any("Made Up Scheme" in record.getMessage() for record in caplog.records)


def test_no_citation_warning_logged_for_a_fully_grounded_answer(caplog):
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("You may get up to $850 [GST Voucher, FAQ].")

    with caplog.at_level(logging.WARNING, logger="generation.pipeline"):
        answer_general_question(
            "gst voucher amount",
            rag_index,
            llm_client,
            top_k=3,
            similarity_threshold=0.3,
            retrieval_mode="dense",
        )

    assert caplog.records == []


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
