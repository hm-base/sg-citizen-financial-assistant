from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def build_bm25_index(chunk_texts: list[str]) -> BM25Okapi:
    tokenized = [_tokenize(text) for text in chunk_texts]
    return BM25Okapi(tokenized)


def search_bm25_index(index: BM25Okapi, query: str, top_k: int) -> list[tuple[int, float]]:
    scores = index.get_scores(_tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    return [(idx, float(score)) for idx, score in ranked[:top_k] if score > 0]
