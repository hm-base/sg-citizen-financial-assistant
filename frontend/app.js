const state = { mode: "general" };

const THEME_STORAGE_KEY = "sg-financial-assistant-theme";
const themeToggleButton = document.getElementById("theme-toggle-button");

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  themeToggleButton.textContent = theme === "dark" ? "☀️ Light mode" : "🌙 Dark mode";
}

function initTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    applyTheme(stored);
    return;
  }
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark ? "dark" : "light");
}

themeToggleButton.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  const next = current === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem(THEME_STORAGE_KEY, next);
});

initTheme();

const generalPanel = document.getElementById("general-panel");
const profilePanel = document.getElementById("profile-panel");
const modeButtons = document.querySelectorAll(".mode-btn");

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    modeButtons.forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    state.mode = button.dataset.mode;
    generalPanel.classList.toggle("hidden", state.mode !== "general");
    profilePanel.classList.toggle("hidden", state.mode !== "profile");
  });
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

function renderThumbnail(source, item) {
  if (!source.thumbnail_path) return;
  const image = document.createElement("img");
  image.className = "source-thumbnail";
  image.src = thumbnailUrl(source.thumbnail_path);
  image.alt = `Thumbnail for ${source.scheme_name || "source"}`;
  image.loading = "lazy";
  item.appendChild(image);
}

const generalAnswerView = document.getElementById("general-answer-view");
const shortlistView = document.getElementById("shortlist-view");

function renderResult(result) {
  generalAnswerView.classList.remove("hidden");
  shortlistView.classList.add("hidden");

  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);

  document.getElementById("answer-text").textContent = result.answer;
  renderCitationWarning(result);
  renderDiagnostics(result.diagnostics);

  const list = document.getElementById("sources-list");
  list.innerHTML = "";
  (result.sources || []).forEach((source) => {
    const item = document.createElement("li");

    const schemeDiv = document.createElement("div");
    schemeDiv.className = "scheme-name";
    schemeDiv.textContent = source.scheme_name;
    item.appendChild(schemeDiv);

    const sectionDiv = document.createElement("div");
    sectionDiv.className = "section";
    sectionDiv.textContent = source.section_or_page;
    item.appendChild(sectionDiv);

    renderThumbnail(source, item);

    const excerptDiv = document.createElement("div");
    excerptDiv.className = "excerpt";
    excerptDiv.textContent = source.text;
    item.appendChild(excerptDiv);

    list.appendChild(item);
  });
}

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

function renderShortlist(result) {
  generalAnswerView.classList.add("hidden");
  shortlistView.classList.remove("hidden");

  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);
  renderDevWarnings(result.dev_warnings || []);
  renderDiagnostics(result.diagnostics);

  shortlistView.innerHTML = "";
  const entriesByGroup = { eligible: [], unclear: [], not_assessed: [] };
  (result.shortlist || []).forEach((entry) => entriesByGroup[entry.group].push(entry));

  GROUP_ORDER.forEach((group) => {
    const entries = entriesByGroup[group];
    if (!entries.length) return;

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

    entries.forEach((entry) => groupCard.appendChild(renderShortlistEntry(entry)));
    shortlistView.appendChild(groupCard);
  });
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
  document.getElementById("sources-list").innerHTML = "";
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
