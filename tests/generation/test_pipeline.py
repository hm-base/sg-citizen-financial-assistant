import json
import logging
import time

import chromadb
import numpy as np
import pytest

from generation.pipeline import (
    RagIndex,
    ShortlistFormatError,
    _derive_group,
    _heuristic_profile_from_question,
    _question_suggests_personal_situation,
    _resolve_citations,
    _retrieve,
    _rewrite_query,
    answer_general_question,
    answer_profile_question,
)
from retrieval.bm25_index import build_bm25_index
from retrieval.chroma_index import build_chroma_collection, upsert_chunks


def _chroma_collection_from(chunk_records: list[dict], vectors: np.ndarray):
    """In-memory Chroma collection for a test's chunk_records + vectors,
    keyed by chunk_id exactly as ingestion.build_index would upsert it."""
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
    """Deterministic fake: maps known strings to fixed unit vectors."""

    VECTORS = {
        "gst voucher amount": np.array([1.0, 0.0], dtype=np.float32),
        "unrelated pet question": np.array([0.0, 1.0], dtype=np.float32),
    }

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False, **kwargs):
        return np.array([self.VECTORS.get(text.lower(), [0.0, 0.0]) for text in texts], dtype=np.float32)


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


class QueuedLLMClient:
    """Returns one queued response per call, in order (e.g. rewrite then answer)."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


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
    bm25_index = build_bm25_index([record["text"] for record in chunk_records])
    return RagIndex(
        chroma_collection=_chroma_collection_from(chunk_records, vectors),
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
        rewrite_query=False,
    )

    assert result["abstained"] is True
    assert "does not contain enough information" in result["answer"]
    assert llm_client.last_prompt is None


def test_answer_general_question_treats_in_prompt_fallback_as_abstained():
    """The gate can pass (relevant-enough chunks retrieved) while the model
    itself still judges them too tangential and emits the exact fallback
    message. That must be treated like a real abstain -- no sources attached
    -- rather than pairing "not enough information" with a Sources list that
    looks like supporting evidence."""
    from config import FALLBACK_MESSAGE

    rag_index = _build_rag_index()
    llm_client = FakeLLMClient(FALLBACK_MESSAGE)

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
        rewrite_query=False,
    )

    assert result["abstained"] is True
    assert result["answer"] == FALLBACK_MESSAGE
    assert result["sources"] == []


def test_answer_general_question_abstains_after_one_rewrite_call_when_rewrite_enabled():
    """With rewriting on (the default), the rewrite call happens before the
    gate check -- so abstaining still skips the answer-generation call, but
    not the rewrite call itself."""
    rag_index = _build_rag_index()
    llm_client = QueuedLLMClient([_rewrite_json("unrelated pet question")])

    result = answer_general_question(
        "unrelated pet question",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is True
    assert len(llm_client.prompts) == 1


def test_answer_general_question_accepts_a_citation_using_display_name():
    """Regression test: the prompt now labels passages with display_name
    (falling back to scheme_name) for nicer citations, e.g. "ComCare SMTA
    -- SupportGoWhere" instead of the title-cased scheme_name. The citation
    gate must recognise that label as grounded, not flag every answer as
    citing an unretrieved source."""
    chunk_records = [
        {
            "chunk_id": "gst-voucher_text_000",
            "scheme_name": "Gst Voucher Gstv Cash Supportgowhere",
            "display_name": "GST Voucher (GSTV) — Cash — SupportGoWhere",
            "category": "Household",
            "section_or_page": "FAQ",
            "text": "GST Voucher gives eligible households up to $850 in cash.",
        },
    ]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    rag_index = RagIndex(
        chroma_collection=_chroma_collection_from(chunk_records, vectors),
        bm25_index=build_bm25_index([record["text"] for record in chunk_records]),
        chunk_records=chunk_records,
        embedder=FakeEmbedder(),
    )
    llm_client = FakeLLMClient("You may get up to $850 [GST Voucher (GSTV) — Cash — SupportGoWhere, FAQ].")

    result = answer_general_question(
        "gst voucher amount",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["citation_warning"] == []


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


def _rewrite_json(rewritten, subQueries=None, ops=None, inferredSchemes=None):
    return json.dumps({
        "rewritten": rewritten,
        "subQueries": subQueries or [],
        "ops": ops or [],
        "inferredSchemes": inferredSchemes or [],
    })


def test_rewrite_query_returns_structured_diagnostics_from_llm_output():
    llm_client = QueuedLLMClient([_rewrite_json("gst voucher amount", inferredSchemes=["GST Voucher"])])

    result = _rewrite_query("how much is that gst thing ah", llm_client, enabled=True)

    assert result["raw"] == "how much is that gst thing ah"
    assert result["rewritten"] == "gst voucher amount"
    assert result["inferredSchemes"] == ["GST Voucher"]
    assert result["ops"] == []
    assert "how much is that gst thing ah" in llm_client.prompts[0]


def test_rewrite_query_falls_back_to_raw_on_malformed_json():
    llm_client = QueuedLLMClient(["not json at all"])

    result = _rewrite_query("original question", llm_client, enabled=True)

    assert result["rewritten"] == "original question"
    assert result["ops"] == [{"kind": "failed"}]


def test_rewrite_query_skipped_when_disabled():
    llm_client = QueuedLLMClient([])

    result = _rewrite_query("original question", llm_client, enabled=False)

    assert result["rewritten"] == "original question"
    assert result["ops"] == [{"kind": "skipped"}]
    assert llm_client.prompts == []


def test_rewrite_query_strips_nric_before_rewriting():
    llm_client = QueuedLLMClient([_rewrite_json("caregiver support schemes")])

    result = _rewrite_query("help for my dad, NRIC S1234567D", llm_client, enabled=True)

    assert "S1234567D" not in llm_client.prompts[0]
    assert any(op["kind"] == "dropped" for op in result["ops"])


def test_rewrite_query_fails_open_on_timeout():
    class SlowLLMClient:
        def generate(self, prompt):
            time.sleep(0.2)
            return _rewrite_json("gst voucher amount")

    result = _rewrite_query(
        "how much is that gst thing ah", SlowLLMClient(), enabled=True, timeout_seconds=0.01
    )

    assert result["rewritten"] == "how much is that gst thing ah"
    assert result["ops"] == [{"kind": "failed"}]


def test_answer_general_question_fans_out_across_sub_queries():
    """The unrewritten question doesn't match any known embedding (FakeEmbedder
    falls back to the zero vector), so retrieval only succeeds because the
    rewrite step maps it to "gst voucher amount" first."""
    rag_index = _build_rag_index()
    llm_client = QueuedLLMClient([
        _rewrite_json("gst voucher amount"),
        "You may get up to $850 [GST Voucher, FAQ].",
    ])

    result = answer_general_question(
        "how much is that gst thing ah",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
        rewrite_query=True,
    )

    assert result["abstained"] is False
    assert result["answer"] == "You may get up to $850 [GST Voucher, FAQ]."
    assert result["diagnostics"]["rewrite"]["rewritten"] == "gst voucher amount"
    assert result["diagnostics"]["retrieval"]["mode"] == "dense"


def test_answer_general_question_does_not_rewrite_when_explicitly_disabled():
    rag_index = _build_rag_index()
    llm_client = QueuedLLMClient([])

    result = answer_general_question(
        "how much is that gst thing ah",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
        rewrite_query=False,
    )

    assert result["abstained"] is True
    assert llm_client.prompts == []
    assert result["diagnostics"]["rewrite"]["ops"] == [{"kind": "skipped"}]


class ThreeChunkEmbedder:
    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False, **kwargs):
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
        chroma_collection=_chroma_collection_from(chunk_records, vectors),
        bm25_index=build_bm25_index([record["text"] for record in chunk_records]),
        chunk_records=chunk_records,
        embedder=ThreeChunkEmbedder(),
    )


def test_hybrid_reranking_does_not_lower_the_abstention_gate():
    """Hybrid must not abstain where dense answers, even when fusion reorders.

    Fusion puts row 2 (cosine 0.85) ahead of dense top-1 (row 0, cosine 1.0),
    but row 0 is still in the fused context, so the best dense evidence
    available to the answer is unchanged at 1.0. A 0.9 threshold must therefore
    let *both* modes answer; only the ranking differs.
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
    # Same gate decision, different ranking — that is the whole point of hybrid.
    assert hybrid_result["abstained"] is False
    assert hybrid_result["sources"][0]["chunk_id"] == "gst-voucher_text_002"


