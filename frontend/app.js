const state = { mode: "general" };

const THEME_STORAGE_KEY = "sg-financial-assistant-theme";
const themeToggleButton = document.getElementById("theme-toggle-button");
// "midnight-luxury" (dark) and "warm-earth" (light) are the two approved
// design themes; the button always names the theme a click will switch TO.
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  themeToggleButton.textContent = theme === "midnight-luxury" ? "Warm earth theme" : "Midnight theme";
}

function initTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "warm-earth" || stored === "midnight-luxury") {
    applyTheme(stored);
    return;
  }
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark ? "midnight-luxury" : "warm-earth");
}

themeToggleButton.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") === "midnight-luxury" ? "midnight-luxury" : "warm-earth";
  const next = current === "midnight-luxury" ? "warm-earth" : "midnight-luxury";
  applyTheme(next);
  localStorage.setItem(THEME_STORAGE_KEY, next);
});

initTheme();

const generalPanel = document.getElementById("general-panel");
const profilePanel = document.getElementById("profile-panel");
const modeButtons = document.querySelectorAll(".mode-btn");

function setMode(mode) {
  modeButtons.forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
    b.setAttribute("aria-selected", String(b.dataset.mode === mode));
  });
  state.mode = mode;
  generalPanel.classList.toggle("hidden", mode !== "general");
  profilePanel.classList.toggle("hidden", mode !== "profile");
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

const advancedToggleButton = document.getElementById("advanced-toggle-button");
const advancedBand = document.getElementById("advanced-band");
const ADVANCED_OPEN_STORAGE_KEY = "sg-financial-assistant-advanced-open";

// Always closed on load -- a demo reload must return to the resident view,
// never resume showing top_k/chunk_id/raw diagnostics. sessionStorage still
// records the in-session toggle state (not localStorage, so it never
// survives past this browser tab), but that stored value is deliberately
// never read back to auto-open the panel at startup.
sessionStorage.setItem(ADVANCED_OPEN_STORAGE_KEY, "false");

advancedToggleButton.addEventListener("click", () => {
  const isOpen = advancedBand.classList.toggle("hidden") === false;
  advancedToggleButton.setAttribute("aria-expanded", String(isOpen));
  sessionStorage.setItem(ADVANCED_OPEN_STORAGE_KEY, String(isOpen));
});

// Curated per-topic FAQ starters for the demo. Purely a UI convenience — each
// button just fills the question box and asks like any manually typed
// question; topics whose source documents haven't been ingested yet will
// correctly abstain rather than hallucinate.
const SAMPLE_QUESTIONS = {
  "SkillsFuture / Career Conversion": [
    "What is SkillsFuture Credit and how much do I get?",
    "How does the Career Conversion Programme (CCP) help mid-career switchers?",
    "Am I eligible for the AI Apprenticeship Programme (AIAP) or SNAIC training support?",
  ],
  "Baby Bonus": [
    "How much cash gift do I get from the Baby Bonus Scheme for my first child?",
    "What is the Child Development Account (CDA) first step grant?",
    "How does government co-matching work for the Baby Bonus CDA?",
  ],
  "GST Voucher": [
    "How much GST Voucher Cash will I receive this year?",
    "What is GST Voucher U-Save and how is it credited to my utilities bill?",
    "Who qualifies for GST Voucher MediSave top-ups?",
  ],
  "CDC Vouchers": [
    "How much CDC Voucher will my household receive?",
    "Where can I spend my CDC Vouchers?",
    "When do CDC Vouchers expire?",
  ],
  "CHAS": [
    "What is CHAS and what card tier am I eligible for?",
    "How much subsidy does CHAS Blue give for chronic condition treatment?",
    "Can Merdeka Generation seniors use CHAS subsidies at GP clinics?",
  ],
  "Silver Support Scheme": [
    "Am I eligible for the Silver Support Scheme?",
    "How much quarterly payout does Silver Support give?",
    "How is Silver Support eligibility determined?",
  ],
  "ComCare": [
    "What is the monthly cash assistance rate for ComCare Long-Term Assistance?",
    "What is ComCare Short-to-Medium Term Assistance (SMTA) for?",
    "How do I apply for ComCare financial assistance?",
  ],
  "Workfare Income Supplement": [
    "How much can I receive from Workfare Income Supplement (WIS) per year?",
    "Am I eligible for Workfare Income Supplement as a self-employed person?",
    "How is the WIS payout split between cash and CPF?",
  ],
  "HDB Grants": [
    "How much is the Enhanced CPF Housing Grant for a resale flat?",
    "What HDB grants can first-timer families get?",
    "Am I eligible for the Proximity Housing Grant?",
  ],
  "MediSave / MediShield Life": [
    "What does MediShield Life cover?",
    "How much can I withdraw from MediSave for hospitalisation bills?",
    "What is the MediShield Life premium subsidy for lower-income Singaporeans?",
  ],
  "CPF Top-Up / Matched Retirement Savings": [
    "How does the Matched Retirement Savings Scheme (MRSS) government matching work?",
    "What are the tax relief benefits of topping up my CPF Retirement Account?",
    "Who is eligible for the Matched Retirement Savings Scheme?",
  ],
  "Home Caregiving Grant": [
    "How much is the Home Caregiving Grant (HCG) per month?",
    "Who qualifies for the Home Caregiving Grant?",
    "Can I use the Home Caregiving Grant together with the Foreign Domestic Worker Levy concession?",
  ],
};

const sampleTopicSelect = document.getElementById("sample-topic-select");
const sampleQuestionButtons = document.getElementById("sample-question-buttons");
const questionInput = document.getElementById("question-input");
const askButton = document.getElementById("ask-button");

function renderSampleQuestions(topic) {
  sampleQuestionButtons.innerHTML = "";
  (SAMPLE_QUESTIONS[topic] || []).forEach((question) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sample-question-btn";
    button.textContent = question;
    button.addEventListener("click", () => {
      questionInput.value = question;
      submitQuery(askButton, "Asking...", "/api/query", { question, ...readControls() });
    });
    sampleQuestionButtons.appendChild(button);
  });
}

Object.keys(SAMPLE_QUESTIONS).forEach((topic) => {
  const option = document.createElement("option");
  option.value = topic;
  option.textContent = topic;
  sampleTopicSelect.appendChild(option);
});
sampleTopicSelect.addEventListener("change", () => renderSampleQuestions(sampleTopicSelect.value));
renderSampleQuestions(sampleTopicSelect.value);

