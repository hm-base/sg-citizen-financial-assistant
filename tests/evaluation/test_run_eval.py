import numpy as np

from evaluation.run_eval import compute_aggregate_metrics, run_comparison, run_single_question
from generation.pipeline import RagIndex
from retrieval.bm25_index import build_bm25_index
from retrieval.faiss_index import build_faiss_index


class FakeEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


class FakeLLMClient:
    def generate(self, prompt: str) -> str:
        return "You may get up to $850 [GST Voucher, FAQ]."


def _rag_index():
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


def test_run_single_question_returns_log_row():
    question_entry = {"id": "F1", "category": "factual", "question": "GST voucher amount"}
    row = run_single_question(
        question_entry, _rag_index(), FakeLLMClient(),
        retrieval_mode="dense", top_k=3, similarity_threshold=0.3,
    )
    assert row["id"] == "F1"
    assert row["retrieved_chunk_ids"] == ["gst-voucher_text_000"]
    assert row["abstained"] is False


def test_compute_aggregate_metrics_skips_questions_without_labels():
    rows = [{"id": "F1", "retrieved_chunk_ids": ["gst-voucher_text_000"]}]
    test_set = [{"id": "F1", "expected_relevant_chunk_ids": ["gst-voucher_text_000"]}]

    metrics = compute_aggregate_metrics(rows, test_set)

    assert metrics["hit_rate"] == 1.0
    assert metrics["recall_at_k"] == 1.0
    assert metrics["mrr"] == 1.0


def test_compute_aggregate_metrics_returns_none_when_no_labels():
    rows = [{"id": "F1", "retrieved_chunk_ids": ["gst-voucher_text_000"]}]
    test_set = [{"id": "F1", "expected_relevant_chunk_ids": []}]

    metrics = compute_aggregate_metrics(rows, test_set)

    assert metrics == {"hit_rate": None, "recall_at_k": None, "mrr": None}


def test_run_comparison_runs_both_retrieval_modes():
    test_set = [{"id": "F1", "category": "factual", "question": "GST voucher amount", "expected_relevant_chunk_ids": ["gst-voucher_text_000"]}]

    comparison = run_comparison(test_set, _rag_index(), FakeLLMClient())

    assert set(comparison.keys()) == {"dense", "hybrid"}
    assert comparison["dense"]["metrics"]["hit_rate"] == 1.0
    assert comparison["hybrid"]["metrics"]["hit_rate"] == 1.0
    assert "rows" in comparison["dense"] and "rows" in comparison["hybrid"]
