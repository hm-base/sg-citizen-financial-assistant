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