const topKInput = document.getElementById("control-top-k");
const thresholdInput = document.getElementById("control-threshold");
const topKReadout = document.getElementById("control-top-k-readout");
const thresholdReadout = document.getElementById("control-threshold-readout");
const modeSelect = document.getElementById("control-mode");
const rewriteCheckbox = document.getElementById("control-rewrite");
const diagnosticsFullCheckbox = document.getElementById("control-diagnostics-full");
const providerIndicator = document.getElementById("provider-indicator");

function updateTopKReadout() {
  topKReadout.textContent = `k=${topKInput.value}`;
}
function updateThresholdReadout() {
  thresholdReadout.textContent = `sim≥${parseFloat(thresholdInput.value).toFixed(2)}`;
}
topKInput.addEventListener("input", updateTopKReadout);
thresholdInput.addEventListener("input", updateThresholdReadout);

// Defaults live in config.py; these are only a last resort for when /api/config
// is unreachable, so the Advanced panel still shows usable numbers instead of
// blank inputs that would post NaN.
const OFFLINE_FALLBACK_CONFIG = { top_k: 5, similarity_threshold: 0.35 };

// "Stale" state: a warning strip under the tabs naming the last index
// refresh date, so a demo doesn't silently answer from a day-old rebuild
// without anyone noticing. 24h is a reasonable staleness threshold for a
// project where the index is rebuilt by hand, not on a schedule.
const STALE_INDEX_THRESHOLD_MS = 24 * 60 * 60 * 1000;

function renderStaleIndexBanner(indexBuiltAt) {
  const banner = document.getElementById("stale-index-banner");
  if (!indexBuiltAt) {
    banner.classList.add("hidden");
    return;
  }
  const builtAtMs = Date.parse(indexBuiltAt);
  if (Number.isNaN(builtAtMs) || Date.now() - builtAtMs < STALE_INDEX_THRESHOLD_MS) {
    banner.classList.add("hidden");
    return;
  }
  const dateLabel = new Date(builtAtMs).toISOString().slice(0, 10);
  banner.textContent = `The knowledge base was last refreshed ${dateLabel}. Answers may not reflect newer documents.`;
  banner.classList.remove("hidden");
}

async function initConfig() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const cfg = await response.json();

    if (cfg.top_k !== undefined && cfg.top_k !== null) topKInput.value = cfg.top_k;
    if (cfg.similarity_threshold !== undefined && cfg.similarity_threshold !== null) {
      thresholdInput.value = cfg.similarity_threshold;
    }
    if (cfg.retrieval_mode) modeSelect.value = cfg.retrieval_mode;
    if (cfg.rewrite_query !== undefined && cfg.rewrite_query !== null) {
      rewriteCheckbox.checked = cfg.rewrite_query;
    }
    if (cfg.llm_provider) {
      providerIndicator.textContent = `LLM: ${cfg.llm_provider}`;
      providerIndicator.classList.remove("hidden");
    }
    renderStaleIndexBanner(cfg.index_built_at);
  } catch (error) {
    if (!topKInput.value) topKInput.value = OFFLINE_FALLBACK_CONFIG.top_k;
    if (!thresholdInput.value) {
      thresholdInput.value = OFFLINE_FALLBACK_CONFIG.similarity_threshold;
    }
    providerIndicator.textContent = "LLM: unavailable";
    providerIndicator.classList.remove("hidden");
  }
  updateTopKReadout();
  updateThresholdReadout();
}

initConfig();

function readControls() {
  return {
    top_k: parseInt(topKInput.value, 10),
    similarity_threshold: parseFloat(thresholdInput.value),
    retrieval_mode: modeSelect.value,
    rewrite_query: rewriteCheckbox.checked,
  };
}

// Developer-only affordance: rendered inside the Advanced panel, never in the
// resident-facing answer view. Residents never see the word "unverified" --
// renderResidentCitationNote (below) is what tells them, in plain language,
// that a claim was dropped.
function renderDevWarnings(messages) {
  const banner = document.getElementById("citation-warning-banner");
  const detail = document.getElementById("citation-warning-detail");
  if (!messages.length) {
    detail.textContent = "";
    banner.classList.add("hidden");
    return;
  }
  detail.textContent = messages.join(" | ");
  banner.classList.remove("hidden");
}

function renderCitationWarning(result) {
  const warnings = result.citation_warning || [];
  renderDevWarnings(
    warnings.map((pair) => (Array.isArray(pair) ? `unverified citation [${pair.join(", ")}]` : String(pair)))
  );
  renderResidentCitationNote(warnings.length);
}

// The resident-facing counterpart to renderDevWarnings: states the same fact
// in plain language, with no jargon ("unverified", "citation") -- a resident
// must never see a scary technical banner attached to an answer they were
// just given.
function renderResidentCitationNote(droppedCount) {
  const note = document.getElementById("answer-citation-note");
  if (!droppedCount) {
    note.classList.add("hidden");
    note.textContent = "";
    return;
  }
  note.textContent =
    droppedCount === 1
      ? "One statement below could not be matched to a document, and has been removed."
      : `${droppedCount} statements below could not be matched to a document, and have been removed.`;
  note.classList.remove("hidden");
}

