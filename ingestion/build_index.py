import json
import logging
from pathlib import Path

from config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS
from ingestion.chunker import chunk_text
from ingestion.load_images_ocr import extract_image_text
from ingestion.load_text import clean_text, extract_pdf_pages, load_text_file
from ingestion.load_video_gemini import transcribe_video
from ingestion.metadata import build_chunk_records
from retrieval.embed import embed_texts
from retrieval.faiss_index import build_faiss_index, save_faiss_index

logger = logging.getLogger(__name__)

TEXT_SUFFIXES = (".pdf", ".html", ".htm")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_SUFFIXES = (".mp4",)

#: Maps a folder name under data/raw/<modality>/ to a profile-filter category.
#: Categories must match the values used by retrieval.profile_filter, otherwise
#: personal-profile re-ranking silently degrades to a no-op.
CATEGORY_BY_FOLDER = {
    "elderly": "Seniors",
    "seniors": "Seniors",
    "caregiving": "Seniors/caregiving",
    "caregiver": "Seniors/caregiving",
    "healthcare": "Healthcare",
    "comcare": "Lower-income/employment",
    "employment": "Lower-income/employment",
    "lower-income": "Lower-income/employment",
    "family": "Family",
    "preschool": "Family",
    "housing": "Housing",
    "household": "Household/cost-of-living",
    "cost-of-living": "Household/cost-of-living",
}


def category_for_path(path: Path, root: Path) -> str:
    """Derive a category from the folder a document sits in, under `root`."""
    try:
        relative = Path(path).relative_to(root)
    except ValueError:
        return "Uncategorized"
    for part in relative.parts[:-1]:
        category = CATEGORY_BY_FOLDER.get(part.lower())
        if category:
            return category
    return "Uncategorized"


def source_urls_from_sources_yaml(path: Path) -> dict[str, str]:
    """Map doc_id -> source URL for documents fetched via ingestion.fetch_sources."""
    path = Path(path)
    if not path.exists():
        return {}
    from ingestion.fetch_sources import load_sources_yaml

    return {
        entry["doc_id"]: entry.get("url", "")
        for entry in load_sources_yaml(path)
        if entry.get("doc_id")
    }


