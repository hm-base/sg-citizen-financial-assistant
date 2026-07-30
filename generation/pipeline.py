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
    build_profile_extract_prompt,
    build_profile_shortlist_prompt,
    build_query_rewrite_prompt,
    extract_cited_scheme_labels,
)
from retrieval.bm25_index import search_bm25_index
from retrieval.chroma_index import search_chroma_index
from retrieval.embed import embed_texts
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.profile_filter import (
    _scheme_stem,
    dedupe_candidates_by_scheme,
    infer_preferred_categories,
    rerank_by_category,
)

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
    history: list[dict] | None = None,
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
            prompt = build_query_rewrite_prompt(stripped, profile, history=history)
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


def _normalize_history(history: list[dict] | None) -> list[dict]:
    """Keep the last N valid user/assistant turns for prompts and rewrite."""
    if not history:
        return []
    cleaned: list[dict] = []
    for turn in history:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "").strip().lower()
        content = str(turn.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        cleaned.append({"role": role, "content": content})
    max_messages = max(0, config.CHAT_HISTORY_MAX_TURNS * 2)
    if max_messages and len(cleaned) > max_messages:
        cleaned = cleaned[-max_messages:]
    return cleaned


def _assistant_history_summary(result: dict) -> str:
    """Compact assistant turn for storing in chat history (client may also do this)."""
    if result.get("abstained"):
        return config.FALLBACK_MESSAGE
    if "shortlist" in result:
        parts = []
        for entry in result.get("shortlist") or []:
            scheme = (entry.get("scheme") or "").strip()
            if not scheme:
                continue
            group = entry.get("group") or "not_assessed"
            amount = entry.get("amount")
            bit = f"{scheme} ({group})"
            if amount:
                bit += f": {amount}"
            parts.append(bit)
        return "Shortlist: " + "; ".join(parts) if parts else "Shortlist: (none)"
    return str(result.get("answer") or "").strip()


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
    retrieved_for_diagnostics: list[dict] | None = None,
) -> dict:
    retrieved = retrieved_for_diagnostics if retrieved_for_diagnostics is not None else result.get("sources", [])
    result["diagnostics"] = {
        "rewrite": rewrite,
        "retrieval": _retrieval_diagnostics(
            top_k, similarity_threshold, retrieval_mode, retrieved, dropped
        ),
        "gain": gain,
    }
    return result


_ALLOWED_CITIZENSHIP = {"Singapore Citizen", "PR", "Other"}
_ALLOWED_INCOME = {"<$1.5k", "$1.5-3k", "$3-6k", ">$6k", "Prefer not to say"}
_ALLOWED_HOUSING = {"HDB", "Private", "Rental", "Other", "Prefer not to say"}
_ALLOWED_EMPLOYMENT = {
    "Employed", "Self-employed", "Unemployed", "Retired", "Student", "Platform worker"
}
_ALLOWED_LIFE_STAGE_TAGS = {
    "Has young child(ren)",
    "Caregiver",
    "Senior (65+)",
    "Pioneer/Merdeka Generation",
    "I have a disability",
    "PWD in household",
    "Own more than 1 property",
}
_PERSONAL_SITUATION_MARKERS = (
    r"\bi am\b",
    r"\bi'm\b",
    r"\bi have\b",
    r"\bmy\b",
    r"\byo\b",
    r"\by/?o\b",
    r"\byear[s]?[- ]?old\b",
    r"\bage\b",
    r"unemployed",
    r"employed",
    r"retrenched",
    r"jobless",
    r"\bchild\b",
    r"\bson\b",
    r"\bdaughter\b",
    r"\bbaby\b",
    r"caregiver",
    r"care for",
    r"dementia",
    r"qualif",
    r"eligible",
    r"what can i",
    r"what do i",
    r"\bhdb\b",
    r"\bwife\b",
    r"\bhusband\b",
    r"\bmum\b",
    r"\bmom\b",
    r"\bmother\b",
)


