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


def test_build_chunk_records_display_name_falls_back_to_scheme_name():
    chunks = [{"chunk_index": 0, "word_start": 0, "word_end": 4, "text": "Some text."}]

    records = build_chunk_records(
        chunks,
        doc_id="baby-bonus-scheme",
        scheme_name="Baby Bonus Scheme",
        category="Family",
        modality="text",
        source_file="data/raw/text/baby_bonus.pdf",
        section_or_page="Eligibility, p.2",
    )

    assert records[0]["display_name"] == "Baby Bonus Scheme"


def test_build_chunk_records_keeps_an_explicit_display_name():
    chunks = [{"chunk_index": 0, "word_start": 0, "word_end": 4, "text": "Some text."}]

    records = build_chunk_records(
        chunks,
        doc_id="comcare-smta",
        scheme_name="Comcare Short To Medium Term Assistance (Smta) Supportgowhere",
        category="Lower-income/employment",
        modality="text",
        source_file="data/raw/text/comcare/comcare-smta.pdf",
        section_or_page="p.1",
        display_name="ComCare Short-to-Medium-Term Assistance (SMTA) — SupportGoWhere",
    )

    assert records[0]["display_name"] == (
        "ComCare Short-to-Medium-Term Assistance (SMTA) — SupportGoWhere"
    )


def test_build_chunk_records_attaches_citation_fields_when_doc_metadata_given():
    chunks = [{"chunk_index": 0, "word_start": 0, "word_end": 4, "text": "Some text."}]

    records = build_chunk_records(
        chunks,
        doc_id="cpf_wis_scheme_page",
        scheme_name="Workfare Income Supplement",
        category="Lower-income/employment",
        modality="text",
        source_file="data/raw/text/wis/cpf_wis_scheme_page.md",
        section_or_page="p.1",
        doc_metadata={
            "agency": "CPF",
            "tier": "A",
            "authority_rank": 1,
            "effective_date": "2025-01-01",
            "citation": "CPF — Workfare Income Supplement (eff. 2025-01-01), retrieved 2026-07-29",
            "doc_type": "scheme_page",
            "is_current": True,
            "canonical_url": "https://www.cpf.gov.sg/wis",
        },
    )

    record = records[0]
    assert record["agency"] == "CPF"
    assert record["tier"] == "A"
    assert record["authority_rank"] == 1
    assert record["effective_date"] == "2025-01-01"
    assert record["citation"] == "CPF — Workfare Income Supplement (eff. 2025-01-01), retrieved 2026-07-29"
    assert record["doc_type"] == "scheme_page"
    assert record["is_current"] is True
    assert record["canonical_url"] == "https://www.cpf.gov.sg/wis"


def test_build_chunk_records_omits_citation_fields_when_no_doc_metadata():
    chunks = [{"chunk_index": 0, "word_start": 0, "word_end": 4, "text": "Some text."}]

    records = build_chunk_records(
        chunks,
        doc_id="unmatched-doc",
        scheme_name="Unmatched Scheme",
        category="Uncategorized",
        modality="text",
        source_file="data/raw/text/unmatched.pdf",
        section_or_page="p.1",
    )

    record = records[0]
    for field in ("agency", "tier", "authority_rank", "effective_date", "citation", "doc_type"):
        assert field not in record


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
