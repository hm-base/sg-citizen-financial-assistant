from retrieval.profile_filter import infer_preferred_categories, rerank_by_category


def test_infer_preferred_categories_maps_senior_age():
    categories = infer_preferred_categories({"age": 68, "life_stage_tags": []})
    assert "Seniors" in categories


def test_infer_preferred_categories_maps_young_children_tag():
    categories = infer_preferred_categories({"age": 32, "life_stage_tags": ["Has young child(ren)"]})
    assert "Family" in categories


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