// Developer-only diagnostics panel (rewrite trace + retrieved chunks + gain).
// Never rendered anywhere in the resident-facing answer view.
function renderDiagnostics(diagnostics) {
  const panel = document.getElementById("diagnostics-panel");
  if (!diagnostics) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");

  const rewrite = diagnostics.rewrite || {};
  document.getElementById("diag-raw-query").textContent = rewrite.raw || "";
  document.getElementById("diag-rewritten-query").textContent = rewrite.rewritten || "";

  const subQueriesEl = document.getElementById("diag-subqueries");
  subQueriesEl.innerHTML = "";
  (rewrite.subQueries || []).forEach((sub) => {
    const chip = document.createElement("span");
    chip.className = "diag-subquery-chip";
    chip.textContent = sub;
    subQueriesEl.appendChild(chip);
  });

  const opsEl = document.getElementById("diag-ops");
  opsEl.innerHTML = "";
  (rewrite.ops || []).forEach((op) => {
    const item = document.createElement("span");
    item.className = `diag-op diag-op-${op.kind}`;
    item.textContent = op.detail ? `${op.kind}: ${op.detail}` : op.kind;
    opsEl.appendChild(item);
  });

  const gainEl = document.getElementById("diag-gain");
  const gain = diagnostics.gain;
  gainEl.textContent = gain
    ? `gain: top1 sim raw=${gain.top1SimRaw.toFixed(3)} rewritten=${gain.top1SimRewritten.toFixed(3)} ` +
      `· schemes above threshold Δ${gain.schemesAboveThresholdDelta >= 0 ? "+" : ""}${gain.schemesAboveThresholdDelta}` +
      (rewrite.latencyMs !== undefined ? ` · rewrite ${rewrite.latencyMs}ms` : "")
    : rewrite.latencyMs !== undefined
      ? `rewrite ${rewrite.latencyMs}ms`
      : "";

  const chunksBody = document.getElementById("diag-chunks-body");
  chunksBody.innerHTML = "";
  const retrieval = diagnostics.retrieval || {};
  const threshold = typeof retrieval.threshold === "number" ? retrieval.threshold : null;
  // Sorted by score descending is the fused rank order the backend already
  // returned; rank Δ vs a separate baseline ordering isn't computed by the
  // backend today, so this column reads "· 0" for every row rather than
  // fabricate a delta -- a real per-chunk rank-change diagnostic would need
  // a retrieval/pipeline change outside this view-layer pass.
  (retrieval.chunks || []).forEach((chunk) => {
    const row = document.createElement("tr");
    const idCell = document.createElement("td");
    idCell.textContent = chunk.chunk_id;
    row.appendChild(idCell);
    const scoreCell = document.createElement("td");
    scoreCell.textContent = typeof chunk.score === "number" ? chunk.score.toFixed(3) : "";
    row.appendChild(scoreCell);
    const deltaCell = document.createElement("td");
    deltaCell.textContent = "· 0";
    row.appendChild(deltaCell);
    const stateCell = document.createElement("td");
    stateCell.textContent =
      threshold === null
        ? ""
        : typeof chunk.score === "number" && chunk.score >= threshold
          ? "above threshold"
          : "below threshold";
    row.appendChild(stateCell);
    chunksBody.appendChild(row);
  });

  document.getElementById("diag-dropped").textContent =
    retrieval.dropped ? `${retrieval.dropped} candidate(s) dropped at top_k truncation` : "";
}

// Records store an on-disk path; data/raw/ is served read-only under /media/.
function thumbnailUrl(thumbnailPath) {
  const normalized = String(thumbnailPath).replace(/\\/g, "/");
  const marker = "/raw/";
  const index = normalized.indexOf(marker);
  return index === -1 ? normalized : `/media/${normalized.slice(index + marker.length)}`;
}

// Caps a source excerpt to ~240 chars at a sentence boundary so the Sources
// panel never dumps a whole OCR'd/scraped page. The full chunk text is
// preserved separately on the record and only ever shown in the
// source-passage drawer.
//
// Scraped gov.sg pages repeat the same nav/footer/legal boilerplate on every
// chunk -- language switchers, breadcrumb chains, scam warnings, cookie
// banners, share/print links. Printing that instead of the actual passage
// ("Support Resources & Tools Read this in: English | 中文 | Melayu |
// தமிழ்...") is worse than a layout bug: it tells the reader the system
// doesn't understand its own documents. Every pattern here was matched
// against real text actually seen in this corpus's PDFs.
const BOILERPLATE_PATTERNS = [
  /^Support\s+Resources\s*&\s*Tools\s+Read this in:.*?Share link\s*/i,
  /Scheme last updated.*$/is,
  // Language-switcher runs anywhere in the text: 2+ "|"-separated segments,
  // each at most 3 words (catches "English | 中文 | Melayu | தமிழ்" and
  // similar even mid-excerpt, not just at the very start).
  /(?:\S+(?:\s+\S+){0,2}\s*\|\s*){2,}\S+(?:\s+\S+){0,2}/g,
  // Breadcrumb chains: 2+ "word/phrase >" segments, e.g.
  // "Early Childhood Development Agency (ECDA)> Parents> Preschool Subsidies >".
  /\b[\w][\w()&/,.'-]*(?:\s+[\w()&/,.'-]+){0,4}\s*>\s*(?:[\w][\w()&/,.'-]*(?:\s+[\w()&/,.'-]+){0,4}\s*>\s*){1,}/g,
  /A Singapore Government Agency Website\.?\s*(Beware of government impersonation scams\.?)?/gi,
  /How to identify\s*/gi,
  /Scam Advisory\s*/gi,
  /AIC staff will NEVER ask you to transfer money or disclose bank log-in details[^.]*\./gi,
  /We are aware of incorrect information[^.]*\.\s*Always verify details on our website first\.\s*If in\s*doubt, contact AIC directly\.?/gi,
  /This site uses cookies\.[^.]*\.\s*(For more information, view our privacy policy\.)?/gi,
  /Chat with Us\s*/gi,
  /Submit (an enquiry|your enquiry)\s*/gi,
  /About Us\s+Contact Us\/Feedback\s+Report Vulnerability\s+Privacy Statement\s+Terms of Use\s*/gi,
  /©\d{4},?\s*Government of Singapore\.[^.]*\.?/gi,
  /Did you find your answer\?\s*(No\s+Yes)?/gi,
  /https?:\/\/\S+/g,
];

function cleanExcerptText(text, displayName) {
  let cleaned = text || "";
  BOILERPLATE_PATTERNS.forEach((pattern) => {
    cleaned = cleaned.replace(pattern, " ");
  });
  cleaned = cleaned.trim().replace(/\s+/g, " ");
  // A cleaned excerpt that opens by repeating the row's own title heading
  // adds nothing -- the title is already shown as the row heading.
  if (displayName) {
    const escaped = displayName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    cleaned = cleaned.replace(new RegExp(`^${escaped}\\s*`, "i"), "").trim();
  }
  return cleaned;
}

function capExcerpt(text, displayName, maxChars = 240) {
  const trimmed = cleanExcerptText(text, displayName);
  if (!trimmed) return "";
  if (trimmed.length <= maxChars) return trimmed;
  const sliced = trimmed.slice(0, maxChars);
  const lastEnd = Math.max(sliced.lastIndexOf(". "), sliced.lastIndexOf("? "), sliced.lastIndexOf("! "));
  const cut = lastEnd > maxChars * 0.4 ? sliced.slice(0, lastEnd + 1) : sliced;
  return `${cut.trim()}…`;
}

// Mirrors generation.prompts.extract_cited_scheme_labels: finds every
// "[scheme_name, section_or_page]" (or "[a, b; c, d]") bracket citation in
// the answer text and returns its character span plus the (name, location)
// pairs it names, in order of appearance.
function extractCitedLabelSpans(answer) {
  const spans = [];
  const bracketRe = /\[([^\[\]]+)\]/g;
  let match;
  while ((match = bracketRe.exec(answer)) !== null) {
    const pairs = [];
    match[1].split(";").forEach((segment) => {
      const commaIndex = segment.indexOf(",");
      if (commaIndex === -1) return;
      const name = segment.slice(0, commaIndex).trim();
      const location = segment.slice(commaIndex + 1).trim();
      if (name && location) pairs.push({ name, location });
    });
    spans.push({ start: match.index, end: match.index + match[0].length, pairs });
  }
  return spans;
}