def _situation_seed_queries(question: str) -> list[str]:
    """Lightweight multi-facet seeds for free-text 'about me' questions.

    Dense retrieval otherwise latches onto one dramatic facet (e.g. dementia
    caregiving) and drops others (young child, unemployment) from the top-k
    that reach the answer prompt.
    """
    text = question.lower()
    seeds: list[str] = []
    if any(token in text for token in ("child", "son", "daughter", "baby", "toddler", "yo ")):
        seeds.append(
            "Baby Bonus Scheme Child Development Account cash gift co-matching eligibility Singapore Citizen"
        )
    if any(token in text for token in ("unemployed", "retrenched", "jobless", "looking for work", "between jobs")):
        seeds.append(
            "Workfare Income Supplement Career Conversion Programme SkillsFuture support for unemployed mid-career Singaporean"
        )
        seeds.append("ComCare financial assistance short-to-medium term for unemployed household Singapore")
    if any(token in text for token in ("caregiver", "care for", "dementia", "mum", "mom", "mother", "father", "parent")):
        seeds.append(
            "Home Caregiving Grant caregiver support for elderly parent dementia Singapore"
        )
    return seeds


def _question_suggests_personal_situation(question: str) -> bool:
    """True when free text looks like a bio / eligibility ask, not a scheme fact Q."""
    text = question.lower()
    hits = sum(1 for pattern in _PERSONAL_SITUATION_MARKERS if re.search(pattern, text))
    return hits >= 2


def _empty_profile() -> dict:
    return {
        "citizenship": None,
        "age": None,
        "household_size": None,
        "monthly_income_band": None,
        "housing": None,
        "employment": None,
        "life_stage_tags": [],
    }


def _normalize_profile(raw: dict) -> dict:
    profile = _empty_profile()
    citizenship = raw.get("citizenship")
    if citizenship in _ALLOWED_CITIZENSHIP:
        profile["citizenship"] = citizenship

    age = raw.get("age")
    if isinstance(age, bool):
        age = None
    if isinstance(age, (int, float)) and 0 <= int(age) <= 120:
        profile["age"] = int(age)
    elif isinstance(age, str) and age.strip().isdigit():
        age_int = int(age.strip())
        if 0 <= age_int <= 120:
            profile["age"] = age_int

    household = raw.get("household_size")
    if isinstance(household, bool):
        household = None
    if isinstance(household, (int, float)) and 1 <= int(household) <= 20:
        profile["household_size"] = int(household)

    income = raw.get("monthly_income_band")
    if income in _ALLOWED_INCOME:
        profile["monthly_income_band"] = income

    housing = raw.get("housing")
    if housing in _ALLOWED_HOUSING:
        profile["housing"] = housing

    employment = raw.get("employment")
    if employment in _ALLOWED_EMPLOYMENT:
        profile["employment"] = employment

    tags = []
    for tag in raw.get("life_stage_tags") or []:
        if tag in _ALLOWED_LIFE_STAGE_TAGS and tag not in tags:
            tags.append(tag)
    if profile["age"] is not None and profile["age"] >= 65 and "Senior (65+)" not in tags:
        tags.append("Senior (65+)")
    profile["life_stage_tags"] = tags
    return profile


