import json
from pathlib import Path

from evaluation.metrics import hit_rate, mean_of, reciprocal_rank, recall_at_k
from generation.pipeline import RagIndex, answer_general_question, answer_profile_question


def run_single_question(
    question_entry: dict,
    rag_index: RagIndex,
    llm_client,
    *,
    retrieval_mode: str,
    top_k: int,
    similarity_threshold: float,
) -> dict:
    if question_entry["category"] == "profile":
        result = answer_profile_question(
            question_entry["profile"],
            rag_index,
            llm_client,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            retrieval_mode=retrieval_mode,
        )
    else:
        result = answer_general_question(
            question_entry["question"],
            rag_index,
            llm_client,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            retrieval_mode=retrieval_mode,
        )

    return {
        "id": question_entry["id"],
        "category": question_entry["category"],
        "retrieved_chunk_ids": [source["chunk_id"] for source in result["sources"]],
        "generated_answer": result["answer"],
        "abstained": result["abstained"],
    }


def compute_aggregate_metrics(rows: list[dict], test_set: list[dict]) -> dict:
    labeled_by_id = {
        entry["id"]: set(entry["expected_relevant_chunk_ids"])
        for entry in test_set
        if entry.get("expected_relevant_chunk_ids")
    }
    rows_by_id = {row["id"]: row for row in rows}

    hit_rates, recalls, rr_values = [], [], []
    for question_id, relevant_ids in labeled_by_id.items():
        retrieved_ids = rows_by_id[question_id]["retrieved_chunk_ids"]
        hit_rates.append(hit_rate(retrieved_ids, relevant_ids))
        recalls.append(recall_at_k(retrieved_ids, relevant_ids))
        rr_values.append(reciprocal_rank(retrieved_ids, relevant_ids))

    if not hit_rates:
        return {"hit_rate": None, "recall_at_k": None, "mrr": None}

    return {
        "hit_rate": mean_of(hit_rates),
        "recall_at_k": mean_of(recalls),
        "mrr": mean_of(rr_values),
    }


def run_comparison(
    test_set: list[dict],
    rag_index: RagIndex,
    llm_client,
    *,
    top_k: int = 5,
    similarity_threshold: float = 0.35,
) -> dict:
    comparison = {}
    for mode in ("dense", "hybrid"):
        rows = [
            run_single_question(
                entry, rag_index, llm_client,
                retrieval_mode=mode, top_k=top_k, similarity_threshold=similarity_threshold,
            )
            for entry in test_set
        ]
        comparison[mode] = {"rows": rows, "metrics": compute_aggregate_metrics(rows, test_set)}
    return comparison


def save_comparison(comparison: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for mode, payload in comparison.items():
        with open(output_dir / f"{mode}_results.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    import config
    from backend.main import get_llm_client, get_rag_index

    with open(Path(__file__).parent / "test_set.json", encoding="utf-8") as handle:
        test_set = json.load(handle)

    rag_index = get_rag_index()
    llm_client = get_llm_client()
    comparison = run_comparison(
        test_set, rag_index, llm_client,
        top_k=config.TOP_K, similarity_threshold=config.SIMILARITY_THRESHOLD,
    )
    save_comparison(comparison, Path(__file__).parent / "results")

    for mode, payload in comparison.items():
        print(f"{mode}: {payload['metrics']}")
