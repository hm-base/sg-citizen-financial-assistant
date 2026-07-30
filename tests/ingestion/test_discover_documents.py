from pathlib import Path

import pytest
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from ingestion.build_index import (
    _disambiguate_doc_ids,
    _display_name,
    _scheme_name,
    build_index_from_documents,
    category_for_path,
    discover_documents,
    source_urls_from_sources_yaml,
)
from retrieval.embed import load_embedder


def _write_pdf(path: Path, pages: list[str]) -> None:
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for page_text in pages:
        pdf.add_page()
        pdf.multi_cell(0, 10, page_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def _write_image(path: Path, text: str) -> None:
    image = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 60), text, fill="black", font=ImageFont.load_default())
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


@pytest.fixture
def nested_corpus(tmp_path: Path) -> Path:
    """A miniature data/raw/ tree with documents nested one level deep."""
    raw_dir = tmp_path / "raw"
    _write_pdf(
        raw_dir / "text" / "elderly" / "silver-support.pdf",
        [
            "Silver Support Scheme gives quarterly cash payouts to lower income seniors.",
            "Seniors aged sixty five and above may qualify for Silver Support payouts.",
        ],
    )
    _write_image(
        raw_dir / "images" / "comcare" / "comcare-steps.png",
        "COMCARE APPLICATION STEPS",
    )
    return raw_dir


def test_discover_documents_finds_files_in_nested_subdirectories(nested_corpus):
    docs = discover_documents(nested_corpus)

    by_modality = {doc["modality"] for doc in docs}
    assert by_modality == {"text", "image"}
    assert {doc["doc_id"] for doc in docs} == {"silver-support", "comcare-steps"}


