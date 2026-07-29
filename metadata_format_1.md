# Metadata Format — Team Guide

**For:** everyone collecting sources for topics (1)–(11)
**Verified against ChromaDB 1.5.9 on 29 Jul 2026** — every rule below was tested, not assumed.

> **You fill in 8 fields, plus up to 3 more if the page shows them. That's it.** Everything else is added later by the ingest script. Don't hold back a source because you're missing metadata.

---

## 1. The 8 required fields

Put this block at the very top of every `.md` file you create:

```yaml
---
doc_id:        "hdb_ehg_families"
title:         "Enhanced CPF Housing Grant for Families"
source_url:    "https://www.hdb.gov.sg/buying-a-flat/flat-grant-and-loan-eligibility/couples-and-families/enhanced-cpf-housing-grant"
agency:        "HDB"
topic:         "HDB_Grants"
scheme:        "Enhanced CPF Housing Grant (Families)"
tier:          "A"
retrieved_on:  "2026-07-29"
---
```

| Field | What it is | How to fill it |
|---|---|---|
| **`doc_id`** | Unique slug for this document; becomes the filename. | Lowercase, underscores, no spaces. Prefix with the agency: `hdb_…`, `cpf_…`, `moh_…`. Must be unique **across the whole team** — see §3. |
| **`title`** | The page's own headline, copied exactly. | From the page `<h1>` or PDF cover. For Budget documents include the year and annex number: `Budget 2025 Annex F-4 — MRSS for Persons With Disabilities`. |
| **`source_url`** | The exact URL the content came from. | Paste the address bar. If the URL redirected, record where you **landed**, not what you typed. This is what the chatbot cites — without it an answer can't be traced. |
| **`agency`** | Which government body published it. | One of: `HDB` `CPF` `MOH` `MOF` `IRAS` `MOM` `MND` `MSF` |
| **`topic`** | Which of the 11 project topics this belongs to. | Your topic folder name exactly: `HDB_Grants` · `Medisave_Medishield` · `CPF_Top_Up` · *(+ the topic-1–8 names)* |
| **`scheme`** | The specific scheme the document is about. | **Be precise, not general.** Write `MediSave` or `MediShield Life`, never "healthcare". Write `Enhanced CPF Housing Grant (Families)`, not "HDB grant". This is what stops the chatbot mixing up two schemes with different numbers. |
| **`tier`** | How authoritative the source is. | One letter: `A` official scheme page · `B` official FAQ · `C` press release / Budget / speech · `D` PDF or annex · `E` adjacent scheme |
| **`retrieved_on`** | The date you captured it. | `"YYYY-MM-DD"`, **in quotes**. Today's date. |

> ⚠️ **Quote every date.** Unquoted `2026-07-29` is parsed by YAML as a *date object*, which ChromaDB rejects outright. `"2026-07-29"` in quotes is a string and works. This is the most common way an ingest run fails.

> ⚠️ **Spelling matters.** `agency`, `topic`, `tier` and `doc_type` use fixed lists. Filters fail *silently* on a typo — the document just never shows up. Copy the values above exactly.

---

## 2. Optional — add only if the page shows it

Leave these out entirely if you can't find them. **Do not guess.**

| Field | What it is | How to fill it |
|---|---|---|
| **`effective_date`** | When the **figures** on this page took effect. | `"YYYY-MM-DD"` in quotes. Look for *"From 20 August 2024…"*, *"with effect from 1 June 2026"*, or a caption printed above a table. **The most valuable optional field** — these schemes change often, and without it the chatbot can quote a superseded amount as current. |
| **`doc_type`** | What kind of document it is. | One of: `scheme_page` · `faq` · `press_release` · `budget_annex` · `pdf` · `process_guide` |
| **`section`** | Which part of the page this came from. | Only if you split one page into several files, e.g. `"Grant amounts by household income"`. |

> **`effective_date` vs `retrieved_on` — the one people get wrong.** `effective_date` = when the *rules changed*. `retrieved_on` = when *you looked*. A page retrieved today can carry figures effective from 2024. Both matter, and they're rarely the same.

---

## 3. `doc_id` must be unique across the whole team

11 topics, 8+ people, one database — this is the real merge risk. Prefix your `doc_id` with the agency and keep it descriptive:

```
hdb_ehg_families
cpf_mrss_canonical
moh_medishield_life_benefits
```

The ingest script adds the topic number and chunk number around it, so you only need yours to be distinct.

---

## 4. Four rules for the file contents

**1. Keep tables as Markdown tables.** If a grant table gets flattened into a run-on sentence, the retriever still returns it and the model invents the tier boundaries. Keep the `| … | … |` structure.

**2. Keep dollar figures verbatim.** `$120,000`, never `120000`.

**3. Strip the page furniture.** Remove navigation menus, breadcrumbs, footers, cookie banners and "Was this page helpful?" widgets. On some pages that's 40% of the text, and all of it pollutes the search.

**4. Put alternative names in the text.** If a scheme has a retired or informal name people still search for — "Half-Housing Grant", MCPS, MGPS, AHG/SHG — write it into the document text itself, e.g. *"…previously known as the Half-Housing Grant…"*. Metadata can't be searched for these; the document text can.

---

## 5. Worked example

`datasets/HDB_Grants/markdown/hdb_ehg_families.md`

```markdown
---
doc_id:         "hdb_ehg_families"
title:          "Enhanced CPF Housing Grant for Families"
source_url:     "https://www.hdb.gov.sg/buying-a-flat/flat-grant-and-loan-eligibility/couples-and-families/enhanced-cpf-housing-grant"
agency:         "HDB"
topic:          "HDB_Grants"
scheme:         "Enhanced CPF Housing Grant (Families)"
tier:           "A"
retrieved_on:   "2026-07-29"
effective_date: "2024-08-20"
doc_type:       "scheme_page"
---

# Enhanced CPF Housing Grant for Families

From 20 August 2024, first-timer families may qualify for an EHG of up to $120,000...

## Grant amounts by average monthly household income

| Average monthly household income | EHG amount |
|---|---|
| Not more than $1,500 | $120,000 |
| $1,501 to $2,000 | $115,000 |
```

The same file with only the 8 required fields is **still acceptable** — submit it rather than holding it back.

---

## 6. Checklist before you submit

- [ ] All 8 required fields present
- [ ] **Every date wrapped in quotes**
- [ ] `agency`, `topic`, `tier` spelled exactly as listed
- [ ] `doc_id` unique and agency-prefixed
- [ ] `source_url` is where you **landed**, not what you typed
- [ ] `scheme` names the specific scheme, not a general area
- [ ] `effective_date` captured **if** the page states one
- [ ] Tables kept as Markdown tables
- [ ] Page furniture stripped out
- [ ] Dollar figures verbatim (`$120,000`, not `120000`)
