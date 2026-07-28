def reciprocal_rank_fusion(
    result_lists: list[list[tuple[int, float]]], k: int = 60
) -> list[tuple[int, float]]:
    """
    Merge multiple ranked result lists using reciprocal rank fusion.

    Args:
        result_lists: List of result lists, each containing (row_index, score) tuples.
        k: Parameter for RRF formula (default 60). Formula: 1 / (k + rank + 1)

    Returns:
        Fused ranking as list of (row_index, fused_score) sorted by fused_score descending.
    """
    fused_scores: dict[int, float] = {}
    for results in result_lists:
        for rank, (row_index, _score) in enumerate(results):
            fused_scores[row_index] = fused_scores.get(row_index, 0.0) + 1.0 / (k + rank + 1)

    ranked = sorted(fused_scores.items(), key=lambda pair: pair[1], reverse=True)
    return [(idx, score) for idx, score in ranked]
