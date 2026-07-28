💡 How to Structure the Domain
Your Knowledge Base will cover two main pillars that every adult in Singapore deals with:
 
Plain Text
                  ┌─────────────────────────────────────────────────┐
                  │ SG Citizen Financial & Tax Assistant (Knowledge)│
                  └────────────────────────┬────────────────────────┘
                                           │
             ┌─────────────────────────────┴─────────────────────────────┐
             ▼                                                           ▼
  Pillar 1: Government Cash Payouts & Schemes             Pillar 2: Income Tax & Reliefs (IRAS)
  • Assurance Package Cash / GST Vouchers                 • Personal Income Tax Reliefs (Earned Income, SRS, CPF)
  • CDC Vouchers (Claiming & Spending Rules)               • Family & Caregiver Reliefs (Parent, Child, Caregiver)
  • U-Save & S&CC Rebates                                 • Working Mother's Child Relief (WMCR)
 
📁 Where to Get the Data (All Public PDFs & Images)
You can easily collect all data from official .gov.sg websites without writing scrapers:  
1. Government Cash Payouts & Schemes
Text Source: Download the official scheme guides and FAQs from Govbenefits.gov.sg (Assurance Package, GST Voucher FAQs).
Image/Infographic Source: Download infographic graphics from vouchers.cdc.gov.sg showing:
CDC Voucher claim flowcharts (Step-by-step Singpass flow).
Eligibility tables for Assurance Package Cash payouts (grouped by Assessable Income & Annual Value of home).
2. IRAS Personal Income Tax & Reliefs
Text Source: Download the Individual Income Tax Reliefs Guide PDF and Tax Resident FAQs from IRAS.gov.sg.
Image/Infographic Source: Save the official IRAS decision flowcharts and summary tables:
Tax Savings at a Glance Infographic (Visual breakdown of all 13 tax reliefs).
Parent Relief / Course Fees Relief Eligibility Decision Tree Flowcharts.
🎯 Sample 10-Question Test Set (To Hit Rubric Requirements)
Here is how you can directly build your required 10 evaluation test questions across both topics:  
 
Question Type  PDF	Example Test Question	Source Document Needed

Factual
  
	"How much CDC Voucher amount does each Singaporean household get, and where can it be spent?"	CDC Voucher Guide + Infographic Diagram

Factual
  
	"What is the maximum claimable cap for total personal income tax reliefs?"	IRAS Tax Reliefs Overview PDF ($80,000 cap)

Semantic / Paraphrase
  
	"My mother lives with me and has no job. Can I reduce my tax bill because of her?"	IRAS Parent Relief Section

Multi-Document Retrieval
  
	"What financial support (cash payouts and tax savings) can a working mother with a young child get from the government?"	Govbenefits (AP Cash) + IRAS (WMCR & Child Relief)

Unanswerable (Abstention)
  
	"Can I use my CDC vouchers to pay for my IRAS income tax bill?"	
Must trigger: "The available knowledge base does not contain enough information..."
  


Unanswerable (Abstention)
  
	"Can I claim tax relief for taking care of my pet dog?"	
Must trigger: "The available knowledge base does not contain enough information..."
  


Ambiguous / Difficult
  
	"How much money will I get from the government this year?"	Tests how agent handles missing info (Needs age, income, property AV).
-------------
 