// Groups retrieved source records by document (display_name, falling back to
// scheme_name) so the same document cited at two different page ranges
// becomes one Sources entry with two passages inside it, not two entries.
function buildDocIndex() {
  const docsByLabel = new Map();
  const docs = [];
  return {
    docs,
    addSource(source) {
      const docLabel = source.display_name || source.scheme_name;
      let doc = docsByLabel.get(docLabel);
      if (!doc) {
        doc = { number: docs.length + 1, docLabel, passages: [] };
        docsByLabel.set(docLabel, doc);
        docs.push(doc);
      }
      const alreadyHasPassage = doc.passages.some((p) => p.source.chunk_id === source.chunk_id);
      if (!alreadyHasPassage) doc.passages.push({ source });
      return doc;
    },
  };
}

const generalAnswerView = document.getElementById("general-answer-view");
const shortlistView = document.getElementById("shortlist-view");
const sourcesCard = document.getElementById("sources-card");
const sourcesExpandBtn = document.getElementById("sources-expand-btn");
const SOURCES_COLLAPSED_COUNT = 3;

const MODALITY_TILE_LABEL = { image: "FIGURE", video: "VIDEO ▸" };
const DOC_TYPE_LABEL = {
  scheme_page: "Scheme page",
  pdf: "PDF",
  video: "Video",
  infographic: "Infographic",
};
// Authority ranking (3e): highest authority first, similarity as tiebreak.
// A document with no authority_rank sorts after every ranked one, rather
// than defaulting to 0 and outranking real tier-A sources.
function docAuthorityRank(doc) {
  const ranks = doc.passages
    .map(({ source }) => source.authority_rank)
    .filter((rank) => typeof rank === "number");
  return ranks.length ? Math.min(...ranks) : Number.POSITIVE_INFINITY;
}
function docBestScore(doc) {
  const scores = doc.passages.map(({ source }) => source.score).filter((s) => typeof s === "number");
  return scores.length ? Math.max(...scores) : -Infinity;
}

function renderSourceEntry(doc, list, showScore) {
  const item = document.createElement("li");
  item.className = "source-entry";

  item.id = `source-row-${doc.number}`;

  const indexDiv = document.createElement("div");
  indexDiv.className = "source-index";
  indexDiv.textContent = String(doc.number);
  item.appendChild(indexDiv);

  const body = document.createElement("div");
  body.className = "source-body";

  const primary = doc.passages[0].source;
  const titleLine = document.createElement("div");
  titleLine.className = "source-title-line";
  if (primary.agency) {
    const agencyEl = document.createElement("span");
    agencyEl.className = "source-agency";
    agencyEl.textContent = primary.agency;
    titleLine.appendChild(agencyEl);
  }
  const title = document.createElement("span");
  title.className = "source-title";
  title.textContent = doc.docLabel;
  titleLine.appendChild(title);
  body.appendChild(titleLine);

  doc.passages.forEach(({ source }) => {
    const passageDiv = document.createElement("div");
    passageDiv.className = "source-passage";

    const refLine = document.createElement("div");
    refLine.className = "source-ref";
    const score = showScore && typeof source.score === "number" ? source.score.toFixed(2) : null;
    refLine.textContent = score
      ? `${doc.docLabel} · ${source.section_or_page} · sim ${score}`
      : `${doc.docLabel} · ${source.section_or_page}`;
    passageDiv.appendChild(refLine);

    // Provenance run: doc_type · Tier {tier} · eff. {date} · retrieved {date},
    // omitting any piece the metadata doesn't have (3c line 3).
    const provenanceParts = [];
    if (source.doc_type) provenanceParts.push(DOC_TYPE_LABEL[source.doc_type] || source.doc_type);
    if (source.tier) provenanceParts.push(`Tier ${source.tier}`);
    if (source.effective_date) provenanceParts.push(`eff. ${source.effective_date}`);
    if (source.last_updated) provenanceParts.push(`retrieved ${source.last_updated}`);
    if (provenanceParts.length) {
      const provenanceLine = document.createElement("div");
      provenanceLine.className = "source-provenance";
      provenanceLine.textContent = provenanceParts.join(" · ");
      passageDiv.appendChild(provenanceLine);
    }

    const excerptText = capExcerpt(source.text, doc.docLabel);
    const excerptDiv = document.createElement("div");
    excerptDiv.className = "source-excerpt";
    excerptDiv.textContent = excerptText || "No quotable passage — open the source document";
    if (!excerptText) excerptDiv.classList.add("source-excerpt-empty");
    passageDiv.appendChild(excerptDiv);

    const actionsRow = document.createElement("div");
    actionsRow.className = "source-actions-row";

    const showBtn = document.createElement("button");
    showBtn.type = "button";
    showBtn.className = "source-show-btn";
    showBtn.textContent = "Show passage in context";
    showBtn.addEventListener("click", () =>
      openSourceDrawer({
        doc_label: doc.docLabel,
        section: source.section_or_page,
        score: source.score,
        chunk_id: source.chunk_id,
        text: source.text,
      })
    );
    actionsRow.appendChild(showBtn);

    // These URLs come from data/metadata/*.json sidecars synced in from an
    // external Google Drive folder, not from this codebase -- textContent
    // protects every other rendered field, but href is a navigation sink, so
    // a malformed or malicious scheme (e.g. "javascript:") must be rejected
    // here rather than trusted.
    const originalUrl = source.canonical_url || source.source_url;
    if (originalUrl && /^https?:\/\//i.test(originalUrl)) {
      const originalLink = document.createElement("a");
      originalLink.className = "source-show-btn";
      originalLink.href = originalUrl;
      originalLink.target = "_blank";
      originalLink.rel = "noopener";
      originalLink.textContent = "View original";
      actionsRow.appendChild(originalLink);
    }

    passageDiv.appendChild(actionsRow);
    body.appendChild(passageDiv);
  });

  item.appendChild(body);

  const firstThumbnail = doc.passages.find(
    (p) => p.source.thumbnail_path || p.source.modality === "video" || p.source.doc_type === "infographic"
  );
  if (firstThumbnail) {
    const source = firstThumbnail.source;
    if (source.thumbnail_path && source.modality === "image") {
      const thumbWrap = document.createElement("div");
      thumbWrap.className = "source-thumb";
      const image = document.createElement("img");
      image.src = thumbnailUrl(source.thumbnail_path);
      image.alt = `Thumbnail for ${doc.docLabel}`;
      image.loading = "lazy";
      thumbWrap.appendChild(image);
      item.appendChild(thumbWrap);
    } else {
      const tileLabel = MODALITY_TILE_LABEL[source.modality] || (source.doc_type === "infographic" ? "FIGURE" : null);
      if (tileLabel) {
        const tile = document.createElement("div");
        tile.className = "source-thumb source-thumb-placeholder";
        const label = document.createElement("span");
        label.className = "source-thumb-label";
        label.textContent = tileLabel;
        tile.appendChild(label);
        const sub = document.createElement("span");
        sub.className = "source-thumb-sub";
        sub.textContent = source.section_or_page || "";
        tile.appendChild(sub);
        item.appendChild(tile);
      }
    }
  }

  list.appendChild(item);
}