def _heuristic_profile_from_question(question: str) -> dict:
    """Rule-based fallback when profile-extract LLM fails or returns little."""
    text = question.lower()
    profile = _empty_profile()

    if "singapore citizen" in text or "singaporean" in text:
        profile["citizenship"] = "Singapore Citizen"
    elif re.search(r"\bpr\b|permanent resident", text):
        profile["citizenship"] = "PR"

    age_match = re.search(r"\b(\d{1,3})\s*(?:yo|y/?o|years?\s*old)\b", text)
    if not age_match:
        age_match = re.search(r"\bage\s*(?:is|:)?\s*(\d{1,3})\b", text)
    if age_match:
        age = int(age_match.group(1))
        if 0 <= age <= 120:
            profile["age"] = age

    if any(token in text for token in ("unemployed", "retrenched", "jobless", "looking for work", "between jobs")):
        profile["employment"] = "Unemployed"
    elif "retired" in text:
        profile["employment"] = "Retired"
    elif "self-employed" in text or "self employed" in text:
        profile["employment"] = "Self-employed"
    elif re.search(r"\bi(?:'m| am)\s+employed\b", text):
        profile["employment"] = "Employed"

    if "hdb" in text:
        profile["housing"] = "HDB"

    tags: list[str] = []
    if any(token in text for token in ("child", "son", "daughter", "baby", "toddler")):
        tags.append("Has young child(ren)")
    if any(token in text for token in ("caregiver", "care for", "dementia", "caring for")):
        tags.append("Caregiver")
    if profile["age"] is not None and profile["age"] >= 65:
        tags.append("Senior (65+)")
    if re.search(r"\bi have a disability\b|\bmy disability\b", text):
        tags.append("I have a disability")
    elif re.search(r"\bpwd\b|disability", text):
        tags.append("PWD in household")
    if "pioneer" in text or "merdeka" in text:
        tags.append("Pioneer/Merdeka Generation")
    profile["life_stage_tags"] = list(dict.fromkeys(tags))
    return profile


def _merge_profiles(primary: dict, fallback: dict) -> dict:
    """Fill nulls from fallback; union life-stage tags."""
    merged = _normalize_profile(primary)
    for key in ("citizenship", "age", "household_size", "monthly_income_band", "housing", "employment"):
        if merged.get(key) in (None, "", "Prefer not to say") and fallback.get(key) not in (None, ""):
            merged[key] = fallback[key]
    tags = list(dict.fromkeys([*(merged.get("life_stage_tags") or []), *(fallback.get("life_stage_tags") or [])]))
    merged["life_stage_tags"] = [t for t in tags if t in _ALLOWED_LIFE_STAGE_TAGS]
    return merged


def _profile_has_signal(profile: dict) -> bool:
    if profile.get("age") is not None:
        return True
    if profile.get("employment"):
        return True
    if profile.get("life_stage_tags"):
        return True
    if profile.get("housing") not in (None, "", "Prefer not to say"):
        return True
    if profile.get("monthly_income_band") not in (None, "", "Prefer not to say"):
        return True
    if profile.get("household_size") is not None:
        return True
    return False


def _parse_profile_json(raw_text: str) -> dict:
    parsed = json.loads(_strip_code_fence(raw_text))
    if not isinstance(parsed, dict):
        raise ValueError("Profile extract response must be a JSON object")
    return _normalize_profile(parsed)


def _infer_profile_from_question(
    question: str,
    llm_client,
    history: list[dict] | None = None,
) -> dict:
    """Infer form-like profile bands from free text (LLM, with heuristic fill-in)."""
    heuristic = _heuristic_profile_from_question(question)
    # Also fold heuristics from prior user turns so follow-ups keep age/employment.
    for turn in history or []:
        if turn.get("role") == "user":
            heuristic = _merge_profiles(heuristic, _heuristic_profile_from_question(turn["content"]))
    try:
        prompt = build_profile_extract_prompt(question, history=history)
        raw = _run_with_timeout(lambda: llm_client.generate(prompt), config.REWRITE_TIMEOUT_SECONDS)
        parsed = _parse_profile_json(raw)
        return _merge_profiles(parsed, heuristic)
    except Exception:  # noqa: BLE001 - extraction must fail open to heuristic
        return heuristic


