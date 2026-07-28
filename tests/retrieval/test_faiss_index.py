import numpy as np

from retrieval.faiss_index import build_faiss_index, load_faiss_index, save_faiss_index, search_faiss_index


def _unit_vectors():
    raw = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.9, 0.1, 0.0]],
        dtype=np.float32,
    )
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    return (raw / norms).astype(np.float32)


def test_build_and_search_faiss_index_ranks_by_similarity():
    vectors = _unit_vectors()
    index = build_faiss_index(vectors)

    query = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    results = search_faiss_index(index, query, top_k=2)

    assert results[0][0] == 0  # most similar to itself
    assert results[1][0] == 2  # second-closest is the near-duplicate
    assert results[0][1] > results[1][1]


def test_save_and_load_faiss_index_roundtrips(tmp_path):
    vectors = _unit_vectors()
    index = build_faiss_index(vectors)
    path = tmp_path / "index.faiss"

    save_faiss_index(index, path)
    loaded = load_faiss_index(path)

    assert loaded.ntotal == index.ntotal
    assert loaded.d == index.d