// Sorts docs by authority (highest first, similarity as tiebreak) and
// reassigns doc.number to match (3e). Must run exactly once, before either
// the answer text's "[n]" markers or the Sources list are rendered -- both
// read doc.number, and they must agree.
function sortAndNumberDocs(docs) {
  docs.sort((a, b) => {
    const rankDelta = docAuthorityRank(a) - docAuthorityRank(b);
    return rankDelta !== 0 ? rankDelta : docBestScore(b) - docBestScore(a);
  });
  docs.forEach((doc, index) => {
    doc.number = index + 1;
  });
  return docs;
}

function renderSources(docs, showScore) {
  const list = document.getElementById("sources-list");
  list.innerHTML = "";
  sourcesCard.classList.toggle("hidden", docs.length === 0);
  if (!docs.length) return;

  const ordered = docs;
  const collapsed = ordered.length > SOURCES_COLLAPSED_COUNT;
  const visible = collapsed ? ordered.slice(0, SOURCES_COLLAPSED_COUNT) : ordered;
  visible.forEach((doc) => renderSourceEntry(doc, list, showScore));

  const licenceNotes = [
    ...new Set(docs.map((doc) => doc.passages[0].source.licence_note).filter(Boolean)),
  ];
  const existingLicenceLine = sourcesCard.querySelector(".source-licence-note");
  if (existingLicenceLine) existingLicenceLine.remove();
  if (licenceNotes.length) {
    const licenceLine = document.createElement("div");
    licenceLine.className = "source-licence-note";
    licenceLine.textContent = licenceNotes.join(" "); // one line, deduplicated across rows, not per row
    sourcesCard.appendChild(licenceLine);
  }

  if (!collapsed) {
    sourcesExpandBtn.classList.add("hidden");
    return;
  }
  sourcesExpandBtn.classList.remove("hidden");
  sourcesExpandBtn.textContent = `Show all ${ordered.length} sources`;
  sourcesExpandBtn.onclick = () => {
    ordered.slice(SOURCES_COLLAPSED_COUNT).forEach((doc) => renderSourceEntry(doc, list, showScore));
    sourcesExpandBtn.classList.add("hidden");
  };
}

// Rebuilds the answer text as DOM nodes (never innerHTML) so bracket
// citations like "[GST Voucher, p.2]" become clickable mono superscript
// markers "[1]" that map onto the deduplicated Sources list below, instead
// of the raw scheme/section text sitting inline in the sentence.
function renderAnswerTextWithCitations(answer, sourcesByKey, docIndex) {
  const container = document.getElementById("answer-text");
  container.innerHTML = "";
  const spans = extractCitedLabelSpans(answer);

  let cursor = 0;
  spans.forEach((span) => {
    if (span.start > cursor) {
      // Markers sit flush after punctuation, no preceding space -- trims
      // trailing whitespace off the text run immediately before a citation
      // (the model sometimes emits "Office , [Scheme, p.2]" with a stray
      // space-before-bracket).
      const between = answer.slice(cursor, span.start).replace(/\s+$/, "");
      if (between) container.appendChild(document.createTextNode(between));
    }
    const numbers = [];
    let firstDoc = null;
    span.pairs.forEach(({ name, location }) => {
      const source = sourcesByKey.get(`${name} ${location}`);
      if (!source) return; // unresolved citation: dropped, not rendered as a broken marker
      const doc = docIndex.addSource(source);
      if (!numbers.includes(doc.number)) numbers.push(doc.number);
      if (!firstDoc) firstDoc = doc;
    });
    if (numbers.length) {
      const marker = document.createElement("sup");
      marker.className = "citation-marker";
      const link = document.createElement("a");
      link.href = `#source-row-${firstDoc.number}`;
      link.textContent = `[${numbers.join(",")}]`;
      link.addEventListener("click", (event) => {
        event.preventDefault();
        scrollToAndHighlightSourceRow(firstDoc.number);
      });
      marker.appendChild(link);
      container.appendChild(marker);
    }
    cursor = span.end;
  });
  if (cursor < answer.length) {
    container.appendChild(document.createTextNode(answer.slice(cursor)));
  }
}

// Scrolls the matching Sources row into view and briefly highlights it, so a
// resident clicking "[1]" can see which row it points to (§4). A marker for
// source 4+ points at a row that isn't in the DOM yet while the Sources list
// is still collapsed to SOURCES_COLLAPSED_COUNT -- expand it first so the
// click always lands somewhere, instead of doing nothing.
function scrollToAndHighlightSourceRow(number) {
  let row = document.getElementById(`source-row-${number}`);
  if (!row && !sourcesExpandBtn.classList.contains("hidden")) {
    sourcesExpandBtn.click();
    row = document.getElementById(`source-row-${number}`);
  }
  if (!row) return;
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.add("source-entry-highlight");
  setTimeout(() => row.classList.remove("source-entry-highlight"), 1600);
}

// 3d: a cited document that's been replaced by a newer version gets a
// warning at the top of the answer card, not buried in the source row.
function renderSupersessionWarning(sources) {
  const banner = document.getElementById("answer-supersession-warning");
  const detail = document.getElementById("answer-supersession-detail");
  const superseded = sources.filter((s) => s.is_current === false || s.superseded === true);
  if (!superseded.length) {
    banner.classList.add("hidden");
    return;
  }
  detail.textContent =
    "One cited document has been replaced by a newer version. Amounts may have changed.";
  banner.classList.remove("hidden");
}