def _apply_form_defaults(profile: dict) -> dict:
    """Match Personal eligibility form defaults for unspecified optional bands.

    The form always sends citizenship / income / housing (defaults: Singapore
    Citizen, Prefer not to say, Prefer not to say). Leaving those null in an
    inferred profile changes shortlist condition checks vs the structured path.
    Do NOT default employment — the form's Employed default would mis-label
    unemployed bios.
    """
    out = dict(profile)
    if not out.get("citizenship"):
        out["citizenship"] = "Singapore Citizen"
    if not out.get("monthly_income_band"):
        out["monthly_income_band"] = "Prefer not to say"
    if not out.get("housing"):
        out["housing"] = "Prefer not to say"
    out["life_stage_tags"] = list(out.get("life_stage_tags") or [])
    return out


def _answer_general_question_classic(
    question: str,
    rag_index: RagIndex,
    llm_client,
    *,
    top_k: int,
    similarity_threshold: float,
    retrieval_mode: str,
    rewrite_query: bool = True,
    diagnostics_full: bool = False,
    history: list[dict] | None = None,
) -> dict:
    history = _normalize_history(history)
    rewrite = _rewrite_query(
        question, llm_client, enabled=rewrite_query, history=history
    )
    seeds = _situation_seed_queries(question)
    queries = [rewrite["rewritten"], *rewrite["subQueries"], *seeds]
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = (query or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    # Pull a wider pool when the question names several life situations, so
    # one facet cannot occupy every top-k slot before the LLM answers.
    retrieve_k = max(top_k, top_k + len(seeds) * 2, 8 if seeds else top_k)
    keep_k = top_k if not seeds else max(top_k, 8)
    merged, gate_score, _dropped_pre = _retrieve_fanout(deduped, rag_index, retrieve_k, retrieval_mode)
    results = merged[:keep_k]
    dropped = max(0, len(merged) - len(results))
    gain = (
        _compute_gain(question, rewrite, rag_index, retrieve_k, similarity_threshold, retrieval_mode)
        if diagnostics_full
        else None
    )

    if not results or gate_score < similarity_threshold:
        result = _abstain_result()
        # Keep retrieval scores in diagnostics even when abstaining so the UI
        # does not falsely imply "0 candidates were found".
        retrieved_for_diag = _records_with_scores(rag_index, results) if results else []
    else:
        retrieved_for_diag = _records_with_scores(rag_index, results)
        prompt = build_general_qa_prompt(question, retrieved_for_diag, history=history)
        result = _generate_result(prompt, retrieved_for_diag, llm_client)

    attached = _attach_diagnostics(
        result,
        rewrite=rewrite,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        retrieval_mode=retrieval_mode,
        dropped=dropped,
        gain=gain,
        retrieved_for_diagnostics=retrieved_for_diag if result.get("abstained") else None,
    )
    attached.setdefault("diagnostics", {})
    attached["diagnostics"]["history_turns"] = len(history)
    return attached


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
    history: list[dict] | None = None,
    sticky_profile: dict | None = None,
) -> dict:
    """General Q&A.

    Personal-situation free text shares the Personal eligibility shortlist
    brain and returns the same shortlist payload (no second prose rewrite that
    drops schemes). Pure scheme fact questions keep classic retrieve → answer.
    Optional history resolves follow-ups; sticky_profile carries form/inferred
    bands across turns.
    """
    history = _normalize_history(history)
    classic_kwargs = {
        "top_k": top_k,
        "similarity_threshold": similarity_threshold,
        "retrieval_mode": retrieval_mode,
        "rewrite_query": rewrite_query,
        "diagnostics_full": diagnostics_full,
        "history": history,
    }

    # Follow-ups after a shortlist ("how much is SkillsFuture?") should use
    # classic grounded Q&A with history, not re-run a full shortlist unless
    # the new message itself looks like a personal bio / eligibility ask.
    if not _question_suggests_personal_situation(question):
        return _answer_general_question_classic(question, rag_index, llm_client, **classic_kwargs)

    inferred = _infer_profile_from_question(question, llm_client, history=history)
    if sticky_profile:
        # Form / sticky bands win when set; inferred fills gaps (and history).
        profile = _apply_form_defaults(
            _merge_profiles(_normalize_profile(sticky_profile), inferred)
        )
    else:
        profile = _apply_form_defaults(inferred)

    if not _profile_has_signal(profile):
        result = _answer_general_question_classic(question, rag_index, llm_client, **classic_kwargs)
        result["diagnostics"]["inferred_profile"] = profile
        result["diagnostics"]["eligibility_path"] = "classic_no_profile_signal"
        return result

    try:
        # Same resident-facing shortlist as Personal eligibility with the same
        # ticks and a blank optional question — do not pass the raw bio into
        # the shortlist prompt (that reintroduced freeform/structured drift).
        shortlist_result = answer_profile_question(
            profile,
            rag_index,
            llm_client,
            free_text_question="",
            history=history,
            **{k: v for k, v in classic_kwargs.items() if k != "history"},
        )
    except ShortlistFormatError:
        result = _answer_general_question_classic(question, rag_index, llm_client, **classic_kwargs)
        result["diagnostics"]["inferred_profile"] = profile
        result["diagnostics"]["eligibility_path"] = "classic_shortlist_format_error"
        result["inferred_profile"] = profile
        return result

    # Same resident-facing payload as Personal eligibility shortlist — do not
    # re-ask the LLM to turn the shortlist into prose (that dropped schemes).
    shortlist_result["inferred_profile"] = profile
    shortlist_result.setdefault("diagnostics", {})
    shortlist_result["diagnostics"]["inferred_profile"] = profile
    shortlist_result["diagnostics"]["eligibility_path"] = (
        "shortlist_abstain" if shortlist_result.get("abstained") else "shortlist"
    )
    shortlist_result["diagnostics"]["history_turns"] = len(history)
    if shortlist_result.get("shortlist"):
        shortlist_result["diagnostics"]["shortlist_summary"] = [
            {"scheme": entry.get("scheme"), "group": entry.get("group")}
            for entry in shortlist_result["shortlist"]
        ]
    return shortlist_result