This SG Govt Cash Payouts + Tax Reliefs Assistant is practically tailor-made for the rubric. It isn't just a solid idea; it systematically checks off every single requirement for high marks.
Here is a breakdown of how this project fares against each evaluation criterion in your rubric:  
📊 Rubric Alignment Breakdown
1. Technical Implementation & System Requirements (40% Weight)
Multi-Modal Data Requirement (2+ Modalities): 10/10
Modality 1 (Text): Policy PDFs, FAQs, and eligibility guides from IRAS and Govbenefits.  
Modality 2 (Images/Tables): Flowcharts (e.g., CDC voucher claim flows, Parent Relief decision trees) and visual payout tables (Assurance Package tiers by Assessable Income).  
Data Processing & Metadata: 10/10
You can easily tag metadata like scheme_type: tax_relief, target_group: parents, or source_agency: iras. This makes chunking and metadata filtering natural to justify in your report.  
Strict Grounding & Abstention: 10/10
Government policies have zero room for hallucination. Testing unanswerable questions (e.g., "Can I use CDC vouchers for tax bills?") allows you to easily demonstrate the required fallback response: "The available knowledge base does not contain enough information..."  
Sources & Transparency: 10/10
Govt documents have clear section names (e.g., IRAS Working Mother's Child Relief Section 3) and diagram names (assurance_package_table.png), making exact citations seamless to display.  
2. Required Improvement Experiment (Core Section of Project)
This domain makes it effortless to design a compelling Baseline vs. Improved experiment:  
Pipeline Stage	Baseline Approach	Improved Version	Why It Improves Results
Chunking / Retrieval	
Standard fixed-size chunking (250 tokens) + Vector Search.  
	
Metadata Filtering + Hybrid Search (BM25 + Dense Vectors).  
	
Standard vector search often gets confused by numerical payout tables and income thresholds. BM25 + Metadata ensures exact match on dollar amounts and eligibility criteria.  

Reranking / Prompting	
Basic Top-K retrieval directly fed to LLM.  
	
Cross-Encoder Reranker or Query Rewriting.  
	
Filters out irrelevant tax categories before generating the final answer, reducing noise.  
3. Report & Technical Quality (20% Weight)
Clear Domain Scope: Public sector schemes are well-defined, eliminating ambiguity around why the domain was selected.  
10-Question Test Set: Easily covers all required question types (factual, semantic paraphrase, multi-document synthesis, and unanswerable/abstention).  
Evaluation Metrics: You can cleanly compute Hit Rate, MRR (Mean Reciprocal Rank), and Faithfulness/Correctness scores across your test set.  
4. Presentation & Live Demonstration (40% Weight)
  
High Engagement & Relatability: Examiners and peers immediately understand Singapore cash payouts (Assurance Package, CDC vouchers) and tax reliefs.
Visual Presentation Impact: During your 3-minute live demo, asking a complex query (e.g., "What payouts and tax savings am I eligible for as a middle-income parent?") and seeing the agent return a grounded answer along with the official IRAS flowchart image will be visually impressive.  
🎯 Final Verdict
Score Potential: Excellent / Top Tier
This topic strikes the sweet spot:
Not too large: You only need 4–6 core PDFs/infographics to build a rich knowledge base.  
Highly structured: Policy logic and visual decision trees map directly into multimodal RAG architectures.  
Presents well: It solves an authentic, practical problem that everyone in Singapore recognizes immediately.  
--------------
📢 Proposal: SG Citizen Financial Schemes & Tax Relief Assistant (Multimodal RAG)
Hey team! Here’s a proposal for our RAG Agent mini-project. It solves a real-world Singapore public use case, uses 2+ data modalities, and hits all the technical requirements in the project rubric.
💡 Project Overview
Domain: Public Sector Financial Guidance (Singapore Govt Schemes + Tax Reliefs)  
Target Audience: Everyday Singapore citizens navigating government cash payouts, vouchers, and income tax deductions.  
Core Function: An intelligent assistant that answers queries strictly using official government documents and outputs both textual policy explanations and visual source citations (infographics/flowcharts).  
📁 Knowledge Base & Modalities (Small, Public, & Clean)
We don't need a massive dataset—just 4 to 6 official public .gov.sg sources:  
Text Modality:
Govbenefits FAQs (Assurance Package cash, GST Vouchers, CDC Vouchers).  
IRAS Individual Income Tax Reliefs PDFs (CPF top-ups, Parent Relief, Working Mother's Child Relief).  
Image / Diagram Modality:
CDC voucher claim process flowcharts.  
IRAS Tax Relief eligibility decision trees & visual summary charts (iras_tax_savings_at_a_glance.png).  
Assurance Package payout tier summary tables.  
🛠️ Architecture & Tech Stack (Runs in Free Google Colab)
Ingestion: Parse PDFs with pypdf/pdfplumber for text and save infographic graphics.  
Embeddings & Vector Store: Open-source CLIP or Sentence-Transformers stored in ChromaDB (lightweight, runs in memory).  
LLM Engine: Google Gemini 1.5 Flash API (free tier) for grounded generation.  
🧪 Baseline vs. Required Improvement Experiment
Baseline Pipeline: Standard fixed-size text chunking + basic vector similarity retrieval.  
Improved Pipeline: Metadata Filtering (e.g., tagging chunks with agency: iras or scheme: cdc) + BM25 Hybrid Search.  
Why: Vector search alone often struggles with exact dollar limits and eligibility thresholds; adding BM25 + metadata ensures precision on figures and rules.  
🎯 Why This Hits Evaluation Metrics (Rubric Checklist)
✅ Multi-Modal (40% Weight): Seamlessly pairs policy text with step-by-step visual diagrams.  
✅ Strict Abstention Testing: Easy to test questions out of scope (e.g., "Can I claim tax relief for my pet?") to trigger the required fallback response: "The available knowledge base does not contain enough information..."
✅ Clear Citations: Shows exact document section and page/diagram identifiers.  
✅ Live Demo (40% Weight): High visual impact when querying complex rules (e.g., "What cash payouts and tax savings am I eligible for as a middle-income parent?") and returning a cited response + visual flowchart.  
👥 Work Allocation Plan (4 Core Roles)
Data & Ingestion: Collect PDFs/infographics, clean text, set up chunking & metadata tagging.  
Retrieval & Pipeline: Build ChromaDB index, embeddings, and BM25 hybrid search.  
Generation & UI: Write system prompts, ground answers with Gemini Flash, handle fallback logic & citations.  
Evaluation & Report: Draft the 10-question test set, compute retrieval metrics (Hit Rate/MRR), run failure analysis.