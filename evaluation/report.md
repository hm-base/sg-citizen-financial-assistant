# Retrieval Evaluation — SG Citizen Financial Assistant

Dense vs. hybrid retrieval, run 2026-07-30 against the Chroma index (385 documents, 1809 chunks).

| | |
|---|---|
| **LLM** | gpt-5.4-mini (OpenAIClient) |
| **Embedding model** | BAAI/bge-m3 |
| **top_k** | 5 |
| **Labeled questions** | 8 / 15 |
| **Query rewrite** | Off (isolates dense vs hybrid retrieval) |
| **Results source** | `evaluation/results/{dense,hybrid}_results.json` (local only, gitignored) |

## The comparison

Computed only over the 8 labeled questions, each against its hand-picked ground-truth chunk(s).

| Metric | Dense (baseline) | Hybrid (improved) | Δ |
|---|---|---|---|
| Hit rate | 25.0% | 37.5% | +12.5% |
| Recall@5 | 18.8% | 31.2% | +12.5% |
| MRR | 0.250 | 0.219 | -0.031 |

### Answer-quality rubric (0–2)

| Rubric | Dense | Hybrid |
|---|---|---|
| Correctness (mean) | 1.27 | 1.40 |
| Faithfulness (mean) | 1.73 | 1.47 |
| Citation accuracy (mean) | 1.80 | 1.80 |

> **Small sample, read directionally.** n = 8 labeled questions and often a single strict ground-truth chunk per question — a top-5 hit on the right *document* but not that exact chunk still counts as a miss. Rubric scores (0=fail, 1=partial, 2=good) were filled by reviewing each generated answer against `expected_answer_criteria`.

## What stood out beyond the numbers

**Hybrid wins coverage; dense wins early rank on this run.** Hit rate and Recall@5 favour hybrid (+12.5 pp each). MRR slightly favours dense (0.250 vs 0.219) — when dense does hit, the labeled chunk tends to appear earlier.

**Hybrid answered F1 (CDC Vouchers); dense abstained.** Hybrid retrieved `CDC_image_000` and stated the $500 amount. Dense fell below the similarity gate with zero chunks.

**Hybrid PR3 invents Singapore Citizenship for a PR profile.** SkillsFuture Credit was marked eligible with reason "You are a Singapore Citizen aged 40" despite `citizenship: PR`. Dense stayed cautious (`not_assessed`). This is a generation/grounding failure, not a retrieval win.

**Paraphrase tax questions (P1/P2) were routed into the personal-shortlist path.** Markers like "my mother" / "working mum" triggered eligibility shortlisting (ComCare / Baby Bonus) instead of IRAS Parent Relief / WMCR answers. Both modes miss the intended tax-relief criteria — partly a corpus gap (no WMCR/Parent Relief docs) and partly classifier routing.

**F2 remains a corpus-gap false-positive risk for hybrid.** Dense abstained (ideal). Hybrid fluently stated the $80,000 cap from CPF top-up relief passages that mention the overall relief ceiling — plausible but not backed by a dedicated personal-reliefs overview doc.

## Per-question detail

Grouped by test category. The hit/miss column applies only to labeled questions; `—` means no ground-truth chunk was labeled.

### Factual

#### **F1** — How much does each eligible Singaporean household get from CDC Vouchers, and where can they be spent?

*Criteria: States the voucher value per household and that they can be spent at participating hawkers/heartland merchants/supermarkets.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ✅ hit
Rubric (C/F/Cit): Dense 0/2/2 · Hybrid 2/2/2

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

Each eligible Singaporean household gets **$500 in CDC Vouchers** in January 2027 [mof_budget2026_statement_sectione, para. 2(c)]. Half can be used at **participating supermarkets**, and the other half at **participating heartland merchants and hawkers** [mof_budget2026_statement_sectione, para. 2(d)].

Retrieved chunks:

- **✓ (expected)** `CDC_image_000`
- `mof_budget2026_statement_sectione_text_006`
- `GST Voucher (GSTV) – MediSave - SupportGoWhere_text_000`
- `moh_pdf_review_committee_2014_text_022`
- `adj_gstv_medisave_2026_text_000`

