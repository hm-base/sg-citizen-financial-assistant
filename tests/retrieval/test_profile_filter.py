from retrieval.profile_filter import infer_preferred_categories, rerank_by_category


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


def test_rerank_by_category_falls_back_when_not_enough_preferred_hits():
    candidates = [(0, 0.9), (1, 0.85)]
    chunk_records = [{"category": "Housing"}, {"category": "Family"}]

    reranked = rerank_by_category(candidates, chunk_records, {"Seniors"}, top_k=2)

    assert [idx for idx, _ in reranked] == [0, 1]
