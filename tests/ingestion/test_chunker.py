import pytest

from ingestion.chunker import chunk_text


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
