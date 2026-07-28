from retrieval.bm25_index import build_bm25_index, search_bm25_index


def test_search_bm25_index_ranks_exact_keyword_matches_first():
    chunk_texts = [
        "The GST Voucher gives eligible households up to $850.",
        "Baby Bonus gives parents cash gifts for each child.",
        "GST Voucher amounts depend on Annual Value of the home.",
    ]
    index = build_bm25_index(chunk_texts)

    results = search_bm25_index(index, "GST Voucher amount", top_k=2)

    result_indices = [idx for idx, _ in results]
    assert 0 in result_indices
    assert 2 in result_indices
    assert 1 not in result_indices
