# Retrieval Evaluation — SG Citizen Financial Assistant

Dense vs. hybrid retrieval, run 2026-07-30 against the rebuilt Chroma index (394 documents, 1818 chunks, built from the full Drive-synced corpus — Silver Support Scheme and IRAS CPF top-up relief now included).

| | |
|---|---|
| **LLM** | gpt-5.4-mini |
| **Embedding model** | BAAI/bge-m3 |
| **top_k** | 5 |
| **Labeled questions** | 8 / 15 |
| **Results source** | `evaluation/results/{dense,hybrid}_results.json` (local only, gitignored) |

## The comparison

Computed only over the 8 labeled questions, each against its hand-picked ground-truth chunk(s).

| Metric | Dense (baseline) | Hybrid (improved) | Δ |
|---|---|---|---|
| Hit rate | 25.0% | 37.5% | +12.5% |
| Recall@5 | 18.8% | 31.2% | +12.5% |
| MRR | 0.167 | 0.192 | +0.025 |

> **Small sample, read directionally.** n = 8 labeled questions and a single strict ground-truth chunk per question — a top-5 retrieval that surfaces the right *document* but not that exact chunk still counts as a miss. Treat this as a signal that hybrid is moving the right way, not a precise percentage.

## What stood out beyond the numbers

**Dense hallucinated a citizenship fact; hybrid didn't.**  
PR3 profiles a Permanent Resident. Dense mode's shortlist opened with "You are a Singapore citizen aged 40" — flatly wrong — and went on to mark SkillsFuture Credit (citizen-only) as eligible. Hybrid's shortlist correctly marked citizenship-gated conditions `not_met` throughout. Same question, same index — the retrieval order changed which passages anchored the answer. See PR3 below.

