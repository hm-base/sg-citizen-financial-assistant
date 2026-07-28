from evaluation.metrics import hit_rate, mean_of, reciprocal_rank, recall_at_k


def test_hit_rate_true_when_any_relevant_chunk_retrieved():
    assert hit_rate(["a", "b", "c"], {"c", "z"}) == 1.0


def test_hit_rate_false_when_no_relevant_chunk_retrieved():
    assert hit_rate(["a", "b"], {"z"}) == 0.0


def test_recall_at_k_computes_fraction_of_relevant_found():
    assert recall_at_k(["a", "b"], {"a", "b", "c"}) == pytest_approx(2 / 3)


def pytest_approx(value):
    return value  # simple helper since exact fractions are used in these fixtures


def test_reciprocal_rank_rewards_earlier_rank():
    assert reciprocal_rank(["z", "a"], {"a"}) == 0.5
    assert reciprocal_rank(["a", "z"], {"a"}) == 1.0
    assert reciprocal_rank(["z", "y"], {"a"}) == 0.0


def test_mean_of_averages_a_list():
    assert mean_of([1.0, 0.0, 1.0]) == pytest_approx(2 / 3)
