---
title: Addendum — Personal Profile Mode (minimal)
version: 0.1
date: 2026-07-27
status: Proposed for team agreement
extends: 2026-07-27-rag-sgsubsidies-design.md (§9 Generation, §12 UI)
---

# Addendum: Personal Profile Mode

**Goal:** Let a typical Singaporean enter a short profile and get a grounded shortlist of schemes + amounts they *may* be eligible for — without rewriting the architecture (still: ingest → retrieve → Gemini → Gradio → eval).

**Non-goal:** A full deterministic eligibility engine / rules mapper for all 8–10 schemes.

**Trust posture:** Prefer abstention and “insufficient evidence” over confident wrong eligibility. The LLM may only apply criteria that appear in retrieved passages; code only *narrows* retrieval and *constrains* the prompt.

---

## A. Profile fields (UI / `app.py` — extends §12)

Collect a **structured profile** (sidebar or collapsible form) plus an optional free-text question.

| Field | Type | Example values | Used for |
|---|---|---|---|
| `citizenship` | enum | Singapore Citizen / PR / Other | Filter + prompt |
| `age` | int | 35 | Prompt; optional age-band filter |
| `household_size` | int | 3 | Prompt |
| `monthly_income_band` | enum | `<$1.5k` / `$1.5–3k` / `$3–6k` / `>$6k` / Prefer not to say | Prompt (bands only — no exact income stored) |
| `housing` | enum | HDB / Private / Rental / Other / Prefer not to say | Prompt + soft category boost |
| `employment` | enum | Employed / Self-employed / Unemployed / Retired / Student | Prompt |
| `life_stage_tags` | multi-select | Has young child(ren) / Caregiver / Senior (65+) / PWD in household | Category filter |
| `free_text_question` | string (optional) | “What can I get and roughly how much?” | Default if blank: eligibility shortlist mode |

**Privacy note (aligns with §16 / NFR-5):** Profile fields are ephemeral request context only. Do not log raw PII into the KB. Eval logs may store anonymised band values for test cases, not real user identities.

**UI behaviour (minimal change to §12 layout):**
- Keep question box + answer + sources + `top_k` / threshold / baseline↔hybrid toggle.
- Add **Profile** panel above/beside the question box.
- Mode toggle: `General Q&A` (current design) | `Personal eligibility shortlist` (this addendum).
- In shortlist mode, if `free_text_question` is empty, use a fixed internal query template (below).

---

## B. Profile → retrieval filters (extends §8 query path; no new index)

Still the same FAISS (+ BM25 hybrid in v2). Profile only **biases which chunks are considered**, then existing top-k / threshold apply.

### B.1 Soft category filter (required for shortlist mode)

Map profile tags → `category` metadata values already planned in §6/§7:

| Profile signal | Boost / prefer categories |
|---|---|
| Senior (65+) or age ≥ 65 | Seniors, Healthcare |
| Has young child(ren) | Family |
| Caregiver | Seniors/caregiving, Healthcare |
| Employed + lower income band | Lower-income/employment |
| HDB | Housing, Household/cost-of-living |
| Default / Prefer not to say | No hard filter — retrieve broadly |

**Implementation (keep tiny):**
1. Embed the **retrieval query** (see B.2), run dense (and BM25 if hybrid) as today, fetch a **candidate pool** of size `max(TOP_K * 3, 15)`.
2. If any preferred categories are set: **re-rank** so preferred-category chunks rise, then take `TOP_K`. Do **not** hard-drop other categories unless the pool still has ≥ `TOP_K` preferred hits (avoid empty retrieval).
3. Existing `SIMILARITY_THRESHOLD` + abstention gate unchanged (§9.3).

No per-scheme eligibility code. No payout table hardcoding in v1 of this addendum.

### B.2 Retrieval query construction

**General Q&A mode:** embed the user’s question (unchanged).

**Personal eligibility shortlist mode:** build a deterministic query string from profile (not LLM rewrite required for v1):

```text
Singapore subsidy eligibility and payout amounts for:
citizenship={citizenship}; age={age}; household_size={household_size};
income_band={monthly_income_band}; housing={housing}; employment={employment};
tags={life_stage_tags}.
Include eligibility criteria and payment or grant amounts.
```

Optional later improvement (fits brief §5 “query rewriting”): LLM expands this into 2–3 sub-queries (seniors / family / COL) and merges results via RRF — **out of scope for this minimal addendum**.

---

## C. Prompt rules (extends §9.2 — shortlist mode only)

Keep the existing system prompt for General Q&A.

For **Personal eligibility shortlist**, replace/extend with this contract:

> You help a Singapore resident understand which schemes in the provided passages they **may** be eligible for.
>
> **User profile (bands only):**  
> {profile_json}
>
> **Rules:**
> 1. Use ONLY the numbered context passages. No outside knowledge.
> 2. Output three sections only:
>    - **Possibly eligible** — scheme name, why (criteria quoted/paraphrased from passages), amount/tier **only if stated in passages**, citations.
>    - **Likely not eligible / unclear** — scheme appears in context but a stated criterion conflicts with the profile, or a required criterion is missing from passages.
>    - **Not assessed** — do not invent schemes that are absent from the passages.
> 3. Never say “you are approved” or “you will receive.” Use “based on the documents, you may be eligible if …”
> 4. If income/age/citizenship thresholds are not in the passages, say so and put the scheme under **unclear**, even if thematically relevant.
> 5. Every factual claim must cite `[scheme_name, section_or_page]`.
> 6. If passages are insufficient for any shortlist, respond exactly with the project fallback abstention sentence.

**Generation inputs:** retrieved chunks + profile JSON + (optional) free-text question. Same Gemini client, same citation/UI wiring.

---

## D. Eval impact (light — for Member D)

Add **2–3** profile-style questions to the ≥10/12 test set (can replace or supplement “multi-document” / “ambiguous” slots):

| ID | Profile sketch | Expected behaviour |
|---|---|---|
| P1 | SC, age 68, income `<$1.5k`, retired, HDB | Multi-doc: seniors + COL schemes; amounts only if in evidence |
| P2 | SC, age 32, young children, income `$3–6k` | Family / Baby Bonus–type evidence; no senior schemes asserted as eligible without criteria |
| P3 | PR, age 40, Prefer not to say income | Heavy **unclear** / abstention where citizen-only or income thresholds missing |

Score with the same rubric (§11.3). Failure analysis should call out over-confident eligibility as a faithfulness failure.

Baseline vs improved (§10) can stay hybrid retrieval; profile mode uses the same switch.

---

## E. What we are explicitly *not* building (agree / disagree)

| Idea | Decision |
|---|---|
| Full if-then rules for all schemes | **No** (out of scope) |
| Hardcoded payout calculators | **No** for v1 |
| Storing user profiles | **No** |
| Soft category re-rank + strict shortlist prompt | **Yes** |
| Separate General vs Profile UI modes | **Yes** |

---

## F. Team agreement checklist

- [ ] Accept Personal eligibility shortlist as a **UI + prompt + soft filter** layer on Hongmeng’s architecture
- [ ] Profile field list above is final enough for Gradio v1 (bands only)
- [ ] No deterministic eligibility engine in the 1-week build
- [ ] Eval set includes ≥2 profile-style questions
- [ ] Demo script: fill profile → shortlist + sources → flip baseline/hybrid

**One-line summary for the report:** *We constrain personalised eligibility to structured profile inputs, category-biased retrieval, and a strict shortlist prompt that prefers abstention over unverified claims — without replacing RAG with a rules engine.*