// 3e: flag once, under the answer, when the strongest (highest-authority)
// cited source is a low-tier form/checklist rather than a scheme page --
// never colour-coded or badged per row, which would invite a resident to
// argue with the ranking.
function renderTopTierNote(sources) {
  const note = document.getElementById("answer-tier-note");
  const ranked = sources
    .filter((s) => typeof s.authority_rank === "number")
    .sort((a, b) => a.authority_rank - b.authority_rank);
  const top = ranked[0];
  if (!top || (top.tier !== "D" && top.tier !== "E")) {
    note.classList.add("hidden");
    note.textContent = "";
    return;
  }
  note.textContent =
    "The strongest match here is a form, not the scheme page — conditions may be stated more fully elsewhere.";
  note.classList.remove("hidden");
}

// Page-level as-of line, derived from the newest last_updated across cited
// sources rather than a hardcoded date (3d).
function renderAsOfLine(sources) {
  const line = document.getElementById("answer-asof-line");
  const dates = sources.map((s) => s.last_updated).filter(Boolean).sort();
  const newest = dates[dates.length - 1];
  const uniqueDocs = new Set(sources.map((s) => s.display_name || s.scheme_name)).size;
  if (!uniqueDocs) {
    line.classList.add("hidden");
    return;
  }
  line.textContent = newest
    ? `Checked against ${uniqueDocs} published document${uniqueDocs === 1 ? "" : "s"} · newest source updated ${newest}.`
    : `Checked against ${uniqueDocs} published document${uniqueDocs === 1 ? "" : "s"}.`;
  line.classList.remove("hidden");
}

function renderResult(result) {
  generalAnswerView.classList.remove("hidden");
  shortlistView.classList.add("hidden");

  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);
  // Empty state (§ States): reassures the resident this isn't a judgment
  // about them, with an escape action, rather than just the raw fallback
  // sentence sitting alone in the answer card.
  document.getElementById("answer-empty-state").classList.toggle("hidden", !result.abstained);

  const sources = result.sources || [];
  const sourcesByKey = new Map();
  sources.forEach((source) =>
    sourcesByKey.set(`${source.display_name || source.scheme_name} ${source.section_or_page}`, source)
  );

  // First pass: walk the citations purely to populate docIndex (the DOM this
  // builds gets discarded by the second pass below, once doc.number is
  // final) -- addSource is idempotent per docLabel, so re-running it after
  // sorting is safe and returns the same doc objects.
  const docIndex = buildDocIndex();
  renderAnswerTextWithCitations(result.answer || "", sourcesByKey, docIndex);

  // Fallback: if no bracket citation resolved to a known source (e.g. the
  // model abstained, or omitted citations), still show what was retrieved
  // rather than leaving the Sources panel empty.
  if (!docIndex.docs.length) {
    sources.forEach((source) => docIndex.addSource(source));
  }

  // Sort by authority once, then re-render the answer text so its "[n]"
  // markers use the final, post-sort numbers -- these must agree with the
  // Sources list below, which reads the same doc.number.
  sortAndNumberDocs(docIndex.docs);
  renderAnswerTextWithCitations(result.answer || "", sourcesByKey, docIndex);

  // A similarity score means nothing to a resident and undercuts the answer
  // -- only show it when the Advanced panel is open (team demo context).
  const showScore = !advancedBand.classList.contains("hidden");
  renderSources(docIndex.docs, showScore);
  renderSupersessionWarning(sources);
  renderTopTierNote(sources);
  renderAsOfLine(sources);

  const retrievalMode = result.diagnostics && result.diagnostics.retrieval ? result.diagnostics.retrieval.mode : null;
  const docCount = docIndex.docs.length;
  document.getElementById("answer-meta").textContent = retrievalMode
    ? `${docCount} source${docCount === 1 ? "" : "s"} · ${retrievalMode} retrieval`
    : `${docCount} source${docCount === 1 ? "" : "s"}`;

  renderCitationWarning(result);
  renderDiagnostics(result.diagnostics);
}

document.getElementById("answer-check-btn").addEventListener("click", () => setMode("profile"));
document.getElementById("answer-print-btn").addEventListener("click", () => window.print());
document.getElementById("answer-empty-rephrase-btn").addEventListener("click", () => {
  const input = document.getElementById("question-input");
  input.value = "";
  input.focus();
});
document.getElementById("answer-wrong-btn").addEventListener("click", (event) => {
  const button = event.currentTarget;
  const original = button.textContent;
  button.textContent = "Thanks, noted";
  button.disabled = true;
  setTimeout(() => {
    button.textContent = original;
    button.disabled = false;
  }, 2500);
});

const GROUP_ORDER = ["eligible", "unclear", "not_assessed"];
const GROUP_LABELS = {
  eligible: "Possibly eligible",
  unclear: "Likely not eligible, or unclear",
  not_assessed: "Not assessed",
};
const GROUP_BLURBS = {
  eligible: "Your answers match the conditions stated in the documents. You still need to apply and be assessed.",
  unclear: "Either your answers fall outside a stated condition, or the documents do not settle it.",
  not_assessed: "The documents did not contain enough to evaluate this scheme against your profile.",
};

function openSourceDrawer(citation) {
  document.getElementById("source-drawer-title").textContent = citation.doc_label;
  const score = citation.score === null || citation.score === undefined ? "n/a" : citation.score.toFixed(3);
  document.getElementById("source-drawer-meta").textContent =
    `${citation.section} · sim ${score} · chunk_id ${citation.chunk_id}`;
  document.getElementById("source-drawer-excerpt").textContent = citation.text || "";
  document.getElementById("source-drawer").classList.remove("hidden");
}

document.getElementById("source-drawer-close").addEventListener("click", () => {
  document.getElementById("source-drawer").classList.add("hidden");
});

function renderCitationChips(citations, container) {
  citations.forEach((citation) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "citation-chip";
    chip.textContent = `${citation.doc_label} · ${citation.section}`;
    chip.addEventListener("click", () => openSourceDrawer(citation));
    container.appendChild(chip);
  });
}

// The blocking condition is what the reader came for, so it sorts first,
// not wherever the model happened to list it (§2).
const CONDITION_SORT_ORDER = { not_met: 0, not_checked: 1, met: 2 };
const CONDITION_CHIPS_CAP = 4;

// Best-effort, view-layer-only heuristic: a "changer" that just restates an
// immutable fact ("being born in 1973 or earlier would change the
// assessment") helps nobody -- the resident cannot act on it.
const IMMUTABLE_CHANGER_PATTERNS = [
  /\bborn\b/i,
  /\byear of birth\b/i,
  /\bdate of birth\b/i,
  /\bage[ds]?\s+\d/i,
  /\bcitizenship at birth\b/i,
];
function isImmutableChanger(changerText) {
  return IMMUTABLE_CHANGER_PATTERNS.some((pattern) => pattern.test(changerText));
}