---

#### **F2** — What is the maximum claimable cap for total personal income tax reliefs?

*Criteria: States the $80,000 overall personal income tax relief cap.*

Dense: — &nbsp;&nbsp; Hybrid: —
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 1/0/1

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

The overall personal income tax relief cap is **$80,000 per year**. [cpf_faq_do_i_get_tax_relief_for_voluntary_top_ups_to_the_med, Full document]

Retrieved chunks:

- `adj_baby_bonus_cda_text_000`
- `iras_cpf_cash_topup_relief_html_text_023`
- `adj_baby_bonus_cda_text_001`
- `Schemes-Terms-Conditions__elderly_text_025`
- `Home Caregiving Grant (HCG) _ AIC__comcare_text_005`
- `cpf_faq_do_i_get_tax_relief_for_voluntary_top_ups_to_the_med_text_000`
- `Schemes-Terms-Conditions__comcare_text_025`
- `Home Caregiving Grant (HCG) _ AIC__elderly_text_005`

---

#### **F3** — What is the Silver Support Scheme payout frequency?

*Criteria: States that payouts are quarterly, and mentions the eligibility tiers by Assessable Income/AV/household support.*

Dense: ✅ hit &nbsp;&nbsp; Hybrid: ✅ hit
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 2/2/2

**Dense (baseline):**

The Silver Support Scheme is paid out every quarter. [adj_silver_support, Full document]

Retrieved chunks:

- **✓ (expected)** `adj_silver_support_text_002`
- `adj_silver_support_text_001`
- `adj_silver_support_text_000`
- `adj_silver_support_text_003`
- `mof_budget2024_annexf1_retirement_system_text_005`

**Hybrid (improved):**

Silver Support is paid out every quarter. [adj_silver_support, Full document]

Retrieved chunks:

- `adj_silver_support_text_003`
- `adj_silver_support_text_001`
- `adj_silver_support_text_000`
- **✓ (expected)** `adj_silver_support_text_002`
- `ElderFund _ AIC_text_008`

---

### Paraphrase

#### **P1** — My mother lives with me and has no job. Can I reduce my tax bill because of her?

*Criteria: Identifies Parent Relief as the relevant relief and states its qualifying conditions (e.g. income/age of dependent, cohabitation).*

Dense: — &nbsp;&nbsp; Hybrid: —
Rubric (C/F/Cit): Dense 0/1/1 · Hybrid 0/1/1

**Dense (baseline):**

- **ComCare Short-to-Medium-Term Assistance** — 🟢 eligible
  - You are a Singapore Citizen who is unemployed and this scheme helps people looking for work or temporarily unable to work.
  - Conditions: ✅ Singapore Citizen or Permanent Resident with at least one immediate family member in the same household a Singapore Citizen &nbsp;·&nbsp; ◻️ Little or no family support, savings or assets to rely on &nbsp;·&nbsp; ✅ Looking for work or temporarily unable to work due to illness or caring duties &nbsp;·&nbsp; ◻️ Monthly household income per capita of $800 and below
  - _What would change this: If you had low per capita household income and limited savings or support, this scheme would be more clearly supported._
- **Home Caregiving Grant** — 🟢 eligible
  - You are a Singapore Citizen and this scheme supports patients who need caregiving help, but the medical assessment details are not provided.
  - Conditions: ✅ Patient is a Singapore Citizen, or a permanent resident with a Singapore Citizen close family member &nbsp;·&nbsp; ◻️ Per capita monthly household income of S$4,800 or less, or no income and annual value of property of S$21,000 or less &nbsp;·&nbsp; ◻️ Assessed by an approved assessor to permanently require some assistance with 3 or more Activities of Daily Living &nbsp;·&nbsp; ◻️ Living in the community and not in a residential long-term care institution &nbsp;·&nbsp; ◻️ Residing in Singapore
  - _What would change this: If the cared-for person had been assessed as needing help with at least three daily activities, this scheme could be assessable._

Retrieved chunks:

- `ComCare Short-to-Medium-Term Assistance (SMTA) - SupportGoWhere_text_000`
- `cpf_mslinfo_booklet_text_017`
- `adj_silver_support_text_001`
- `Schemes-Terms-Conditions__comcare_text_025`
- `moh_pdf_review_committee_2014_text_105`

