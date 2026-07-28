import json

from ingestion.build_index import build_index_from_documents, load_metadata, persist_index
from retrieval.embed import load_embedder


def test_build_index_from_documents_chunks_embeds_and_indexes_all_docs():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [
        {
            # Repeated enough times to exceed CHUNK_SIZE_WORDS and force multiple chunks
            "text": "Baby Bonus gives cash gifts to parents of Singaporean children. " * 50,
            "doc_id": "baby-bonus-scheme",
            "scheme_name": "Baby Bonus Scheme",
            "category": "Family",
            "modality": "text",
            "source_file": "data/raw/text/baby_bonus.pdf",
            "section_or_page": "Overview",
            "source_url": "",
            "thumbnail_path": "",
        },
    ]

    faiss_index, chunk_records = build_index_from_documents(documents, embedder)

    assert faiss_index.ntotal == len(chunk_records)
    assert faiss_index.ntotal > 1  # long text should split into multiple chunks
    assert all(record["doc_id"] == "baby-bonus-scheme" for record in chunk_records)


def test_persist_index_and_load_metadata_roundtrip(tmp_path):
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [
        {
            "text": "Silver Support gives quarterly payouts to eligible seniors. " * 30,
            "doc_id": "silver-support",
            "scheme_name": "Silver Support Scheme",
            "category": "Seniors",
            "modality": "text",
            "source_file": "data/raw/text/silver_support.pdf",
            "section_or_page": "Overview",
            "source_url": "",
            "thumbnail_path": "",
        },
    ]
    faiss_index, chunk_records = build_index_from_documents(documents, embedder)
    faiss_path = tmp_path / "index.faiss"
    metadata_path = tmp_path / "metadata.jsonl"

    persist_index(faiss_index, chunk_records, faiss_path, metadata_path)
    loaded_records = load_metadata(metadata_path)

    assert faiss_path.exists()
    assert len(loaded_records) == len(chunk_records)
    assert loaded_records[0]["chunk_id"] == chunk_records[0]["chunk_id"]
