import json

from ingestion.build_index import (
    build_index_from_documents,
    load_doc_metadata_index,
    load_metadata,
    persist_index,
    swap_in_new_chroma_index,
)
from retrieval.chroma_index import get_chroma_client, get_or_create_chroma_collection
from retrieval.embed import load_embedder


def _document(doc_id="baby-bonus-scheme", repeat_text="Baby Bonus gives cash gifts to parents of Singaporean children. "):
    return {
        "text": repeat_text * 50,
        "doc_id": doc_id,
        "scheme_name": "Baby Bonus Scheme",
        "category": "Family",
        "modality": "text",
        "source_file": f"data/raw/text/{doc_id}.pdf",
        "section_or_page": "Overview",
        "source_url": "",
        "thumbnail_path": "",
    }


def test_build_index_from_documents_chunks_and_embeds_all_docs():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [_document()]

    chunk_records, chroma_metadatas, vectors, stats = build_index_from_documents(documents, embedder)

    assert vectors.shape[0] == len(chunk_records)
    assert len(chunk_records) > 1  # long text should split into multiple chunks
    assert len(chroma_metadatas) == len(chunk_records)
    assert all(record["doc_id"] == "baby-bonus-scheme" for record in chunk_records)
    # No contextualize_llm_client given -- every chunk falls back to raw text.
    assert stats == {"contextualized": 0, "fell_back": len(chunk_records), "circuit_broken": False}


def test_build_index_from_documents_fills_chunk_index_and_total_in_chroma_metadata():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [_document()]

    chunk_records, chroma_metadatas, _vectors, _stats = build_index_from_documents(documents, embedder)

    total = len(chunk_records)
    for position, metadata in enumerate(chroma_metadatas):
        assert metadata["chunk_index"] == position
        assert metadata["chunk_total"] == total
        assert metadata["doc_id"] == "baby-bonus-scheme"


def test_build_index_from_documents_uses_contextualize_client_when_given():
    class FakeLLMClient:
        def generate(self, prompt: str) -> str:
            return "Context sentence."

    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [_document()]

    chunk_records, _metadatas, _vectors, stats = build_index_from_documents(
        documents, embedder, contextualize_llm_client=FakeLLMClient()
    )

    assert stats["contextualized"] == len(chunk_records)
    assert stats["fell_back"] == 0
    assert all(record["embed_text"].startswith("Context sentence.") for record in chunk_records)
    # The displayed/prompted text must stay the original chunk text, never
    # the LLM-written context sentence.
    assert all(not record["text"].startswith("Context sentence.") for record in chunk_records)


def test_load_doc_metadata_index_reads_individual_and_combined_files(tmp_path):
    (tmp_path / "single.json").write_text(
        json.dumps({
            "doc_id": "cpf_wis_scheme_page",
            "agency": "CPF",
            "tier": "A",
            "chroma_flat_metadata_template": {
                "doc_id": "cpf_wis_scheme_page",
                "agency": "CPF",
                "tier": "A",
                "chunk_index": 0,
                "chunk_total": 0,
            },
        }),
        encoding="utf-8",
    )
    (tmp_path / "combined.json").write_text(
        json.dumps([
            {"doc_id": "CHAS_Green", "title": "CHAS Green", "agency": "MOH", "tier": "A"},
            {"doc_id": "CHAS_Orange", "title": "CHAS Orange", "agency": "MOH", "tier": "A"},
        ]),
        encoding="utf-8",
    )

    index = load_doc_metadata_index(tmp_path)

    assert index["cpf_wis_scheme_page"]["agency"] == "CPF"
    assert index["CHAS_Green"]["title"] == "CHAS Green"
    assert index["CHAS_Orange"]["agency"] == "MOH"


def test_load_doc_metadata_index_returns_empty_for_missing_directory(tmp_path):
    assert load_doc_metadata_index(tmp_path / "does-not-exist") == {}


