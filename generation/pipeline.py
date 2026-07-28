from dataclasses import dataclass

from config import FALLBACK_MESSAGE
from generation.prompts import build_general_qa_prompt, build_profile_prompt, extract_cited_scheme_labels
from retrieval.bm25_index import search_bm25_index
from retrieval.embed import embed_texts
from retrieval.faiss_index import search_faiss_index
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.profile_filter import infer_preferred_categories, rerank_by_category


@dataclass
class RagIndex:
    faiss_index: object
    bm25_index: object
    chunk_records: list[dict]
    embedder: object


def _retrieve(
    query: str, rag_index: RagIndex, top_k: int, retrieval_mode: str
) -> tuple[list[tuple[int, float]], float]:
    """Returns (results_for_ranking, dense_top_score).

    `results_for_ranking` is dense-only in "dense" mode, or RRF-fused with BM25
    otherwise. `dense_top_score` is always the raw FAISS cosine-similarity top
    score, which is the only score on the same scale as `similarity_threshold`
    and must be used for the abstention gate regardless of retrieval mode.
    """
    query_vector = embed_texts([query], rag_index.embedder)
    dense_results = search_faiss_index(rag_index.faiss_index, query_vector, top_k)
    dense_top_score = dense_results[0][1] if dense_results else float("-inf")

    if retrieval_mode == "dense":
        return dense_results, dense_top_score

    bm25_results = search_bm25_index(rag_index.bm25_index, query, top_k)
    fused = reciprocal_rank_fusion([dense_results, bm25_results])
    return fused[:top_k], dense_top_score


def _abstain_result() -> dict:
    return {"answer": FALLBACK_MESSAGE, "sources": [], "abstained": True, "citation_warning": None}


def _generate_result(prompt: str, retrieved_records: list[dict], llm_client) -> dict:
    answer = llm_client.generate(prompt)
    cited = extract_cited_scheme_labels(answer)
    allowed = {(r["scheme_name"], r["section_or_page"]) for r in retrieved_records}
    warnings = [pair for pair in cited if (pair[0].strip(), pair[1].strip()) not in allowed]
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
    results, dense_top_score = _retrieve(question, rag_index, top_k, retrieval_mode)
    if not results or dense_top_score < similarity_threshold:
        return _abstain_result()

    retrieved_records = [rag_index.chunk_records[idx] for idx, _ in results]
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
    candidates, dense_top_score = _retrieve(query, rag_index, candidate_pool_size, retrieval_mode)
    if not candidates or dense_top_score < similarity_threshold:
        return _abstain_result()

    preferred_categories = infer_preferred_categories(profile)
    reranked = rerank_by_category(candidates, rag_index.chunk_records, preferred_categories, top_k)

    retrieved_records = [rag_index.chunk_records[idx] for idx, _ in reranked]
    prompt = build_profile_prompt(profile, retrieved_records, free_text_question)
    return _generate_result(prompt, retrieved_records, llm_client)