def test_discover_documents_disambiguates_colliding_filename_stems(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_pdf(
        raw_dir / "text" / "comcare" / "Terms-Conditions.pdf",
        ["ComCare terms and conditions apply to all applicants."],
    )
    _write_pdf(
        raw_dir / "text" / "elderly" / "Terms-Conditions.pdf",
        ["Silver Support terms and conditions apply to all applicants."],
    )

    docs = discover_documents(raw_dir)

    doc_ids = [doc["doc_id"] for doc in docs]
    assert len(doc_ids) == len(set(doc_ids)), "colliding doc_ids must be disambiguated"
    assert "Terms-Conditions__comcare" in doc_ids
    assert "Terms-Conditions__elderly" in doc_ids


def test_disambiguate_doc_ids_escalates_to_modality_when_parent_folder_name_also_matches():
    """Regression test: two files with the same stem AND the same parent
    *folder name* (but under different modality subtrees, e.g. text/AIAP/
    and video/AIAP/) used to get the identical parent-only suffix and still
    collide, corrupting the shared doc_id's chunk position/total counters."""
    docs = [
        {
            "doc_id": "aisg_aiap_video_86q_VISXpzM",
            "source_file": "data/raw/text/AIAP/aisg_aiap_video_86q_VISXpzM.md",
            "modality": "text",
        },
        {
            "doc_id": "aisg_aiap_video_86q_VISXpzM",
            "source_file": "data/raw/video/AIAP/aisg_aiap_video_86q_VISXpzM.mp4",
            "modality": "video",
        },
    ]

    _disambiguate_doc_ids(docs)

    doc_ids = [doc["doc_id"] for doc in docs]
    assert len(doc_ids) == len(set(doc_ids))
    assert "aisg_aiap_video_86q_VISXpzM__AIAP__text" in doc_ids
    assert "aisg_aiap_video_86q_VISXpzM__AIAP__video" in doc_ids


def test_disambiguate_doc_ids_falls_back_to_a_path_hash_when_modality_also_matches():
    """Regression test: two files with the same stem, same parent folder,
    AND same modality (e.g. a .pdf and its .md transcription dropped in one
    folder) used to still collide after the modality suffix, which Chroma's
    upsert rejects -- but only after embedding the whole batch with BGE-M3."""
    docs = [
        {
            "doc_id": "scheme-page",
            "source_file": "data/raw/text/comcare/scheme-page.pdf",
            "modality": "text",
        },
        {
            "doc_id": "scheme-page",
            "source_file": "data/raw/text/comcare/scheme-page.md",
            "modality": "text",
        },
    ]

    _disambiguate_doc_ids(docs)

    doc_ids = [doc["doc_id"] for doc in docs]
    assert len(doc_ids) == len(set(doc_ids))
    assert all(doc_id.startswith("scheme-page__") for doc_id in doc_ids)


def test_discover_documents_skips_unproduced_video_transcript_placeholders(tmp_path):
    """Regression test: a .md stub authored as a placeholder pointer to an
    untranscribed video (real content in this corpus: 9 such files) was
    indexed as a real document, so a scheme could be "cited" by a chunk
    whose entire content is "transcript coming soon"."""
    raw_dir = tmp_path / "raw"
    stub = raw_dir / "text" / "AIAP" / "aisg_aiap_video_86q_VISXpzM.md"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(
        "---\ndoc_id: \"aisg_aiap_video_86q_VISXpzM\"\n---\n\n"
        "# AIAP YouTube\n\n"
        "This source is a **video**.\n\n"
        "Transcript will be produced at index time via Gemini (`modality: video`).",
        encoding="utf-8",
    )
    _write_pdf(
        raw_dir / "text" / "AIAP" / "aisg_aiap_apprenticeship.pdf",
        ["AI Apprenticeship Programme gives stipends to trainees."],
    )

    docs = discover_documents(raw_dir)

    doc_ids = {doc["doc_id"] for doc in docs}
    assert "aisg_aiap_video_86q_VISXpzM" not in doc_ids
    assert "aisg_aiap_apprenticeship" in doc_ids


def test_discover_documents_skips_underscore_prefixed_archive_folders(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_pdf(
        raw_dir / "text" / "comcare" / "scheme-page.pdf",
        ["ComCare scheme page transcribed to markdown."],
    )
    _write_pdf(
        raw_dir / "text" / "_pdf_archive" / "comcare" / "scheme-page.pdf",
        ["Archived original PDF, same content as the transcribed copy."],
    )

    docs = discover_documents(raw_dir)

    assert len(docs) == 1
    assert docs[0]["doc_id"] == "scheme-page"
    assert "_pdf_archive" not in docs[0]["source_file"]


def test_discover_documents_skips_directories_and_unsupported_suffixes(nested_corpus):
    (nested_corpus / "text" / "elderly" / "notes.txt").write_text("ignore me", encoding="utf-8")
    (nested_corpus / "images" / "empty-subdir").mkdir(parents=True, exist_ok=True)

    docs = discover_documents(nested_corpus)

    assert all(Path(doc["source_file"]).is_file() for doc in docs)
    assert "notes" not in {doc["doc_id"] for doc in docs}


def test_discover_documents_derives_category_from_parent_folder(nested_corpus):
    docs = {doc["doc_id"]: doc for doc in discover_documents(nested_corpus)}

    assert docs["silver-support"]["category"] == "Seniors"
    assert docs["comcare-steps"]["category"] == "Lower-income/employment"


def test_discover_documents_threads_source_url_from_sources_map(nested_corpus):
    docs = {
        doc["doc_id"]: doc
        for doc in discover_documents(
            nested_corpus,
            source_urls={"silver-support": "https://example.gov.sg/silver-support.pdf"},
        )
    }

    assert docs["silver-support"]["source_url"] == "https://example.gov.sg/silver-support.pdf"
    assert docs["comcare-steps"]["source_url"] == ""


def test_discover_documents_captures_per_page_text_for_pdfs(nested_corpus):
    docs = {doc["doc_id"]: doc for doc in discover_documents(nested_corpus)}

    page_texts = docs["silver-support"]["page_texts"]
    assert len(page_texts) == 2
    assert "quarterly" in page_texts[0].lower()
    assert "sixty five" in page_texts[1].lower()


class FakeVideoClient:
    """Stands in for the Gemini SDK (the only genuinely external collaborator)."""

    def __init__(self, transcript: str):
        self.transcript = transcript
        self.calls = []

    def transcribe(self, video_path: Path, prompt: str) -> str:
        self.calls.append((video_path, prompt))
        return self.transcript


def test_discover_documents_transcribes_videos_when_client_provided(nested_corpus):
    video_path = nested_corpus / "video" / "elderly" / "cpf-life-guide.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"fake video bytes")
    client = FakeVideoClient("CPF LIFE pays monthly payouts for life from age sixty five.")

    docs = {doc["doc_id"]: doc for doc in discover_documents(nested_corpus, video_client=client)}

    assert client.calls[0][0] == video_path
    video_doc = docs["cpf-life-guide"]
    assert video_doc["modality"] == "video"
    assert video_doc["category"] == "Seniors"
    assert "CPF LIFE" in video_doc["text"]


def test_discover_documents_skips_videos_without_a_transcription_client(nested_corpus):
    video_path = nested_corpus / "video" / "cpf-life-guide.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"fake video bytes")

    docs = discover_documents(nested_corpus)

    assert "video" not in {doc["modality"] for doc in docs}


def test_video_transcripts_are_chunked_and_indexed_like_text(nested_corpus):
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    video_path = nested_corpus / "video" / "elderly" / "cpf-life-guide.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"fake video bytes")
    client = FakeVideoClient("CPF LIFE pays monthly payouts for life. " * 40)

    documents = discover_documents(nested_corpus, video_client=client)
    chunk_records, _metadatas, _vectors, _stats = build_index_from_documents(documents, embedder)

    video_records = [r for r in chunk_records if r["modality"] == "video"]
    assert video_records
    assert video_records[0]["section_or_page"] == "Video transcript"
    assert video_records[0]["doc_id"] == "cpf-life-guide"


def test_scheme_name_collapses_separator_runs_into_a_single_space(tmp_path):
    """A filename like 'ElderFund - AIC.pdf' must not become 'Elderfund   Aic'
    (multiple spaces): the LLM naturally collapses whitespace when it echoes a
    scheme name into a citation, so a stored name with doubled spaces can never
    match the citation and always trips a false 'unverified citation' warning."""
    assert _scheme_name(tmp_path / "ElderFund - AIC.pdf") == "Elderfund Aic"
    assert _scheme_name(tmp_path / "comcare__long_term-assistance.pdf") == (
        "Comcare Long Term Assistance"
    )


def test_display_name_preserves_original_casing_and_normalizes_the_separator(tmp_path):
    assert _display_name(
        tmp_path / "ComCare Short-to-Medium-Term Assistance (SMTA) - SupportGoWhere.pdf"
    ) == "ComCare Short-to-Medium-Term Assistance (SMTA) — SupportGoWhere"
    assert _display_name(tmp_path / "ElderFund _ AIC.pdf") == "ElderFund — AIC"
    assert _display_name(
        tmp_path / "GST Voucher (GSTV) – Cash - SupportGoWhere.pdf"
    ) == "GST Voucher (GSTV) — Cash — SupportGoWhere"


def test_discover_documents_carries_display_name_into_chunk_records(nested_corpus):
    """_display_name preserves the filename's own casing rather than
    title-casing it -- "silver-support.pdf" has no separator surrounded by
    spaces, so it passes through unchanged. Real corpus filenames (e.g.
    "ElderFund _ AIC.pdf") are naturally cased, unlike this slug-style
    fixture name."""
    docs = {doc["doc_id"]: doc for doc in discover_documents(nested_corpus)}

    assert docs["silver-support"]["display_name"] == "silver-support"


def test_category_for_path_falls_back_to_uncategorized(tmp_path):
    root = tmp_path / "text"
    path = root / "mystery-folder" / "doc.pdf"
    assert category_for_path(path, root) == "Uncategorized"
    assert category_for_path(root / "doc.pdf", root) == "Uncategorized"


def test_category_for_path_falls_back_to_filename_keywords(tmp_path):
    """Files dropped straight into data/raw/<modality>/ with no category
    subfolder would otherwise all land in Uncategorized, silently switching off
    profile re-ranking for them."""
    root = tmp_path / "video"

    assert category_for_path(root / "ComCare Financial Assistance.mp4", root) == (
        "Lower-income/employment"
    )
    assert category_for_path(root / "Silver Support Explainer.mp4", root) == "Seniors"
    assert category_for_path(root / "A guide for seniors (2025).mp4", root) == "Seniors"
    assert category_for_path(root / "Preschool subsidy walkthrough.mp4", root) == "Family"


def test_category_subfolder_beats_a_conflicting_filename_keyword(tmp_path):
    """An explicit curator-chosen folder must win over the loose keyword guess."""
    root = tmp_path / "video"
    path = root / "elderly" / "ComCare walkthrough.mp4"

    assert category_for_path(path, root) == "Seniors"


def test_source_urls_from_sources_yaml_maps_doc_id_to_url(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        "- doc_id: silver-support\n"
        "  url: https://example.gov.sg/silver-support.pdf\n"
        "  modality: text\n",
        encoding="utf-8",
    )

    assert source_urls_from_sources_yaml(yaml_path) == {
        "silver-support": "https://example.gov.sg/silver-support.pdf"
    }


def test_source_urls_from_sources_yaml_returns_empty_when_file_missing(tmp_path):
    assert source_urls_from_sources_yaml(tmp_path / "nope.yaml") == {}


def test_build_index_from_documents_rejects_empty_corpus():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")

    with pytest.raises(ValueError, match="No documents found"):
        build_index_from_documents([], embedder)


def test_discovered_corpus_keeps_real_category_and_page_level_citations(nested_corpus):
    """Integration: real discovery -> real chunking -> real embedding/index."""
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    documents = discover_documents(nested_corpus)

    chunk_records, chroma_metadatas, vectors, _stats = build_index_from_documents(documents, embedder)

    assert vectors.shape[0] == len(chunk_records)
    assert len(chroma_metadatas) == len(chunk_records)
    categories = {record["category"] for record in chunk_records}
    assert categories == {"Seniors", "Lower-income/employment"}
    assert "Uncategorized" not in categories

    text_records = [r for r in chunk_records if r["modality"] == "text"]
    assert text_records
    assert all(r["section_or_page"] != "Full document" for r in text_records)
    assert any(r["section_or_page"].startswith(("p.", "pp.")) for r in text_records)


def test_discover_documents_reuses_cached_transcripts_across_runs(nested_corpus, tmp_path):
    """A second build must not re-upload and re-transcribe an unchanged video."""
    video_path = nested_corpus / "video" / "elderly" / "cpf-life-guide.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"fake video bytes")
    cache_dir = tmp_path / "processed"
    client = FakeVideoClient("CPF LIFE pays monthly payouts for life from age sixty five.")

    first = discover_documents(
        nested_corpus, video_client=client, transcript_cache_dir=cache_dir
    )
    second = discover_documents(
        nested_corpus, video_client=client, transcript_cache_dir=cache_dir
    )

    assert len(client.calls) == 1, "second run should have hit the transcript cache"
    texts = [
        {doc["doc_id"]: doc for doc in run}["cpf-life-guide"]["text"] for run in (first, second)
    ]
    assert texts[0] == texts[1]
    assert (cache_dir / "cpf-life-guide.txt").exists()


def test_discover_documents_indexes_videos_from_cache_with_no_client(nested_corpus, tmp_path):
    """Once transcribed, re-indexing works offline without an API key."""
    video_path = nested_corpus / "video" / "elderly" / "cpf-life-guide.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"fake video bytes")
    cache_dir = tmp_path / "processed"
    cache_dir.mkdir()
    (cache_dir / "cpf-life-guide.txt").write_text(
        "CPF LIFE pays monthly payouts for life from age sixty five.", encoding="utf-8"
    )

    docs = {
        doc["doc_id"]: doc
        for doc in discover_documents(
            nested_corpus, video_client=None, transcript_cache_dir=cache_dir
        )
    }

    assert "CPF LIFE" in docs["cpf-life-guide"]["text"]
    assert docs["cpf-life-guide"]["category"] == "Seniors"