**Hybrid (improved):**

- **ComCare Short-to-Medium-Term Assistance** — 🟢 eligible
  - You are unemployed and caring for dependants, which matches the temporary assistance and employment support description.
  - Conditions: ✅ Singapore Citizen or Permanent Resident with at least one immediate family member in the same household who is a Singapore Citizen &nbsp;·&nbsp; ◻️ Have little or no family support, savings or assets to rely on for daily needs &nbsp;·&nbsp; ✅ Looking for work or temporarily unable to work due to illness or have to care for children, elderly or other dependants &nbsp;·&nbsp; ◻️ Monthly household income per capita of $800 and below
  - _What would change this: A higher per-capita household income or enough savings and support could change this from likely to less likely._
- **Home Caregiving Grant** — 🟢 eligible
  - Your caregiver role matches the scheme's caregiving context, but the care recipient details needed for eligibility are not provided.
  - Conditions: ◻️ Patient is a citizen of Singapore or a Singapore permanent resident with a living Singapore Citizen parent, child or spouse &nbsp;·&nbsp; ◻️ Per capita monthly household income is S$4,800 or less, or annual value is S$21,000 or less if household has no income &nbsp;·&nbsp; ◻️ Patient permanently requires some assistance with 3 or more Activities of Daily Living &nbsp;·&nbsp; ◻️ Patient lives in the community and not in a residential long-term care institution &nbsp;·&nbsp; ◻️ Patient is residing in Singapore
  - _What would change this: If the cared-for person is a Singapore resident needing help with at least three Activities of Daily Living and living in the community, this assessment could change._
- **Workfare Skills Support Scheme** — 🟢 eligible
  - Your unemployment may make training support relevant, but the age and low-wage work requirements are not provided.
  - Amount: `$6/hr`
  - Conditions: ✅ Are a Singapore Citizen &nbsp;·&nbsp; ◻️ Are at least 30 years old or older as of 31 December of the preceding year &nbsp;·&nbsp; ◻️ Have monthly income of $2,500 and below
  - _What would change this: If you are at least 30 and earned $2,500 or less monthly before unemployment, this scheme would look more applicable._

Retrieved chunks:

- `swda_wss_scheme_text_000`
- `Schemes-Terms-Conditions__elderly_text_025`
- `ssg_sctp_scheme_page_text_002`
- `Home Caregiving Grant (HCG) _ AIC__comcare_text_005`
- `ComCare Short-to-Medium-Term Assistance (SMTA) - SupportGoWhere_text_000`

---

#### **P2** — I'm a working mum with a young kid — is there a tax break for that?

*Criteria: Identifies Working Mother's Child Relief (WMCR) and its qualifying conditions.*

Dense: — &nbsp;&nbsp; Hybrid: —
Rubric (C/F/Cit): Dense 0/1/1 · Hybrid 0/1/1

**Dense (baseline):**

- **Baby Bonus Scheme** — ⚪ not_assessed
  - You have young child(ren), and this scheme supports parents of Singapore citizen children.
  - Amount: `$20,000`
  - _What would change this: A child’s birth order and birth date would change the payout tier._
- **SkillsFuture Credit** — 🟢 eligible
  - You are a Singapore Citizen and the scheme covers citizens aged 25 and above, but your age is not provided.
  - Amount: `$500`
  - Conditions: ✅ Singapore Citizen &nbsp;·&nbsp; ◻️ Aged 25 and above
  - _What would change this: If you are 25 or older, the credit tier becomes available._

Retrieved chunks:

- `Schemes-Terms-Conditions__comcare_text_025`
- `adj_baby_bonus_cda_text_000`
- `cpf_mslinfo_booklet_text_017`
- `ssg_skillsfuture_credit_amounts_image_000`
- `adj_silver_support_text_001`

**Hybrid (improved):**

