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

const topKInput = document.getElementById("control-top-k");
const thresholdInput = document.getElementById("control-threshold");
const modeSelect = document.getElementById("control-mode");
const providerIndicator = document.getElementById("provider-indicator");

// Defaults live in config.py; the UI must not hardcode its own copies.
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
