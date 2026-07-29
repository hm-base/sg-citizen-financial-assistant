Here's what you asked for.

1. The UI design prompt
This is already written in the spec (§6.1) — you can hand this directly to a fresh Claude session/tab to work on the frontend visual design in parallel:

Design a clean, trustworthy web UI for a Singapore government subsidies & tax reliefs assistant, aimed at everyday residents (not developers). Two modes, switchable via a top-level toggle: (1) General Q&A — a single question box, a submit button, a generated-answer area, and a "Sources" panel listing each cited scheme with its section/page, an excerpt, and a thumbnail when the evidence is an image or video frame; (2) Personal Eligibility Shortlist — a short profile form (citizenship, age, household size, income band, housing type, employment status, life-stage tags as checkboxes) plus an optional free-text question, producing a results view with three clearly distinct sections: "Possibly eligible", "Likely not eligible / unclear", and "Not assessed" — each entry shows the scheme name, a plain-language reason, an amount/tier only if the source states one, and a citation. Include a compact "Advanced" panel for top_k, similarity threshold, and a baseline/hybrid retrieval toggle, meant for the team's own demo use rather than end users. Visual tone: SG public-service style — calm, legible, high contrast, no dark patterns, mobile-friendly single column that expands to two columns (question/profile on the left, answer/sources on the right) on wider screens. Avoid anything that looks like it's promising a guaranteed payout — the "Possibly eligible" language and citations must stay visually prominent, not fine print.

Good news: this can run fully in parallel with my backend work — I'll be building frontend/index.html/style.css/app.js in Task 20 anyway, so whatever comes out of that other session can just replace my version later, or I can fold in its design decisions.

2. Where to save your files
Once Task 1 lands (already done), drop files here — no need to wait for me:


data/raw/text/      ← scheme PDFs / HTML pages   (e.g. baby-bonus-scheme.pdf)
data/raw/images/    ← infographics / eligibility tables (e.g. cdc-vouchers.png)
data/raw/video/     ← scheme explainer videos     (e.g. silver-support.mp4)
Naming tip: name each file after its doc_id (lowercase-with-hyphens, matching scheme names in the spec — baby-bonus-scheme, cdc-vouchers, silver-support, comcare-assistance, workfare-income-supplement, gst-voucher, hdb-housing-grants, medisave-medishield-subsidies, cpf-matched-retirement-savings, home-caregiving-grant) — Task 17's ingestion script derives scheme name/doc_id from the filename, so consistent naming now saves relabeling later.

3. What else you can do in parallel
Collect source docs (above) — the biggest unblock, since real evaluation (Task 22's note) is stuck on this.
Get API keys: GEMINI_API_KEY from Google AI Studio, and a Grok key from x.ai if you want that provider too. Drop them in .env (copy from .env.example) — I won't see or need them for the implementation tasks themselves, only when you actually run ingestion/generation.
Fill in data/sources.yaml if you have official URLs instead of downloaded files — Task 7 (fetch module) can pull from that automatically.
Start the frontend-design conversation (above).
I'll hold off on Task 2 until you say go.





++++++++++++++

Done — sample questions are added and pushed (b299c8d): a "Try a sample question" dropdown appears at the top of the General Q&A panel with 12 topics (SkillsFuture/CCP, Baby Bonus, GST Voucher, CDC, CHAS, Silver Support, ComCare, Workfare, HDB Grants, MediSave/MediShield, CPF top-up/MRSS, Home Caregiving Grant), each with 3 clickable starter questions that auto-ask. Just refresh the browser tab (no server restart needed, it's static files) — no server restart needed, no build step.

For your team adding data tomorrow:

Drop files into the right modality folder, in a subfolder named after the topic (the subfolder name drives the profile-matching category, so this matters):

PDFs/HTML → data/raw/text/<topic>/
Infographic images → data/raw/images/<topic>/
Videos → data/raw/video/<topic>/
e.g. Hongming's Baby Bonus PDF → data/raw/text/baby-bonus/baby-bonus-guide.pdf. Folder naming isn't picky, but keep it consistent per topic so all of one scheme's files land together.

Run:


.venv\Scripts\python -m ingestion.build_index
This re-chunks and re-embeds everything from scratch (not incremental) and overwrites data/faiss/. Takes a couple minutes; video files will hit the Gemini API for transcription (cached afterward, so re-running doesn't re-transcribe unchanged videos).

Restart the backend (uvicorn) if it's already running, so it picks up the new index — it loads data/faiss/ once at startup, not live.

Sanity check: ask one of the new sample questions for that topic and confirm it stops abstaining.

One thing to flag to whoever adds folders: the category-to-profile mapping (CATEGORY_BY_FOLDER in ingestion/build_index.py) currently only knows about the ComCare/Elderly folder names we've used so far. If a new topic's folder name isn't in that mapping, it'll fall back to "Uncategorized" (correct RAG answers still work fine, just the Personal Profile re-ranking won't preferentially surface it). Send me the actual folder names your team ends up using and I'll add the mappings.