import json

import chromadb
import numpy as np

from evaluation.run_eval import (
    RUBRIC_FIELDS,
    compute_aggregate_metrics,
    load_test_set,
    missing_labels_warning,
    run_comparison,
    run_single_question,
    save_comparison,
)
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
        chroma_collection=_chroma_collection_from(chunk_records, vectors),
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


def test_run_single_question_logs_retrieval_scores():
    question_entry = {"id": "F1", "category": "factual", "question": "GST voucher amount"}
    row = run_single_question(
        question_entry, _rag_index(), FakeLLMClient(),
        retrieval_mode="dense", top_k=3, similarity_threshold=0.3,
    )
    assert row["retrieved_scores"] == [1.0]
    assert len(row["retrieved_scores"]) == len(row["retrieved_chunk_ids"])


def test_run_single_question_includes_blank_human_rubric_columns():
    question_entry = {"id": "F1", "category": "factual", "question": "GST voucher amount"}
    row = run_single_question(
        question_entry, _rag_index(), FakeLLMClient(),
        retrieval_mode="dense", top_k=3, similarity_threshold=0.3,
    )
    assert RUBRIC_FIELDS == ("correctness_score", "faithfulness_score", "citation_accuracy_score")
    for field in RUBRIC_FIELDS:
        assert field in row
        assert row[field] is None


class FakeShortlistLLMClient:
    def generate(self, prompt: str) -> str:
        return json.dumps([{
            "scheme": "GST Voucher",
            "reason": "Matches the stated criteria.",
            "conditions": [{"label": "Singapore Citizen", "state": "met"}],
            "changer": "n/a",
            "citation_chunk_ids": ["gst-voucher_text_000"],
        }])


def test_run_single_question_serializes_profile_shortlist_as_json():
    question_entry = {
        "id": "P1",
        "category": "profile",
        "profile": {"age": 68, "life_stage_tags": []},
    }
    row = run_single_question(
        question_entry, _rag_index(), FakeShortlistLLMClient(),
        retrieval_mode="dense", top_k=3, similarity_threshold=0.3,
    )

    parsed = json.loads(row["generated_answer"])
    assert parsed[0]["scheme"] == "GST Voucher"
    assert row["citation_warning"] == []


def test_save_comparison_writes_json_and_csv(tmp_path):
    comparison = {
        "dense": {
            "rows": [{
                "id": "F1",
                "category": "factual",
                "retrieved_chunk_ids": ["gst-voucher_text_000"],
                "retrieved_scores": [1.0],
                "generated_answer": "answer",
                "abstained": False,
                "correctness_score": None,
                "faithfulness_score": None,
                "citation_accuracy_score": None,
            }],
            "metrics": {"hit_rate": 1.0, "recall_at_k": 1.0, "mrr": 1.0},
        }
    }

    save_comparison(comparison, tmp_path)

    payload = json.loads((tmp_path / "dense_results.json").read_text(encoding="utf-8"))
    assert payload["rows"][0]["retrieved_scores"] == [1.0]
    csv_text = (tmp_path / "dense_results.csv").read_text(encoding="utf-8")
    assert "correctness_score" in csv_text
    assert "F1" in csv_text


def test_load_test_set_accepts_note_wrapped_and_bare_list_shapes(tmp_path):
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(
        json.dumps({"_note": "labels pending", "questions": [{"id": "F1"}]}), encoding="utf-8"
    )
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps([{"id": "F1"}]), encoding="utf-8")

    assert load_test_set(wrapped) == [{"id": "F1"}]
    assert load_test_set(bare) == [{"id": "F1"}]


def test_real_test_set_file_carries_a_note_and_loads():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "evaluation" / "test_set.json"
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert "_note" in raw
    assert "label" in raw["_note"].lower()
    entries = load_test_set(path)
    assert len(entries) == 15
    assert all("expected_relevant_chunk_ids" in entry for entry in entries)


def test_missing_labels_warning_counts_questions_dynamically():
    test_set = [{"id": f"F{i}", "expected_relevant_chunk_ids": []} for i in range(1, 4)]

    assert missing_labels_warning(test_set) == (
        "WARNING: 0 of 3 questions have labeled expected_relevant_chunk_ids; "
        "retrieval metrics unavailable."
    )


def test_missing_labels_warning_is_none_when_any_question_is_labeled():
    test_set = [
        {"id": "F1", "expected_relevant_chunk_ids": ["a"]},
        {"id": "F2", "expected_relevant_chunk_ids": []},
    ]

    assert missing_labels_warning(test_set) is None


def test_missing_labels_warning_is_none_for_the_shipped_hand_labeled_test_set():
    """The shipped test set was hand-labelled 2026-07-30 against the real
    index (see its _note); 8 of 15 questions have real expected_relevant_chunk_ids,
    so retrieval metrics are available and no warning should fire."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "evaluation" / "test_set.json"

    assert missing_labels_warning(load_test_set(path)) is None


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
