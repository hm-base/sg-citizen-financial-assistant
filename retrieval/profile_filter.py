PROFILE_CATEGORY_MAP = {
    "senior_age": ["Seniors", "Healthcare"],
    "young_children": ["Family"],
    "caregiver": ["Seniors/caregiving", "Healthcare"],
    "lower_income_employed": ["Lower-income/employment"],
    "hdb_housing": ["Housing", "Household/cost-of-living"],
}


def infer_preferred_categories(profile: dict) -> set[str]:
    preferred: set[str] = set()

    if profile.get("age") is not None and profile["age"] >= 65:
        preferred.update(PROFILE_CATEGORY_MAP["senior_age"])

    tags = profile.get("life_stage_tags") or []
    if "Has young child(ren)" in tags:
        preferred.update(PROFILE_CATEGORY_MAP["young_children"])
    if "Caregiver" in tags:
        preferred.update(PROFILE_CATEGORY_MAP["caregiver"])

    if profile.get("employment") == "Employed" and profile.get("monthly_income_band") in (
        "<$1.5k",
        "$1.5-3k",
    ):
        preferred.update(PROFILE_CATEGORY_MAP["lower_income_employed"])

    if profile.get("housing") == "HDB":
        preferred.update(PROFILE_CATEGORY_MAP["hdb_housing"])

    return preferred


def rerank_by_category(
    candidates: list[tuple[int, float]],
    chunk_records: list[dict],
    preferred_categories: set[str],
    top_k: int,
) -> list[tuple[int, float]]:
    if not preferred_categories:
        return candidates[:top_k]

    preferred = [c for c in candidates if chunk_records[c[0]]["category"] in preferred_categories]
    if len(preferred) < top_k:
        return candidates[:top_k]

    others = [c for c in candidates if chunk_records[c[0]]["category"] not in preferred_categories]
    return (preferred + others)[:top_k]
