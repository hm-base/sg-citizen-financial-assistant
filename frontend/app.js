const state = { mode: "general" };

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

function readControls() {
  return {
    top_k: parseInt(document.getElementById("control-top-k").value, 10),
    similarity_threshold: parseFloat(document.getElementById("control-threshold").value),
    retrieval_mode: document.getElementById("control-mode").value,
  };
}

function renderResult(result) {
  const badge = document.getElementById("answer-abstained-badge");
  badge.classList.toggle("hidden", !result.abstained);

  document.getElementById("answer-text").textContent = result.answer;

  const list = document.getElementById("sources-list");
  list.innerHTML = "";
  (result.sources || []).forEach((source) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="scheme-name">${source.scheme_name}</div>
      <div class="section">${source.section_or_page}</div>
      <div class="excerpt">${source.text}</div>
    `;
    list.appendChild(item);
  });
}

document.getElementById("ask-button").addEventListener("click", async () => {
  const question = document.getElementById("question-input").value.trim();
  if (!question) return;

  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, ...readControls() }),
  });
  renderResult(await response.json());
});

document.getElementById("profile-button").addEventListener("click", async () => {
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

  const response = await fetch("/api/profile-query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, free_text_question, ...readControls() }),
  });
  renderResult(await response.json());
});