- **Baby Bonus Scheme** — 🟢 eligible
  - Your profile includes young child(ren), which matches the family support scheme for parents with children.
  - Amount: `$20,000`
  - Conditions: ◻️ Parent has a child enrolled in the scheme &nbsp;·&nbsp; ◻️ Child is a Singapore Citizen born on or after 14 February 2023 for the stated amounts
  - _What would change this: A child’s birth date and enrolment status would determine whether the stated Baby Bonus amount applies._
- **Child LifeSG Credits** — 🟢 eligible
  - Your profile includes young child(ren), matching the support for Singapore Citizen children aged 0 to 12.
  - Amount: `$500`
  - Conditions: ◻️ Child is a Singapore Citizen aged 0 to 12
  - _What would change this: A child’s age and citizenship would change whether these credits apply._

Retrieved chunks:

- `adj_baby_bonus_cda_text_000`
- `Child LifeSG Credits - SupportGoWhere_text_000`
- `adj_silver_support_text_001`
- `cpf_mrss_canonical_text_001`
- `Schemes-Terms-Conditions__comcare_text_025`

---

#### **P3** — I put extra money into my CPF for retirement — do I get anything back on tax?

*Criteria: Identifies CPF top-up / SRS-related relief and its qualifying conditions.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss
Rubric (C/F/Cit): Dense 2/1/2 · Hybrid 2/1/2

**Dense (baseline):**

Yes, you may get CPF Cash Top-up Relief on eligible cash top-ups for retirement savings. You can receive up to $8,000 tax relief when you make a cash top-up to yourself, and up to another $8,000 when you make a cash top-up to eligible loved ones in each calendar year. [cpf_rstu_topup, Full document]

The relief is automatic if you are eligible, so you do not need to claim it. [iras_cpf_cash_topup_relief_html, Full document]

But there are limits: the tax relief depends on the recipient’s age and CPF balances, and if the recipient’s CPF savings have already reached the Full Retirement Sum, no tax relief is given for the cash top-up. [cpf_rstu_topup, Full document] [iras_cpf_cash_topup_relief_html, Full document]

Retrieved chunks:

- `cpf_rstu_topup_text_001`
- `iras_cpf_cash_topup_relief_html_text_022`
- `cpf_reaching_55_text_001`
- `cpf_faq_can_i_continue_to_use_my_cpf_savings_for_the_propert_text_000`
- `iras_cpf_cash_topup_relief_html_text_023`

**Hybrid (improved):**

Yes, if the cash top-up was made to your own CPF retirement account, you may get up to $8,000 tax relief for top-ups to yourself in each calendar year. If you top up certain loved ones’ accounts, you may get up to another $8,000 tax relief in the same year. [cpf_rstu_topup, Full document]

Tax relief only applies to the giver, not the recipient. The amount that qualifies depends on the recipient’s age and CPF balances, and cash top-ups that exceed the tax-relief limit do not get relief. [cpf_rstu_topup, Full document; iras_cpf_cash_topup_relief_html, Full document]

You do not need to claim this relief; it is granted automatically if you are eligible. [iras_cpf_cash_topup_relief_html, Full document]

Retrieved chunks:

- `cpf_rstu_topup_text_001`
- `adj_retirement_sum_scheme_text_002`
- `iras_cpf_cash_topup_relief_html_text_022`
- `Home Caregiving Grant (HCG) _ AIC__elderly_text_007`
- `cpf_reaching_55_text_001`

---

### Multi-document

#### **M1** — What financial support (cash payouts and tax savings) can a working mother with a young child get from the government?

*Criteria: Combines Assurance Package/GST Voucher cash payouts with Working Mother's Child Relief and Child Relief, citing both a Govbenefits-style scheme doc and the IRAS reliefs doc.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss
Rubric (C/F/Cit): Dense 1/1/2 · Hybrid 1/1/2

**Dense (baseline):**

- **Baby Bonus Scheme** — 🟢 eligible
  - You have young children, but the passage gives no child birth details to confirm eligibility.
  - Amount: `$20,000`
  - Conditions: ◻️ Singapore citizen child born on or after 14 February 2023
  - _What would change this: A confirmed Singapore citizen child born on or after 14 February 2023 would make this scheme assessable._
