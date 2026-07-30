import logging
from pathlib import Path

import chromadb
import numpy as np

logger = logging.getLogger(__name__)


def get_chroma_client(path: Path) -> chromadb.ClientAPI:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def build_chroma_collection(client: chromadb.ClientAPI, name: str):
    """(Re)creates an empty collection so a rebuild never mixes stale chunks
    from a previous corpus with the current one."""
    try:
        client.delete_collection(name=name)
    except Exception:  # noqa: BLE001 - collection may not exist yet
        pass
    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def get_or_create_chroma_collection(client: chromadb.ClientAPI, name: str):
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def upsert_chunks(
    collection,
    chunk_ids: list[str],
    vectors: np.ndarray,
    documents: list[str],
    metadatas: list[dict],
) -> None:
    if not chunk_ids:
        return
    collection.upsert(
        ids=chunk_ids,
        embeddings=vectors.tolist(),
        documents=documents,
        metadatas=metadatas,
    )


def search_chroma_index(
    collection,
    query_vector: np.ndarray,
    top_k: int,
    chunk_id_to_index: dict[str, int],
    *,
    collection_count: int | None = None,
) -> list[tuple[int, float]]:
    """Returns (row_index, cosine_similarity) tuples keyed into the same
    chunk_records array BM25 already indexes into -- this is deliberately the
    same contract this project's original FAISS-backed search function used
    (since removed), so retrieval/hybrid.py's reciprocal rank fusion and
    generation/pipeline.py's gate-score logic need no changes.

    Chroma's own identity for a hit is its string chunk_id; chunk_id_to_index
    (built once from chunk_records order at RagIndex construction time)
    translates that back to the positional index BM25 and the rest of the
    pipeline already assume.

    `collection_count` lets a caller that already knows the collection's size
    (RagIndex caches it once at construction) skip a DB round trip that
    otherwise happens on every single retrieval call. Falls back to a live
    `collection.count()` when not given, so existing callers are unaffected.
    """
    safe_k = min(top_k, collection.count() if collection_count is None else collection_count)
    if safe_k <= 0:
        return []
    result = collection.query(query_embeddings=query_vector.tolist(), n_results=safe_k)
    ids = result["ids"][0]
    distances = result["distances"][0]
    output = []
    for chunk_id, distance in zip(ids, distances):
        index = chunk_id_to_index.get(chunk_id)
        if index is None:
            logger.warning(
                "Chroma returned chunk_id %r with no matching entry in chunk_records -- "
                "the Chroma collection and metadata.jsonl have drifted out of sync. "
                "Dropping this hit.",
                chunk_id,
            )
            continue
        # Vectors are pre-normalized (retrieval.embed.embed_texts), so cosine
        # distance = 1 - cosine_similarity for Chroma's "cosine" hnsw space.
        similarity = 1.0 - distance
        output.append((index, float(similarity)))
    return output
