from ingestion.metadata import build_chunk_records


def test_build_chunk_records_attaches_all_fields():
    chunks = [
        {"chunk_index": 0, "word_start": 0, "word_end": 5, "text": "Baby Bonus is a scheme."},
        {"chunk_index": 1, "word_start": 3, "word_end": 8, "text": "It gives cash payouts."},
    ]

    records = build_chunk_records(
        chunks,
        doc_id="baby-bonus-scheme",
        scheme_name="Baby Bonus Scheme",
        category="Family",
        modality="text",
        source_file="data/raw/text/baby_bonus.pdf",
        section_or_page="Eligibility, p.2",
        source_url="https://example.gov.sg/baby-bonus",
    )

    assert len(records) == 2
    assert records[0]["chunk_id"] == "baby-bonus-scheme_text_000"
    assert records[1]["chunk_id"] == "baby-bonus-scheme_text_001"
    for record in records:
        assert record["doc_id"] == "baby-bonus-scheme"
        assert record["scheme_name"] == "Baby Bonus Scheme"
        assert record["category"] == "Family"
        assert record["modality"] == "text"
        assert record["source_file"] == "data/raw/text/baby_bonus.pdf"
        assert record["section_or_page"] == "Eligibility, p.2"
        assert record["source_url"] == "https://example.gov.sg/baby-bonus"
        assert record["thumbnail_path"] == ""
        assert record["text"]


def test_build_chunk_records_image_modality_keeps_thumbnail():
    chunks = [{"chunk_index": 0, "word_start": 0, "word_end": 4, "text": "Payout tiers table."}]

    records = build_chunk_records(
        chunks,
        doc_id="cdc-vouchers",
        scheme_name="CDC Vouchers",
        category="Household",
        modality="image",
        source_file="data/raw/images/cdc.png",
        section_or_page="Infographic",
        thumbnail_path="data/raw/images/cdc.png",
    )

    assert records[0]["chunk_id"] == "cdc-vouchers_image_000"
    assert records[0]["thumbnail_path"] == "data/raw/images/cdc.png"
