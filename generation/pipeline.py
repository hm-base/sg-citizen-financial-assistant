import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import config
from config import FALLBACK_MESSAGE
from generation.prompts import (
    build_general_qa_prompt,
    build_profile_shortlist_prompt,
    build_query_rewrite_prompt,
    extract_cited_scheme_labels,
)
from retrieval.bm25_index import search_bm25_index
from retrieval.chroma_index import search_chroma_index
from retrieval.embed import embed_texts
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.profile_filter import infer_preferred_categories, rerank_by_category

logger = logging.getLogger(__name__)


@dataclass
class RagIndex:
    chroma_collection: object
    bm25_index: object
    chunk_records: list[dict]
    embedder: object
    chunk_id_to_index: dict | None = None
    collection_count: int | None = None

    def __post_init__(self):
        # Derived from chunk_records rather than required at every call site:
        # chunk_records order is exactly the positional index space BM25
        # already indexes into (see ingestion.build_index), and each record's
        # chunk_id is what Chroma stores as its own identity -- this map is
        # the translation between the two, built once here.
        if self.chunk_id_to_index is None:
            self.chunk_id_to_index = {
                record["chunk_id"]: index for index, record in enumerate(self.chunk_records)
            }

        # metadata.jsonl and the Chroma collection are two independently
        # persisted artifacts of the same build; a crash mid-persist (or a
        # copy/sync that only moved one of them) can leave them out of sync.
        # This can't repair the drift, but a loud warning beats the silent,
        # unexplained-abstention failure mode of search_chroma_index quietly
        # dropping hits it can't resolve.
        if self.collection_count is None:
            self.collection_count = self.chroma_collection.count()
        record_count = len(self.chunk_records)
        if self.collection_count != record_count:
            logger.warning(
                "Chroma collection has %d chunks but chunk_records (metadata.jsonl) has %d -- "
                "the index and its metadata have drifted out of sync. Consider rebuilding "
                "via `python -m ingestion.build_index`.",
                self.collection_count,
                record_count,
            )


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

    Consequence, stated plainly: under dense search (Chroma's HNSW, an
    approximate index -- not exhaustive) plus RRF, "hybrid rescues a query
    that dense abstains on" is not achievable by construction, *modulo* HNSW's
    own recall<1.0 approximation error — the two modes make the identical
    gate decision as long as both traversals surface the same dense top-1
    chunk, which HNSW does not literally guarantee the way an exhaustive scan
    would. The gate's only job here is to guarantee hybrid is never *more*
    abstention-prone than dense. Hybrid's actual benefit is re-ranking what
    reaches the prompt, and must be demonstrated with Hit Rate / Recall / MRR
    in the evaluation, not with abstention behaviour.
    """
    query_vector = embed_texts([query], rag_index.embedder)
    dense_results = search_chroma_index(
        rag_index.chroma_collection,
        query_vector,
        top_k,
        rag_index.chunk_id_to_index,
        collection_count=rag_index.collection_count,
    )

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


_NRIC_PATTERN = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)


def _strip_nric(text: str) -> tuple[str, bool]:
    """Strip Singapore NRIC/FIN-shaped identifiers before anything downstream
    (including the rewriter's own LLM call) ever sees them."""
    stripped, count = _NRIC_PATTERN.subn("[REDACTED]", text)
    return stripped, count > 0


def _run_with_timeout(fn, timeout_seconds: float):
    """Run `fn` with a hard wall-clock budget. On timeout, stop waiting (the
    thread finishes on its own in the background) rather than blocking the
    request for however long the slow call eventually takes."""
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        return executor.submit(fn).result(timeout=timeout_seconds)
    finally:
        executor.shutdown(wait=False)


def _empty_rewrite_diagnostics(raw: str, question: str, kind: str) -> dict:
    return {
        "raw": raw,
        "rewritten": question,
        "subQueries": [],
        "ops": [{"kind": kind}],
        "inferredSchemes": [],
        "latencyMs": 0.0,
    }


def _parse_rewrite_json(raw_text: str) -> dict:
    parsed = json.loads(_strip_code_fence(raw_text))
    if not isinstance(parsed, dict):
        raise ValueError("Rewrite response must be a JSON object")
    return {
        "rewritten": str(parsed.get("rewritten") or "").strip(),
        "subQueries": [str(q).strip() for q in (parsed.get("subQueries") or []) if str(q).strip()][:4],
        "ops": parsed.get("ops") or [],
        "inferredSchemes": [str(s).strip() for s in (parsed.get("inferredSchemes") or [])],
    }


def _rewrite_query(
    question: str,
    llm_client,
    *,
    enabled: bool,
    profile: dict | None = None,
    timeout_seconds: float | None = None,
) -> dict:
    """Structured query rewrite: expands colloquialisms/abbreviations into scheme
    vocabulary, names likely schemes, and proposes facet sub-queries -- returned
    as a diagnostics object, never as prose. The ORIGINAL question always still
    reaches the answer prompt; this only ever changes what gets retrieved.

    Fails open: a rewrite error or timeout falls back to the raw question and
    is recorded as an "ops": [{"kind": "failed"}] diagnostic -- a rewrite
    problem must never fail the request (contrast with the shortlist's
    fail-loud contract, which is a resident-facing correctness guarantee, not
    an internal retrieval optimization).
    """
    stripped, redacted = _strip_nric(question)
    if not enabled:
        result = _empty_rewrite_diagnostics(question, stripped, "skipped")
    else:
        start = time.perf_counter()
        try:
            prompt = build_query_rewrite_prompt(stripped, profile)
            budget = config.REWRITE_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
            raw = _run_with_timeout(lambda: llm_client.generate(prompt), budget)
            parsed = _parse_rewrite_json(raw)
            result = {
                "raw": question,
                "rewritten": parsed["rewritten"] or stripped,
                "subQueries": parsed["subQueries"],
                "ops": list(parsed["ops"]),
                "inferredSchemes": parsed["inferredSchemes"],
                "latencyMs": round((time.perf_counter() - start) * 1000, 1),
            }
        except Exception:  # noqa: BLE001 - any rewrite failure must fall back, never raise
            result = _empty_rewrite_diagnostics(question, stripped, "failed")
            result["latencyMs"] = round((time.perf_counter() - start) * 1000, 1)

    if redacted:
        result["ops"] = [{"kind": "dropped", "detail": "removed NRIC/FIN-like identifier"}] + result["ops"]
    return result


def _retrieve_fanout(
    queries: list[str], rag_index: "RagIndex", top_k: int, retrieval_mode: str
) -> tuple[list[tuple[int, float]], float, int]:
    """Retrieve for each query independently, merge by chunk row keeping the
    max score, then truncate to top_k. Returns (merged_results, gate_score,
    dropped_count).

    `gate_score` is the max of each query's own gate score: each individual
    gate score already satisfies "no higher real evidence exists in that
    query's context", so the max over several phrasings is still a real,
    grounded score -- just the best one found across the ways the question
    was asked.
    """
    merged: dict[int, float] = {}
    gate_scores = []
    for query in queries:
        results, gate_score = _retrieve(query, rag_index, top_k, retrieval_mode)
        gate_scores.append(gate_score)
        for row_index, score in results:
            if row_index not in merged or score > merged[row_index]:
                merged[row_index] = score

    ranked = sorted(merged.items(), key=lambda item: item[1], reverse=True)
    truncated = ranked[:top_k]
    dropped = len(ranked) - len(truncated)
    gate_score = max(gate_scores) if gate_scores else float("-inf")
    return truncated, gate_score, dropped


def _retrieval_diagnostics(
    top_k: int, similarity_threshold: float, retrieval_mode: str, retrieved_records: list[dict], dropped: int
) -> dict:
    return {
        "topK": top_k,
        "threshold": similarity_threshold,
        "mode": retrieval_mode,
        "chunks": [
            {"chunk_id": r["chunk_id"], "score": r["score"]} for r in retrieved_records
        ],
        "dropped": dropped,
    }


def _compute_gain(
    question: str,
    rewrite: dict,
    rag_index: "RagIndex",
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
) -> dict:
    """Re-run retrieval on the raw (unrewritten) question to compare against
    the rewritten result. Only ever called when the caller explicitly asked
    for full diagnostics, since it doubles retrieval cost.

    `schemesAboveThresholdDelta` compares each candidate's own score directly
    against `similarity_threshold` -- an exact comparison in dense mode; in
    hybrid mode the RRF-fused scores live on a different scale, so the count
    is a best-effort diagnostic there, not a resident-facing gate.
    """
    raw_results, raw_gate = _retrieve(question, rag_index, top_k, retrieval_mode)
    rewritten_results, rewritten_gate = _retrieve(rewrite["rewritten"], rag_index, top_k, retrieval_mode)

    def scheme_count_above_threshold(results):
        return len({
            rag_index.chunk_records[idx]["scheme_name"]
            for idx, score in results
            if score >= similarity_threshold
        })

    return {
        "top1SimRaw": raw_gate,
        "top1SimRewritten": rewritten_gate,
        "schemesAboveThresholdDelta": (
            scheme_count_above_threshold(rewritten_results) - scheme_count_above_threshold(raw_results)
        ),
    }


def _abstain_result() -> dict:
    return {"answer": FALLBACK_MESSAGE, "sources": [], "abstained": True, "citation_warning": None}


def _abstain_shortlist_result() -> dict:
    return {"abstained": True, "shortlist": [], "sources": [], "dev_warnings": []}


class ShortlistFormatError(Exception):
    """The LLM did not return a valid shortlist JSON array, even after a retry."""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```\s*$", "", text)
    return text.strip()


def _parse_shortlist_json(raw_text: str) -> list[dict]:
    cleaned = _strip_code_fence(raw_text)
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ShortlistFormatError(f"Model did not return valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ShortlistFormatError("Expected a JSON array of shortlist entries")
    for entry in parsed:
        if not isinstance(entry, dict) or "scheme" not in entry or "reason" not in entry:
            raise ShortlistFormatError(
                "Each shortlist entry must be an object with at least 'scheme' and 'reason'"
            )
    return parsed


def _generate_shortlist_entries(prompt: str, llm_client) -> list[dict]:
    """Call the LLM for the shortlist JSON, retrying once on a format failure.

    Fails loudly (raises ShortlistFormatError) rather than falling back to
    treating the raw text as a markdown answer -- a malformed response must
    not silently degrade into unstructured prose reaching the view.
    """
    raw = llm_client.generate(prompt)
    try:
        return _parse_shortlist_json(raw)
    except ShortlistFormatError:
        retry_prompt = (
            f"{prompt}\n\nYour previous output was not a valid JSON array. Return ONLY a raw "
            "JSON array, with no markdown code fences and no commentary before or after it."
        )
        raw = llm_client.generate(retry_prompt)
        return _parse_shortlist_json(raw)


def _derive_group(conditions: list[dict]) -> str:
    """Group placement is derived from evaluated conditions, never from the
    model's prose: no conditions -> not assessed; any failed condition ->
    unclear; all met or unchecked -> eligible."""
    if not conditions:
        return "not_assessed"
    if any(condition.get("state") == "not_met" for condition in conditions):
        return "unclear"
    return "eligible"


def _resolve_citations(
    chunk_ids: list[str], chunk_by_id: dict[str, dict]
) -> tuple[list[dict], list[str]]:
    """Resolve chunk ids the model cited into display-ready citation chips.

    Only ids present in `chunk_by_id` (the actual retrieved set) are ever
    resolved -- an id outside that set is dropped and recorded as a
    developer-only warning, never shown to the resident as a scary banner.
    Distinct sources are deduplicated so one heavily-cited passage produces
    one chip, not six.
    """
    citations: list[dict] = []
    dev_warnings: list[str] = []
    seen = set()
    for chunk_id in chunk_ids or []:
        record = chunk_by_id.get(chunk_id)
        if record is None:
            dev_warnings.append(f"Dropped citation to unretrieved chunk_id={chunk_id!r}")
            continue
        dedupe_key = (record.get("display_name") or record["scheme_name"], record["section_or_page"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        citations.append({
            "doc_label": record.get("display_name") or record["scheme_name"],
            "section": record["section_or_page"],
            "chunk_id": chunk_id,
            "score": record.get("score"),
            "text": record.get("text", ""),
        })
    return citations, dev_warnings


def _records_with_scores(rag_index: RagIndex, results: list[tuple[int, float]]) -> list[dict]:
    """Copy chunk records and attach the retrieval score used to rank them."""
    return [{**rag_index.chunk_records[idx], "score": float(score)} for idx, score in results]


def _generate_result(prompt: str, retrieved_records: list[dict], llm_client) -> dict:
    answer = llm_client.generate(prompt)
    if answer.strip() == FALLBACK_MESSAGE:
        # The similarity gate passed, but the model itself judged the
        # retrieved passages too tangential to answer from -- the in-prompt
        # half of the two-layer abstention. Treat it exactly like a gate-level
        # abstain: no sources, since showing "evidence" alongside "not enough
        # information" is self-contradictory to the resident.
        return _abstain_result()
    cited = extract_cited_scheme_labels(answer)
    allowed = {
        (r.get("display_name") or r["scheme_name"], r["section_or_page"]) for r in retrieved_records
    }
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


def _attach_diagnostics(
    result: dict,
    *,
    rewrite: dict,
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
    dropped: int,
    gain: dict | None,
) -> dict:
    result["diagnostics"] = {
        "rewrite": rewrite,
        "retrieval": _retrieval_diagnostics(
            top_k, similarity_threshold, retrieval_mode, result.get("sources", []), dropped
        ),
        "gain": gain,
    }
    return result


def answer_general_question(
    question: str,
    rag_index: RagIndex,
    llm_client,
    *,
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
    rewrite_query: bool = True,
    diagnostics_full: bool = False,
) -> dict:
    rewrite = _rewrite_query(question, llm_client, enabled=rewrite_query)
    queries = [rewrite["rewritten"], *rewrite["subQueries"]]
    results, gate_score, dropped = _retrieve_fanout(queries, rag_index, top_k, retrieval_mode)
    gain = (
        _compute_gain(question, rewrite, rag_index, top_k, similarity_threshold, retrieval_mode)
        if diagnostics_full
        else None
    )

    if not results or gate_score < similarity_threshold:
        result = _abstain_result()
    else:
        retrieved_records = _records_with_scores(rag_index, results)
        prompt = build_general_qa_prompt(question, retrieved_records)
        result = _generate_result(prompt, retrieved_records, llm_client)

    return _attach_diagnostics(
        result,
        rewrite=rewrite,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        retrieval_mode=retrieval_mode,
        dropped=dropped,
        gain=gain,
    )


def answer_profile_question(
    profile: dict,
    rag_index: RagIndex,
    llm_client,
    *,
    free_text_question: str = "",
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
    rewrite_query: bool = True,
    diagnostics_full: bool = False,
) -> dict:
    query = free_text_question or (
        f"Singapore subsidy eligibility and payout amounts for profile: {profile}"
    )
    # The optional free-text question is rewritten with the profile in scope,
    # so e.g. "help with my mother's medical bills" resolves as a
    # caregiver/eldercare-scoped query rather than a generic one.
    rewrite = _rewrite_query(query, llm_client, enabled=rewrite_query, profile=profile)
    queries = [rewrite["rewritten"], *rewrite["subQueries"]]
    candidate_pool_size = max(top_k * 3, 15)
    candidates, gate_score, dropped = _retrieve_fanout(
        queries, rag_index, candidate_pool_size, retrieval_mode
    )
    gain = (
        _compute_gain(query, rewrite, rag_index, candidate_pool_size, similarity_threshold, retrieval_mode)
        if diagnostics_full
        else None
    )

    if not candidates or gate_score < similarity_threshold:
        result = _abstain_shortlist_result()
    else:
        preferred_categories = infer_preferred_categories(profile)
        reranked = rerank_by_category(candidates, rag_index.chunk_records, preferred_categories, top_k)

        retrieved_records = _records_with_scores(rag_index, reranked)
        chunk_by_id = {record["chunk_id"]: record for record in retrieved_records}

        prompt = build_profile_shortlist_prompt(profile, retrieved_records, free_text_question)
        raw_entries = _generate_shortlist_entries(prompt, llm_client)

        shortlist = []
        dev_warnings: list[str] = []
        for entry in raw_entries:
            conditions = entry.get("conditions") or []
            citations, warnings = _resolve_citations(entry.get("citation_chunk_ids") or [], chunk_by_id)
            dev_warnings.extend(warnings)
            shortlist.append({
                "group": _derive_group(conditions),
                "scheme": str(entry.get("scheme", "")).strip(),
                "reason": str(entry.get("reason", "")).strip(),
                "amount": entry.get("amount") or None,
                "conditions": conditions,
                "changer": str(entry.get("changer", "")).strip(),
                "citations": citations,
            })

        result = {
            "abstained": False,
            "shortlist": shortlist,
            "sources": retrieved_records,
            "dev_warnings": dev_warnings,
        }

    return _attach_diagnostics(
        result,
        rewrite=rewrite,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        retrieval_mode=retrieval_mode,
        dropped=dropped,
        gain=gain,
    )
