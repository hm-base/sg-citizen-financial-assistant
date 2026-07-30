import numpy as np

from retrieval.chroma_index import (
    build_chroma_collection,
    get_chroma_client,
    get_or_create_chroma_collection,
    search_chroma_index,
    upsert_chunks,
)


def _unit_vectors():
    raw = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.9, 0.1, 0.0]],
        dtype=np.float32,
    )
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    return (raw / norms).astype(np.float32)


CHUNK_IDS = ["doc-a_text_000", "doc-b_text_000", "doc-c_text_000"]


def _index_map():
    return {chunk_id: i for i, chunk_id in enumerate(CHUNK_IDS)}


def test_build_and_search_chroma_index_ranks_by_similarity(tmp_path):
    client = get_chroma_client(tmp_path / "chroma")
    collection = build_chroma_collection(client, "test-collection")
    vectors = _unit_vectors()
    upsert_chunks(
        collection,
        CHUNK_IDS,
        vectors,
        documents=["a", "b", "c"],
        metadatas=[{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}],
    )

    query = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    results = search_chroma_index(collection, query, top_k=2, chunk_id_to_index=_index_map())

    assert results[0][0] == 0  # most similar to itself
    assert results[1][0] == 2  # second-closest is the near-duplicate
    assert results[0][1] > results[1][1]


def test_search_chroma_index_returns_empty_for_non_positive_top_k(tmp_path):
    client = get_chroma_client(tmp_path / "chroma")
    collection = build_chroma_collection(client, "test-collection")
    upsert_chunks(
        collection,
        CHUNK_IDS[:2],
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        documents=["a", "b"],
        metadatas=[{"doc_id": "a"}, {"doc_id": "b"}],
    )
    query_vector = np.array([[1.0, 0.0]], dtype=np.float32)

    assert search_chroma_index(collection, query_vector, 0, _index_map()) == []


def test_build_chroma_collection_clears_stale_chunks_from_a_previous_build(tmp_path):
    """A rebuild must not mix stale chunks from a previous corpus into the
    new one -- build_chroma_collection always starts from an empty
    collection, unlike get_or_create which would keep old entries."""
    client = get_chroma_client(tmp_path / "chroma")
    first = build_chroma_collection(client, "test-collection")
    upsert_chunks(
        first,
        ["stale_text_000"],
        np.array([[1.0, 0.0]], dtype=np.float32),
        documents=["stale"],
        metadatas=[{"doc_id": "stale"}],
    )
    assert first.count() == 1

    second = build_chroma_collection(client, "test-collection")
    assert second.count() == 0


def test_search_chroma_index_warns_and_drops_a_chunk_id_missing_from_the_index_map(tmp_path, caplog):
    """Regression test: if metadata.jsonl and the Chroma collection ever
    drift out of sync (e.g. a crash mid-persist), a hit whose chunk_id has no
    entry in chunk_id_to_index used to be dropped with zero visibility --
    silently degrading into an unexplained abstention somewhere upstream."""
    client = get_chroma_client(tmp_path / "chroma")
    collection = build_chroma_collection(client, "test-collection")
    upsert_chunks(
        collection,
        CHUNK_IDS[:2],
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        documents=["a", "b"],
        metadatas=[{"doc_id": "a"}, {"doc_id": "b"}],
    )
    # chunk_id_to_index only knows about "doc-a_text_000" -- "doc-b_text_000"
    # stands in for a chunk present in Chroma but absent from chunk_records.
    incomplete_index_map = {"doc-a_text_000": 0}
    query = np.array([[1.0, 0.0]], dtype=np.float32)

    with caplog.at_level("WARNING"):
        results = search_chroma_index(collection, query, top_k=2, chunk_id_to_index=incomplete_index_map)

    assert results == [(0, 1.0)]
    assert any("doc-b_text_000" in record.message for record in caplog.records)


def test_get_or_create_chroma_collection_persists_across_client_instances(tmp_path):
    path = tmp_path / "chroma"
    client_a = get_chroma_client(path)
    collection_a = get_or_create_chroma_collection(client_a, "persisted")
    upsert_chunks(
        collection_a,
        ["doc_text_000"],
        np.array([[1.0, 0.0]], dtype=np.float32),
        documents=["hello"],
        metadatas=[{"doc_id": "doc"}],
    )

    client_b = get_chroma_client(path)
    collection_b = get_or_create_chroma_collection(client_b, "persisted")
    assert collection_b.count() == 1
