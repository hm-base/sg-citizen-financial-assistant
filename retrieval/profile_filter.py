import re

PROFILE_CATEGORY_MAP = {
    "senior_age": ["Seniors", "Healthcare"],
    "young_children": ["Family"],
    "caregiver": ["Seniors", "Seniors/caregiving", "Healthcare", "Lower-income/employment"],
    "lower_income_employed": ["Lower-income/employment"],
    # Unemployed / jobseeking is its own signal: low-income Employed mapping
    # alone never fires for "Unemployed", so ComCare / SkillsFuture / CCP /
    # WSS chunks were never preferred and got crowded out by caregiver docs.
    "unemployed": ["Lower-income/employment"],
    "hdb_housing": ["Housing", "Household/cost-of-living"],
    # Pioneer/Merdeka Generation and own-disability are distinct from the
    # generic "Senior (65+)"/"PWD in household" tags: they gate specific
    # schemes (CHAS tier, Merdeka Generation Package, PioneerDAS, MediShield
    # Life Premium Subsidies for the former; CareShield Life, ElderFund,
    # ElderShield, HCG, IDAPE, MediSave Care for the latter) that a plain
    # age or household-PWD signal doesn't reliably surface.
    "pioneer_merdeka_generation": ["Seniors", "Healthcare"],
    "own_disability": ["Seniors", "Seniors/caregiving", "Healthcare"],
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
    if "Pioneer/Merdeka Generation" in tags:
        preferred.update(PROFILE_CATEGORY_MAP["pioneer_merdeka_generation"])
    if "I have a disability" in tags:
        preferred.update(PROFILE_CATEGORY_MAP["own_disability"])

    if profile.get("employment") == "Unemployed":
        preferred.update(PROFILE_CATEGORY_MAP["unemployed"])
    elif profile.get("employment") == "Employed" and profile.get("monthly_income_band") in (
        "<$1.5k",
        "$1.5-3k",
    ):
        preferred.update(PROFILE_CATEGORY_MAP["lower_income_employed"])

    if profile.get("housing") == "HDB":
        preferred.update(PROFILE_CATEGORY_MAP["hdb_housing"])

    return preferred


def _scheme_stem(record: dict) -> str:
    """Collapse near-duplicate scheme titles so one programme can't fill top_k.

    ComCare SMTA / Interim / LTA are separate pages but the same resident-facing
    theme; without stemming, unemployment retrieval floods top_k with ComCare
    variants and crowds out HCG / SkillsFuture / Baby Bonus.
    """
    name = (record.get("display_name") or record.get("scheme_name") or "").lower()
    if not name:
        # Unique fallback so stem-dedupe in rerank does not collapse unrelated
        # chunks that lack titles (common in unit-test fixtures).
        return f"__id__{record.get('chunk_id') or id(record)}"
    if "comcare" in name:
        return "comcare"
    if "baby bonus" in name or "baby_bonus" in name:
        return "baby bonus"
    if "home caregiving" in name or re.search(r"\bhcg\b", name):
        return "home caregiving grant"
    if "skillsfuture" in name:
        return "skillsfuture"
    if "career conversion" in name or re.search(r"\bccp\b", name):
        return "career conversion"
    if "workfare" in name or re.search(r"\bwis\b", name):
        return "workfare"
    stem = re.split(r"[—\-–(|]", name, maxsplit=1)[0].strip()
    return stem or f"__id__{record.get('chunk_id') or id(record)}"


def dedupe_candidates_by_scheme(
    candidates: list[tuple[int, float]],
    chunk_records: list[dict],
) -> list[tuple[int, float]]:
    """Keep the highest-scoring chunk per scheme stem, preserving score order."""
    seen: set[str] = set()
    deduped: list[tuple[int, float]] = []
    for idx, score in candidates:
        stem = _scheme_stem(chunk_records[idx])
        if stem in seen:
            continue
        seen.add(stem)
        deduped.append((idx, score))
    return deduped


def rerank_by_category(
    candidates: list[tuple[int, float]],
    chunk_records: list[dict],
    preferred_categories: set[str],
    top_k: int,
) -> list[tuple[int, float]]:
    if not preferred_categories:
        return candidates[:top_k]

    preferred = [c for c in candidates if chunk_records[c[0]]["category"] in preferred_categories]
    others = [c for c in candidates if chunk_records[c[0]]["category"] not in preferred_categories]
    if len(preferred) < top_k:
        return candidates[:top_k]

    # Round-robin across preferred categories so one facet (e.g. unemployment
    # ComCare docs) cannot occupy every top_k slot when caregiver / child /
    # housing signals also apply. Within a category, skip scheme stems already
    # taken so SkillsFuture is not crowded out by a second ComCare-adjacent hit
    # that somehow survived earlier dedupe under a different display name.
    by_category: dict[str, list[tuple[int, float]]] = {}
    for item in preferred:
        category = chunk_records[item[0]]["category"]
        by_category.setdefault(category, []).append(item)

    diversified: list[tuple[int, float]] = []
    used_stems: set[str] = set()
    while len(diversified) < top_k and by_category:
        exhausted: list[str] = []
        progress = False
        for category in list(by_category.keys()):
            bucket = by_category[category]
            while bucket:
                candidate = bucket.pop(0)
                stem = _scheme_stem(chunk_records[candidate[0]])
                if stem in used_stems:
                    continue
                diversified.append(candidate)
                used_stems.add(stem)
                progress = True
                break
            if not bucket:
                exhausted.append(category)
            if len(diversified) >= top_k:
                break
        for category in exhausted:
            del by_category[category]
        if not progress:
            break

    if len(diversified) < top_k:
        for item in others:
            stem = _scheme_stem(chunk_records[item[0]])
            if stem in used_stems:
                continue
            diversified.append(item)
            used_stems.add(stem)
            if len(diversified) >= top_k:
                break
    return diversified[:top_k]
