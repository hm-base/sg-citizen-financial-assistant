import gradio as gr

import config
from backend.main import get_llm_client, get_rag_index
from generation.pipeline import answer_general_question, answer_profile_question


def general_qa(question: str) -> str:
    rag_index = get_rag_index()
    llm_client = get_llm_client()
    result = answer_general_question(
        question,
        rag_index,
        llm_client,
        top_k=config.TOP_K,
        similarity_threshold=config.SIMILARITY_THRESHOLD,
        retrieval_mode=config.RETRIEVAL_MODE,
    )
    sources = "\n".join(f"- {s['scheme_name']} ({s['section_or_page']})" for s in result["sources"])
    return f"{result['answer']}\n\nSources:\n{sources}"


def profile_shortlist(citizenship, age, income_band, housing, employment, free_text) -> str:
    rag_index = get_rag_index()
    llm_client = get_llm_client()
    profile = {
        "citizenship": citizenship,
        "age": age,
        "monthly_income_band": income_band,
        "housing": housing,
        "employment": employment,
        "life_stage_tags": [],
    }
    result = answer_profile_question(
        profile,
        rag_index,
        llm_client,
        free_text_question=free_text,
        top_k=config.TOP_K,
        similarity_threshold=config.SIMILARITY_THRESHOLD,
        retrieval_mode=config.RETRIEVAL_MODE,
    )
    if result["abstained"]:
        return config.FALLBACK_MESSAGE

    lines = []
    for entry in result["shortlist"]:
        amount = entry["amount"] or "Amount not stated"
        chips = ", ".join(f"{c['doc_label']} · {c['section']}" for c in entry["citations"])
        lines.append(
            f"[{entry['group']}] {entry['scheme']} — {amount}\n"
            f"  {entry['reason']}\n"
            f"  Sources: {chips}"
        )
    return "\n\n".join(lines) if lines else config.FALLBACK_MESSAGE


with gr.Blocks(title="SG Citizen Financial Assistant (fallback)") as demo:
    gr.Markdown("# SG Citizen Financial Assistant — fallback demo UI")
    with gr.Tab("General Q&A"):
        question_box = gr.Textbox(label="Question")
        qa_output = gr.Textbox(label="Answer", lines=8)
        gr.Button("Ask").click(general_qa, inputs=question_box, outputs=qa_output)
    with gr.Tab("Personal Profile"):
        citizenship = gr.Dropdown(["Singapore Citizen", "PR", "Other"], label="Citizenship")
        age = gr.Number(label="Age")
        income_band = gr.Dropdown(["<$1.5k", "$1.5-3k", "$3-6k", ">$6k", "Prefer not to say"], label="Income band")
        housing = gr.Dropdown(["HDB", "Private", "Rental", "Other", "Prefer not to say"], label="Housing")
        employment = gr.Dropdown(["Employed", "Self-employed", "Unemployed", "Retired", "Student"], label="Employment")
        free_text = gr.Textbox(label="Optional question")
        profile_output = gr.Textbox(label="Shortlist", lines=10)
        gr.Button("Get shortlist").click(
            profile_shortlist,
            inputs=[citizenship, age, income_band, housing, employment, free_text],
            outputs=profile_output,
        )

if __name__ == "__main__":
    demo.launch()
