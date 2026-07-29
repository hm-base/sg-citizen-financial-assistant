import logging
from dataclasses import dataclass

from config import FALLBACK_MESSAGE
from generation.prompts import (
    build_general_qa_prompt,
    build_profile_prompt,
    build_query_rewrite_prompt,
    extract_cited_scheme_labels,
)
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


def _retrieve(
    query: str, rag_index: RagIndex, top_k: int, retrieval_mode: str
) -> tuple[list[tuple[int, float]], float]:
    """Returns (results_for_ranking, gate_score).

    `results_for_ranking` is dense-only in "dense" mode, or RRF-fused with BM25
    otherwise.

    `gate_score` is always a raw dense cosine similarity, because that is the
    only scale comparable to `similarity_threshold` (RRF scores are ~<=0.033).
    Specifically it is the *maximum* dense cosine over the chunks actually
    returned in context — i.e. the best real dense evidence the answer is
    allowed to draw on, which is how spec §5.2's "top retrieved similarity
    score" is meant. Taking the maximum over the whole returned set, rather than
    the cosine of whichever chunk happens to rank first, is what makes hybrid
    mode's gate provably equal to dense mode's:

    - Dense mode's gate is the dense top-1 cosine.
    - Under RRF, the dense top-1 chunk can never be truncated out of the fused
      top-k. It scores at least 1/(k_rrf+1); the only chunks that can outscore
      that are ones appearing in *both* input lists, and if the dense top-1 is
      absent from the BM25 list there are at most top_k-1 such chunks. So it
      always lands within the first top_k fused slots and its cosine is always
      in the max below.

    Consequence, stated plainly: under exhaustive IndexFlatIP search plus RRF,
    "hybrid rescues a query that dense abstains on" is not achievable by
    construction — the two modes always make the identical gate decision. The
    gate's only job here is to guarantee hybrid is never *more* abstention-prone
    than dense. Hybrid's actual benefit is re-ranking what reaches the prompt,
    and must be demonstrated with Hit Rate / Recall / MRR in the evaluation, not
    with abstention behaviour.
    """
    query_vector = embed_texts([query], rag_index.embedder)
    dense_results = search_faiss_index(rag_index.faiss_index, query_vector, top_k)

    if retrieval_mode == "dense":
        dense_top_score = dense_results[0][1] if dense_results else float("-inf")
        return dense_results, dense_top_score

    bm25_results = search_bm25_index(rag_index.bm25_index, query, top_k)
    fused = reciprocal_rank_fusion([dense_results, bm25_results])[:top_k]

    # BM25-only chunks have no dense cosine and simply do not vote on the gate;
    # they can add evidence to the prompt but never withhold it.
    dense_scores_by_row = dict(dense_results)
    dense_scores_in_context = [
        dense_scores_by_row[row_index]
        for row_index, _fused_score in fused
        if row_index in dense_scores_by_row
    ]
    gate_score = max(dense_scores_in_context) if dense_scores_in_context else float("-inf")
    return fused, gate_score


def _rewrite_query(question: str, llm_client) -> str:
    """Rewrite a question into retrieval-friendly search terms.

    Used only to pick which chunks to retrieve; the original question is
    still what gets answered and cited, so a bad rewrite can only hurt
    recall, never make the answer address the wrong question.
    """
    rewritten = llm_client.generate(build_query_rewrite_prompt(question)).strip()
    return rewritten or question


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
    rewrite_query: bool = False,
) -> dict:
    search_query = _rewrite_query(question, llm_client) if rewrite_query else question
    results, gate_score = _retrieve(search_query, rag_index, top_k, retrieval_mode)
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
    rewrite_query: bool = False,
) -> dict:
    query = free_text_question or (
        f"Singapore subsidy eligibility and payout amounts for profile: {profile}"
    )
    search_query = _rewrite_query(query, llm_client) if rewrite_query else query
    candidate_pool_size = max(top_k * 3, 15)
    candidates, gate_score = _retrieve(search_query, rag_index, candidate_pool_size, retrieval_mode)
    if not candidates or gate_score < similarity_threshold:
        return _abstain_result()

    preferred_categories = infer_preferred_categories(profile)
    reranked = rerank_by_category(candidates, rag_index.chunk_records, preferred_categories, top_k)

    retrieved_records = _records_with_scores(rag_index, reranked)
    prompt = build_profile_prompt(profile, retrieved_records, free_text_question)
    return _generate_result(prompt, retrieved_records, llm_client)
