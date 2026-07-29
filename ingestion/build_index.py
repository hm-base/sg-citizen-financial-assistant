import json
import logging
import re
from pathlib import Path

from config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS
from ingestion.chunker import chunk_text_structured
from ingestion.contextualize import contextualize_chunks
from ingestion.load_images_ocr import extract_image_text
from ingestion.load_text import clean_text, extract_pdf_pages, load_text_file
from ingestion.load_video_gemini import transcribe_video
from ingestion.metadata import build_chunk_records
from retrieval.chroma_index import build_chroma_collection, get_chroma_client, upsert_chunks
from retrieval.embed import embed_texts

logger = logging.getLogger(__name__)

TEXT_SUFFIXES = (".pdf", ".html", ".htm", ".md", ".markdown")
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
    # Jony — SkillsFuture / WIS / CCP / AIAP / SNAIC
    "skillsfuture": "Lower-income/employment",
    "training": "Lower-income/employment",
    "wis": "Lower-income/employment",
    "sctp": "Lower-income/employment",
    "ccp": "Lower-income/employment",
    "aiap": "Lower-income/employment",
    "snaic": "Lower-income/employment",
    # Drive / datasets topic folder names (same category)
    "workfare_wis": "Lower-income/employment",
    "skillsfuture_sctp": "Lower-income/employment",
    "career_conversion_ccp": "Lower-income/employment",
}


#: Last-resort keyword fallback for files dropped straight into
#: data/raw/<modality>/ with no category subfolder. Without it such files land in
#: "Uncategorized", which silently switches off profile re-ranking for them.
#: Ordered most- to least-specific; a category subfolder always wins over these.
CATEGORY_BY_FILENAME_KEYWORD = (
    ("comcare", "Lower-income/employment"),
    ("caregiv", "Seniors/caregiving"),
    ("silver support", "Seniors"),
    ("elder", "Seniors"),
    ("senior", "Seniors"),
    ("efass", "Seniors"),
    ("healthcare", "Healthcare"),
    ("medisave", "Healthcare"),
    ("medishield", "Healthcare"),
    ("preschool", "Family"),
    ("baby bonus", "Family"),
    ("housing", "Housing"),
    ("cost of living", "Household/cost-of-living"),
)


def category_for_path(path: Path, root: Path) -> str:
    """Derive a category for a document from its folder, then its filename.

    A category subfolder under `root` is authoritative because a curator chose
    it. Only when there is no recognised subfolder do we guess from filename
    keywords, so a stray drop still re-ranks instead of going Uncategorized.
    """
    path = Path(path)
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "Uncategorized"
    for part in relative.parts[:-1]:
        category = CATEGORY_BY_FOLDER.get(part.lower())
        if category:
            return category

    stem = path.stem.replace("-", " ").replace("_", " ").lower()
    for keyword, category in CATEGORY_BY_FILENAME_KEYWORD:
        if keyword in stem:
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
    spaced = path.stem.replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", spaced).strip().title()


