from generation.prompts import (
    build_general_qa_prompt,
    build_profile_prompt,
    build_query_rewrite_prompt,
    extract_cited_scheme_labels,
)

SAMPLE_CHUNKS = [
    {
        "scheme_name": "Baby Bonus Scheme",
        "section_or_page": "Eligibility, p.2",
        "text": "Parents receive a cash gift for each Singaporean child.",
    },
    {
        "scheme_name": "CDC Vouchers",
        "section_or_page": "FAQ",
        "text": "Vouchers can be spent at participating hawkers and merchants.",
    },
]


def test_build_general_qa_prompt_includes_question_and_labeled_passages():
    prompt = build_general_qa_prompt("What is Baby Bonus?", SAMPLE_CHUNKS)

    assert "What is Baby Bonus?" in prompt
    assert "[Baby Bonus Scheme, Eligibility, p.2]" in prompt
    assert "Parents receive a cash gift" in prompt
    assert "does not contain enough information" in prompt  # abstention instruction present


def test_build_profile_prompt_includes_profile_and_three_section_contract():
    profile = {"citizenship": "Singapore Citizen", "age": 68, "monthly_income_band": "<$1.5k"}
    prompt = build_profile_prompt(profile, SAMPLE_CHUNKS, free_text_question="")

    assert "Singapore Citizen" in prompt
    assert "Possibly eligible" in prompt
    assert "Likely not eligible" in prompt
    assert "Not assessed" in prompt


def test_build_query_rewrite_prompt_includes_the_question():
    prompt = build_query_rewrite_prompt("how much is that gst thing ah")

    assert "how much is that gst thing ah" in prompt
    assert "search query" in prompt.lower()


def test_extract_cited_scheme_labels_parses_bracketed_citations():
    answer = "You may get a cash gift [Baby Bonus Scheme, Eligibility, p.2] and vouchers [CDC Vouchers, FAQ]."

    labels = extract_cited_scheme_labels(answer)

    assert ("Baby Bonus Scheme", "Eligibility, p.2") in labels
    assert ("CDC Vouchers", "FAQ") in labels


def test_extract_cited_scheme_labels_splits_multi_source_citations():
    answer = "Combined support [Scheme A, pp.2-4; Scheme B, Video transcript] is available."

    labels = extract_cited_scheme_labels(answer)

    assert ("Scheme A", "pp.2-4") in labels
    assert ("Scheme B", "Video transcript") in labels
    assert len(labels) == 2