- **SkillsFuture Credit** — 🟢 eligible
  - You are a Singapore Citizen, and the scheme is available from age 25, which your profile does not confirm.
  - Amount: `$500`
  - Conditions: ◻️ Singapore Citizens aged 25 and above &nbsp;·&nbsp; ◻️ Singapore Citizens aged 40 and above
  - _What would change this: If you are at least 25 years old, the base credit amount becomes assessable._

Retrieved chunks:

- `Schemes-Terms-Conditions__comcare_text_025`
- `adj_baby_bonus_cda_text_000`
- `cpf_mslinfo_booklet_text_017`
- `ssg_skillsfuture_credit_amounts_image_000`
- `adj_silver_support_text_001`

**Hybrid (improved):**

- **Baby Bonus Scheme** — 🟢 eligible
  - You are a Singapore Citizen with young child(ren), which matches the family support scheme for children.
  - Amount: `$20,000`
  - Conditions: ◻️ Child is a Singapore citizen born on or after 14 February 2023 &nbsp;·&nbsp; ◻️ First child
  - _What would change this: If your child is a Singapore citizen born on or after 14 February 2023, the scheme details would be assessable._
- **Child LifeSG Credits** — 🟢 eligible
  - You are a Singapore Citizen with child(ren), which matches the broad family support scheme for children aged 0 to 12.
  - Amount: `$500`
  - Conditions: ◻️ Child is a Singapore Citizen aged 0 to 12
  - _What would change this: If your child is a Singapore citizen aged 0 to 12 in the relevant year, the credits would apply._

Retrieved chunks:

- `adj_baby_bonus_cda_text_000`
- `Child LifeSG Credits - SupportGoWhere_text_000`
- `adj_silver_support_text_001`
- `cpf_mrss_canonical_text_001`
- `Schemes-Terms-Conditions__comcare_text_025`

---

#### **M2** — What can a low-income retired senior living in a rental flat get from the government?

*Criteria: Combines Silver Support Scheme and ComCare Assistance, citing both scheme docs.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss
Rubric (C/F/Cit): Dense 0/2/2 · Hybrid 1/1/2

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

A low-income retired senior living in a rental flat may be relevant to ComLink+ support, because MSF aims to support families living in public rental housing that have agreed to work with them [supporting-lower-income-households-trends-report-2024, pp.23-24]. Family coaches may help with immediate needs such as access to food and healthcare, and can refer families to ComCare SMTA, MUIS Zakat financial assistance, subsidised antenatal care, e2i, and KidSTART where relevant [supporting-lower-income-households-trends-report-2024, pp.23-24].  

If the senior wants to right-size their HDB flat, the Silver Housing Bonus may also be relevant for eligible seniors aged 55 and above who commit cash to their CPF Retirement Account after right-sizing; the maximum SHB amount can be up to $40,000, or $20,000 / $10,000 in some cases depending on the next flat type and property value [hdb_silver_housing_bonus, Full document].  

For seniors aged 55 and above, CPF housing refunds from selling a property are first refunded to the RA up to the member’s cohort Full Retirement Sum, and any balance remains in the Ordinary Account [hdb_pr_2025_shb_enhancements, Full document].

Retrieved chunks:

- `hdb_pr_2025_shb_enhancements_text_004`
- `supporting-lower-income-households-trends-report-2024_text_016`
- `hdb_silver_housing_bonus_text_002`
- `supporting-lower-income-households-trends-report-2024_text_022`
- `hdb_seniors_eligibility_text_000`

---

### Unanswerable

#### **U1** — Can I use my CDC vouchers to pay for my IRAS income tax bill?

*Criteria: Must trigger the exact fallback: "The available knowledge base does not contain enough information to answer this question."*

Dense: — &nbsp;&nbsp; Hybrid: —
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 2/2/2

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
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 2/2/2

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
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 2/2/2

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
Rubric (C/F/Cit): Dense 1/2/2 · Hybrid 2/2/2

**Dense (baseline):**

_Abstained — no answer generated._

Retrieved chunks:

_(none retrieved — below similarity threshold)_

**Hybrid (improved):**

