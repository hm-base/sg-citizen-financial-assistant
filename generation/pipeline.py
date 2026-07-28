import logging
from dataclasses import dataclass

import numpy as np

from config import FALLBACK_MESSAGE
from generation.prompts import build_general_qa_prompt, build_profile_prompt, extract_cited_scheme_labels
from retrieval.bm25_index import search_bm25_index
from retrieval.embed import embed_texts
from retrieval.faiss_index import search_faiss_index
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.profile_filter import infer_preferred_categories, rerank_by_category

logger = logging.getLogger(__name__)


@dataclass
class RagIndex:
    faiss_index: object
    bm25_index: object
    chunk_records: list[dict]
    embedder: object


def dense_score_for_chunk(faiss_index, query_vector: np.ndarray, row_index: int) -> float:
    """Cosine similarity between the query and one specific indexed chunk.

    Vectors are stored L2-normalised in an IndexFlatIP, so the inner product of
    the reconstructed chunk vector with the query vector *is* the cosine score,
    on exactly the same scale as `similarity_threshold`.
    """
    try:
        chunk_vector = faiss_index.reconstruct(int(row_index))
    except Exception:  # noqa: BLE001 - index type may not support reconstruction
        return float("-inf")
    return float(np.dot(np.asarray(query_vector[0], dtype=np.float32),
                        np.asarray(chunk_vector, dtype=np.float32)))


def _retrieve(
    query: str, rag_index: RagIndex, top_k: int, retrieval_mode: str
) -> tuple[list[tuple[int, float]], float]:
    """Returns (results_for_ranking, gate_score).

    `results_for_ranking` is dense-only in "dense" mode, or RRF-fused with BM25
    otherwise. `gate_score` is always a raw dense cosine similarity — the only
    scale comparable to `similarity_threshold` (RRF scores are ~<=0.033) — but it
    is the cosine score of the *top-ranked returned chunk*, so in hybrid mode a
    BM25-surfaced chunk carries the gate for the answer it actually grounds,
    rather than a dense top-1 chunk that fusion may have dropped from the context.
    """
    query_vector = embed_texts([query], rag_index.embedder)
    dense_results = search_faiss_index(rag_index.faiss_index, query_vector, top_k)

    if retrieval_mode == "dense":
        dense_top_score = dense_results[0][1] if dense_results else float("-inf")
        return dense_results, dense_top_score

    bm25_results = search_bm25_index(rag_index.bm25_index, query, top_k)
    fused = reciprocal_rank_fusion([dense_results, bm25_results])[:top_k]
    if not fused:
        return fused, float("-inf")

    top_row_index = fused[0][0]
    dense_scores_by_row = dict(dense_results)
    if top_row_index in dense_scores_by_row:
        gate_score = dense_scores_by_row[top_row_index]
    else:
        gate_score = dense_score_for_chunk(rag_index.faiss_index, query_vector, top_row_index)
    return fused, gate_score


def _abstain_result() -> dict:
    return {"answer": FALLBACK_MESSAGE, "sources": [], "abstained": True, "citation_warning": None}


def _records_with_scores(rag_index: RagIndex, results: list[tuple[int, float]]) -> list[dict]:
    """Copy chunk records and attach the retrieval score used to rank them."""
    return [{**rag_index.chunk_records[idx], "score": float(score)} for idx, score in results]


def _generate_result(prompt: str, retrieved_records: list[dict], llm_client) -> dict:
    answer = llm_client.generate(prompt)
    cited = extract_cited_scheme_labels(answer)
    allowed = {(r["scheme_name"], r["section_or_page"]) for r in retrieved_records}
    warnings = [pair for pair in cited if (pair[0].strip(), pair[1].strip()) not in allowed]
    if warnings:
        logger.warning(
            "Citation warning: answer cites %d label(s) not present in the retrieved sources: %s",
            len(warnings),
            "; ".join(f"[{scheme}, {section}]" for scheme, section in warnings),
        )
    return {
        "answer": answer,
        "sources": retrieved_records,
        "abstained": False,
        "citation_warning": warnings,
    }


def answer_general_question(
    question: str,
    rag_index: RagIndex,
    llm_client,
    *,
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
) -> dict:
    results, gate_score = _retrieve(question, rag_index, top_k, retrieval_mode)
    if not results or gate_score < similarity_threshold:
        return _abstain_result()

    retrieved_records = _records_with_scores(rag_index, results)
    prompt = build_general_qa_prompt(question, retrieved_records)
    return _generate_result(prompt, retrieved_records, llm_client)


def answer_profile_question(
    profile: dict,
    rag_index: RagIndex,
    llm_client,
    *,
    free_text_question: str = "",
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
) -> dict:
    query = free_text_question or (
        f"Singapore subsidy eligibility and payout amounts for profile: {profile}"
    )
    candidate_pool_size = max(top_k * 3, 15)
    candidates, gate_score = _retrieve(query, rag_index, candidate_pool_size, retrieval_mode)
    if not candidates or gate_score < similarity_threshold:
        return _abstain_result()

    preferred_categories = infer_preferred_categories(profile)
    reranked = rerank_by_category(candidates, rag_index.chunk_records, preferred_categories, top_k)

    retrieved_records = _records_with_scores(rag_index, reranked)
    prompt = build_profile_prompt(profile, retrieved_records, free_text_question)
    return _generate_result(prompt, retrieved_records, llm_client)
