import json
from pathlib import Path

from config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS
from ingestion.chunker import chunk_text
from ingestion.metadata import build_chunk_records
from retrieval.embed import embed_texts
from retrieval.faiss_index import build_faiss_index, save_faiss_index


def build_index_from_documents(documents: list[dict], embedder):
    all_records: list[dict] = []
    for doc in documents:
        chunks = chunk_text(doc["text"], CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS)
        records = build_chunk_records(
            chunks,
            doc_id=doc["doc_id"],
            scheme_name=doc["scheme_name"],
            category=doc["category"],
            modality=doc["modality"],
            source_file=doc["source_file"],
            section_or_page=doc["section_or_page"],
            source_url=doc.get("source_url", ""),
            thumbnail_path=doc.get("thumbnail_path", ""),
        )
        all_records.extend(records)

    vectors = embed_texts([record["text"] for record in all_records], embedder)
    faiss_index = build_faiss_index(vectors)
    return faiss_index, all_records


def persist_index(faiss_index, chunk_records: list[dict], faiss_path: Path, metadata_path: Path) -> None:
    save_faiss_index(faiss_index, faiss_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as handle:
        for record in chunk_records:
            handle.write(json.dumps(record) + "\n")


def load_metadata(metadata_path: Path) -> list[dict]:
    with open(metadata_path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    import config
    from ingestion.load_images_ocr import extract_image_text
    from ingestion.load_text import clean_text, load_text_file
    from retrieval.embed import get_device, load_embedder

    def _discover_documents() -> list[dict]:
        docs = []
        text_dir = config.DATA_DIR / "raw" / "text"
        for path in text_dir.glob("*"):
            if path.suffix.lower() in (".pdf", ".html", ".htm"):
                docs.append({
                    "text": clean_text(load_text_file(path)),
                    "doc_id": path.stem,
                    "scheme_name": path.stem.replace("-", " ").title(),
                    "category": "Uncategorized",
                    "modality": "text",
                    "source_file": str(path),
                    "section_or_page": "Full document",
                    "source_url": "",
                    "thumbnail_path": "",
                })

        image_dir = config.DATA_DIR / "raw" / "images"
        for path in image_dir.glob("*"):
            docs.append({
                "text": clean_text(extract_image_text(path)),
                "doc_id": path.stem,
                "scheme_name": path.stem.replace("-", " ").title(),
                "category": "Uncategorized",
                "modality": "image",
                "source_file": str(path),
                "section_or_page": "Infographic",
                "source_url": "",
                "thumbnail_path": str(path),
            })
        return [doc for doc in docs if doc["text"].strip()]

    print(f"Using device: {get_device()}")
    embedder = load_embedder(config.EMBEDDING_MODEL)
    documents = _discover_documents()
    print(f"Discovered {len(documents)} documents under data/raw/")

    faiss_index, chunk_records = build_index_from_documents(documents, embedder)
    persist_index(faiss_index, chunk_records, config.FAISS_INDEX_PATH, config.FAISS_METADATA_PATH)
    print(f"Indexed {len(chunk_records)} chunks into {config.FAISS_INDEX_PATH}")