You may be eligible for Workfare Income Supplement if you are a Singapore Citizen, are at least 30 years old as of 31 December of the work year (or a person with disabilities of any age), earn a gross monthly income of at least $500 and not more than $3,000, earn an average gross monthly income of not more than $3,000 over the past 12 months, live in a property with annual value of $21,000 and below, own not more than one property, and if married, you and your spouse together own not more than one property and your spouse’s assessable income does not exceed $70,000. [adj_workfare_income_supplement, Full document]

If you are a person with disabilities, a worker who qualifies for ComCare Short-to-Medium-Term Assistance, or a caregiver of a care recipient, you may qualify for concessionary WIS even if you earn less than $500. [adj_workfare_income_supplement, Full document]

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
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 2/2/2

**Dense (baseline):**

- **Silver Support Scheme** — 🟢 eligible
  - You match the age, citizenship, housing type, and low income profile, but your lifetime CPF contributions and household income per capita are not checked.
  - Conditions: ✅ Singapore Citizen aged 65 and above &nbsp;·&nbsp; ◻️ Low lifetime wages &nbsp;·&nbsp; ✅ Lives in a 1- to 5-room HDB flat &nbsp;·&nbsp; ◻️ You or your spouse do not own a 5-room or larger HDB flat, private property or multiple properties &nbsp;·&nbsp; ◻️ Per capita household income of up to $2,300
  - _What would change this: If your CPF contributions were above $140,000 or your household income per person exceeded $2,300, this scheme would no longer fit._
- **Premium Subsidies** — 🟢 eligible
  - You match the citizenship, income, and residence profile, but the residence annual value and property count are not checked.
  - Conditions: ✅ Singapore Citizen or Permanent Resident &nbsp;·&nbsp; ✅ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in a residence with an Annual Value of $31,000 and below &nbsp;·&nbsp; ◻️ Owns not more than one property
  - _What would change this: If your home annual value were above $31,000 or you owned more than one property, this subsidy would not apply._
- **Matched Retirement Savings Scheme** — 🟢 eligible
  - You match the citizenship, Singapore residence, age, and income profile, but retirement savings, annual value, and property ownership are not checked.
  - Conditions: ✅ Singapore Citizen only &nbsp;·&nbsp; ✅ Reside in Singapore &nbsp;·&nbsp; ✅ Age 55 or above as of 31st December of the year, or below 55 years old with disability status verified with the Ministry of Social and Family Development &nbsp;·&nbsp; ◻️ Retirement Account savings or Ordinary and Special Account savings less than $110,200 &nbsp;·&nbsp; ✅ Average monthly income not more than $4,000 &nbsp;·&nbsp; ◻️ Annual Value of Residence not more than $21,000 &nbsp;·&nbsp; ◻️ Own not more than one property
  - _What would change this: If your retirement savings were at least $110,200 or you owned more than one property, this scheme would not fit._

Retrieved chunks:

- **✓ (expected)** `adj_silver_support_text_001`
- `cpf_mslinfo_booklet_text_017`
- `cpf_faq_mrss_eligibility_text_000`
- `moh_pdf_council_report_2020_text_046`
- `moh_pdf_review_committee_2014_text_105`

**Hybrid (improved):**

- **Silver Support Scheme** — 🟢 eligible
  - You are a Singapore Citizen aged 68 living in an HDB flat and your income band suggests lower means.
  - Amount: `$430 per quarter`
  - Conditions: ✅ Singapore Citizen aged 65 and above &nbsp;·&nbsp; ◻️ Low lifetime wages: total CPF contributions by age 55 up to $140,000, or self-employed/platform worker average annual net trade income age 45 to 54 up to $27,600 &nbsp;·&nbsp; ◻️ Live in a 1- to 5-room HDB flat &nbsp;·&nbsp; ◻️ You or your spouse do not own a 5-room or larger HDB flat, private property or multiple properties &nbsp;·&nbsp; ◻️ Per capita household income up to $2,300
  - _What would change this: If your flat size, property ownership, or lifetime wage history differed, your Silver Support assessment could change._