def test_load_doc_metadata_index_merges_conflicting_entries_preferring_the_richer_one(tmp_path):
    """Regression test: a thin, alphabetically-later file used to silently
    replace a richer, earlier-processed entry for the same doc_id, discarding
    citation-contract fields the richer file existed to add."""
    (tmp_path / "aaa_thin.json").write_text(
        json.dumps({"doc_id": "cpf_wis_scheme_page", "agency": "CPF", "tier": "A"}),
        encoding="utf-8",
    )
    (tmp_path / "zzz_rich.json").write_text(
        json.dumps({
            "doc_id": "cpf_wis_scheme_page",
            "agency": "CPF",
            "tier": "A",
            "citation": "CPF Board — Workfare Income Supplement",
            "canonical_url": "https://www.cpf.gov.sg/wis",
            "authority_rank": 1,
        }),
        encoding="utf-8",
    )

    index = load_doc_metadata_index(tmp_path)

    entry = index["cpf_wis_scheme_page"]
    assert entry["citation"] == "CPF Board — Workfare Income Supplement"
    assert entry["canonical_url"] == "https://www.cpf.gov.sg/wis"
    assert entry["authority_rank"] == 1


def test_load_doc_metadata_index_skips_template_files(tmp_path):
    """Regression test: metadata_template.json is contributor scaffolding
    full of "*_REPLACE_ME" placeholder doc_ids and a placeholder source_url
    -- it must never be ingested as real metadata."""
    (tmp_path / "metadata_template.json").write_text(
        json.dumps([
            {
                "doc_id": "hdb_REPLACE_ME",
                "source_url": "REPLACE WITH THE URL YOU LANDED ON",
                "agency": "HDB",
            }
        ]),
        encoding="utf-8",
    )
    (tmp_path / "real.json").write_text(
        json.dumps({"doc_id": "hdb_ehg_families", "agency": "HDB", "tier": "A"}),
        encoding="utf-8",
    )

    index = load_doc_metadata_index(tmp_path)

    assert "hdb_REPLACE_ME" not in index
    assert index["hdb_ehg_families"]["agency"] == "HDB"


def test_load_doc_metadata_index_warns_on_malformed_file_and_keeps_other_files(tmp_path, caplog):
    (tmp_path / "broken.json").write_text('{"doc_id": "oops,', encoding="utf-8")
    (tmp_path / "good.json").write_text(
        json.dumps({"doc_id": "cpf_wis_scheme_page", "agency": "CPF"}), encoding="utf-8"
    )

    with caplog.at_level("WARNING"):
        index = load_doc_metadata_index(tmp_path)

    assert index == {"cpf_wis_scheme_page": {"doc_id": "cpf_wis_scheme_page", "agency": "CPF"}}
    assert any("broken.json" in record.message for record in caplog.records)


def test_persist_index_and_load_metadata_roundtrip(tmp_path):
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = [_document(doc_id="silver-support", repeat_text="Silver Support gives quarterly payouts. ")]
    chunk_records, chroma_metadatas, vectors, _stats = build_index_from_documents(documents, embedder)
    metadata_path = tmp_path / "metadata.jsonl"
    chroma_path = tmp_path / "chroma"

    persist_index(
        chunk_records,
        chroma_metadatas,
        vectors,
        metadata_path,
        chroma_path=chroma_path,
        chroma_collection_name="test-collection",
    )
    loaded_records = load_metadata(metadata_path)

    assert len(loaded_records) == len(chunk_records)
    assert loaded_records[0]["chunk_id"] == chunk_records[0]["chunk_id"]

    client = get_chroma_client(chroma_path)
    collection = get_or_create_chroma_collection(client, "test-collection")
    assert collection.count() == len(chunk_records)

    build_info = json.loads((metadata_path.parent / "build_info.json").read_text(encoding="utf-8"))
    assert "built_at" in build_info


def test_swap_in_new_chroma_index_replaces_the_live_directory_with_staging(tmp_path):
    live_path = tmp_path / "chroma"
    live_path.mkdir()
    (live_path / "old_metadata.jsonl").write_text("old", encoding="utf-8")

    staging_path = tmp_path / "chroma_staging"
    staging_path.mkdir()
    (staging_path / "metadata.jsonl").write_text("new", encoding="utf-8")

    swap_in_new_chroma_index(staging_path, live_path)

    assert not staging_path.exists()
    assert (live_path / "metadata.jsonl").read_text(encoding="utf-8") == "new"
    assert not (live_path / "old_metadata.jsonl").exists()


def test_swap_in_new_chroma_index_works_when_no_live_directory_exists_yet(tmp_path):
    live_path = tmp_path / "chroma"
    staging_path = tmp_path / "chroma_staging"
    staging_path.mkdir()
    (staging_path / "metadata.jsonl").write_text("new", encoding="utf-8")

    swap_in_new_chroma_index(staging_path, live_path)

    assert (live_path / "metadata.jsonl").read_text(encoding="utf-8") == "new"