function renderConditionChips(conditions, container) {
  const sorted = [...conditions].sort(
    (a, b) => (CONDITION_SORT_ORDER[a.state] ?? 1) - (CONDITION_SORT_ORDER[b.state] ?? 1)
  );
  const visible = sorted.slice(0, CONDITION_CHIPS_CAP);
  visible.forEach((condition) => {
    const chip = document.createElement("span");
    chip.className = `condition-chip condition-${condition.state}`;
    const dot = document.createElement("span");
    dot.className = "condition-chip-dot";
    chip.appendChild(dot);
    const suffix = condition.state === "not_met" ? " — not met" : condition.state === "not_checked" ? " — not checked" : "";
    chip.appendChild(document.createTextNode(`${condition.label}${suffix}`));
    container.appendChild(chip);
  });
  const remaining = sorted.length - visible.length;
  if (remaining > 0) {
    const more = document.createElement("span");
    more.className = "condition-chip-more";
    more.textContent = `+${remaining} more`;
    container.appendChild(more);
  }
}

function renderShortlistEntry(entry) {
  const card = document.createElement("div");
  card.className = "shortlist-entry";

  const header = document.createElement("div");
  header.className = "shortlist-entry-header";
  const schemeName = document.createElement("h4");
  schemeName.textContent = entry.scheme;
  header.appendChild(schemeName);
  const amount = document.createElement("span");
  amount.className = "shortlist-amount";
  // "—" per row, never a repeated "Amount not stated" -- that's said once,
  // in the group blurb, by renderShortlistGroupCard below (§2).
  amount.textContent = entry.amount || "—";
  header.appendChild(amount);
  card.appendChild(header);

  const reason = document.createElement("p");
  reason.className = "shortlist-reason";
  reason.textContent = entry.reason;
  card.appendChild(reason);

  if (entry.conditions && entry.conditions.length) {
    const conditionsDiv = document.createElement("div");
    conditionsDiv.className = "condition-chips";
    renderConditionChips(entry.conditions, conditionsDiv);
    card.appendChild(conditionsDiv);
  }

  // Dropped for immutable facts (year of birth, citizenship at birth, etc.)
  // rather than printing a tautology like "being born in 1973 or earlier
  // would change the assessment" -- content-only heuristic at the view
  // layer, since rewriting the LLM's own changer text is out of scope here.
  if (entry.changer && !isImmutableChanger(entry.changer)) {
    const changerDiv = document.createElement("div");
    changerDiv.className = "shortlist-changer";
    const changerLabel = document.createElement("span");
    changerLabel.className = "shortlist-changer-label";
    changerLabel.textContent = "What would change this: ";
    changerDiv.appendChild(changerLabel);
    changerDiv.appendChild(document.createTextNode(entry.changer));
    card.appendChild(changerDiv);
  }

  if (entry.citations && entry.citations.length) {
    const citationsDiv = document.createElement("div");
    citationsDiv.className = "citation-chips";
    renderCitationChips(entry.citations, citationsDiv);
    card.appendChild(citationsDiv);
  }

  return card;
}

function renderShortlistInfoBanner() {
  const banner = document.createElement("div");
  banner.className = "shortlist-info-banner";
  const title = document.createElement("strong");
  title.textContent = "This is a shortlist to check, not an approval.";
  banner.appendChild(title);
  const body = document.createElement("p");
  body.textContent =
    "Every scheme below is grouped by how closely your answers match the conditions stated in its source document. Applying and being assessed by the agency is still required.";
  banner.appendChild(body);
  return banner;
}

function renderShortlistEmptyState() {
  const empty = document.createElement("div");
  empty.className = "shortlist-empty-state";
  const line1 = document.createElement("p");
  line1.textContent = "No scheme in the document set matched your answers.";
  empty.appendChild(line1);
  const line2 = document.createElement("p");
  line2.className = "shortlist-empty-note";
  line2.textContent = "That is not a decision about you.";
  empty.appendChild(line2);
  const actions = document.createElement("div");
  actions.className = "answer-actions";
  const askDifferently = document.createElement("button");
  askDifferently.type = "button";
  askDifferently.className = "answer-action-btn";
  askDifferently.textContent = "Ask a question instead";
  askDifferently.addEventListener("click", () => setMode("general"));
  actions.appendChild(askDifferently);
  empty.appendChild(actions);
  return empty;
}

function renderGlossaryCard() {
  const card = document.createElement("div");
  card.className = "glossary-card";
  const eyebrow = document.createElement("span");
  eyebrow.className = "section-eyebrow";
  eyebrow.textContent = "Words used here";
  card.appendChild(eyebrow);
  const list = document.createElement("dl");
  list.className = "glossary-list";
  [
    ["AV", "Annual Value — the estimated yearly rent your home could fetch, used by IRAS/HDB as an income-and-wealth proxy for means-testing."],
    ["AI", "Assessable Income — your income for a Year of Assessment after allowable deductions, used by IRAS-linked schemes."],
    ["YA", "Year of Assessment — the year in which income from the preceding calendar year is assessed for tax."],
  ].forEach(([term, def]) => {
    const dt = document.createElement("dt");
    dt.textContent = term;
    list.appendChild(dt);
    const dd = document.createElement("dd");
    dd.textContent = def;
    list.appendChild(dd);
  });
  card.appendChild(list);
  return card;
}

function renderShortlistClosing(documentCount) {
  const closing = document.createElement("p");
  closing.className = "shortlist-closing";
  const count = typeof documentCount === "number" ? documentCount : null;
  closing.textContent =
    `Amounts shown are what the source documents state, not a calculation. ` +
    (count !== null ? `${count} document${count === 1 ? "" : "s"} checked. ` : "") +
    `As of ${new Date().toISOString().slice(0, 10)}.`;
  return closing;
}

