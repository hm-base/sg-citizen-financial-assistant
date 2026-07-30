from ingestion.contextualize import contextualize_chunk, contextualize_chunks


class FakeLLMClient:
    def __init__(self, response: str = "This is from the Eligibility section."):
        self.response = response
        self.calls = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


class FailingLLMClient:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        raise self.error


def _records(n):
    return [
        {
            "chunk_id": f"doc_text_{i:03d}",
            "doc_id": "doc",
            "text": f"Chunk body {i}.",
            "embed_text": f"Chunk body {i}.",
        }
        for i in range(n)
    ]


def test_contextualize_chunk_prepends_llm_generated_sentence():
    client = FakeLLMClient("This chunk is from the Eligibility section.")

    result = contextualize_chunk("Must be 21 and above.", {"title": "CHAS"}, client)

    assert result.startswith("This chunk is from the Eligibility section.")
    assert "Must be 21 and above." in result
    assert len(client.calls) == 1


def test_contextualize_chunks_contextualizes_every_chunk_when_all_calls_succeed():
    records = _records(3)
    client = FakeLLMClient("Context sentence.")

    output, stats = contextualize_chunks(records, {"doc": {"title": "CHAS"}}, client, enabled=True)

    assert stats == {"contextualized": 3, "fell_back": 0, "circuit_broken": False}
    for original, new in zip(records, output):
        assert new["embed_text"].startswith("Context sentence.")
        assert original["text"] in new["embed_text"]
        # The displayed/prompted `text` field must never be touched --
        # residents quote this verbatim and the prompt is grounded in it.
        assert new["text"] == original["text"]


def test_contextualize_chunks_never_rewrites_the_displayed_text_field():
    """Regression test for a real bug: contextualization used to overwrite
    `text` with the LLM's context sentence prepended, so what a resident saw
    as a "quoted excerpt" was partly model-written. Only `embed_text` may
    change."""
    records = _records(5)
    client = FakeLLMClient("This is model-written framing that must not leak.")

    output, _ = contextualize_chunks(records, {}, client, enabled=True)

    for original, new in zip(records, output):
        assert new["text"] == original["text"]
        assert "model-written framing" not in new["text"]
        assert "model-written framing" in new["embed_text"]


def test_contextualize_chunks_passes_the_chunk_own_section_to_the_prompt():
    """Regression test: doc_metadata is document-level (agency/tier/...) and
    never carries a "section" key, so build_context_prompt's Section: line
    was always blank. The per-chunk location lives on the chunk record as
    section_or_page and must reach the prompt."""
    records = [
        {
            "chunk_id": "doc_text_000",
            "doc_id": "doc",
            "text": "Must be 21 and above.",
            "embed_text": "Must be 21 and above.",
            "section_or_page": "Eligibility, p.2",
        }
    ]
    client = FakeLLMClient("Context sentence.")

    contextualize_chunks(records, {"doc": {"title": "CHAS"}}, client, enabled=True)

    assert len(client.calls) == 1
    assert "Section: Eligibility, p.2" in client.calls[0]


def test_contextualize_chunks_does_not_mutate_input_records():
    records = _records(1)
    original_text = records[0]["text"]
    client = FakeLLMClient("Context sentence.")

    contextualize_chunks(records, {}, client, enabled=True)

    assert records[0]["text"] == original_text


def test_contextualize_chunks_skips_entirely_when_disabled():
    records = _records(3)
    client = FakeLLMClient("Context sentence.")

    output, stats = contextualize_chunks(records, {}, client, enabled=False)

    assert output == records
    assert client.calls == []
    assert stats == {"contextualized": 0, "fell_back": 3, "circuit_broken": False}


def test_contextualize_chunks_falls_back_per_chunk_on_llm_error():
    records = _records(2)
    client = FailingLLMClient(RuntimeError("boom"))

    output, stats = contextualize_chunks(
        records, {}, client, enabled=True, circuit_breaker_threshold=10
    )

    assert output == records  # unchanged raw text
    assert stats == {"contextualized": 0, "fell_back": 2, "circuit_broken": False}
    assert client.calls == 2  # still tried every chunk -- breaker threshold not reached


def test_contextualize_chunks_trips_circuit_breaker_after_consecutive_failures():
    records = _records(10)
    client = FailingLLMClient(RuntimeError("quota exceeded"))

    output, stats = contextualize_chunks(
        records, {}, client, enabled=True, circuit_breaker_threshold=3
    )

    assert output == records
    assert stats["circuit_broken"] is True
    assert stats["contextualized"] == 0
    assert stats["fell_back"] == 10
    # Breaker trips after 3 consecutive failures; the remaining 7 chunks are
    # never sent to the LLM at all.
    assert client.calls == 3


def test_contextualize_chunks_resets_failure_streak_on_a_later_success():
    """A transient blip that recovers must not eventually trip the breaker
    from unrelated earlier failures long since past."""
    class FlakyClient:
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1
            # Fails on calls 1-2, then succeeds forever after.
            if self.calls <= 2:
                raise RuntimeError("transient")
            return "Context sentence."

    records = _records(6)
    client = FlakyClient()

    output, stats = contextualize_chunks(
        records, {}, client, enabled=True, circuit_breaker_threshold=3
    )

    assert stats["circuit_broken"] is False
    assert stats["fell_back"] == 2
    assert stats["contextualized"] == 4
