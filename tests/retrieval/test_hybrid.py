from retrieval.hybrid import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_boosts_items_ranked_high_in_both_lists():
    dense_results = [(2, 0.9), (0, 0.8), (1, 0.5)]
    bm25_results = [(0, 5.0), (2, 4.0), (3, 1.0)]

    fused = reciprocal_rank_fusion([dense_results, bm25_results])

    fused_indices = [idx for idx, _ in fused]
    # 0 and 2 each appear in both lists near the top, so they should fuse to the top two.
    assert set(fused_indices[:2]) == {0, 2}
    # 1 only appears in dense results, 3 only in bm25 — both should still be present, ranked lower.
    assert set(fused_indices) == {0, 1, 2, 3}


def test_reciprocal_rank_fusion_handles_empty_list():
    fused = reciprocal_rank_fusion([[], [(0, 1.0)]])
    assert fused == [(0, 1.0 / 61)]
