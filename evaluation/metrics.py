def hit_rate(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    return 1.0 if any(rid in relevant_ids for rid in retrieved_ids) else 0.0


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    if not relevant_ids:
        raise ValueError("relevant_ids must not be empty")
    found = sum(1 for rid in relevant_ids if rid in retrieved_ids)
    return found / len(relevant_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_of(values: list[float]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)
