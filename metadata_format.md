Metadata should be JSON-shaped, but with an important ChromaDB constraint that changes the design.

## The one constraint that drives everything

**ChromaDB metadata values must be scalars — `str`, `int`, `float`, `bool` only.** No nested objects, no arrays, and `None` is rejected outright. So the rich sidecar (`data/meta/{doc_id}.json`, which may nest `local_paths` / companions) **cannot go into Chroma as-is**.

Use two layers:

| Layer | Format | Purpose |
|---|---|---|
| **`data/meta/{doc_id}.json`** | Full JSON, nesting and arrays fine | Provenance, audit trail, rebuild source. Never ingested into Chroma. |
| **Chunk metadata** | Flat dict of scalars | What actually goes into `collection.add(metadatas=[...])` — copy from each sidecar's `chroma_flat_metadata_template` and set `chunk_index` / `chunk_total` / `section` per chunk. |

---

## Jony data layout (GH repo)

```
data/
├── meta/{doc_id}.json          # full sidecars (this inventory)
├── sources_jony.yaml           # core text + non-core video catalog
├── sources_core.yaml           # text/PDF only (index these first)
├── sources_video_noncore.yaml  # 9 YouTube MP4s
└── raw/
    ├── text/
    │   ├── wis/   sctp/   ccp/   aiap/   snaic/   # curated (core)
    │   └── _pool/                                 # extra Y downloads (do not index yet)
    └── video/
        ├── wis/   sctp/   ccp/   aiap/   snaic/   # non-core MP4s
```

Owner: **Jony**. Parent repo: `hm-base/sg-citizen-financial-assistant`. Fork: `jonyling/SNAIC_Week7_sg-citizen-financial-assistant`.

---

## Recommended flat schema (for ChromaDB)

```python
{
    # ── identity ──────────────────────────────────────────────
    "doc_id":            "01_cpf_wis_scheme_page",
    "chunk_index":       2,
    "chunk_total":       7,

    # ── source attribution ────────────────────────────────────
    "source_url":        "https://www.cpf.gov.sg/...",
    "canonical_url":     "https://www.cpf.gov.sg/...",
    "title":             "Workfare Income Supplement",
    "agency":            "CPF",
    "citation":          "CPF — Workfare Income Supplement (eff. 2025-01-01), retrieved 2026-07-29",
    "section":           "Eligibility",
    "retrieved_at":      "2026-07-29T14:05:00+08:00",
    "content_sha256":    "a3f1…",

    # ── classification ────────────────────────────────────────
    "topic":             "Workfare_WIS",
    "topic_no":          1,
    "entity":            "WIS",
    "scheme":            "Workfare Income Supplement",
    "tier":              "A",
    "authority_rank":    1,
    "doc_type":          "scheme_page",

    # ── temporal ──────────────────────────────────────────────
    "effective_date":     "2025-01-01",
    "effective_date_int": 20250101,
    "last_updated":       "",
    "last_updated_int":   0,
    "is_current":         True,
    "superseded":         False,
    "supersedes_doc_id":  "",

    # ── Budget pinning ────────────────────────────────────────
    "budget_year":       0,
    "annex_ref":         "",

    # ── quality / safety ──────────────────────────────────────
    "deny_listed":       False,
    "deny_reason":       "",
    "has_table":         True,
    "table_verified":    False,
    "extraction_source": "dom",

    "licence_note": "© Source owner; reproduced for academic Capstone use only",

    # ── Jony extras (still scalars) ───────────────────────────
    "modality":          "text",
    "core":              True,
    "source_file":       "data/raw/text/wis/01_cpf_wis_scheme_page.html",
    "owner":             "Jony",
}
```

---

## Five gotchas worth telling the team

**1. Store dates twice.** Keep the ISO string for display *and* an `int` (`20240820`) for filtering — Chroma's `$gte`/`$lte` work reliably on numbers.

**2. Never use `None`.** Chroma rejects it. Use `""` for empty strings and `0` for empty ints.

**3. Lists don't work.** Put aliases in chunk **text**, not metadata.

**4. IDs must be globally unique.** Jony namespace:

```
{topic_no:02d}_{agency_slug}_{doc_slug}
→ "01_cpf_wis_scheme_page"
chunk ids: "{doc_id}_{modality}_{chunk_index:03d}"
```

**5. Set the distance metric explicitly** to cosine when using sentence-transformers.

---

## Enforce closed vocabularies (Jony + shared)

