from pathlib import Path

import faiss
import numpy as np


def build_faiss_index(vectors: np.ndarray) -> faiss.IndexFlatIP:
    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)
    return index


def save_faiss_index(index: faiss.IndexFlatIP, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_faiss_index(path: Path) -> faiss.IndexFlatIP:
    return faiss.read_index(str(path))


def search_faiss_index(
    index: faiss.IndexFlatIP, query_vector: np.ndarray, top_k: int
) -> list[tuple[int, float]]:
    safe_k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, safe_k)
    return [
        (int(idx), float(score))
        for idx, score in zip(indices[0], scores[0])
        if idx != -1
    ]