def _scheme_name(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _files_under(directory: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )


def discover_documents(
    raw_dir: Path,
    *,
    source_urls: dict[str, str] | None = None,
    video_client=None,
) -> list[dict]:
    """Walk data/raw/ recursively and build one document dict per source file."""
    raw_dir = Path(raw_dir)
    source_urls = source_urls or {}
    docs: list[dict] = []

    text_dir = raw_dir / "text"
    for path in _files_under(text_dir, TEXT_SUFFIXES):
        try:
            page_texts = (
                [clean_text(page) for page in extract_pdf_pages(path)]
                if path.suffix.lower() == ".pdf"
                else []
            )
            text = "\n".join(page_texts) if page_texts else clean_text(load_text_file(path))
        except Exception:  # noqa: BLE001 - one unreadable file must not abort the build
            logger.warning("Skipping unreadable text document: %s", path, exc_info=True)
            continue
        docs.append({
            "text": text,
            "page_texts": page_texts,
            "doc_id": path.stem,
            "scheme_name": _scheme_name(path),
            "category": category_for_path(path, text_dir),
            "modality": "text",
            "source_file": str(path),
            "section_or_page": "Full document",
            "source_url": source_urls.get(path.stem, ""),
            "thumbnail_path": "",
        })

    image_dir = raw_dir / "images"
    for path in _files_under(image_dir, IMAGE_SUFFIXES):
        try:
            text = clean_text(extract_image_text(path))
        except Exception:  # noqa: BLE001
            logger.warning("Skipping unreadable image document: %s", path, exc_info=True)
            continue
        docs.append({
            "text": text,
            "doc_id": path.stem,
            "scheme_name": _scheme_name(path),
            "category": category_for_path(path, image_dir),
            "modality": "image",
            "source_file": str(path),
            "section_or_page": "Infographic",
            "source_url": source_urls.get(path.stem, ""),
            "thumbnail_path": str(path),
        })

    video_dir = raw_dir / "video"
    video_paths = _files_under(video_dir, VIDEO_SUFFIXES)
    if video_paths and video_client is None:
        logger.warning(
            "Found %d video file(s) under %s but no transcription client was provided; "
            "skipping video ingestion.",
            len(video_paths),
            video_dir,
        )
    elif video_paths:
        for path in video_paths:
            try:
                text = clean_text(transcribe_video(path, video_client))
            except Exception:  # noqa: BLE001
                logger.warning("Skipping untranscribable video: %s", path, exc_info=True)
                continue
            docs.append({
                "text": text,
                "doc_id": path.stem,
                "scheme_name": _scheme_name(path),
                "category": category_for_path(path, video_dir),
                "modality": "video",
                "source_file": str(path),
                "section_or_page": "Video transcript",
                "source_url": source_urls.get(path.stem, ""),
                "thumbnail_path": "",
            })

    return [doc for doc in docs if doc["text"].strip()]


def section_labels_for_chunks(chunks: list[dict], doc: dict) -> list[str]:
    """Per-chunk citation labels, using real PDF page numbers when available."""
    page_texts = doc.get("page_texts") or []
    default = doc["section_or_page"]
    if not page_texts:
        return [default] * len(chunks)

    spans: list[tuple[int, int, int]] = []
    cursor = 0
    for page_number, page_text in enumerate(page_texts, start=1):
        word_count = len(page_text.split())
        spans.append((cursor, cursor + word_count, page_number))
        cursor += word_count

    labels = []
    for chunk in chunks:
        pages = [
            page
            for start, end, page in spans
            if start < chunk["word_end"] and end > chunk["word_start"]
        ]
        if not pages:
            labels.append(default)
        elif len(pages) == 1:
            labels.append(f"p.{pages[0]}")
        else:
            labels.append(f"pp.{pages[0]}-{pages[-1]}")
    return labels


def build_index_from_documents(documents: list[dict], embedder):
    if not documents:
        raise ValueError("No documents found under data/raw/ — nothing to index")

    all_records: list[dict] = []
    for doc in documents:
        chunks = chunk_text(doc["text"], CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS)
        labels = section_labels_for_chunks(chunks, doc)
        for chunk, label in zip(chunks, labels):
            all_records.extend(
                build_chunk_records(
                    [chunk],
                    doc_id=doc["doc_id"],
                    scheme_name=doc["scheme_name"],
                    category=doc["category"],
                    modality=doc["modality"],
                    source_file=doc["source_file"],
                    section_or_page=label,
                    source_url=doc.get("source_url", ""),
                    thumbnail_path=doc.get("thumbnail_path", ""),
                )
            )

    if not all_records:
        raise ValueError("No documents found under data/raw/ — nothing to index")

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
    from retrieval.embed import get_device, load_embedder

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    def _video_client():
        try:
            from backend.main import get_llm_client

            client = get_llm_client()
        except Exception:  # noqa: BLE001
            logger.warning("Could not construct an LLM client for video transcription.", exc_info=True)
            return None
        return client if hasattr(client, "transcribe") else None

    print(f"Using device: {get_device()}")
    embedder = load_embedder(config.EMBEDDING_MODEL)
    documents = discover_documents(
        config.DATA_DIR / "raw",
        source_urls=source_urls_from_sources_yaml(config.SOURCES_YAML_PATH),
        video_client=_video_client(),
    )
    print(f"Discovered {len(documents)} documents under data/raw/")

    faiss_index, chunk_records = build_index_from_documents(documents, embedder)
    persist_index(faiss_index, chunk_records, config.FAISS_INDEX_PATH, config.FAISS_METADATA_PATH)
    print(f"Indexed {len(chunk_records)} chunks into {config.FAISS_INDEX_PATH}")
