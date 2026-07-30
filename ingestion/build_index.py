import hashlib
import json
import logging
import re
import shutil
from datetime import datetime, timezone
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

#: Marks a .md stub authored as a placeholder pointer to a video file whose
#: transcript hasn't been produced yet (see data/raw/text/*/*_video_*.md).
#: Indexing these as real documents would let a government scheme be "cited"
#: by a chunk whose entire content is "transcript coming soon" -- worse than
#: not citing anything.
_UNPRODUCED_TRANSCRIPT_MARKER = "Transcript will be produced at index time"

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
    # CPF top-ups, MRSS/MMSS, Silver Support, retirement sum schemes -- mostly
    # retirement-age content, so it re-ranks alongside the rest of Seniors.
    "cpf_top_up": "Seniors",
    "hdb_grants": "Housing",
    "medisave_medishield": "Healthcare",
    # Pre-existing corpus folders that had no mapping at all (fell to
    # Uncategorized for both text and images).
    "chas": "Healthcare",
    "col": "Household/cost-of-living",
    "gstv": "Household/cost-of-living",
    "cdc": "Household/cost-of-living",
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
    """Files under `directory`, skipping any path with an underscore-prefixed
    directory component (e.g. `_pdf_archive/`) -- the convention this corpus
    uses for archived originals whose content already has a live counterpart
    elsewhere (e.g. a PDF re-archived after being transcribed to .md).
    Indexing both would duplicate that content under two different doc_ids.
    """
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and not any(part.startswith("_") for part in path.relative_to(directory).parts[:-1])
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
        if _UNPRODUCED_TRANSCRIPT_MARKER in text:
            logger.info("Skipping unproduced video-transcript placeholder: %s", path)
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

    docs = [doc for doc in docs if doc["text"].strip()]
    _disambiguate_doc_ids(docs)
    return docs


