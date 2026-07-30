from retrieval.profile_filter import (
    dedupe_candidates_by_scheme,
    infer_preferred_categories,
    rerank_by_category,
)


def test_infer_preferred_categories_maps_senior_age():
    categories = infer_preferred_categories({"age": 68, "life_stage_tags": []})
    assert "Seniors" in categories


def test_infer_preferred_categories_maps_young_children_tag():
    categories = infer_preferred_categories({"age": 32, "life_stage_tags": ["Has young child(ren)"]})
    assert "Family" in categories


def test_infer_preferred_categories_maps_caregiver_tag():
    categories = infer_preferred_categories({"age": 40, "life_stage_tags": ["Caregiver"]})
    assert "Seniors/caregiving" in categories
    assert "Healthcare" in categories


def test_infer_preferred_categories_maps_lower_income_employed():
    # Test with $<1.5k income
    categories = infer_preferred_categories(
        {"age": 35, "employment": "Employed", "monthly_income_band": "<$1.5k"}
    )
    assert "Lower-income/employment" in categories

    # Test with $1.5-3k income
    categories = infer_preferred_categories(
        {"age": 35, "employment": "Employed", "monthly_income_band": "$1.5-3k"}
    )
    assert "Lower-income/employment" in categories

    # Negative case: employed but income band NOT in lower range should NOT trigger
    categories = infer_preferred_categories(
        {"age": 35, "employment": "Employed", "monthly_income_band": "$5-7k"}
    )
    assert "Lower-income/employment" not in categories


def test_infer_preferred_categories_maps_unemployed():
    categories = infer_preferred_categories(
        {"age": 40, "employment": "Unemployed", "monthly_income_band": "Prefer not to say", "life_stage_tags": []}
    )
    assert "Lower-income/employment" in categories

    # Unemployed must still map even when caregiver/child tags are also set —
    # otherwise employment docs lose the preferred-category boost.
    categories = infer_preferred_categories(
        {
            "age": 40,
            "employment": "Unemployed",
            "life_stage_tags": ["Has young child(ren)", "Caregiver"],
        }
    )
    assert "Lower-income/employment" in categories
    assert "Family" in categories
    assert "Seniors" in categories


def test_infer_preferred_categories_maps_pioneer_merdeka_generation_tag():
    categories = infer_preferred_categories({"age": 76, "life_stage_tags": ["Pioneer/Merdeka Generation"]})
    assert "Seniors" in categories
    assert "Healthcare" in categories


def test_infer_preferred_categories_maps_own_disability_tag():
    categories = infer_preferred_categories({"age": 40, "life_stage_tags": ["I have a disability"]})
    assert "Seniors/caregiving" in categories
    assert "Healthcare" in categories


def test_infer_preferred_categories_maps_hdb_housing():
    categories = infer_preferred_categories({"age": 50, "housing": "HDB", "life_stage_tags": []})
    assert "Housing" in categories
    assert "Household/cost-of-living" in categories


def test_infer_preferred_categories_defaults_to_empty_when_no_signals():
    categories = infer_preferred_categories({"age": 40, "life_stage_tags": []})
    assert categories == set()


def test_rerank_by_category_promotes_preferred_categories_without_dropping_others():
    candidates = [(0, 0.9), (1, 0.85), (2, 0.8), (3, 0.75)]
    chunk_records = [
        {"category": "Housing"},
        {"category": "Seniors"},
        {"category": "Family"},
        {"category": "Seniors"},
    ]

    reranked = rerank_by_category(candidates, chunk_records, {"Seniors"}, top_k=2)

    reranked_indices = [idx for idx, _ in reranked]
    assert reranked_indices == [1, 3]


def test_rerank_by_category_round_robins_across_preferred_categories():
    candidates = [(0, 0.95), (1, 0.94), (2, 0.93), (3, 0.92), (4, 0.91)]
    chunk_records = [
        {"category": "Lower-income/employment"},
        {"category": "Lower-income/employment"},
        {"category": "Lower-income/employment"},
        {"category": "Seniors"},
        {"category": "Family"},
    ]

    reranked = rerank_by_category(
        candidates,
        chunk_records,
        {"Lower-income/employment", "Seniors", "Family"},
        top_k=3,
    )

    assert [idx for idx, _ in reranked] == [0, 3, 4]


def test_dedupe_candidates_by_scheme_collapses_comcare_variants():
    candidates = [(0, 0.9), (1, 0.88), (2, 0.87), (3, 0.86)]
    chunk_records = [
        {"display_name": "ComCare Short-to-Medium-Term Assistance (SMTA) — SupportGoWhere", "scheme_name": "a"},
        {"display_name": "ComCare Interim Assistance — SupportGoWhere", "scheme_name": "b"},
        {"display_name": "Home Caregiving Grant (HCG) — AIC", "scheme_name": "c"},
        {"display_name": "Baby Bonus Scheme", "scheme_name": "d"},
    ]

    deduped = dedupe_candidates_by_scheme(candidates, chunk_records)

    assert [idx for idx, _ in deduped] == [0, 2, 3]


def test_rerank_by_category_skips_duplicate_scheme_stems_within_category():
    candidates = [(0, 0.95), (1, 0.94), (2, 0.93), (3, 0.92)]
    chunk_records = [
        {"category": "Lower-income/employment", "display_name": "ComCare SMTA", "scheme_name": "a"},
        {"category": "Lower-income/employment", "display_name": "ComCare Interim", "scheme_name": "b"},
        {"category": "Lower-income/employment", "display_name": "SkillsFuture Credit", "scheme_name": "c"},
        {"category": "Family", "display_name": "Baby Bonus Scheme", "scheme_name": "d"},
    ]

    reranked = rerank_by_category(
        candidates,
        chunk_records,
        {"Lower-income/employment", "Family"},
        top_k=3,
    )

    # ComCare once, then Family, then SkillsFuture — not a second ComCare.
    assert [idx for idx, _ in reranked] == [0, 3, 2]


def test_rerank_by_category_falls_back_when_not_enough_preferred_hits():
    candidates = [(0, 0.9), (1, 0.85)]
    chunk_records = [{"category": "Housing"}, {"category": "Family"}]

    reranked = rerank_by_category(candidates, chunk_records, {"Seniors"}, top_k=2)

    assert [idx for idx, _ in reranked] == [0, 1]