def test_hybrid_mode_answers_when_the_fused_set_clears_the_threshold():
    """Same fusion ordering, threshold below every candidate's cosine score."""
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


def test_hybrid_gate_is_never_below_the_dense_gate():
    """The core guarantee: hybrid can never be more abstention-prone than dense.

    Randomised over index size, top_k and vector geometry, the hybrid gate must
    equal the dense gate — the fused set always retains the dense top-1 chunk,
    so the maximum dense cosine in context is identical in both modes.
    """
    rng = np.random.default_rng(20260728)

    for _ in range(300):
        n_chunks = int(rng.integers(1, 40))
        top_k = int(rng.integers(1, 12))
        vectors = rng.normal(size=(n_chunks, 8)).astype(np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        texts = [
            " ".join(rng.choice(["gst", "voucher", "amount", "cash", "senior", "payout"], size=6))
            for _ in range(n_chunks)
        ]
        query_vector = rng.normal(size=(1, 8)).astype(np.float32)
        query_vector /= np.linalg.norm(query_vector)

        class FixedEmbedder:
            def encode(self, texts_, **kwargs):
                return np.repeat(query_vector, len(texts_), axis=0)

        chunk_records = [{"chunk_id": f"chunk_{i:03d}", "text": text} for i, text in enumerate(texts)]
        rag_index = RagIndex(
            chroma_collection=_chroma_collection_from(chunk_records, vectors),
            bm25_index=build_bm25_index(texts),
            chunk_records=chunk_records,
            embedder=FixedEmbedder(),
        )

        _, dense_gate = _retrieve("gst voucher amount", rag_index, top_k, "dense")
        _, hybrid_gate = _retrieve("gst voucher amount", rag_index, top_k, "hybrid")

        assert hybrid_gate >= dense_gate - 1e-6, (n_chunks, top_k, dense_gate, hybrid_gate)


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


def _shortlist_json(entries: list[dict]) -> str:
    return json.dumps(entries)


def test_answer_profile_question_returns_structured_shortlist():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient(_shortlist_json([
        {
            "scheme": "GST Voucher",
            "reason": "Household income and citizenship match the stated criteria.",
            "amount": "$850",
            "conditions": [{"label": "Singapore Citizen", "state": "met"}],
            "changer": "A higher home annual value would reduce the amount.",
            "citation_chunk_ids": ["gst-voucher_text_000"],
        },
    ]))

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
    entry = result["shortlist"][0]
    assert entry["scheme"] == "GST Voucher"
    assert entry["group"] == "eligible"
    assert entry["amount"] == "$850"
    assert entry["citations"] == [{
        "doc_label": "GST Voucher",
        "section": "FAQ",
        "chunk_id": "gst-voucher_text_000",
        "score": pytest.approx(1.0),
        "text": "GST Voucher gives eligible households up to $850 in cash.",
    }]


def test_answer_profile_question_abstains_below_threshold_without_calling_llm():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient("should never be returned")

    result = answer_profile_question(
        {"age": 68, "life_stage_tags": []},
        rag_index,
        llm_client,
        free_text_question="unrelated pet question",
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
        rewrite_query=False,
    )

    assert result["abstained"] is True
    assert result["shortlist"] == []
    assert result["sources"] == []
    assert result["dev_warnings"] == []
    assert llm_client.last_prompt is None


def test_answer_profile_question_strips_markdown_code_fences():
    rag_index = _build_rag_index()
    fenced = "```json\n" + _shortlist_json([
        {"scheme": "GST Voucher", "reason": "Matches.", "conditions": [], "changer": "n/a"},
    ]) + "\n```"
    llm_client = FakeLLMClient(fenced)

    result = answer_profile_question(
        {"age": 68, "life_stage_tags": []},
        rag_index,
        llm_client,
        free_text_question="gst voucher amount",
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["shortlist"][0]["scheme"] == "GST Voucher"


def test_answer_profile_question_retries_once_on_malformed_json_then_succeeds():
    rag_index = _build_rag_index()
    llm_client = QueuedLLMClient([
        "this is not json at all",
        _shortlist_json([{"scheme": "GST Voucher", "reason": "Matches.", "conditions": []}]),
    ])

    result = answer_profile_question(
        {"age": 68, "life_stage_tags": []},
        rag_index,
        llm_client,
        free_text_question="gst voucher amount",
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
        rewrite_query=False,
    )

    assert result["shortlist"][0]["scheme"] == "GST Voucher"
    assert len(llm_client.prompts) == 2


def test_answer_profile_question_fails_loudly_when_still_malformed_after_retry():
    rag_index = _build_rag_index()
    llm_client = QueuedLLMClient(["not json", "still not json"])

    with pytest.raises(ShortlistFormatError):
        answer_profile_question(
            {"age": 68, "life_stage_tags": []},
            rag_index,
            llm_client,
            free_text_question="gst voucher amount",
            top_k=3,
            similarity_threshold=0.3,
            retrieval_mode="dense",
            rewrite_query=False,
        )


def test_answer_profile_question_drops_citations_outside_the_retrieved_set_as_dev_warnings():
    rag_index = _build_rag_index()
    llm_client = FakeLLMClient(_shortlist_json([
        {
            "scheme": "GST Voucher",
            "reason": "Matches.",
            "conditions": [],
            "changer": "n/a",
            "citation_chunk_ids": ["gst-voucher_text_000", "made-up-chunk-id"],
        },
    ]))

    result = answer_profile_question(
        {"age": 68, "life_stage_tags": []},
        rag_index,
        llm_client,
        free_text_question="gst voucher amount",
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert len(result["shortlist"][0]["citations"]) == 1
    assert any("made-up-chunk-id" in warning for warning in result["dev_warnings"])


def test_derive_group_from_conditions():
    assert _derive_group([]) == "not_assessed"
    assert _derive_group([{"label": "Age 65+", "state": "not_checked"}]) == "eligible"
    assert _derive_group([{"label": "Age 65+", "state": "met"}]) == "eligible"
    assert _derive_group([{"label": "Age 65+", "state": "not_met"}]) == "unclear"
    assert _derive_group([
        {"label": "Age 65+", "state": "met"},
        {"label": "Income", "state": "not_met"},
    ]) == "unclear"


def test_resolve_citations_deduplicates_repeated_sources():
    chunk_by_id = {
        "a": {"scheme_name": "GST Voucher", "display_name": "GST Voucher", "section_or_page": "p.1"},
        "b": {"scheme_name": "GST Voucher", "display_name": "GST Voucher", "section_or_page": "p.1"},
    }

    citations, warnings = _resolve_citations(["a", "b"], chunk_by_id)

    assert len(citations) == 1
    assert warnings == []


def test_question_suggests_personal_situation_for_bios_not_fact_queries():
    assert _question_suggests_personal_situation(
        "I am 40 yo and unemployed; I have a two yo son and care for my mum."
    )
    assert not _question_suggests_personal_situation("gst voucher amount")
    assert not _question_suggests_personal_situation("How much is Baby Bonus?")


def test_heuristic_profile_from_question_fills_ticks_from_bio():
    profile = _heuristic_profile_from_question(
        "I am 40 yo and unemployed now; I have a two yo son. "
        "Also, my mum doesn't live with me but I need to care for her; she has dementia."
    )

    assert profile["age"] == 40
    assert profile["employment"] == "Unemployed"
    assert "Has young child(ren)" in profile["life_stage_tags"]
    assert "Caregiver" in profile["life_stage_tags"]


def test_normalize_history_keeps_last_n_turns():
    from generation.pipeline import _normalize_history
    import config

    history = [
        {"role": "user", "content": f"q{i}"} if i % 2 == 0 else {"role": "assistant", "content": f"a{i}"}
        for i in range(20)
    ]
    cleaned = _normalize_history(history)
    assert len(cleaned) == config.CHAT_HISTORY_MAX_TURNS * 2
    assert cleaned[0]["content"].startswith("q") or cleaned[0]["content"].startswith("a")
    assert cleaned[-1]["content"] == "a19"


def test_answer_general_question_personal_situation_uses_shortlist_then_answers():
    rag_index = _build_rag_index()
    profile_json = json.dumps({
        "citizenship": "Singapore Citizen",
        "age": 40,
        "household_size": 3,
        "monthly_income_band": None,
        "housing": "HDB",
        "employment": "Unemployed",
        "life_stage_tags": ["Has young child(ren)", "Caregiver"],
    })
    llm_client = QueuedLLMClient([
        profile_json,
        _rewrite_json("gst voucher amount"),
        _shortlist_json([{
            "scheme": "GST Voucher",
            "reason": "Citizen household may qualify.",
            "amount": "$850",
            "conditions": [{"label": "Singapore Citizen", "state": "met"}],
            "changer": "Higher annual value reduces amount.",
            "citation_chunk_ids": ["gst-voucher_text_000"],
        }]),
    ])

    result = answer_general_question(
        "I am 40 yo and unemployed; I have a two yo son and care for my mum with dementia.",
        rag_index,
        llm_client,
        top_k=3,
        similarity_threshold=0.3,
        retrieval_mode="dense",
    )

    assert result["abstained"] is False
    assert "shortlist" in result
    assert "answer" not in result
    assert result["diagnostics"]["eligibility_path"] == "shortlist"
    assert result["inferred_profile"]["employment"] == "Unemployed"
    assert result["inferred_profile"]["citizenship"] == "Singapore Citizen"
    assert "Has young child(ren)" in result["inferred_profile"]["life_stage_tags"]
    assert result["shortlist"][0]["scheme"] == "GST Voucher"
    assert result["shortlist"][0]["group"] == "eligible"


def test_ensure_signal_schemes_adds_skillsfuture_when_llm_omits_it():
    from generation.pipeline import _ensure_signal_schemes_in_shortlist

    profile = {
        "employment": "Unemployed",
        "life_stage_tags": ["Has young child(ren)"],
    }
    shortlist = [{
        "group": "eligible",
        "scheme": "ComCare Short-to-Medium-Term Assistance",
        "reason": "Unemployed household may apply.",
        "amount": None,
        "conditions": [],
        "changer": "",
        "citations": [],
    }]
    retrieved = [
        {
            "display_name": "ComCare Short-to-Medium-Term Assistance (SMTA) — SupportGoWhere",
            "scheme_name": "comcare",
            "chunk_id": "comcare_000",
            "section_or_page": "p1",
            "score": 0.9,
            "text": "ComCare",
        },
        {
            "display_name": "ssg_skillsfuture_credit_amounts",
            "scheme_name": "SkillsFuture Credit",
            "chunk_id": "sfc_000",
            "section_or_page": "p1",
            "score": 0.8,
            "text": "SkillsFuture Credit",
        },
        {
            "display_name": "adj_baby_bonus_cda",
            "scheme_name": "Baby Bonus Scheme",
            "chunk_id": "bb_000",
            "section_or_page": "p1",
            "score": 0.7,
            "text": "Baby Bonus",
        },
    ]

    merged, warnings = _ensure_signal_schemes_in_shortlist(profile, shortlist, retrieved)
    schemes = {entry["scheme"] for entry in merged}
    assert "ComCare Short-to-Medium-Term Assistance" in schemes
    assert any("skillsfuture" in s.lower() or "SkillsFuture" in s for s in schemes)
    assert any("baby bonus" in s.lower() for s in schemes)
    assert warnings
