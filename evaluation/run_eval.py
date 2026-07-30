import json
from pathlib import Path

import pandas as pd

from evaluation.metrics import hit_rate, mean_of, reciprocal_rank, recall_at_k
from generation.pipeline import RagIndex, answer_general_question, answer_profile_question

#: Human answer-quality rubric, scored 0-2 each by a human reviewer after the run.
RUBRIC_FIELDS = ("correctness_score", "faithfulness_score", "citation_accuracy_score")


def load_test_set(path: Path) -> list[dict]:
    """Load the test set, accepting either a bare list or a `_note`-wrapped object."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if isinstance(raw, dict):
        return raw.get("questions", [])
    return raw


def missing_labels_warning(test_set: list[dict]) -> str | None:
    """Explain why retrieval metrics come back as None when nothing is labeled."""
    labeled = sum(1 for entry in test_set if entry.get("expected_relevant_chunk_ids"))
    if labeled:
        return None
    return (
        f"WARNING: {labeled} of {len(test_set)} questions have labeled "
        "expected_relevant_chunk_ids; retrieval metrics unavailable."
    )


def run_single_question(
    question_entry: dict,
    rag_index: RagIndex,
    llm_client,
    *,
    retrieval_mode: str,
    top_k: int,
    similarity_threshold: float,
    rewrite_query: bool = False,
) -> dict:
    if question_entry["category"] == "profile":
        result = answer_profile_question(
            question_entry["profile"],
            rag_index,
            llm_client,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            retrieval_mode=retrieval_mode,
            rewrite_query=rewrite_query,
        )
    else:
        result = answer_general_question(
            question_entry["question"],
            rag_index,
            llm_client,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            retrieval_mode=retrieval_mode,
            rewrite_query=rewrite_query,
        )

    # Profile questions return a structured "shortlist" (no free-text "answer");
    # serialize it to JSON so both question categories share one CSV/JSON schema.
    if "shortlist" in result:
        generated_answer = json.dumps(result["shortlist"])
        citation_warning = result.get("dev_warnings")
    else:
        generated_answer = result["answer"]
        citation_warning = result.get("citation_warning")

    row = {
        "id": question_entry["id"],
        "category": question_entry["category"],
        "retrieved_chunk_ids": [source["chunk_id"] for source in result["sources"]],
        "retrieved_scores": [source.get("score") for source in result["sources"]],
        "generated_answer": generated_answer,
        "abstained": result["abstained"],
        "citation_warning": citation_warning,
    }
    # Blank columns for the human 0-2 rubric; no automated scoring is attempted.
    row.update({field: None for field in RUBRIC_FIELDS})
    return row


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
    rewrite_query: bool = False,
) -> dict:
    """Query rewriting defaults OFF here even though it defaults on for the
    live app: this comparison exists to isolate dense vs. hybrid *retrieval*,
    and rewriting is a separate, orthogonal variable that would confound it
    if left implicitly on. Pass rewrite_query=True to evaluate the two
    together instead."""
    comparison = {}
    for mode in ("dense", "hybrid"):
        rows = [
            run_single_question(
                entry, rag_index, llm_client,
                retrieval_mode=mode, top_k=top_k, similarity_threshold=similarity_threshold,
                rewrite_query=rewrite_query,
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
        # CSV alongside JSON so the human rubric columns can be filled in a spreadsheet.
        pd.DataFrame(payload["rows"]).to_csv(
            output_dir / f"{mode}_results.csv", index=False, encoding="utf-8"
        )


if __name__ == "__main__":
    import config
    from backend.main import get_llm_clients, get_rag_index

    test_set = load_test_set(Path(__file__).parent / "test_set.json")

    warning = missing_labels_warning(test_set)
    if warning:
        print(warning)

    rag_index = get_rag_index()
    llm_clients = get_llm_clients()
    if not llm_clients:
        raise SystemExit("No LLM provider is configured (all API keys are unset).")
    llm_client = llm_clients[0]
    print(f"Using LLM client: {type(llm_client).__name__}")
    comparison = run_comparison(
        test_set, rag_index, llm_client,
        top_k=config.TOP_K, similarity_threshold=config.SIMILARITY_THRESHOLD,
    )
    save_comparison(comparison, Path(__file__).parent / "results")

    for mode, payload in comparison.items():
        print(f"{mode}: {payload['metrics']}")