def _shortlist_fallback_from_sources(retrieved_records: list[dict]) -> list[dict]:
    """When the LLM returns [], still surface retrieved schemes as not_assessed.

    An empty shortlist with non-empty retrieval is usually a generation miss
    (timeout, over-cautious abstention), not "nothing in the corpus matched".
    Showing the retrieved scheme names with not_assessed conditions keeps the
    resident-facing result honest about what the index found.
    """
    fallback: list[dict] = []
    seen: set[str] = set()
    for record in retrieved_records:
        scheme = (record.get("display_name") or record.get("scheme_name") or "").strip()
        if not scheme or scheme in seen:
            continue
        seen.add(scheme)
        fallback.append({
            "group": "not_assessed",
            "scheme": scheme,
            "reason": (
                "This scheme appeared in retrieved documents for your profile, "
                "but the assistant could not finish a condition-by-condition check."
            ),
            "amount": None,
            "conditions": [],
            "changer": "Ask again, or open the cited source for the published criteria.",
            "citations": [{
                "doc_label": scheme,
                "section": record.get("section_or_page") or "",
                "chunk_id": record.get("chunk_id"),
                "score": record.get("score"),
                "text": record.get("text") or "",
            }],
        })
    return fallback


def _required_scheme_stems_for_profile(profile: dict) -> set[str]:
    """Scheme stems the shortlist must cover when the index retrieved them.

    Stops freeform vs structured (and LLM variance) from dropping a whole
    profile facet — e.g. Unemployed without SkillsFuture — when the chunk
    was already in the evidence set.
    """
    stems: set[str] = set()
    tags = profile.get("life_stage_tags") or []
    if profile.get("employment") == "Unemployed":
        stems.update({"skillsfuture", "career conversion", "comcare", "workfare"})
    elif profile.get("employment") == "Employed" and profile.get("monthly_income_band") in (
        "<$1.5k",
        "$1.5-3k",
    ):
        stems.update({"workfare", "skillsfuture"})
    if "Has young child(ren)" in tags:
        stems.add("baby bonus")
    if "Caregiver" in tags:
        stems.add("home caregiving grant")
    return stems


