import pytest

from ingestion.chunker import chunk_text, chunk_text_structured, split_into_sections


def test_chunk_text_produces_overlapping_chunks():
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["word_start"] == 0
    assert chunks[0]["word_end"] == 100
    assert chunks[1]["word_start"] == 80  # step = chunk_size - overlap
    for chunk in chunks:
        assert chunk["text"].strip()
        assert chunk["word_start"] <= chunk["word_end"]


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size=10, overlap=10)


def test_chunk_text_rejects_empty_text():
    with pytest.raises(ValueError):
        chunk_text("   ", chunk_size=10, overlap=2)


def test_split_into_sections_splits_on_blank_lines():
    text = "Eligibility\nMust be 21.\n\nAmount\nUp to $850 per year.\n\nHow to apply\nNo application needed."
    sections = split_into_sections(text)
    assert sections == [
        "Eligibility\nMust be 21.",
        "Amount\nUp to $850 per year.",
        "How to apply\nNo application needed.",
    ]


def test_chunk_text_structured_keeps_short_paragraphs_whole_and_never_splits_mid_sentence():
    text = "Eligibility\nMust be a Singapore Citizen aged 21 and above.\n\nAmount\nUp to $850 per year, paid in August."
    chunks = chunk_text_structured(text, chunk_size=350, overlap=50)

    assert len(chunks) == 1  # both short paragraphs fit in one chunk together
    assert "Eligibility" in chunks[0]["text"]
    assert "Amount" in chunks[0]["text"]
    assert chunks[0]["word_start"] == 0


def test_chunk_text_structured_packs_multiple_paragraphs_up_to_chunk_size():
    # Each paragraph is 10 words; chunk_size=25 should pack 2 per chunk, not 1.
    paragraph = " ".join(f"w{i}" for i in range(10))
    text = "\n\n".join([paragraph] * 4)

    chunks = chunk_text_structured(text, chunk_size=25, overlap=5)

    assert len(chunks) == 2
    assert chunks[0]["word_start"] == 0
    assert chunks[0]["word_end"] == 20
    assert chunks[1]["word_start"] == 20
    assert chunks[1]["word_end"] == 40


def test_chunk_text_structured_falls_back_to_word_count_split_for_oversized_paragraph():
    # One paragraph alone exceeds chunk_size -- must not silently overflow.
    long_paragraph = " ".join(f"w{i}" for i in range(500))
    text = f"Short intro.\n\n{long_paragraph}"

    chunks = chunk_text_structured(text, chunk_size=100, overlap=20)

    assert len(chunks) > 2  # intro chunk + multiple word-count-split pieces
    for chunk in chunks:
        assert len(chunk["text"].split()) <= 100 + 1  # allow off-by-one at join boundaries


def test_chunk_text_structured_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text_structured("some text here", chunk_size=10, overlap=10)


def test_chunk_text_structured_rejects_empty_text():
    with pytest.raises(ValueError):
        chunk_text_structured("   ", chunk_size=10, overlap=2)