- **Premium Subsidies** — 🟡 unclear
  - You are a Singapore Citizen living in an HDB residence and your income band is within the low-income range.
  - Conditions: ✅ Singapore Citizen or Permanent Resident &nbsp;·&nbsp; ◻️ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in a residence with Annual Value of $31,000 and below &nbsp;·&nbsp; ❌ Own more than one property
  - _What would change this: If you owned more than one property, or your residence annual value or income per person were higher, this assessment could change._
- **Matched Retirement Savings Scheme** — 🟢 eligible
  - You are 68, so you meet the age condition for this Singapore Citizen-only retirement matching scheme.
  - Conditions: ✅ Singapore Citizen only &nbsp;·&nbsp; ◻️ Reside in Singapore &nbsp;·&nbsp; ✅ Age 55 or above as of 31 December, or below 55 with disability status verified by Ministry of Social and Family Development &nbsp;·&nbsp; ◻️ Retirement Account savings less than $110,200, or Ordinary and Special Account savings if not yet 55 &nbsp;·&nbsp; ◻️ Average monthly income not more than $4,000 &nbsp;·&nbsp; ◻️ Annual Value of residence not more than $21,000 &nbsp;·&nbsp; ◻️ Own not more than one property
  - _What would change this: If your retirement savings, residence annual value, income, or property ownership were different, your MRSS assessment could change._

Retrieved chunks:

- `moh_pr_2025_keeping_healthcare_affordable_sustainable_text_008`
- **✓ (expected)** `adj_silver_support_text_001`
- `cpf_mslinfo_booklet_text_017`
- `cpf_faq_mrss_eligibility_text_000`
- `moh_pdf_review_committee_2014_text_118`

---

#### **PR2** — profile: Singapore Citizen, age 32, $3-6k, HDB, Employed, tags: Has young child(ren)

*Criteria: Shortlist should surface Baby Bonus / family-oriented schemes as 'Possibly eligible' and not assert senior schemes as eligible.*

Dense: ❌ miss &nbsp;&nbsp; Hybrid: ❌ miss
Rubric (C/F/Cit): Dense 2/2/2 · Hybrid 2/2/2

**Dense (baseline):**

- **Baby Bonus Scheme** — ⚪ not_assessed
  - You are a Singapore Citizen with young children, matching the child-focused scheme for Singapore citizen children born on or after 14 February 2023.
  - Amount: `$20,000`
  - _What would change this: A different child birth date or citizenship status would change this scheme's assessment._
- **SkillsFuture Credit** — 🟢 eligible
  - You are a Singapore Citizen aged 32, which meets the age threshold for the base SkillsFuture Credit.
  - Amount: `$500`
  - Conditions: ✅ Singapore Citizen aged 25 and above
  - _What would change this: Being below age 25 would make this scheme inapplicable._

Retrieved chunks:

- `Schemes-Terms-Conditions__comcare_text_025`
- `adj_baby_bonus_cda_text_000`
- `Student Care Fee Assistance (SCFA) - SupportGoWhere_text_001`
- `ssg_skillsfuture_credit_amounts_image_000`
- `adj_silver_support_text_001`

**Hybrid (improved):**

- **Baby Bonus Scheme** — 🟢 eligible
  - Your profile includes a young child, and this scheme is for Singapore citizen children born on or after 14 February 2023.
  - Amount: `$20,000`
  - Conditions: ◻️ Child is a Singapore citizen born on or after 14 February 2023 &nbsp;·&nbsp; ◻️ Child is first child &nbsp;·&nbsp; ◻️ Child is second child &nbsp;·&nbsp; ◻️ Child is third or fourth child &nbsp;·&nbsp; ◻️ Child is fifth or subsequent child
  - _What would change this: If your child is not a Singapore citizen born from 14 February 2023 onward, this scheme would not apply._
- **Child LifeSG Credits** — 🟢 eligible
  - You have a young child and this scheme provides Singapore Citizen children aged 0 to 12 with credits.
  - Amount: `$500`
  - Conditions: ◻️ Child is a Singapore Citizen aged 0 to 12 &nbsp;·&nbsp; ◻️ Disbursed to the eligible child's CDA trustee via the LifeSG mobile app &nbsp;·&nbsp; ✅ No application needed
  - _What would change this: If your child is not a Singapore Citizen aged 0 to 12, the credits would not be available._