def _friendly_scheme_name(record: dict) -> str:
    scheme = (record.get("scheme_name") or "").strip()
    display = (record.get("display_name") or "").strip()
    # Prefer a human scheme_name (e.g. "SkillsFuture Credit") over file-like
    # display ids (e.g. "ssg_skillsfuture_credit_amounts").
    raw = scheme if scheme and (" " in scheme or scheme[:1].isupper()) else (display or scheme)
    if not raw:
        return ""
    return re.split(r"[—\-–|]", raw, maxsplit=1)[0].strip() or raw


def _ensure_signal_schemes_in_shortlist(
    profile: dict,
    shortlist: list[dict],
    retrieved_records: list[dict],
) -> tuple[list[dict], list[str]]:
    """Append retrieved profile-signal schemes the LLM omitted."""
    required = _required_scheme_stems_for_profile(profile)
    if not required or not retrieved_records:
        return shortlist, []

    present = {_scheme_stem({"display_name": entry.get("scheme", "")}) for entry in shortlist}
    by_stem: dict[str, dict] = {}
    for record in retrieved_records:
        stem = _scheme_stem(record)
        if stem in required and stem not in present and stem not in by_stem:
            by_stem[stem] = record

    warnings: list[str] = []
    if not by_stem:
        return shortlist, warnings

    merged = list(shortlist)
    for stem, record in by_stem.items():
        scheme = _friendly_scheme_name(record)
        merged.append({
            "group": "not_assessed",
            "scheme": scheme,
            "reason": (
                "Retrieved for your profile signals, but the model did not finish "
                "a full condition check on this scheme."
            ),
            "amount": None,
            "conditions": [],
            "changer": "Open the cited source, or re-run with more profile detail.",
            "citations": [{
                "doc_label": scheme,
                "section": record.get("section_or_page") or "",
                "chunk_id": record.get("chunk_id"),
                "score": record.get("score"),
                "text": record.get("text") or "",
            }],
        })
        warnings.append(f"Added retrieved signal scheme omitted by model: {scheme} ({stem})")
    return merged, warnings


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
    history: list[dict] | None = None,
) -> dict:
    history = _normalize_history(history)
    # Always retrieve against a profile-wide eligibility query so optional
    # free-text (e.g. a dementia caregiving story) cannot crowd out other
    # facets already present in the structured profile (young child, HDB, …).
    # Rewrite from the profile bands only — not free-text — so General Q&A
    # (inferred profile) and Personal eligibility (same ticks) share one
    # retrieval fanout. Free-text still informs the shortlist prompt below.
    # History helps rewrite resolve follow-ups when free_text is present.
    profile_query = f"Singapore subsidy eligibility and payout amounts for profile: {profile}"
    free_text = (free_text_question or "").strip()
    rewrite = _rewrite_query(
        profile_query if not free_text else free_text,
        llm_client,
        enabled=rewrite_query,
        profile=profile,
        history=history if free_text else None,
    )
    # Seed queries from structured life-stage tags / employment so optional
    # free-text about one facet (e.g. dementia caregiving) cannot monopolise
    # dense retrieval and drop unemployment or child-support schemes.
    tag_seeds: list[str] = []
    tags = profile.get("life_stage_tags") or []
    if "Has young child(ren)" in tags:
        tag_seeds.append(
            "Baby Bonus Scheme Child Development Account cash gift co-matching eligibility Singapore Citizen"
        )
    if "Caregiver" in tags:
        tag_seeds.append(
            "Home Caregiving Grant caregiver support for elderly parent dementia Singapore"
        )
    if "I have a disability" in tags or "PWD in household" in tags:
        tag_seeds.append("disability support CareShield Life PioneerDAS eligibility Singapore")
    if profile.get("employment") == "Unemployed":
        tag_seeds.append(
            "ComCare Short-to-Medium Term Assistance financial help for unemployed household Singapore"
        )
        tag_seeds.append(
            "SkillsFuture Credit SkillsFuture Career Transition Programme mid-career Singaporean"
        )
        tag_seeds.append(
            "SkillsFuture Career Conversion Programme mid-career switch unemployed Singaporean jobseeker"
        )
        tag_seeds.append(
            "Workfare Skills Support lower-wage workers employment assistance Singapore"
        )
    queries = [profile_query, rewrite["rewritten"], *rewrite["subQueries"], *tag_seeds]
    # Optional free-text is an extra retrieval hint only (e.g. "gst voucher
    # amount"). It must not drive the rewrite, or freeform vs structured with
    # the same ticks diverge. Leave blank for the shared personal-situation path.
    if free_text:
        queries.append(free_text)
    # Deduplicate while preserving order — fanout is cheap relative to a
    # missed Baby Bonus / caregiver scheme.
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = query.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    queries = deduped
    # Multi-facet profiles (unemployed + child + caregiver, …) need a wider
    # shortlist window: default top_k=5 is easily filled by one category.
    facet_count = sum(
        1
        for flag in (
            "Has young child(ren)" in tags,
            "Caregiver" in tags,
            "I have a disability" in tags or "PWD in household" in tags,
            profile.get("employment") == "Unemployed",
            profile.get("housing") == "HDB",
            profile.get("age") is not None and profile["age"] >= 65,
        )
        if flag
    )
    effective_top_k = max(top_k, min(2 * facet_count + 1, 10)) if facet_count >= 2 else top_k
    candidate_pool_size = max(effective_top_k * 4, 20)
    candidates, gate_score, dropped = _retrieve_fanout(
        queries, rag_index, candidate_pool_size, retrieval_mode
    )
    gain = (
        _compute_gain(
            profile_query,
            rewrite,
            rag_index,
            candidate_pool_size,
            similarity_threshold,
            retrieval_mode,
        )
        if diagnostics_full
        else None
    )

    if not candidates or gate_score < similarity_threshold:
        result = _abstain_shortlist_result()
    else:
        preferred_categories = infer_preferred_categories(profile)
        deduped_candidates = dedupe_candidates_by_scheme(candidates, rag_index.chunk_records)
        reranked = rerank_by_category(
            deduped_candidates, rag_index.chunk_records, preferred_categories, effective_top_k
        )

        retrieved_records = _records_with_scores(rag_index, reranked)
        chunk_by_id = {record["chunk_id"]: record for record in retrieved_records}

        prompt = build_profile_shortlist_prompt(
            profile, retrieved_records, free_text, history=history
        )
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

        if not shortlist:
            shortlist = _shortlist_fallback_from_sources(retrieved_records)
            if shortlist:
                dev_warnings.append(
                    "Model returned an empty shortlist; surfaced retrieved schemes as not_assessed."
                )

        shortlist, ensure_warnings = _ensure_signal_schemes_in_shortlist(
            profile, shortlist, retrieved_records
        )
        dev_warnings.extend(ensure_warnings)

        result = {
            "abstained": False,
            "shortlist": shortlist,
            "sources": retrieved_records,
            "dev_warnings": dev_warnings,
        }

    attached = _attach_diagnostics(
        result,
        rewrite=rewrite,
        top_k=effective_top_k,
        similarity_threshold=similarity_threshold,
        retrieval_mode=retrieval_mode,
        dropped=dropped,
        gain=gain,
    )
    attached.setdefault("diagnostics", {})
    attached["diagnostics"]["history_turns"] = len(history)
    return attached
