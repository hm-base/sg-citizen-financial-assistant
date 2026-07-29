import logging

logger = logging.getLogger(__name__)


def build_context_prompt(chunk_text: str, doc_metadata: dict) -> str:
    title = doc_metadata.get("title") or doc_metadata.get("scheme") or ""
    section = doc_metadata.get("section", "")
    return (
        "Write ONE short sentence (no more than 25 words) describing where this "
        "passage sits in its source document, to help a search system retrieve "
        "it for the right query. Do not repeat the passage itself.\n\n"
        f"Document: {title}\n"
        f"Section: {section}\n\n"
        f"Passage:\n{chunk_text}\n\n"
        "One-sentence context:"
    )


def contextualize_chunk(chunk_text: str, doc_metadata: dict, llm_client) -> str:
    """Prepend a short LLM-generated context sentence to `chunk_text`.

    Raises on failure -- the caller (contextualize_chunks) implements the
    fail-open/circuit-breaker policy, so this stays a plain, testable call
    with no error handling of its own.
    """
    prompt = build_context_prompt(chunk_text, doc_metadata)
    context_sentence = llm_client.generate(prompt).strip()
    return f"{context_sentence}\n\n{chunk_text}"


def contextualize_chunks(
    chunk_records: list[dict],
    doc_metadata_by_id: dict[str, dict],
    llm_client,
    *,
    enabled: bool = True,
    circuit_breaker_threshold: int = 5,
) -> tuple[list[dict], dict]:
    """Prepend context to each chunk's text (returns new dicts; does not
    mutate the input list or its records).

    Fails open per chunk: a single bad call falls back to that chunk's raw
    text rather than aborting the run. Trips a circuit breaker after
    `circuit_breaker_threshold` consecutive failures (a sustained problem
    like an exhausted daily quota, not a one-off blip) -- once tripped, every
    remaining chunk is left as raw text with no further LLM calls, rather
    than burning through an already-exhausted quota chunk-by-chunk across a
    multi-hundred-chunk corpus. See docs/superpowers/specs/2026-07-29-
    chromadb-context-chunking-design.md, "Contextual chunking is optional".

    Returns (new_chunk_records, stats) where
    stats = {"contextualized": int, "fell_back": int, "circuit_broken": bool}.
    """
    if not enabled:
        return list(chunk_records), {
            "contextualized": 0,
            "fell_back": len(chunk_records),
            "circuit_broken": False,
        }

    consecutive_failures = 0
    circuit_broken = False
    contextualized_count = 0
    fell_back_count = 0
    output: list[dict] = []

    for record in chunk_records:
        if circuit_broken:
            output.append(record)
            fell_back_count += 1
            continue

        doc_metadata = doc_metadata_by_id.get(record["doc_id"], {})
        try:
            new_text = contextualize_chunk(record["text"], doc_metadata, llm_client)
            output.append({**record, "text": new_text})
            contextualized_count += 1
            consecutive_failures = 0
        except Exception:  # noqa: BLE001 - any contextualization failure must fail open, never abort the run
            logger.warning(
                "Contextualization failed for chunk %s; falling back to raw text",
                record.get("chunk_id"),
                exc_info=True,
            )
            output.append(record)
            fell_back_count += 1
            consecutive_failures += 1
            if consecutive_failures >= circuit_breaker_threshold:
                circuit_broken = True
                logger.warning(
                    "Contextualization circuit breaker tripped after %d consecutive "
                    "failures; remaining chunks will use raw text with no further LLM calls.",
                    consecutive_failures,
                )

    return output, {
        "contextualized": contextualized_count,
        "fell_back": fell_back_count,
        "circuit_broken": circuit_broken,
    }