**Three questions are corpus gaps, not retrieval failures.**  
F2 (tax relief cap), P1 (Parent Relief), and P2 (Working Mother's Child Relief) all target IRAS content the corpus doesn't actually contain — the only two IRAS documents indexed are both specific to CPF Cash Top-up Relief. Both modes still answered F2's $80,000 figure fluently despite it not being in scope; a plausible surface-level answer is a harder failure mode to catch than an abstain, since nothing about the output looks wrong at a glance.

## Per-question detail

Grouped by test category. The hit/miss column applies only to the 8 labeled questions; `—` means no ground-truth chunk was labeled for that question (see `evaluation/test_set.json`'s `_note` for why F2/P1/P2 are left unlabeled).

### Factual

#### **F1** — How much does each eligible Singaporean household get from CDC Vouchers, and where can they be spent?

*Criteria: States the voucher value per household and that they can be spent at participating hawkers/heartland merchants/supermarkets.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ✅ hit

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

Each eligible Singaporean household gets **$500 in CDC Vouchers** [Mof Budget2026 Statement Sectione, full document]. Half can be used at **participating supermarkets**, and the other half at **participating heartland merchants and hawkers** [Mof Budget2026 Statement Sectione, full document].

Retrieved chunks:

- **✓ (expected)** `CDC_image_000`
- `mof_budget2026_statement_sectione_text_006`
- `GST Voucher (GSTV) – MediSave - SupportGoWhere_text_000`
- `adj_gstv_medisave_2026_text_000`
- `moh_pdf_review_committee_2014_text_022`

---

#### **F2** — What is the maximum claimable cap for total personal income tax reliefs?

*Criteria: States the $80,000 overall personal income tax relief cap.*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

The maximum claimable cap for the total amount of personal income tax reliefs is **$80,000 per Year of Assessment** [Iras Pdf Cpf Cash Topup Relief, Full document]

Retrieved chunks:

- `iras_cpf_cash_topup_relief_html_text_017`
- `iras_cpf_cash_topup_relief_html_text_023`
- `iras_pdf_cpf_cash_topup_relief_text_004`
- `cpf_faq_how_can_i_find_out_if_i_have_reached_the_personal_in_text_000`
- `iras_cpf_cash_topup_relief_html_text_015`

**Hybrid (improved):**

The maximum claimable cap for total personal income tax reliefs is $80,000 per year of assessment. [Iras Pdf Cpf Cash Topup Relief, Full document]

Retrieved chunks:

- `iras_cpf_cash_topup_relief_html_text_023`
- `iras_pdf_cpf_cash_topup_relief_text_004`
- `iras_cpf_cash_topup_relief_html_text_017`
- `cpf_faq_do_i_get_tax_relief_for_voluntary_top_ups_to_the_med_text_000`
- `cpf_faq_how_can_i_find_out_if_i_have_reached_the_personal_in_text_000`

---

#### **F3** — What is the Silver Support Scheme payout frequency?

*Criteria: States that payouts are quarterly, and mentions the eligibility tiers by Assessable Income/AV/household support.*

Dense: ✅ hit &nbsp;&nbsp; Hybrid: ✅ hit

**Dense (baseline):**

Silver Support Scheme payouts are made every quarter. [Adj Silver Support, Full document]

Retrieved chunks:

- **✓ (expected)** `adj_silver_support_text_002`
- `adj_silver_support_text_000`
- `adj_silver_support_text_001`
- `adj_silver_support_text_003`
- `mof_budget2024_annexf1_retirement_system_text_005`

**Hybrid (improved):**

The Silver Support Scheme is paid out every quarter. [Adj Silver Support, Full document]

Retrieved chunks:

- `adj_silver_support_text_000`
- `adj_silver_support_text_003`
- **✓ (expected)** `adj_silver_support_text_002`
- `adj_silver_support_text_001`
- `ElderFund _ AIC_text_008`

---

### Paraphrase

#### **P1** — My mother lives with me and has no job. Can I reduce my tax bill because of her?

*Criteria: Identifies Parent Relief as the relevant relief and states its qualifying conditions (e.g. income/age of dependent, cohabitation).*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

---

#### **P2** — I'm a working mum with a young kid — is there a tax break for that?

*Criteria: Identifies Working Mother's Child Relief (WMCR) and its qualifying conditions.*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

---

#### **P3** — I put extra money into my CPF for retirement — do I get anything back on tax?

*Criteria: Identifies CPF top-up / SRS-related relief and its qualifying conditions.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss

**Dense (baseline):**

Yes, cash top-ups to CPF retirement savings can give you tax relief, but only for the giver, not the recipient [Cpf Rstu Topup, Full document]. You can receive up to $8,000 tax relief when you make a cash top-up to yourself, and up to another $8,000 when you make a cash top-up to certain loved ones in a calendar year [Cpf Rstu Topup, Full document]. The total tax relief for family members is capped at $8,000 for each individual taxpayer from YA 2023 onwards [Iras Cpf Cash Topup Relief Html, Full document].  

Tax relief is only available if the top-up is within the qualifying limits; if your CPF savings have already reached the Full Retirement Sum, you will not be eligible for CPF Cash Top-up Relief [Iras Cpf Cash Topup Relief Html, Full document]. Cash top-up relief is granted automatically, so you do not need to claim it [Iras Cpf Cash Topup Relief Html, Full document].

Retrieved chunks:

- `cpf_rstu_topup_text_001`
- `iras_cpf_cash_topup_relief_html_text_022`
- `cpf_reaching_55_text_001`
- `cpf_what_is_retirement_sum_text_003`
- `iras_cpf_cash_topup_relief_html_text_023`

**Hybrid (improved):**

Yes. If you make a cash top-up to yourself, you can receive up to $8,000 tax relief in each calendar year, and up to another $8,000 if you top up your loved ones’ CPF accounts in the same year [Cpf Rstu Topup, Full document]. Tax relief only applies to the giver, not the recipient [Cpf Rstu Topup, Full document].

For CPF cash top-up relief, you generally get tax relief only up to the prevailing Full Retirement Sum, and not for amounts above the tax-relief limit [Iras Cpf Cash Topup Relief Html, Full document]. The relief is granted automatically if you are eligible, so you do not need to claim it [Iras Cpf Cash Topup Relief Html, Full document].

Retrieved chunks:

- `cpf_rstu_topup_text_001`
- `adj_retirement_sum_scheme_text_002`
- `iras_cpf_cash_topup_relief_html_text_022`
- `Home Caregiving Grant (HCG) _ AIC__comcare_text_007`
- `cpf_reaching_55_text_001`

---

### Multi-document

#### **M1** — What financial support (cash payouts and tax savings) can a working mother with a young child get from the government?

*Criteria: Combines Assurance Package/GST Voucher cash payouts with Working Mother's Child Relief and Child Relief, citing both a Govbenefits-style scheme doc and the IRAS reliefs doc.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

A working mother with a young child may be eligible for the Baby Bonus Scheme if she is lawfully married to her spouse and the child is a Singapore Citizen. The scheme provides the Baby Bonus Cash Gift and Child Development Account benefits, including the First Step Grant and Government co-matching of parents’ savings, up to a cap. [Baby Bonus Scheme, pp.1-2]

For the Baby Bonus Cash Gift, the amount is $11,000 for the first and second child, and $13,000 for the third and subsequent child. It is paid over the child’s first six-and-a-half years of life. [Baby Bonus Scheme, pp.1-2]

The context passages do not contain information on any tax savings for a working mother with a young child.

Retrieved chunks:

- `parentkit-ccic_text_001`
- `Baby_Bonus_Scheme_text_000`
- `adj_retirement_sum_scheme_text_002`
- `mof_budget2026_statement_sectione_text_000`
- `ECDA _ Overview of the infant and childcare subsidy scheme_text_002`

---

#### **M2** — What can a low-income retired senior living in a rental flat get from the government?

*Criteria: Combines Silver Support Scheme and ComCare Assistance, citing both scheme docs.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

---

### Unanswerable

#### **U1** — Can I use my CDC vouchers to pay for my IRAS income tax bill?

*Criteria: Must trigger the exact fallback: "The available knowledge base does not contain enough information to answer this question."*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

---

#### **U2** — Can I claim tax relief for taking care of my pet dog?

*Criteria: Must trigger the exact fallback: "The available knowledge base does not contain enough information to answer this question."*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

---

### Ambiguous

#### **A1** — How much money will I get from the government this year?

*Criteria: Should not fabricate a single number; should ask for or note the missing inputs it needs (age, income, property AV, citizenship) before giving a number, or abstain/qualify heavily.*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

---

#### **A2** — Am I eligible for Workfare?

*Criteria: Should note that eligibility depends on age, income, and employment type, and not assert a definite yes/no without those inputs.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

You qualify for Workfare Income Supplement if you are a Singapore Citizen, are at least 30 years old as of 31 December of the work year (or a person with disabilities of any age), earn a gross monthly income of at least $500 and not more than $3,000 for the month worked, have an average gross monthly income of not more than $3,000 in the past 12 months, live in a property with an annual value of $21,000 and below, own not more than one property, and if you are married, you and your spouse together own not more than one property and your spouse’s assessable income does not exceed $70,000 for the preceding Year of Assessment [Cpf Wis Scheme Page, Full document]. 

Gross monthly income includes basic salary and extra wages such as overtime pay, commissions and bonuses [Cpf Wis Scheme Page, Full document]. Persons with disabilities, workers who qualify for ComCare Short-to-Medium-Term Assistance, and caregivers of care recipients may qualify for concessionary WIS even if they earn less than $500 [Cpf Wis Scheme Page, Full document].

Retrieved chunks:

- `adj_workfare_income_supplement_text_001`
- `COL_policies_text_001`
- `cpf_wis_scheme_page_text_005`
- `cpf_pdf_faqs_budget2026_topup_text_002`
- `cpf_wis_scheme_page_text_016`

---

### Personal profile

#### **PR1** — profile: Singapore Citizen, age 68, <$1.5k, HDB, Retired, tags: Senior (65+)

*Criteria: Shortlist should surface Silver Support and cost-of-living schemes as 'Possibly eligible', citing amounts only if stated in evidence.*

Dense: ✅ hit &nbsp;&nbsp; Hybrid: ✅ hit

**Dense (baseline):**

- **Silver Support Scheme** — 🟢 eligible
  - You are a Singapore Citizen aged 65 and above with low household income, matching two stated eligibility conditions.
  - Amount: `$430 per quarter`
  - Conditions: ✅ Singapore Citizen aged 65 and above &nbsp;·&nbsp; ◻️ Total Central Provident Fund (CPF) contributions by age 55 up to $140,000, or average annual net trade income up to $27,600 for self-employed or platform workers aged 45 to 54 &nbsp;·&nbsp; ✅ Live in a 1- to 5-room HDB flat &nbsp;·&nbsp; ◻️ You or your spouse do not own a 5-room or larger HDB flat, private property or multiple properties &nbsp;·&nbsp; ✅ Per capita household income up to $2,300
  - _What would change this: A CPF contribution record above $140,000 or property ownership that breaks the housing rule would change this assessment._
- **MediShield Life premium subsidies** — 🟢 eligible
  - You are a Singapore Citizen aged 68 with household income per person below $1,500, matching the income and age subsidy bands.
  - Amount: `40%`
  - Conditions: ✅ Singapore Citizen or Permanent Resident &nbsp;·&nbsp; ✅ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in a residence with Annual Value of $31,000 and below &nbsp;·&nbsp; ◻️ Not owning more than one property &nbsp;·&nbsp; ✅ Age next birthday 61–70 for the listed subsidy tier
  - _What would change this: A residence annual value above $31,000 or owning more than one property would change the subsidy assessment._

Retrieved chunks:

- `Schemes-Terms-Conditions__elderly_text_025`
- `cpf_mslinfo_booklet_text_017`
- **✓ (expected)** `adj_silver_support_text_001`
- `moh_pdf_review_committee_2014_text_105`
- `cpf_mslinfo_booklet_text_018`

**Hybrid (improved):**

- **CHAS Blue** — 🟢 eligible
  - You are a Singapore Citizen with household monthly income per person below $1,500, matching the key income criterion.
  - Amount: `Up to $18.50 subsidy per visit`
  - Conditions: ✅ Singapore Citizen &nbsp;·&nbsp; ✅ Household monthly income per person: $1,500 and below &nbsp;·&nbsp; ◻️ Annual value of home: $21,000 and below, for households without income
  - _What would change this: If your income per person were above $1,500, this CHAS Blue assessment would no longer fit the listed income tier._
- **Premium Subsidies** — 🟢 eligible
  - You are a Singapore Citizen with income per person below $1,500, and your HDB housing suggests you may fit the residence requirement.
  - Amount: `40%`
  - Conditions: ✅ Singapore Citizens and Permanent Residents &nbsp;·&nbsp; ✅ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in residences with Annual Value of $31,000 and below &nbsp;·&nbsp; ◻️ Own more than one property
  - _What would change this: If your residence annual value were above $31,000 or you owned more than one property, these subsidies would not apply._
- **Silver Support Scheme** — 🟢 eligible
  - You are a Singapore Citizen aged 68 living in HDB housing with low income, matching the age, housing, and household income profile.
  - Amount: `Up to $1,080 per quarter`
  - Conditions: ✅ Singapore Citizen aged 65 and above &nbsp;·&nbsp; ◻️ Total CPF contributions by age 55 up to $140,000, or for self-employed/platform worker average annual net trade income up to $27,600 &nbsp;·&nbsp; ◻️ Live in a 1- to 5-room HDB flat &nbsp;·&nbsp; ◻️ You or your spouse do not own a 5-room or larger HDB flat, private property or multiple properties &nbsp;·&nbsp; ✅ Per capita household income up to $2,300
  - _What would change this: If your lifetime CPF contributions were too high or you lived in a non-qualifying property, this scheme would change._

Retrieved chunks:

- `Schemes-Terms-Conditions__elderly_text_025`
- `CHAS_Blue_text_000`
- `cpf_mslinfo_booklet_text_017`
- `Schemes-Terms-Conditions__elderly_text_005`
- **✓ (expected)** `adj_silver_support_text_001`

---

#### **PR2** — profile: Singapore Citizen, age 32, $3-6k, HDB, Employed, tags: Has young child(ren)

*Criteria: Shortlist should surface Baby Bonus / family-oriented schemes as 'Possibly eligible' and not assert senior schemes as eligible.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss

**Dense (baseline):**

_Empty shortlist — no schemes surfaced._

Retrieved chunks:

- `Schemes-Terms-Conditions__elderly_text_025`
- `Schemes-Terms-Conditions__comcare_text_025`
- `cpf_mslinfo_booklet_text_017`
- `Student Care Fee Assistance (SCFA) - SupportGoWhere_text_001`
- `adj_silver_support_text_001`

**Hybrid (improved):**

- **Premium Subsidies** — 🟢 eligible
  - Your income band fits the lower- to middle-income limit, but your residence annual value and property count were not provided.
  - Conditions: ✅ Singapore Citizen or Singapore Permanent Resident &nbsp;·&nbsp; ◻️ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in residences with annual value of $31,000 and below &nbsp;·&nbsp; ◻️ Does not own more than one property
  - _What would change this: A lower household income per person, an eligible residence annual value, and no more than one property would strengthen this assessment._
- **Basic Subsidy** — 🟢 eligible
  - Your child is a Singapore Citizen, but the child’s enrolment in an ECDA-licensed infant care or childcare centre was not provided.
  - Amount: `$300 per month`
  - Conditions: ✅ Child is a Singapore Citizen &nbsp;·&nbsp; ◻️ Child is enrolled in an ECDA-licensed infant care or childcare centre
  - _What would change this: If your child is enrolled in an ECDA-licensed infant care or childcare centre, this scheme becomes a better fit._
- **Additional Subsidy** — 🟢 eligible
  - Your child is a Singapore Citizen and your household income appears within the limit, but enrolment and family-size details were not provided.
  - Conditions: ✅ Child is a Singapore Citizen &nbsp;·&nbsp; ◻️ Child is enrolled in an ECDA-licensed infant care or childcare preschool &nbsp;·&nbsp; ◻️ Family's gross monthly household income is $12,000 or below, or per capita income is $3,000 or below for households with 5 or more family members
  - _What would change this: If the child is enrolled in an ECDA-licensed preschool and your household meets the income test, this scheme becomes more likely._
- **Home Caregiving Grant** — 🟢 eligible
  - Your profile does not show a patient who needs help with daily living activities or lives in the community.
  - Conditions: ◻️ Patient is a Singapore citizen, or a Singapore permanent resident with a living Singapore citizen parent, child or spouse &nbsp;·&nbsp; ◻️ Per capita monthly household income of S$4,800 or less, or annual property value of S$21,000 or less if no income &nbsp;·&nbsp; ◻️ Assessed by an approved assessor to permanently require some assistance with 3 or more Activities of Daily Living &nbsp;·&nbsp; ◻️ Living in the community and not in a residential long-term care institution &nbsp;·&nbsp; ◻️ Residing in Singapore
  - _What would change this: If there is a Singapore-resident patient assessed to need daily living assistance, eligibility could change._

Retrieved chunks:

- `Schemes-Terms-Conditions__elderly_text_025`
- `cpf_what_is_retirement_sum_text_004`
- `Schemes-Terms-Conditions__comcare_text_025`
- `Early Childhood Development Agency _ Who is eligible for Basic and Additional Subsidies__text_000`
- `cpf_mslinfo_booklet_text_017`

---

#### **PR3** — profile: PR, age 40, Prefer not to say, Private, Employed, tags: none

*Criteria: Heavy 'Likely not eligible / unclear' due to PR status and undisclosed income on citizen-only/income-gated schemes.*

Dense: — &nbsp;&nbsp; Hybrid: —

**Dense (baseline):**

- **Premium Subsidies** — 🟢 eligible
  - You are a permanent resident, but your income band and property value are not provided, so eligibility cannot be confirmed.
  - Conditions: ✅ Singapore Citizen or Permanent Resident &nbsp;·&nbsp; ◻️ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in a residence with an Annual Value of $31,000 and below &nbsp;·&nbsp; ◻️ Not owning more than one property
  - _What would change this: A household income per person above $3,600, a home value above $31,000, or owning multiple properties would change this assessment._
- **SkillsFuture Credit** — 🟢 eligible
  - You are a Singapore citizen aged 40, which matches the age threshold for the $4,000 opening credit.
  - Amount: `$4,000`
  - Conditions: ✅ Singapore Citizens aged 40 and above
  - _What would change this: Being under 40 or not being a Singapore citizen would change this assessment._

Retrieved chunks:

- `Schemes-Terms-Conditions__elderly_text_025`
- `cpf_mslinfo_booklet_text_017`
- `Schemes-Terms-Conditions__comcare_text_025`
- `moh_pdf_review_committee_2014_text_105`
- `ssg_skillsfuture_credit_amounts_image_000`

**Hybrid (improved):**

- **CHAS Blue** — 🟡 unclear
  - Your Singapore permanent resident status matches, but this scheme requires a Singapore citizen and lower household income details we cannot confirm.
  - Conditions: ❌ Singapore citizen &nbsp;·&nbsp; ◻️ Household monthly income per person is $1,500 and below, or annual value of home is $21,000 and below if no income
  - _What would change this: A Singapore citizen profile with qualifying household income and housing value would change this assessment._
- **MediShield Life premium subsidies** — 🟢 eligible
  - Your permanent resident status matches, but the income-per-person and residence value limits are not provided.
  - Amount: `half of the applicable subsidy rates`
  - Conditions: ✅ Singapore citizen or permanent resident &nbsp;·&nbsp; ◻️ Household monthly income per person is $3,600 and below &nbsp;·&nbsp; ◻️ Living in residences with an annual value of $31,000 and below &nbsp;·&nbsp; ◻️ Owns no more than one property
  - _What would change this: Knowing your household income per person, home annual value, and property count could change this assessment._
- **Home Caregiving Grant** — 🟢 eligible
  - Your permanent resident status fits only with a Singapore citizen parent, child, or spouse, and the care-needs assessment is not known.
  - Conditions: ◻️ Singapore citizen or permanent resident with a living Singapore citizen parent, child, or spouse &nbsp;·&nbsp; ◻️ Per capita monthly household income is S$4,800 or less, or annual value of home is S$21,000 or less if no income &nbsp;·&nbsp; ◻️ Assessed to permanently require assistance with 3 or more Activities of Daily Living &nbsp;·&nbsp; ◻️ Living in the community and not in a residential long-term care institution &nbsp;·&nbsp; ◻️ Residing in Singapore
  - _What would change this: A Singapore citizen relation, qualifying income or home value, and a disability assessment could change this assessment._
- **Interim Disability Assistance Programme for the Elderly** — 🟡 unclear
  - Your age is far below the birth-date window, and the citizenship, income, and disability-assessment details are not provided.
  - Conditions: ◻️ Singapore citizen residing in Singapore &nbsp;·&nbsp; ❌ Born on or before 30 September 1932, or born between 1 October 1932 and 30 September 1962 with pre-existing disability preventing ElderShield entry as of 30 September 2002 &nbsp;·&nbsp; ◻️ Per capita monthly household income is S$3,600 or less, or annual value of home is S$21,000 or less if no income &nbsp;·&nbsp; ◻️ Assessed by an MOH-accredited disability assessor
  - _What would change this: Being much older and having the required citizenship, income, and disability assessment would change this assessment._

Retrieved chunks:

- `Schemes-Terms-Conditions__elderly_text_025`
- `Schemes-Terms-Conditions__elderly_text_005`
- `cpf_mslinfo_booklet_text_017`
- `CHAS_Blue_text_000`
- `Schemes-Terms-Conditions__comcare_text_025`

---

---

Generated from `evaluation/results/{dense,hybrid}_results.json` and `evaluation/test_set.json`. Result files are local-only (gitignored); the hand-labeled test set is committed.
