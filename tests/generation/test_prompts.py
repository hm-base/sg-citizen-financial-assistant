from generation.prompts import (
    build_general_qa_from_shortlist_prompt,
    build_general_qa_prompt,
    build_profile_extract_prompt,
    build_profile_shortlist_prompt,
    build_query_rewrite_prompt,
    extract_cited_scheme_labels,
    format_chat_history,
)

SAMPLE_CHUNKS = [
    {
        "chunk_id": "baby-bonus_text_000",
        "scheme_name": "Baby Bonus Scheme",
        "section_or_page": "Eligibility, p.2",
        "text": "Parents receive a cash gift for each Singaporean child.",
    },
    {
        "chunk_id": "cdc-vouchers_text_000",
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
    assert "may qualify for" in prompt  # eligibility-list guidance present


def test_build_profile_shortlist_prompt_includes_profile_and_allowed_chunk_ids():
    profile = {"citizenship": "Singapore Citizen", "age": 68, "monthly_income_band": "<$1.5k"}
    prompt = build_profile_shortlist_prompt(profile, SAMPLE_CHUNKS, free_text_question="")

    assert "Singapore Citizen" in prompt
    assert "baby-bonus_text_000" in prompt
    assert "cdc-vouchers_text_000" in prompt
    assert "JSON array" in prompt
    assert "conditions" in prompt
    assert "citation_chunk_ids" in prompt


def test_build_profile_extract_prompt_asks_for_closed_form_fields():
    prompt = build_profile_extract_prompt("I am 40 yo and unemployed with a two yo son")

    assert "I am 40 yo and unemployed with a two yo son" in prompt
    assert "life_stage_tags" in prompt
    assert "Has young child(ren)" in prompt
    assert "Caregiver" in prompt
    assert "JSON object:" in prompt


def test_build_general_qa_from_shortlist_prompt_includes_shortlist_and_passages():
    profile = {"age": 40, "employment": "Unemployed", "life_stage_tags": ["Has young child(ren)"]}
    shortlist = [{
        "group": "eligible",
        "scheme": "Baby Bonus Scheme",
        "reason": "Young Singaporean child mentioned.",
        "amount": None,
        "conditions": [{"label": "Singapore Citizen child", "state": "not_checked"}],
        "changer": "Confirm child's citizenship.",
    }]
    prompt = build_general_qa_from_shortlist_prompt(
        "What support might apply to me?",
        profile,
        shortlist,
        SAMPLE_CHUNKS,
    )

    assert "What support might apply to me?" in prompt
    assert "Baby Bonus Scheme" in prompt
    assert "eligible" in prompt
    assert "[Baby Bonus Scheme, Eligibility, p.2]" in prompt
    assert "does not contain enough information" in prompt


def test_build_query_rewrite_prompt_includes_the_question():
    prompt = build_query_rewrite_prompt("how much is that gst thing ah")

    assert "how much is that gst thing ah" in prompt
    assert "subQueries" in prompt
    assert "JSON object" in prompt
    assert "Resident profile" not in prompt  # no profile given


def test_build_query_rewrite_prompt_includes_profile_when_given():
    prompt = build_query_rewrite_prompt("help with my mother's medical bills", {"age": 70})

    assert "Resident profile" in prompt
    assert "70" in prompt


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


def test_format_chat_history_compacts_prior_turns():
    block = format_chat_history([
        {"role": "user", "content": "How much is GST Voucher?"},
        {"role": "assistant", "content": "Up to $850 for eligible households."},
        {"role": "system", "content": "ignore me"},
        {"role": "user", "content": ""},
    ])

    assert "Prior conversation" in block
    assert "Resident: How much is GST Voucher?" in block
    assert "Assistant: Up to $850" in block
    assert "ignore me" not in block


def test_build_general_qa_prompt_includes_history_when_provided():
    prompt = build_general_qa_prompt(
        "How much is that?",
        SAMPLE_CHUNKS,
        history=[
            {"role": "user", "content": "Tell me about Baby Bonus"},
            {"role": "assistant", "content": "Baby Bonus includes a cash gift."},
        ],
    )

    assert "Prior conversation" in prompt
    assert "Tell me about Baby Bonus" in prompt
    assert "How much is that?" in prompt


def test_build_query_rewrite_prompt_includes_history_for_follow_ups():
    prompt = build_query_rewrite_prompt(
        "how much is that?",
        history=[{"role": "user", "content": "SkillsFuture Credit"}, {"role": "assistant", "content": "Credit amounts vary."}],
    )

    assert "Prior conversation" in prompt
    assert "SkillsFuture Credit" in prompt
    assert "standalone" in prompt.lower() or "follow-up" in prompt.lower() or "pronoun" in prompt.lower()