| Field | Allowed values |
|---|---|
| `topic` | `Workfare_WIS` · `SkillsFuture_SCTP` · `Career_Conversion_CCP` · `AIAP` · `SNAIC` · *(+ teammates' topics)* |
| `agency` | `CPF` · `MOM` · `SSG` · `WSG` · `SWDA` · `AISG` · `SIT` · `HDB` · `MOH` · `MOF` · `IRAS` · `MND` |
| `tier` | `A` scheme · `B` faq · `C` policy/news · `D` pdf · `E` adjacent/video |
| `authority_rank` | `1`–`6` |
| `doc_type` | `scheme_page` · `faq` · `press_release` · `budget_annex` · `pdf` · `process_guide` · `video` |
| `extraction_source` | `next_data` · `dom` · `http` · `pdf` · `ocr` · `youtube_yt_dlp` · `gemini_transcript` |
| `modality` | `text` · `image` · `video` |

The `citation` field is pre-formatted at ingest; the answer template should print it verbatim.

---

## Inventory summary (Jony)


| Kind | Count |
|---|---:|
| Core text/PDF | 16 |
| Non-core video | 9 |
| **Total catalogued** | **25** |

`data/raw/text/_pool/` holds extra Accept-Y pages (~190 files) — **not** catalogued here; do not index until promoted.

---

## Filled metadata for every catalogued item

Each block is the **Chroma flat template** from `data/meta/{doc_id}.json` → `chroma_flat_metadata_template`.
At chunking time, overwrite `chunk_index`, `chunk_total`, and `section`.

### Topic: `Workfare_WIS` (topic_no=1)

#### `01_cpf_wis_eligibility_faq` — CORE · text · faq

- **Title:** What are the eligibility criteria of the Workfare Income Supplement scheme?
- **URL:** https://www.cpf.gov.sg/service/article/what-are-the-eligibility-criteria-of-the-workfare-income-supplement-scheme
- **Primary file:** `data/raw/text/wis/01_cpf_wis_eligibility_faq.html`
- **Sidecar:** `data/meta/01_cpf_wis_eligibility_faq.json`

```json
{
  "doc_id": "01_cpf_wis_eligibility_faq",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.cpf.gov.sg/service/article/what-are-the-eligibility-criteria-of-the-workfare-income-supplement-scheme",
  "canonical_url": "https://www.cpf.gov.sg/service/article/what-are-the-eligibility-criteria-of-the-workfare-income-supplement-scheme",
  "title": "What are the eligibility criteria of the Workfare Income Supplement scheme?",
  "agency": "CPF",
  "citation": "CPF — What are the eligibility criteria of the Workfare Income Supplement scheme? (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "2f28b25923e74943be44de363dc2fbd0e69c3a1add6a3bd2168a56aa4f52c731",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "WIS",
  "scheme": "Workfare Income Supplement",
  "tier": "B",
  "authority_rank": 1,
  "doc_type": "faq",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": true,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/wis/01_cpf_wis_eligibility_faq.html",
  "owner": "Jony"
}
```

#### `01_cpf_wis_scheme_page` — CORE · text · scheme_page

- **Title:** Workfare Income Supplement
- **URL:** https://www.cpf.gov.sg/member/growing-your-savings/government-support/workfare-income-supplement
- **Primary file:** `data/raw/text/wis/01_cpf_wis_scheme_page.html`
- **Sidecar:** `data/meta/01_cpf_wis_scheme_page.json`

```json
{
  "doc_id": "01_cpf_wis_scheme_page",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.cpf.gov.sg/member/growing-your-savings/government-support/workfare-income-supplement",
  "canonical_url": "https://www.cpf.gov.sg/member/growing-your-savings/government-support/workfare-income-supplement",
  "title": "Workfare Income Supplement",
  "agency": "CPF",
  "citation": "CPF — Workfare Income Supplement (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "640ee5a27e819afda6507b0a014e5a80b6c9c7a4c4c2aedb6f194a0b9fdca1b3",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "WIS",
  "scheme": "Workfare Income Supplement",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": true,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/wis/01_cpf_wis_scheme_page.html",
  "owner": "Jony"
}
```

#### `01_govbenefits_wis` — CORE · text · scheme_page

- **Title:** Workfare Income Supplement | Govbenefits
- **URL:** https://www.govbenefits.gov.sg/government-benefits-schemes/workfare-income-supplement/
- **Primary file:** `data/raw/text/wis/01_govbenefits_wis.html`
- **Sidecar:** `data/meta/01_govbenefits_wis.json`

```json
{
  "doc_id": "01_govbenefits_wis",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.govbenefits.gov.sg/government-benefits-schemes/workfare-income-supplement/",
  "canonical_url": "https://www.govbenefits.gov.sg/government-benefits-schemes/workfare-income-supplement/",
  "title": "Workfare Income Supplement | Govbenefits",
  "agency": "CPF",
  "citation": "CPF — Workfare Income Supplement | Govbenefits (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "ad4d1579d078f0919cafaa6b5e52bae9e5706e3a0c337f94a41222208f6a1b2f",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "WIS",
  "scheme": "Workfare Income Supplement",
  "tier": "A",
  "authority_rank": 2,
  "doc_type": "scheme_page",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/wis/01_govbenefits_wis.html",
  "owner": "Jony"
}
```

#### `01_mom_workfare_umbrella` — CORE · text · scheme_page

- **Title:** Workfare
- **URL:** https://www.mom.gov.sg/employment-practices/schemes-for-employers-and-employees/workfare
- **Primary file:** `data/raw/text/wis/01_mom_workfare_umbrella.html`
- **Sidecar:** `data/meta/01_mom_workfare_umbrella.json`

```json
{
  "doc_id": "01_mom_workfare_umbrella",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.mom.gov.sg/employment-practices/schemes-for-employers-and-employees/workfare",
  "canonical_url": "https://www.mom.gov.sg/employment-practices/schemes-for-employers-and-employees/workfare",
  "title": "Workfare",
  "agency": "MOM",
  "citation": "MOM — Workfare (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "6ce450a674e3d8958d4b3a0f85216e3eb0c56513ecc6caf2c97105df906061b9",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "Workfare",
  "scheme": "Workfare (WIS + WSS)",
  "tier": "A",
  "authority_rank": 2,
  "doc_type": "scheme_page",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/wis/01_mom_workfare_umbrella.html",
  "owner": "Jony"
}
```

#### `01_swda_wss_scheme` — CORE · text · scheme_page

- **Title:** Workfare Skills Support Scheme
- **URL:** https://www.swda.gov.sg/home/individuals/funding-training-allowance/workfare-skills-support-scheme
- **Primary file:** `data/raw/text/wis/01_swda_wss_scheme.html`
- **Sidecar:** `data/meta/01_swda_wss_scheme.json`

```json
{
  "doc_id": "01_swda_wss_scheme",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.swda.gov.sg/home/individuals/funding-training-allowance/workfare-skills-support-scheme",
  "canonical_url": "https://www.swda.gov.sg/home/individuals/funding-training-allowance/workfare-skills-support-scheme",
  "title": "Workfare Skills Support Scheme",
  "agency": "SWDA",
  "citation": "SWDA — Workfare Skills Support Scheme (eff. 2026-03-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "48b424de0e46b1a90c21e2f7b80f900ca3c4ce31ddaa2e3727550778f953e19d",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "WSS",
  "scheme": "Workfare Skills Support Scheme",
  "tier": "A",
  "authority_rank": 2,
  "doc_type": "scheme_page",
  "effective_date": "2026-03-01",
  "effective_date_int": 20260301,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/wis/01_swda_wss_scheme.html",
  "owner": "Jony"
}
```

#### `01_cpf_wis_video_NgsDN7EaeK0` — NON-CORE · video · video

- **Title:** WIS YouTube explainer (NgsDN7EaeK0)
- **URL:** https://www.youtube.com/watch?v=NgsDN7EaeK0
- **Primary file:** `data/raw/video/wis/01_cpf_wis_video_NgsDN7EaeK0.mp4`
- **Sidecar:** `data/meta/01_cpf_wis_video_NgsDN7EaeK0.json`

```json
{
  "doc_id": "01_cpf_wis_video_NgsDN7EaeK0",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=NgsDN7EaeK0",
  "canonical_url": "https://www.youtube.com/watch?v=NgsDN7EaeK0",
  "title": "WIS YouTube explainer (NgsDN7EaeK0)",
  "agency": "CPF",
  "citation": "CPF — WIS YouTube explainer (NgsDN7EaeK0), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "45b3a6f552115c7a486fc39c6da1fef41f854d9e487c3ac7fe6f2f9910ef244a",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "WIS",
  "scheme": "Workfare Income Supplement",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/wis/01_cpf_wis_video_NgsDN7EaeK0.mp4",
  "owner": "Jony"
}
```

#### `01_cpf_wis_video_T80EdXXPPes` — NON-CORE · video · video

- **Title:** WIS YouTube explainer (T80EdXXPPes)
- **URL:** https://www.youtube.com/watch?v=T80EdXXPPes
- **Primary file:** `data/raw/video/wis/01_cpf_wis_video_T80EdXXPPes.mp4`
- **Sidecar:** `data/meta/01_cpf_wis_video_T80EdXXPPes.json`

```json
{
  "doc_id": "01_cpf_wis_video_T80EdXXPPes",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=T80EdXXPPes",
  "canonical_url": "https://www.youtube.com/watch?v=T80EdXXPPes",
  "title": "WIS YouTube explainer (T80EdXXPPes)",
  "agency": "CPF",
  "citation": "CPF — WIS YouTube explainer (T80EdXXPPes), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "bdcb6cd2aa8617f86fb51a95129459dd208a90252a7a91b9e64d69832ba391c7",
  "topic": "Workfare_WIS",
  "topic_no": 1,
  "entity": "WIS",
  "scheme": "Workfare Income Supplement",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/wis/01_cpf_wis_video_T80EdXXPPes.mp4",
  "owner": "Jony"
}
```

### Topic: `SkillsFuture_SCTP` (topic_no=2)

#### `02_ssg_sctp_scheme_page` — CORE · text · scheme_page

- **Title:** SkillsFuture Career Transition Programme
- **URL:** https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/skillsfuture-career-transition-programme.html
- **Primary file:** `data/raw/text/sctp/02_ssg_sctp_scheme_page.html`
- **Sidecar:** `data/meta/02_ssg_sctp_scheme_page.json`

```json
{
  "doc_id": "02_ssg_sctp_scheme_page",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/skillsfuture-career-transition-programme.html",
  "canonical_url": "https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/skillsfuture-career-transition-programme.html",
  "title": "SkillsFuture Career Transition Programme",
  "agency": "SSG",
  "citation": "SSG — SkillsFuture Career Transition Programme (eff. 2022-04-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "afc6467b2e191f19b8ebad6f197f8d92940a6f346a391827f455ac0963d15840",
  "topic": "SkillsFuture_SCTP",
  "topic_no": 2,
  "entity": "SCTP",
  "scheme": "SkillsFuture Career Transition Programme",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2022-04-01",
  "effective_date_int": 20220401,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/sctp/02_ssg_sctp_scheme_page.html",
  "owner": "Jony"
}
```

#### `02_ssg_skillsfuture_credit` — CORE · text · scheme_page

- **Title:** SkillsFuture Credit
- **URL:** https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/SkillsFuture_Credit.html
- **Primary file:** `data/raw/text/sctp/02_ssg_skillsfuture_credit.html`
- **Sidecar:** `data/meta/02_ssg_skillsfuture_credit.json`

```json
{
  "doc_id": "02_ssg_skillsfuture_credit",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/SkillsFuture_Credit.html",
  "canonical_url": "https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/SkillsFuture_Credit.html",
  "title": "SkillsFuture Credit",
  "agency": "SSG",
  "citation": "SSG — SkillsFuture Credit (eff. 2020-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:20:00+08:00",
  "content_sha256": "b95e0dad0eadec5298dd10cca040d37c328eadb422f46524b86fb7df842efb3c",
  "topic": "SkillsFuture_SCTP",
  "topic_no": 2,
  "entity": "SFC",
  "scheme": "SkillsFuture Credit",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2020-01-01",
  "effective_date_int": 20200101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": true,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/sctp/02_ssg_skillsfuture_credit.html",
  "owner": "Jony"
}
```

#### `02_ssg_sctp_video_CkIBjH8z3GU` — NON-CORE · video · video

- **Title:** SCTP YouTube explainer (CkIBjH8z3GU)
- **URL:** https://www.youtube.com/watch?v=CkIBjH8z3GU
- **Primary file:** `data/raw/video/sctp/02_ssg_sctp_video_CkIBjH8z3GU.mp4`
- **Sidecar:** `data/meta/02_ssg_sctp_video_CkIBjH8z3GU.json`

```json
{
  "doc_id": "02_ssg_sctp_video_CkIBjH8z3GU",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=CkIBjH8z3GU",
  "canonical_url": "https://www.youtube.com/watch?v=CkIBjH8z3GU",
  "title": "SCTP YouTube explainer (CkIBjH8z3GU)",
  "agency": "SSG",
  "citation": "SSG — SCTP YouTube explainer (CkIBjH8z3GU), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "a414f2dde24eba06f9cf27667e0a0d8c7b176981a787fe63ff95ac4203a401ad",
  "topic": "SkillsFuture_SCTP",
  "topic_no": 2,
  "entity": "SCTP",
  "scheme": "SkillsFuture Career Transition Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/sctp/02_ssg_sctp_video_CkIBjH8z3GU.mp4",
  "owner": "Jony"
}
```

#### `02_ssg_sctp_video_c4sf5C4hPb8` — NON-CORE · video · video

- **Title:** SCTP YouTube explainer (c4sf5C4hPb8)
- **URL:** https://www.youtube.com/watch?v=c4sf5C4hPb8
- **Primary file:** `data/raw/video/sctp/02_ssg_sctp_video_c4sf5C4hPb8.mp4`
- **Sidecar:** `data/meta/02_ssg_sctp_video_c4sf5C4hPb8.json`

```json
{
  "doc_id": "02_ssg_sctp_video_c4sf5C4hPb8",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=c4sf5C4hPb8",
  "canonical_url": "https://www.youtube.com/watch?v=c4sf5C4hPb8",
  "title": "SCTP YouTube explainer (c4sf5C4hPb8)",
  "agency": "SSG",
  "citation": "SSG — SCTP YouTube explainer (c4sf5C4hPb8), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "78e799676155b5bdaf5184b0415f1068a9e2dcdc3e673495d811f38c1e1d2caa",
  "topic": "SkillsFuture_SCTP",
  "topic_no": 2,
  "entity": "SCTP",
  "scheme": "SkillsFuture Career Transition Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/sctp/02_ssg_sctp_video_c4sf5C4hPb8.mp4",
  "owner": "Jony"
}
```

### Topic: `Career_Conversion_CCP` (topic_no=3)

#### `03_swda_ccp_factsheet_202607` — CORE · text · pdf

- **Title:** CCP Factsheet (Jul 2026)
- **URL:** https://www.swda.gov.sg/docs/programme/38b67413-cd3c-4968-8587-d370c4dc9256/ccp-factsheet-jul-2026.pdf
- **Primary file:** `data/raw/text/ccp/03_swda_ccp_factsheet_202607.pdf`
- **Sidecar:** `data/meta/03_swda_ccp_factsheet_202607.json`

```json
{
  "doc_id": "03_swda_ccp_factsheet_202607",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.swda.gov.sg/docs/programme/38b67413-cd3c-4968-8587-d370c4dc9256/ccp-factsheet-jul-2026.pdf",
  "canonical_url": "https://www.swda.gov.sg/docs/programme/38b67413-cd3c-4968-8587-d370c4dc9256/ccp-factsheet-jul-2026.pdf",
  "title": "CCP Factsheet (Jul 2026)",
  "agency": "SWDA",
  "citation": "SWDA — CCP Factsheet (Jul 2026) (eff. 2026-07-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "f3f8c306dc4300741b6346518d0599e7fd4397b1bf73b587df8bca2485bf5983",
  "topic": "Career_Conversion_CCP",
  "topic_no": 3,
  "entity": "CCP",
  "scheme": "Career Conversion Programme",
  "tier": "D",
  "authority_rank": 1,
  "doc_type": "pdf",
  "effective_date": "2026-07-01",
  "effective_date_int": 20260701,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": true,
  "table_verified": false,
  "extraction_source": "pdf",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/ccp/03_swda_ccp_factsheet_202607.pdf",
  "owner": "Jony"
}
```

#### `03_swda_ccp_faqs_202607` — CORE · text · pdf

- **Title:** CCP FAQs (Jul 2026)
- **URL:** https://www.swda.gov.sg/docs/programme/5b1a3d31-3037-4a4c-b405-4e6130e4a763/ccp-faqs-jul-2026.pdf
- **Primary file:** `data/raw/text/ccp/03_swda_ccp_faqs_202607.pdf`
- **Sidecar:** `data/meta/03_swda_ccp_faqs_202607.json`

```json
{
  "doc_id": "03_swda_ccp_faqs_202607",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.swda.gov.sg/docs/programme/5b1a3d31-3037-4a4c-b405-4e6130e4a763/ccp-faqs-jul-2026.pdf",
  "canonical_url": "https://www.swda.gov.sg/docs/programme/5b1a3d31-3037-4a4c-b405-4e6130e4a763/ccp-faqs-jul-2026.pdf",
  "title": "CCP FAQs (Jul 2026)",
  "agency": "SWDA",
  "citation": "SWDA — CCP FAQs (Jul 2026) (eff. 2026-07-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "c4bbcd3725ad619875b9fb0f9bcbb3dccf93172ddd4d6ab79b640857b3038f14",
  "topic": "Career_Conversion_CCP",
  "topic_no": 3,
  "entity": "CCP",
  "scheme": "Career Conversion Programme",
  "tier": "D",
  "authority_rank": 1,
  "doc_type": "pdf",
  "effective_date": "2026-07-01",
  "effective_date_int": 20260701,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "pdf",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/ccp/03_swda_ccp_faqs_202607.pdf",
  "owner": "Jony"
}
```

#### `03_wsg_ccp_employers` — CORE · text · scheme_page

- **Title:** Career Conversion Programmes (CCP) for Employers
- **URL:** https://www.wsg.gov.sg/home/employers-industry-partners/workforce-development-job-redesign/career-conversion-programmes-employers
- **Primary file:** `data/raw/text/ccp/03_wsg_ccp_employers.html`
- **Sidecar:** `data/meta/03_wsg_ccp_employers.json`

```json
{
  "doc_id": "03_wsg_ccp_employers",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.wsg.gov.sg/home/employers-industry-partners/workforce-development-job-redesign/career-conversion-programmes-employers",
  "canonical_url": "https://www.wsg.gov.sg/home/employers-industry-partners/workforce-development-job-redesign/career-conversion-programmes-employers",
  "title": "Career Conversion Programmes (CCP) for Employers",
  "agency": "WSG",
  "citation": "WSG — Career Conversion Programmes (CCP) for Employers (eff. 2026-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "3b9d5c61590e97ac9756304a7c0010d44cdfce1a06ad537689cfc5c072fc0ea9",
  "topic": "Career_Conversion_CCP",
  "topic_no": 3,
  "entity": "CCP",
  "scheme": "Career Conversion Programme",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2026-01-01",
  "effective_date_int": 20260101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": true,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/ccp/03_wsg_ccp_employers.html",
  "owner": "Jony"
}
```

#### `03_wsg_ccp_individuals` — CORE · text · scheme_page

- **Title:** Career Conversion Programmes (CCP) for Individuals
- **URL:** https://www.wsg.gov.sg/home/individuals/attachment-placement-programmes/career-conversion-programmes-for-individuals
- **Primary file:** `data/raw/text/ccp/03_wsg_ccp_individuals.html`
- **Sidecar:** `data/meta/03_wsg_ccp_individuals.json`

```json
{
  "doc_id": "03_wsg_ccp_individuals",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.wsg.gov.sg/home/individuals/attachment-placement-programmes/career-conversion-programmes-for-individuals",
  "canonical_url": "https://www.wsg.gov.sg/home/individuals/attachment-placement-programmes/career-conversion-programmes-for-individuals",
  "title": "Career Conversion Programmes (CCP) for Individuals",
  "agency": "WSG",
  "citation": "WSG — Career Conversion Programmes (CCP) for Individuals (eff. 2026-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "b04a1b4f7e1888f5cf43992a8b26ad855ce668c18c7c552ac4a49a4d2b2d1371",
  "topic": "Career_Conversion_CCP",
  "topic_no": 3,
  "entity": "CCP",
  "scheme": "Career Conversion Programme",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2026-01-01",
  "effective_date_int": 20260101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/ccp/03_wsg_ccp_individuals.html",
  "owner": "Jony"
}
```

#### `03_wsg_ccp_video_JIA9PgfCTgM` — NON-CORE · video · video

- **Title:** CCP YouTube explainer (JIA9PgfCTgM)
- **URL:** https://www.youtube.com/watch?v=JIA9PgfCTgM
- **Primary file:** `data/raw/video/ccp/03_wsg_ccp_video_JIA9PgfCTgM.mp4`
- **Sidecar:** `data/meta/03_wsg_ccp_video_JIA9PgfCTgM.json`

```json
{
  "doc_id": "03_wsg_ccp_video_JIA9PgfCTgM",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=JIA9PgfCTgM",
  "canonical_url": "https://www.youtube.com/watch?v=JIA9PgfCTgM",
  "title": "CCP YouTube explainer (JIA9PgfCTgM)",
  "agency": "WSG",
  "citation": "WSG — CCP YouTube explainer (JIA9PgfCTgM), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "353c2ab0bf00204ed681601c8fd2df3ae8db59f9fa229e1d844a606990dfc10f",
  "topic": "Career_Conversion_CCP",
  "topic_no": 3,
  "entity": "CCP",
  "scheme": "Career Conversion Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/ccp/03_wsg_ccp_video_JIA9PgfCTgM.mp4",
  "owner": "Jony"
}
```

#### `03_wsg_ccp_video_r1WeRjPmbCE` — NON-CORE · video · video

- **Title:** CCP YouTube explainer (r1WeRjPmbCE)
- **URL:** https://www.youtube.com/watch?v=r1WeRjPmbCE
- **Primary file:** `data/raw/video/ccp/03_wsg_ccp_video_r1WeRjPmbCE.mp4`
- **Sidecar:** `data/meta/03_wsg_ccp_video_r1WeRjPmbCE.json`

```json
{
  "doc_id": "03_wsg_ccp_video_r1WeRjPmbCE",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=r1WeRjPmbCE",
  "canonical_url": "https://www.youtube.com/watch?v=r1WeRjPmbCE",
  "title": "CCP YouTube explainer (r1WeRjPmbCE)",
  "agency": "WSG",
  "citation": "WSG — CCP YouTube explainer (r1WeRjPmbCE), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "f844a744d2bc6e54caf1cfddd5d5499facff941eb672dd14c9637d252d316849",
  "topic": "Career_Conversion_CCP",
  "topic_no": 3,
  "entity": "CCP",
  "scheme": "Career Conversion Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/ccp/03_wsg_ccp_video_r1WeRjPmbCE.mp4",
  "owner": "Jony"
}
```

### Topic: `AIAP` (topic_no=4)

#### `04_aisg_aiap_apprenticeship` — CORE · text · scheme_page

- **Title:** AI Apprenticeship Programme (AIAP)
- **URL:** https://aiap.sg/apprenticeship/
- **Primary file:** `data/raw/text/aiap/04_aisg_aiap_apprenticeship.html`
- **Sidecar:** `data/meta/04_aisg_aiap_apprenticeship.json`

```json
{
  "doc_id": "04_aisg_aiap_apprenticeship",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://aiap.sg/apprenticeship/",
  "canonical_url": "https://aiap.sg/apprenticeship/",
  "title": "AI Apprenticeship Programme (AIAP)",
  "agency": "AISG",
  "citation": "AISG — AI Apprenticeship Programme (AIAP) (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "784e1272691b542b427dcdf1509fe0f8495dc8439a81252f7529bc8e775647c2",
  "topic": "AIAP",
  "topic_no": 4,
  "entity": "AIAP",
  "scheme": "AI Apprenticeship Programme",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/aiap/04_aisg_aiap_apprenticeship.html",
  "owner": "Jony"
}
```

#### `04_aisg_aiap_candidates_faq` — CORE · text · faq

- **Title:** What type of candidates are we looking for in AIAP?
- **URL:** https://aisingapore.org/faq/what-type-of-candidates-are-we-looking-for-in-aiap/
- **Primary file:** `data/raw/text/aiap/04_aisg_aiap_candidates_faq.html`
- **Sidecar:** `data/meta/04_aisg_aiap_candidates_faq.json`

```json
{
  "doc_id": "04_aisg_aiap_candidates_faq",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://aisingapore.org/faq/what-type-of-candidates-are-we-looking-for-in-aiap/",
  "canonical_url": "https://aisingapore.org/faq/what-type-of-candidates-are-we-looking-for-in-aiap/",
  "title": "What type of candidates are we looking for in AIAP?",
  "agency": "AISG",
  "citation": "AISG — What type of candidates are we looking for in AIAP? (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "0a43b7ca3f24e59af9fa8acac380b4aa11e0fd4422a70a4d914550c0f1c0fc48",
  "topic": "AIAP",
  "topic_no": 4,
  "entity": "AIAP",
  "scheme": "AI Apprenticeship Programme",
  "tier": "B",
  "authority_rank": 1,
  "doc_type": "faq",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/aiap/04_aisg_aiap_candidates_faq.html",
  "owner": "Jony"
}
```

#### `04_aisg_aiap_innovation_page` — CORE · text · scheme_page

- **Title:** AI Apprenticeship Programme (AIAP) — AISG Innovation
- **URL:** https://aisingapore.org/innovation/aiap/
- **Primary file:** `data/raw/text/aiap/04_aisg_aiap_innovation_page.html`
- **Sidecar:** `data/meta/04_aisg_aiap_innovation_page.json`

```json
{
  "doc_id": "04_aisg_aiap_innovation_page",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://aisingapore.org/innovation/aiap/",
  "canonical_url": "https://aisingapore.org/innovation/aiap/",
  "title": "AI Apprenticeship Programme (AIAP) — AISG Innovation",
  "agency": "AISG",
  "citation": "AISG — AI Apprenticeship Programme (AIAP) — AISG Innovation (eff. 2025-01-01), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "87fbb10a397bdce994bf98c7d5f00876a5adcea675c4afc6a237f514b2b4629c",
  "topic": "AIAP",
  "topic_no": 4,
  "entity": "AIAP",
  "scheme": "AI Apprenticeship Programme",
  "tier": "A",
  "authority_rank": 2,
  "doc_type": "scheme_page",
  "effective_date": "2025-01-01",
  "effective_date_int": 20250101,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/aiap/04_aisg_aiap_innovation_page.html",
  "owner": "Jony"
}
```

#### `04_aisg_aiap_video_86q_VISXpzM` — NON-CORE · video · video

- **Title:** AIAP YouTube (86q_VISXpzM)
- **URL:** https://www.youtube.com/watch?v=86q_VISXpzM
- **Primary file:** `data/raw/video/aiap/04_aisg_aiap_video_86q_VISXpzM.mp4`
- **Sidecar:** `data/meta/04_aisg_aiap_video_86q_VISXpzM.json`

```json
{
  "doc_id": "04_aisg_aiap_video_86q_VISXpzM",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=86q_VISXpzM",
  "canonical_url": "https://www.youtube.com/watch?v=86q_VISXpzM",
  "title": "AIAP YouTube (86q_VISXpzM)",
  "agency": "AISG",
  "citation": "AISG — AIAP YouTube (86q_VISXpzM), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "8743174426c4a3520925fa4049ca6d5748598767d6d7bd502eb2bd89be9fa69d",
  "topic": "AIAP",
  "topic_no": 4,
  "entity": "AIAP",
  "scheme": "AI Apprenticeship Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/aiap/04_aisg_aiap_video_86q_VISXpzM.mp4",
  "owner": "Jony"
}
```

#### `04_aisg_aiap_video_fByVHVZtmQc` — NON-CORE · video · video

- **Title:** AIAP YouTube (fByVHVZtmQc)
- **URL:** https://www.youtube.com/watch?v=fByVHVZtmQc
- **Primary file:** `data/raw/video/aiap/04_aisg_aiap_video_fByVHVZtmQc.mp4`
- **Sidecar:** `data/meta/04_aisg_aiap_video_fByVHVZtmQc.json`

```json
{
  "doc_id": "04_aisg_aiap_video_fByVHVZtmQc",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=fByVHVZtmQc",
  "canonical_url": "https://www.youtube.com/watch?v=fByVHVZtmQc",
  "title": "AIAP YouTube (fByVHVZtmQc)",
  "agency": "AISG",
  "citation": "AISG — AIAP YouTube (fByVHVZtmQc), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "8e86879730c85560b4d20b7d7485a09efdb4bdbcfae4e993451d06b1fbffc3e3",
  "topic": "AIAP",
  "topic_no": 4,
  "entity": "AIAP",
  "scheme": "AI Apprenticeship Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/aiap/04_aisg_aiap_video_fByVHVZtmQc.mp4",
  "owner": "Jony"
}
```

### Topic: `SNAIC` (topic_no=5)

#### `05_sit_snaic_news_opening` — CORE · text · press_release

- **Title:** SIT Marks Opening of Flagship AI Centre / SNAIC AI Programme
- **URL:** https://www.singaporetech.edu.sg/news/sit-marks-opening-its-flagship-ai-centre-sit-punggol-campus-key-initiatives-and-partnerships-advance
- **Primary file:** `data/raw/text/snaic/05_sit_snaic_news_opening.html`
- **Sidecar:** `data/meta/05_sit_snaic_news_opening.json`

```json
{
  "doc_id": "05_sit_snaic_news_opening",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.singaporetech.edu.sg/news/sit-marks-opening-its-flagship-ai-centre-sit-punggol-campus-key-initiatives-and-partnerships-advance",
  "canonical_url": "https://www.singaporetech.edu.sg/news/sit-marks-opening-its-flagship-ai-centre-sit-punggol-campus-key-initiatives-and-partnerships-advance",
  "title": "SIT Marks Opening of Flagship AI Centre / SNAIC AI Programme",
  "agency": "SIT",
  "citation": "SIT — SIT Marks Opening of Flagship AI Centre / SNAIC AI Programme (eff. 2025-10-02), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "496f4bc6cc909f6f260b45ff2e173e207f9abc0fbc7f2d2617182d0f5b323a81",
  "topic": "SNAIC",
  "topic_no": 5,
  "entity": "SNAIC",
  "scheme": "SNAIC AI Programme",
  "tier": "C",
  "authority_rank": 3,
  "doc_type": "press_release",
  "effective_date": "2025-10-02",
  "effective_date_int": 20251002,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/snaic/05_sit_snaic_news_opening.html",
  "owner": "Jony"
}
```

#### `05_sit_snaic_programme` — CORE · text · scheme_page

- **Title:** SNAIC AI Programme (SIT x NVIDIA)
- **URL:** https://www.singaporetech.edu.sg/sitlearn/register-interest-snaic
- **Primary file:** `data/raw/text/snaic/05_sit_snaic_programme.html`
- **Sidecar:** `data/meta/05_sit_snaic_programme.json`

```json
{
  "doc_id": "05_sit_snaic_programme",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.singaporetech.edu.sg/sitlearn/register-interest-snaic",
  "canonical_url": "https://www.singaporetech.edu.sg/sitlearn/register-interest-snaic",
  "title": "SNAIC AI Programme (SIT x NVIDIA)",
  "agency": "SIT",
  "citation": "SIT — SNAIC AI Programme (SIT x NVIDIA) (eff. 2025-10-02), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T14:05:00+08:00",
  "content_sha256": "e85e3ebbc3d09429d052df8a382df5ed0c665adf518b4b732b2cb22d644d48c2",
  "topic": "SNAIC",
  "topic_no": 5,
  "entity": "SNAIC",
  "scheme": "SNAIC AI Programme",
  "tier": "A",
  "authority_rank": 1,
  "doc_type": "scheme_page",
  "effective_date": "2025-10-02",
  "effective_date_int": 20251002,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": true,
  "table_verified": false,
  "extraction_source": "dom",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "text",
  "core": true,
  "source_file": "data/raw/text/snaic/05_sit_snaic_programme.html",
  "owner": "Jony"
}
```

#### `05_sit_snaic_video_i3SeCbgRkec` — NON-CORE · video · video

- **Title:** SNAIC YouTube (i3SeCbgRkec)
- **URL:** https://www.youtube.com/watch?v=i3SeCbgRkec
- **Primary file:** `data/raw/video/snaic/05_sit_snaic_video_i3SeCbgRkec.mp4`
- **Sidecar:** `data/meta/05_sit_snaic_video_i3SeCbgRkec.json`

```json
{
  "doc_id": "05_sit_snaic_video_i3SeCbgRkec",
  "chunk_index": 0,
  "chunk_total": 0,
  "source_url": "https://www.youtube.com/watch?v=i3SeCbgRkec",
  "canonical_url": "https://www.youtube.com/watch?v=i3SeCbgRkec",
  "title": "SNAIC YouTube (i3SeCbgRkec)",
  "agency": "SIT",
  "citation": "SIT — SNAIC YouTube (i3SeCbgRkec), retrieved 2026-07-29",
  "section": "",
  "retrieved_at": "2026-07-29T15:00:00+08:00",
  "content_sha256": "3b177da054238648715e16a3bb2139b4ef3d76066b6b39031b1c44dab0d92ab8",
  "topic": "SNAIC",
  "topic_no": 5,
  "entity": "SNAIC",
  "scheme": "SNAIC AI Programme",
  "tier": "E",
  "authority_rank": 4,
  "doc_type": "video",
  "effective_date": "",
  "effective_date_int": 0,
  "last_updated": "",
  "last_updated_int": 0,
  "is_current": true,
  "superseded": false,
  "supersedes_doc_id": "",
  "budget_year": 0,
  "annex_ref": "",
  "deny_listed": false,
  "deny_reason": "",
  "has_table": false,
  "table_verified": false,
  "extraction_source": "youtube_yt_dlp",
  "licence_note": "© Source owner; reproduced for academic Capstone use only",
  "modality": "video",
  "core": false,
  "source_file": "data/raw/video/snaic/05_sit_snaic_video_i3SeCbgRkec.mp4",
  "owner": "Jony"
}
```
