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


def test_reciprocal_rank_fusion_unequal_length_lists():
    """
    Test RRF with two non-empty lists of different lengths.

    This catches buggy implementations that might use zip() instead of
    iterating each list independently, which would silently drop rows
    from the longer list or cause rank misalignment.
    """
    # Dense list has 4 items, BM25 list has only 2 items (simulating BM25
    # filtering out zero-score matches per Task 10).
    dense_results = [(0, 0.9), (1, 0.8), (2, 0.7), (3, 0.6)]
    bm25_results = [(0, 5.0), (2, 4.0)]

    fused = reciprocal_rank_fusion([dense_results, bm25_results])

    fused_indices = [idx for idx, _ in fused]

    # All rows from both lists must be present in the output.
    assert set(fused_indices) == {0, 1, 2, 3}, (
        f"Missing or extra rows. Expected {{0, 1, 2, 3}}, got {set(fused_indices)}"
    )

    # Create a dict for easier lookup of fused scores.
    fused_dict = {idx: score for idx, score in fused}

    # Rows appearing in both lists must have higher fused scores than
    # rows appearing in only one list.
    # Row 0 and 2 appear in both lists.
    # Row 1 and 3 appear only in dense_results.
    assert fused_dict[0] > fused_dict[1], (
        f"Row 0 (in both lists) score {fused_dict[0]:.4f} should be > "
        f"row 1 (dense only) score {fused_dict[1]:.4f}"
    )
    assert fused_dict[2] > fused_dict[3], (
        f"Row 2 (in both lists) score {fused_dict[2]:.4f} should be > "
        f"row 3 (dense only) score {fused_dict[3]:.4f}"
    )