def _disambiguate_doc_ids(docs: list[dict]) -> None:
    """Make doc_id unique in place when two source files share a filename stem.

    Several schemes reuse generic filenames (e.g. "Schemes-Terms-Conditions.pdf")
    across different folders. doc_id is derived from path.stem alone, so without
    this pass those documents collide and their chunk_ids collide too, which
    Chroma's upsert rejects outright. Disambiguation only touches doc_ids that
    actually collide, so the majority of doc_ids -- and whatever metadata
    reconciliation already matches them -- are left untouched.

    A single parent-folder suffix isn't always enough: some same-stem files
    also share a parent *folder name* across different modality subtrees
    (e.g. text/AIAP/x.md and video/AIAP/x.mp4, both under a folder literally
    named "AIAP"). Escalates in stages -- parent folder, then + modality,
    then a hash of the full source path (unique by construction) -- checking
    after each stage and only touching whatever still collides, so a
    same-parent-and-modality pair (e.g. x.pdf and x.md dropped in one folder)
    still resolves instead of raising.
    """
    original_ids = {id(doc): doc["doc_id"] for doc in docs}

    def _colliding_groups(key):
        seen: dict[str, list[dict]] = {}
        for doc in docs:
            seen.setdefault(key(doc), []).append(doc)
        return [group for group in seen.values() if len(group) > 1]

    for group in _colliding_groups(lambda d: original_ids[id(d)]):
        for doc in group:
            base = original_ids[id(doc)]
            parent = Path(doc["source_file"]).parent.name
            doc["doc_id"] = f"{base}__{parent}"

    for group in _colliding_groups(lambda d: d["doc_id"]):
        for doc in group:
            base = original_ids[id(doc)]
            parent = Path(doc["source_file"]).parent.name
            doc["doc_id"] = f"{base}__{parent}__{doc['modality']}"

    for group in _colliding_groups(lambda d: d["doc_id"]):
        for doc in group:
            base = original_ids[id(doc)]
            digest = hashlib.sha1(doc["source_file"].encode("utf-8")).hexdigest()[:8]
            doc["doc_id"] = f"{base}__{digest}"

    remaining = _colliding_groups(lambda d: d["doc_id"])
    if remaining:
        colliding_ids = sorted({doc["doc_id"] for group in remaining for doc in group})
        raise ValueError(f"doc_id collisions could not be resolved: {colliding_ids}")


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

    Several doc_ids are defined in more than one sidecar file (a thin,
    early-authored entry and a later richer one with citation-contract
    fields). Rather than letting whichever file glob-sorts last silently
    replace the other -- which could as easily discard the richer entry as
    the thin one -- entries for the same doc_id are merged, with the entry
    that has more fields treated as the base and the other only filling in
    keys it's missing. Every such conflict is logged so shadowing is visible
    instead of silent.

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
        if "template" in path.stem.lower():
            # Contributor scaffolding (e.g. metadata_template.json), not real
            # metadata -- it's full of "hdb_REPLACE_ME"/"REPLACE WITH THE URL
            # YOU LANDED ON" placeholder rows. Any real doc_id in it (kept as
            # a worked example) is expected to also exist in a real file.
            logger.info("Skipping metadata template file %s", path)
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping unparseable metadata file %s: %s", path, exc)
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
            existing = index.get(doc_id)
            if existing is None:
                index[doc_id] = flat
            elif existing == flat:
                pass  # identical duplicate, not a real conflict
            else:
                base, fill_in = (existing, flat) if len(existing) >= len(flat) else (flat, existing)
                logger.info(
                    "doc_id %r defined in more than one metadata file under %s; "
                    "merging (%d-field entry as base, %d-field entry fills gaps)",
                    doc_id, metadata_dir, len(base), len(fill_in),
                )
                index[doc_id] = {**fill_in, **base}
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
                    doc_metadata=doc_metadata_index.get(doc["doc_id"]),
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

    vectors = embed_texts([record["embed_text"] for record in all_records], embedder)
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
    # metadata.jsonl is written before the Chroma upsert so a crash between
    # the two steps always leaves Chroma with fewer chunks than metadata.jsonl
    # describes -- a state get_rag_index's count check (RagIndex.__post_init__)
    # can detect cleanly -- rather than the reverse (Chroma holding chunk_ids
    # metadata.jsonl doesn't know about, which search_chroma_index can only
    # drop silently at query time).
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as handle:
        for record in chunk_records:
            handle.write(json.dumps(record) + "\n")

    client = get_chroma_client(chroma_path)
    collection = build_chroma_collection(client, chroma_collection_name)
    upsert_chunks(
        collection,
        [record["chunk_id"] for record in chunk_records],
        vectors,
        documents=[record["embed_text"] for record in chunk_records],
        metadatas=chroma_metadatas,
    )

    # A real timestamp, not metadata.jsonl's mtime -- a git checkout, file
    # copy, or Drive resync all reset mtime without rebuilding anything, which
    # would make the frontend's stale-index banner lie in either direction.
    build_info_path = metadata_path.parent / "build_info.json"
    build_info_path.write_text(
        json.dumps({"built_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


def load_metadata(metadata_path: Path) -> list[dict]:
    with open(metadata_path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def swap_in_new_chroma_index(staging_path: Path, live_path: Path) -> None:
    """Replace `live_path` with the already-fully-built `staging_path`.

    Called only after persist_index has successfully written the staging
    directory, so the previous live index stays intact and queryable for the
    entire (multi-hour) build, and a crash mid-build never leaves `live_path`
    empty or partially written -- it is only ever touched by this final,
    fast rename step.
    """
    if live_path.exists():
        shutil.rmtree(live_path)
    staging_path.rename(live_path)


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

    # Build into a staging directory and only swap it in once fully persisted,
    # so the previous live index stays queryable for the whole build and a
    # crash never leaves data/chroma empty or half-written.
    staging_path = config.CHROMA_PATH.parent / "chroma_staging"
    if staging_path.exists():
        shutil.rmtree(staging_path)
    persist_index(
        chunk_records,
        chroma_metadatas,
        vectors,
        staging_path / "metadata.jsonl",
        chroma_path=staging_path,
        chroma_collection_name=config.CHROMA_COLLECTION_NAME,
    )

    import gc

    gc.collect()  # release chromadb's sqlite handle before renaming the directory
    swap_in_new_chroma_index(staging_path, config.CHROMA_PATH)

    print(f"Indexed {len(chunk_records)} chunks into {config.CHROMA_PATH}")
    print(
        f"Contextualization: {contextualize_stats['contextualized']} contextualized, "
        f"{contextualize_stats['fell_back']} fell back to raw text"
        + (" (circuit breaker tripped)" if contextualize_stats["circuit_broken"] else "")
    )