def _display_name(path: Path) -> str:
    """A human-friendly title for UI citation chips, preserving the source
    filename's own casing (e.g. "ComCare", "SMTA", "AIC") instead of
    title-casing it into "Comcare"/"Smta"/"Aic".

    Filenames use " - ", " _ ", or " – " (space-padded) as the separator
    between the document title and its source site/agency, e.g.
    "ComCare Short-to-Medium-Term Assistance (SMTA) - SupportGoWhere.pdf" or
    "ElderFund _ AIC.pdf". Only that space-padded separator is normalized to
    an em dash; hyphens inside real words ("Short-to-Medium-Term", "(LTA)")
    are left untouched.
    """
    normalized = re.sub(r"\s+[-_–]\s+", " — ", path.stem)
    normalized = normalized.rstrip(" _-")
    return re.sub(r"\s+", " ", normalized).strip()


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
    transcript_cache_dir: Path | None = None,
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
            "display_name": _display_name(path),
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
            "display_name": _display_name(path),
            "category": category_for_path(path, image_dir),
            "modality": "image",
            "source_file": str(path),
            "section_or_page": "Infographic",
            "source_url": source_urls.get(path.stem, ""),
            "thumbnail_path": str(path),
        })

    video_dir = raw_dir / "video"
    video_paths = _files_under(video_dir, VIDEO_SUFFIXES)
    if video_paths and video_client is None and transcript_cache_dir is None:
        logger.warning(
            "Found %d video file(s) under %s but no transcription client was provided; "
            "skipping video ingestion.",
            len(video_paths),
            video_dir,
        )
    elif video_paths:
        # A cached transcript is reused without any Gemini call, so videos can
        # still be indexed on a re-run even with no client available.
        for path in video_paths:
            try:
                text = clean_text(
                    transcribe_video(path, video_client, cache_dir=transcript_cache_dir)
                )
            except Exception:  # noqa: BLE001
                logger.warning("Skipping untranscribable video: %s", path, exc_info=True)
                continue
            docs.append({
                "text": text,
                "doc_id": path.stem,
                "scheme_name": _scheme_name(path),
                "display_name": _display_name(path),
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


def load_doc_metadata_index(metadata_dir: Path) -> dict[str, dict]:
    """doc_id -> flat, Chroma-metadata-safe dict, sourced from
    data/metadata/*.json (both individual per-document files and combined
    arrays like metadata_hm_base.json).

    Known gap: a document whose doc_id (the raw filename stem, from
    discover_documents) doesn't match the doc_id used when its metadata file
    was authored simply gets no entry here and falls back to the minimal
    fields always available from chunk_records -- not every document in this
    corpus has had its metadata doc_id reconciled with its filename stem yet.
    """
    metadata_dir = Path(metadata_dir)
    index: dict[str, dict] = {}
    if not metadata_dir.exists():
        return index
    for path in sorted(metadata_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            doc_id = entry.get("doc_id")
            if not doc_id:
                continue
            flat = entry.get("chroma_flat_metadata_template")
            if not isinstance(flat, dict):
                flat = {
                    key: value
                    for key, value in entry.items()
                    if isinstance(value, (str, int, float, bool))
                }
            index[doc_id] = flat
    return index


def _chroma_metadata_for_chunk(
    chunk_record: dict, doc_metadata_index: dict[str, dict], chunk_index: int, chunk_total: int
) -> dict:
    """Chroma requires flat str/int/float/bool metadata values. Builds that
    payload from the doc-level template (if this doc_id has one) plus this
    chunk's own position/section, so a document with no metadata match still
    gets a usable (if minimal) payload rather than failing the upsert."""
    template = doc_metadata_index.get(chunk_record["doc_id"], {})
    base = {
        "doc_id": chunk_record["doc_id"],
        "scheme_name": chunk_record["scheme_name"],
        "category": chunk_record["category"],
        "modality": chunk_record["modality"],
        "section": chunk_record["section_or_page"],
        "source_url": chunk_record.get("source_url") or "",
    }
    return {**template, **base, "chunk_index": chunk_index, "chunk_total": chunk_total}


def build_index_from_documents(
    documents: list[dict],
    embedder,
    *,
    doc_metadata_index: dict[str, dict] | None = None,
    contextualize_llm_client=None,
    enable_contextual_chunking: bool = True,
    circuit_breaker_threshold: int = 5,
):
    """Chunks, (optionally) contextualizes, and embeds every document.

    Returns (chunk_records, chroma_metadatas, vectors, contextualize_stats).
    Contextualization only runs when `contextualize_llm_client` is given;
    otherwise every chunk keeps its plain structure-aware text, matching the
    "ENABLE_CONTEXTUAL_CHUNKING=False skips it entirely, no LLM calls made"
    contract even before that flag is checked.
    """
    if not documents:
        raise ValueError("No documents found under data/raw/ — nothing to index")

    doc_metadata_index = doc_metadata_index or {}
    all_records: list[dict] = []
    for doc in documents:
        chunks = chunk_text_structured(doc["text"], CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS)
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
                    display_name=doc.get("display_name"),
                    source_url=doc.get("source_url", ""),
                    thumbnail_path=doc.get("thumbnail_path", ""),
                )
            )

    if not all_records:
        raise ValueError("No documents found under data/raw/ — nothing to index")

    contextualize_stats = {"contextualized": 0, "fell_back": len(all_records), "circuit_broken": False}
    if contextualize_llm_client is not None:
        all_records, contextualize_stats = contextualize_chunks(
            all_records,
            doc_metadata_index,
            contextualize_llm_client,
            enabled=enable_contextual_chunking,
            circuit_breaker_threshold=circuit_breaker_threshold,
        )

    chunk_totals: dict[str, int] = {}
    for record in all_records:
        chunk_totals[record["doc_id"]] = chunk_totals.get(record["doc_id"], 0) + 1
    chunk_position: dict[str, int] = {}
    chroma_metadatas = []
    for record in all_records:
        position = chunk_position.get(record["doc_id"], 0)
        chunk_position[record["doc_id"]] = position + 1
        chroma_metadatas.append(
            _chroma_metadata_for_chunk(record, doc_metadata_index, position, chunk_totals[record["doc_id"]])
        )

    vectors = embed_texts([record["text"] for record in all_records], embedder)
    return all_records, chroma_metadatas, vectors, contextualize_stats


def persist_index(
    chunk_records: list[dict],
    chroma_metadatas: list[dict],
    vectors,
    metadata_path: Path,
    *,
    chroma_path: Path,
    chroma_collection_name: str,
) -> None:
    client = get_chroma_client(chroma_path)
    collection = build_chroma_collection(client, chroma_collection_name)
    upsert_chunks(
        collection,
        [record["chunk_id"] for record in chunk_records],
        vectors,
        documents=[record["text"] for record in chunk_records],
        metadatas=chroma_metadatas,
    )

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

    def _contextualize_client():
        # Deliberately keyed off CONTEXTUAL_CHUNKING_LLM_PROVIDER, not
        # LLM_PROVIDER -- see config.py's comment on why this bulk ingestion-
        # time job should not share a daily quota with live-query generation.
        try:
            if config.CONTEXTUAL_CHUNKING_LLM_PROVIDER == "groq":
                from generation.groq_client import GroqClient

                return GroqClient(api_key=config.GROQ_API_KEY, model_name=config.GROQ_MODEL)
            if config.CONTEXTUAL_CHUNKING_LLM_PROVIDER == "gemini":
                from generation.gemini_client import GeminiClient

                return GeminiClient(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL)
            from generation.openai_client import OpenAIClient

            return OpenAIClient(api_key=config.OPENAI_API_KEY, model_name=config.OPENAI_MODEL)
        except Exception:  # noqa: BLE001
            logger.warning("Could not construct an LLM client for contextualization.", exc_info=True)
            return None

    print(f"Using device: {get_device()}")
    embedder = load_embedder(config.EMBEDDING_MODEL)
    documents = discover_documents(
        config.DATA_DIR / "raw",
        source_urls=source_urls_from_sources_yaml(config.SOURCES_YAML_PATH),
        video_client=_video_client(),
        transcript_cache_dir=config.DATA_DIR / "processed",
    )
    print(f"Discovered {len(documents)} documents under data/raw/")

    doc_metadata_index = load_doc_metadata_index(config.DATA_DIR / "metadata")
    chunk_records, chroma_metadatas, vectors, contextualize_stats = build_index_from_documents(
        documents,
        embedder,
        doc_metadata_index=doc_metadata_index,
        contextualize_llm_client=_contextualize_client() if config.ENABLE_CONTEXTUAL_CHUNKING else None,
        enable_contextual_chunking=config.ENABLE_CONTEXTUAL_CHUNKING,
        circuit_breaker_threshold=config.CONTEXTUALIZE_CIRCUIT_BREAKER_THRESHOLD,
    )
    persist_index(
        chunk_records,
        chroma_metadatas,
        vectors,
        config.CHROMA_METADATA_PATH,
        chroma_path=config.CHROMA_PATH,
        chroma_collection_name=config.CHROMA_COLLECTION_NAME,
    )
    print(f"Indexed {len(chunk_records)} chunks into {config.CHROMA_PATH}")
    print(
        f"Contextualization: {contextualize_stats['contextualized']} contextualized, "
        f"{contextualize_stats['fell_back']} fell back to raw text"
        + (" (circuit breaker tripped)" if contextualize_stats["circuit_broken"] else "")
    )
