import re


def split_into_sections(text: str) -> list[str]:
    """Split on blank-line paragraph/heading boundaries. Every word in `text`
    ends up in exactly one section, in order -- callers rely on this to
    derive word offsets by cumulative counting rather than re-locating each
    section's text in the original string."""
    parts = re.split(r"\n\s*\n+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def chunk_text_structured(text: str, chunk_size: int, overlap: int) -> list[dict]:
    """Structure-aware chunking: pack whole paragraphs together up to
    chunk_size words, so a chunk never splits a paragraph mid-sentence.

    A paragraph that alone exceeds chunk_size falls back to chunk_text's
    fixed word-count splitting for that paragraph only, so no chunk ever
    silently exceeds the configured size regardless of source formatting.

    No artificial word-overlap is added between packed paragraphs -- the
    paragraph boundary itself is the natural break point Anthropic's
    "contextual retrieval" pattern and most semantic chunkers rely on instead
    of overlap. `overlap` is only used by the oversized-paragraph fallback,
    where word-count splitting still needs it.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    if not text.strip():
        raise ValueError("Cannot chunk empty text")

    sections = split_into_sections(text)
    chunks: list[dict] = []
    buffer_texts: list[str] = []
    buffer_word_count = 0
    buffer_start = 0
    cursor = 0  # running word offset into the document

    def flush():
        nonlocal buffer_texts, buffer_word_count
        if buffer_texts:
            chunks.append({
                "chunk_index": len(chunks),
                "word_start": buffer_start,
                "word_end": buffer_start + buffer_word_count,
                "text": "\n\n".join(buffer_texts).strip(),
            })
        buffer_texts = []
        buffer_word_count = 0

    for section in sections:
        section_len = len(section.split())

        if section_len > chunk_size:
            flush()
            for sub in chunk_text(section, chunk_size, overlap):
                chunks.append({
                    "chunk_index": len(chunks),
                    "word_start": cursor + sub["word_start"],
                    "word_end": cursor + sub["word_end"],
                    "text": sub["text"],
                })
            cursor += section_len
            continue

        if buffer_texts and buffer_word_count + section_len > chunk_size:
            flush()

        if not buffer_texts:
            buffer_start = cursor
        buffer_texts.append(section)
        buffer_word_count += section_len
        cursor += section_len

    flush()
    return chunks


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    if not text.strip():
        raise ValueError("Cannot chunk empty text")

    words = text.split()
    step = chunk_size - overlap
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_value = " ".join(words[start:end]).strip()
        if chunk_value:
            chunks.append({
                "chunk_index": len(chunks),
                "word_start": start,
                "word_end": end,
                "text": chunk_value,
            })
        if end == len(words):
            break
        start += step
    return chunks