- **SkillsFuture Credit** — 🟢 eligible
  - You are 32, so you meet the age threshold for the $500 SkillsFuture Credit base tier.
  - Amount: `$500`
  - Conditions: ✅ Singapore Citizen aged 25 and above
  - _What would change this: If you were under 25 or not a Singapore Citizen, you would not meet the base tier._

Retrieved chunks:

- `adj_baby_bonus_cda_text_000`
- `ssg_skillsfuture_credit_amounts_image_000`
- `Child LifeSG Credits - SupportGoWhere_text_000`
- `moh_pr_2025_keeping_healthcare_affordable_sustainable_text_008`
- `cpf_mrss_canonical_text_001`

---

#### **PR3** — profile: PR, age 40, Prefer not to say, Private, Employed, tags: none

*Criteria: Heavy 'Likely not eligible / unclear' due to PR status and undisclosed income on citizen-only/income-gated schemes.*

Dense: — &nbsp;&nbsp; Hybrid: —
Rubric (C/F/Cit): Dense 1/2/1 · Hybrid 0/1/2

**Dense (baseline):**

- **Schemes-Terms-Conditions** — ⚪ not_assessed
  - This scheme appeared in retrieved documents for your profile, but the assistant could not finish a condition-by-condition check.
  - _What would change this: Ask again, or open the cited source for the published criteria._
- **ssg_skillsfuture_credit_amounts** — ⚪ not_assessed
  - This scheme appeared in retrieved documents for your profile, but the assistant could not finish a condition-by-condition check.
  - _What would change this: Ask again, or open the cited source for the published criteria._
- **cpf_mslinfo_booklet** — ⚪ not_assessed
  - This scheme appeared in retrieved documents for your profile, but the assistant could not finish a condition-by-condition check.
  - _What would change this: Ask again, or open the cited source for the published criteria._
- **moh_pdf_council_report_2020** — ⚪ not_assessed
  - This scheme appeared in retrieved documents for your profile, but the assistant could not finish a condition-by-condition check.
  - _What would change this: Ask again, or open the cited source for the published criteria._
- **adj_silver_support** — ⚪ not_assessed
  - This scheme appeared in retrieved documents for your profile, but the assistant could not finish a condition-by-condition check.
  - _What would change this: Ask again, or open the cited source for the published criteria._

Retrieved chunks:

- `Schemes-Terms-Conditions__comcare_text_025`
- `ssg_skillsfuture_credit_amounts_image_000`
- `cpf_mslinfo_booklet_text_017`
- `moh_pdf_council_report_2020_text_046`
- `adj_silver_support_text_001`

**Hybrid (improved):**

- **SkillsFuture Credit** — 🟢 eligible
  - You are a Singapore Citizen aged 40, which meets the opening SkillsFuture Credit age requirement.
  - Amount: `$4,000`
  - Conditions: ✅ Singapore Citizen aged 40 and above
  - _What would change this: If you were not a Singapore Citizen or were under 40, this credit would not apply._
- **MediShield Life Premium Subsidies** — 🟢 eligible
  - You are a Permanent Resident aged 40, and the scheme covers Permanent Residents with household monthly income per person at $3,600 and below.
  - Conditions: ✅ Singapore Citizen or Permanent Resident &nbsp;·&nbsp; ◻️ Household monthly income per person of $3,600 and below &nbsp;·&nbsp; ◻️ Living in a residence with annual value of $31,000 and below &nbsp;·&nbsp; ◻️ Own more than one property
  - _What would change this: A household income above $3,600 per person, a home above $31,000 annual value, or multiple properties would change the result._

Retrieved chunks:

- `adj_silver_support_text_001`
- `Schemes-Terms-Conditions__comcare_text_025`
- `ssg_skillsfuture_credit_amounts_image_000`
- `moh_pr_2025_keeping_healthcare_affordable_sustainable_text_008`
- `cpf_mslinfo_booklet_text_017`

---


Generated from `evaluation/results/{dense,hybrid}_results.json` and `evaluation/test_set.json`. Result files are local-only (gitignored); the hand-labeled test set is committed. Rubric columns in the CSV/JSON were filled during this run.
