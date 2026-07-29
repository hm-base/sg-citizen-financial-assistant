def build_chunk_records(
    chunks: list[dict],
    *,
    doc_id: str,
    scheme_name: str,
    category: str,
    modality: str,
    source_file: str,
    section_or_page: str,
    source_url: str = "",
    thumbnail_path: str = "",
    display_name: str | None = None,
) -> list[dict]:
    """
    Attach document-level metadata to chunk dicts from chunker.

    Args:
        chunks: List of chunk dicts from ingestion.chunker.chunk_text
                Each dict must have: chunk_index, word_start, word_end, text
        doc_id: Document identifier (e.g., "baby-bonus-scheme")
        scheme_name: Name of the government scheme (e.g., "Baby Bonus Scheme")
        category: Category of the scheme (e.g., "Family", "Household")
        modality: Type of content (e.g., "text", "image")
        source_file: Path to the source file (e.g., "data/raw/text/baby_bonus.pdf")
        section_or_page: Location within the document (e.g., "Eligibility, p.2")
        source_url: Optional URL to the original document
        thumbnail_path: Optional path to thumbnail image (for image modality)
        display_name: Human-friendly document title for UI citation chips
                      (e.g. "ComCare SMTA — SupportGoWhere"); falls back to
                      scheme_name when not given.

    Returns:
        List of dicts, each with keys:
        chunk_id, doc_id, scheme_name, category, modality, source_file,
        section_or_page, source_url, thumbnail_path, display_name, text
    """
    records = []
    for chunk in chunks:
        chunk_id = f"{doc_id}_{modality}_{chunk['chunk_index']:03d}"
        records.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "scheme_name": scheme_name,
            "category": category,
            "modality": modality,
            "source_file": source_file,
            "section_or_page": section_or_page,
            "source_url": source_url,
            "thumbnail_path": thumbnail_path,
            "display_name": display_name or scheme_name,
            "text": chunk["text"],
        })
    return records
