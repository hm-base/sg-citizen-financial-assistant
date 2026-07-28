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
  };
}

function renderCitationWarning(result) {
  const banner = document.getElementById("citation-warning-banner");
  const warnings = result.citation_warning || [];
  if (!warnings.length) {
    banner.textContent = "";
    banner.classList.add("hidden");
    return;
  }
  const labels = warnings.map((pair) => (Array.isArray(pair) ? `[${pair.join(", ")}]` : String(pair)));
  banner.textContent =
    `Citation check: the answer cites ${warnings.length} source label(s) that are not in the ` +
    `retrieved sources below — ${labels.join(" ")}. Verify before relying on it.`;
  banner.classList.remove("hidden");
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

function renderResult(result) {
  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);

  document.getElementById("answer-text").textContent = result.answer;
  renderCitationWarning(result);

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

function renderError(message) {
  document.getElementById("answer-abstained-badge").classList.add("hidden");
  document.getElementById("citation-warning-banner").classList.add("hidden");
  document.getElementById("answer-text").textContent = message;
  document.getElementById("sources-list").innerHTML = "";
}

async function submitQuery(button, loadingLabel, url, payload) {
  if (button.disabled) return; // double-submit guard
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = loadingLabel;
  try {
    const response = await fetch(url, {
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
    renderResult(await response.json());
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
