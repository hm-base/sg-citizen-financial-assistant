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

advancedToggleButton.addEventListener("click", () => {
  const isOpen = advancedBand.classList.toggle("hidden") === false;
  advancedToggleButton.setAttribute("aria-expanded", String(isOpen));
  advancedToggleButton.classList.toggle("active", isOpen);
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
const modeSelect = document.getElementById("control-mode");
const rewriteCheckbox = document.getElementById("control-rewrite");
const diagnosticsFullCheckbox = document.getElementById("control-diagnostics-full");
const providerIndicator = document.getElementById("provider-indicator");

// Defaults live in config.py; these are only a last resort for when /api/config
// is unreachable, so the Advanced panel still shows usable numbers instead of
// blank inputs that would post NaN.
const OFFLINE_FALLBACK_CONFIG = { top_k: 5, similarity_threshold: 0.35 };

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
  } catch (error) {
    if (!topKInput.value) topKInput.value = OFFLINE_FALLBACK_CONFIG.top_k;
    if (!thresholdInput.value) {
      thresholdInput.value = OFFLINE_FALLBACK_CONFIG.similarity_threshold;
    }
    providerIndicator.textContent = "LLM: unavailable";
    providerIndicator.classList.remove("hidden");
  }
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
// resident-facing answer view. Residents never see raw/unverified citations --
// generation.pipeline already drops those from what they're shown.
function renderDevWarnings(messages) {
  const banner = document.getElementById("citation-warning-banner");
  if (!messages.length) {
    banner.textContent = "";
    banner.classList.add("hidden");
    return;
  }
  banner.textContent = `Developer diagnostics: ${messages.join(" | ")}`;
  banner.classList.remove("hidden");
}

function renderCitationWarning(result) {
  const warnings = result.citation_warning || [];
  renderDevWarnings(
    warnings.map((pair) => (Array.isArray(pair) ? `unverified citation [${pair.join(", ")}]` : String(pair)))
  );
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
  (retrieval.chunks || []).forEach((chunk) => {
    const row = document.createElement("tr");
    const idCell = document.createElement("td");
    idCell.textContent = chunk.chunk_id;
    row.appendChild(idCell);
    const scoreCell = document.createElement("td");
    scoreCell.textContent = typeof chunk.score === "number" ? chunk.score.toFixed(3) : "";
    row.appendChild(scoreCell);
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

// Caps a source excerpt to ~2-3 sentences / ~300 chars so the Sources panel
// never dumps a whole OCR'd page. The full chunk text is preserved
// separately on the record and only ever shown in the source-passage drawer.
// Scraped SupportGoWhere pages repeat the same nav/footer boilerplate on
// every chunk ("Read this in: English | ... Share link", the "Scheme last
// updated" footer). Stripping it before capping means the excerpt starts on
// the actual scheme text instead of language-picker chrome.
const BOILERPLATE_PATTERNS = [
  /^Support\s+Resources\s*&\s*Tools\s+Read this in:.*?Share link\s*/i,
  /Scheme last updated.*$/is,
];

function capExcerpt(text, maxChars = 300) {
  if (!text) return "";
  let cleaned = text;
  BOILERPLATE_PATTERNS.forEach((pattern) => {
    cleaned = cleaned.replace(pattern, " ");
  });
  const trimmed = cleaned.trim().replace(/\s+/g, " ");
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

function renderSourceEntry(doc, list) {
  const item = document.createElement("li");
  item.className = "source-entry";

  const indexDiv = document.createElement("div");
  indexDiv.className = "source-index";
  indexDiv.textContent = String(doc.number);
  item.appendChild(indexDiv);

  const body = document.createElement("div");
  body.className = "source-body";

  const title = document.createElement("div");
  title.className = "source-title";
  title.textContent = doc.docLabel;
  body.appendChild(title);

  doc.passages.forEach(({ source }) => {
    const passageDiv = document.createElement("div");
    passageDiv.className = "source-passage";

    const refLine = document.createElement("div");
    refLine.className = "source-ref";
    const score = typeof source.score === "number" ? source.score.toFixed(2) : null;
    refLine.textContent = score ? `${source.section_or_page} · sim ${score}` : source.section_or_page;
    passageDiv.appendChild(refLine);

    const excerptDiv = document.createElement("div");
    excerptDiv.className = "source-excerpt";
    excerptDiv.textContent = capExcerpt(source.text);
    passageDiv.appendChild(excerptDiv);

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
    passageDiv.appendChild(showBtn);

    body.appendChild(passageDiv);
  });

  item.appendChild(body);

  const firstThumbnail = doc.passages.find((p) => p.source.thumbnail_path);
  if (firstThumbnail) {
    const thumbWrap = document.createElement("div");
    thumbWrap.className = "source-thumb";
    const image = document.createElement("img");
    image.src = thumbnailUrl(firstThumbnail.source.thumbnail_path);
    image.alt = `Thumbnail for ${doc.docLabel}`;
    image.loading = "lazy";
    thumbWrap.appendChild(image);
    item.appendChild(thumbWrap);
  }

  list.appendChild(item);
}

function renderSources(docs) {
  const list = document.getElementById("sources-list");
  list.innerHTML = "";
  sourcesCard.classList.toggle("hidden", docs.length === 0);
  if (!docs.length) return;

  const collapsed = docs.length > SOURCES_COLLAPSED_COUNT;
  const visible = collapsed ? docs.slice(0, SOURCES_COLLAPSED_COUNT) : docs;
  visible.forEach((doc) => renderSourceEntry(doc, list));

  if (!collapsed) {
    sourcesExpandBtn.classList.add("hidden");
    return;
  }
  sourcesExpandBtn.classList.remove("hidden");
  sourcesExpandBtn.textContent = `Show all ${docs.length} sources`;
  sourcesExpandBtn.onclick = () => {
    docs.slice(SOURCES_COLLAPSED_COUNT).forEach((doc) => renderSourceEntry(doc, list));
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
      container.appendChild(document.createTextNode(answer.slice(cursor, span.start)));
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
      marker.textContent = `[${numbers.join(",")}]`;
      marker.addEventListener("click", () => {
        const { source } = firstDoc.passages[0];
        openSourceDrawer({
          doc_label: firstDoc.docLabel,
          section: source.section_or_page,
          score: source.score,
          chunk_id: source.chunk_id,
          text: source.text,
        });
      });
      container.appendChild(marker);
    }
    cursor = span.end;
  });
  if (cursor < answer.length) {
    container.appendChild(document.createTextNode(answer.slice(cursor)));
  }
}

function renderResult(result) {
  generalAnswerView.classList.remove("hidden");
  shortlistView.classList.add("hidden");

  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);

  const sources = result.sources || [];
  const sourcesByKey = new Map();
  sources.forEach((source) => sourcesByKey.set(`${source.scheme_name} ${source.section_or_page}`, source));

  const docIndex = buildDocIndex();
  renderAnswerTextWithCitations(result.answer || "", sourcesByKey, docIndex);

  // Fallback: if no bracket citation resolved to a known source (e.g. the
  // model abstained, or omitted citations), still show what was retrieved
  // rather than leaving the Sources panel empty.
  if (!docIndex.docs.length) {
    sources.forEach((source) => docIndex.addSource(source));
  }
  renderSources(docIndex.docs);

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

const CONDITION_STATE_LABEL = { met: "", not_met: "not checked", not_checked: "not checked" };

function renderConditionChips(conditions, container) {
  conditions.forEach((condition) => {
    const chip = document.createElement("span");
    chip.className = `condition-chip condition-${condition.state}`;
    const suffix = condition.state === "not_met" ? " — not met" : condition.state === "not_checked" ? " — not checked" : "";
    chip.textContent = `${condition.label}${suffix}`;
    container.appendChild(chip);
  });
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
  amount.textContent = entry.amount || "Amount not stated";
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

  if (entry.changer) {
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
    blurb.textContent = GROUP_BLURBS[group];
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

function renderError(message) {
  document.getElementById("answer-abstained-badge").classList.add("hidden");
  document.getElementById("citation-warning-banner").classList.add("hidden");
  document.getElementById("diagnostics-panel").classList.add("hidden");
  generalAnswerView.classList.remove("hidden");
  shortlistView.classList.add("hidden");
  document.getElementById("answer-text").textContent = message;
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
      renderError(`Something went wrong: ${detail}`);
      return;
    }
    renderAnswer(await response.json());
  } catch (error) {
    renderError(
      "Could not reach the assistant. Check that the server is running, then try again."
    );
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