function renderShortlist(result) {
  generalAnswerView.classList.add("hidden");
  shortlistView.classList.remove("hidden");

  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);
  renderDevWarnings(result.dev_warnings || []);
  renderDiagnostics(result.diagnostics);

  shortlistView.innerHTML = "";
  shortlistView.appendChild(renderShortlistInfoBanner());

  const entriesByGroup = { eligible: [], unclear: [], not_assessed: [] };
  (result.shortlist || []).forEach((entry) => entriesByGroup[entry.group].push(entry));
  const totalEntries = (result.shortlist || []).length;

  if (!totalEntries) {
    shortlistView.appendChild(renderShortlistEmptyState());
    shortlistView.appendChild(renderShortlistClosing(result.documents_checked));
    return;
  }

  GROUP_ORDER.forEach((group) => {
    const entries = entriesByGroup[group];

    const groupCard = document.createElement("div");
    groupCard.className = `shortlist-group shortlist-group-${group}`;

    const header = document.createElement("div");
    header.className = "shortlist-group-header";
    const dot = document.createElement("span");
    dot.className = "shortlist-group-dot";
    header.appendChild(dot);
    const title = document.createElement("h3");
    title.textContent = GROUP_LABELS[group];
    header.appendChild(title);
    const count = document.createElement("span");
    count.className = "shortlist-group-count";
    count.textContent = `${entries.length} scheme${entries.length === 1 ? "" : "s"}`;
    header.appendChild(count);
    groupCard.appendChild(header);

    const blurb = document.createElement("p");
    blurb.className = "shortlist-group-blurb";
    // "Amount not stated" is said once here, not once per row (the row
    // itself just prints "—") -- avoids repeating near-identical grey mono
    // text down a whole column (§2).
    const anyAmountMissing = entries.some((entry) => !entry.amount);
    blurb.textContent = anyAmountMissing
      ? `${GROUP_BLURBS[group]} Amount not stated in the documents where blank.`
      : GROUP_BLURBS[group];
    groupCard.appendChild(blurb);

    if (!entries.length) {
      const none = document.createElement("p");
      none.className = "shortlist-group-none";
      none.textContent = "None in this group.";
      groupCard.appendChild(none);
    }

    entries.forEach((entry) => groupCard.appendChild(renderShortlistEntry(entry)));
    shortlistView.appendChild(groupCard);
  });

  const footerActions = document.createElement("div");
  footerActions.className = "answer-actions";
  footerActions.setAttribute("data-noprint", "");
  const printBtn = document.createElement("button");
  printBtn.type = "button";
  printBtn.className = "answer-action-btn";
  printBtn.textContent = "Print or save this shortlist";
  printBtn.addEventListener("click", () => window.print());
  footerActions.appendChild(printBtn);
  const wrongBtn = document.createElement("button");
  wrongBtn.type = "button";
  wrongBtn.className = "answer-action-btn answer-action-btn-flag";
  wrongBtn.textContent = "This looks wrong";
  wrongBtn.addEventListener("click", () => {
    wrongBtn.textContent = "Thanks, noted";
    wrongBtn.disabled = true;
    setTimeout(() => {
      wrongBtn.textContent = "This looks wrong";
      wrongBtn.disabled = false;
    }, 2500);
  });
  footerActions.appendChild(wrongBtn);
  shortlistView.appendChild(footerActions);

  shortlistView.appendChild(renderGlossaryCard());
  shortlistView.appendChild(renderShortlistClosing(result.documents_checked));
}

function renderAnswer(result) {
  if ("shortlist" in result) {
    renderShortlist(result);
  } else {
    renderResult(result);
  }
}

function renderError(debugDetail) {
  document.getElementById("answer-abstained-badge").classList.add("hidden");
  document.getElementById("answer-empty-state").classList.add("hidden");
  document.getElementById("citation-warning-banner").classList.add("hidden");
  document.getElementById("diagnostics-panel").classList.add("hidden");
  document.getElementById("answer-citation-note").classList.add("hidden");
  document.getElementById("answer-supersession-warning").classList.add("hidden");
  document.getElementById("answer-tier-note").classList.add("hidden");
  document.getElementById("answer-asof-line").classList.add("hidden");
  generalAnswerView.classList.remove("hidden");
  shortlistView.classList.add("hidden");

  const container = document.getElementById("answer-text");
  container.innerHTML = "";
  const line1 = document.createElement("p");
  line1.textContent = "The document search did not respond.";
  container.appendChild(line1);
  const line2 = document.createElement("p");
  line2.className = "answer-error-note";
  line2.textContent = "No answer was generated, so nothing here is a partial result.";
  container.appendChild(line2);
  const debugLine = document.createElement("p");
  debugLine.className = "answer-error-debug";
  debugLine.textContent = debugDetail;
  container.appendChild(debugLine);

  document.getElementById("answer-meta").textContent = "";
  document.getElementById("sources-list").innerHTML = "";
  sourcesCard.classList.add("hidden");
  sourcesExpandBtn.classList.add("hidden");
}

const answerPanel = document.querySelector(".answer-panel");

// Results render into the right column, which sits below the input form on
// narrow/short viewports and after switching tabs -- scroll it into view so
// a new answer or shortlist is visible without the user having to scroll
// down and hunt for it every time.
function scrollResultIntoView() {
  answerPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitQuery(button, loadingLabel, url, payload) {
  if (button.disabled) return; // double-submit guard
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = loadingLabel;
  try {
    // diagnostics=full doubles retrieval cost, so it is only sent when the
    // Advanced panel's "Show retrieval gain" checkbox is explicitly on.
    const requestUrl = diagnosticsFullCheckbox.checked
      ? `${url}${url.includes("?") ? "&" : "?"}diagnostics=full`
      : url;
    const response = await fetch(requestUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const body = await response.json();
        if (body && body.detail) detail = body.detail;
      } catch (parseError) {
        // Non-JSON error body; keep the status-code message.
      }
      renderError(`HTTP ${response.status}: ${detail}`);
      return;
    }
    renderAnswer(await response.json());
  } catch (error) {
    renderError("Network error: could not reach the assistant server.");
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
    scrollResultIntoView();
  }
}

document.getElementById("ask-button").addEventListener("click", async (event) => {
  const question = document.getElementById("question-input").value.trim();
  if (!question) return;

  await submitQuery(event.currentTarget, "Asking...", "/api/query", {
    question,
    ...readControls(),
  });
});

document.getElementById("profile-button").addEventListener("click", async (event) => {
  const tags = Array.from(document.querySelectorAll(".life-stage-tag:checked")).map((el) => el.value);
  const profile = {
    citizenship: document.getElementById("profile-citizenship").value,
    age: parseInt(document.getElementById("profile-age").value, 10) || null,
    household_size: parseInt(document.getElementById("profile-household-size").value, 10) || null,
    monthly_income_band: document.getElementById("profile-income-band").value,
    housing: document.getElementById("profile-housing").value,
    employment: document.getElementById("profile-employment").value,
    life_stage_tags: tags,
  };
  const free_text_question = document.getElementById("profile-question").value.trim();

  await submitQuery(event.currentTarget, "Finding schemes...", "/api/profile-query", {
    profile,
    free_text_question,
    ...readControls(),
  });
});
