import re

from config import FALLBACK_MESSAGE

GENERAL_QA_SYSTEM_RULES = f"""You are an assistant that answers questions about Singapore \
government subsidy schemes and tax reliefs using ONLY the context passages provided below. \
Each passage is labeled with a source ID.

Rules:
1. Answer only using facts present in the provided passages. Do not use outside knowledge.
2. For every factual claim, cite the source ID(s) it came from, in the form [scheme_name, section_or_page].
3. If the passages do not contain enough information to answer, respond with exactly: \
"{FALLBACK_MESSAGE}" Do not guess.
4. Keep answers concise and in plain language suitable for a member of the public.
"""

PROFILE_SYSTEM_RULES = f"""You help a Singapore resident understand which schemes in the provided \
passages they may be eligible for.

Rules:
1. Use ONLY the numbered context passages. No outside knowledge.
2. Output three sections only:
   - Possibly eligible - scheme name, why (criteria quoted/paraphrased from passages), \
amount/tier only if stated in passages, citations.
   - Likely not eligible / unclear - scheme appears in context but a stated criterion conflicts \
with the profile, or a required criterion is missing from passages.
   - Not assessed - do not invent schemes that are absent from the passages.
3. Never say "you are approved" or "you will receive." Use "based on the documents, you may be \
eligible if ..."
4. If income/age/citizenship thresholds are not in the passages, say so and put the scheme under \
Likely not eligible / unclear, even if thematically relevant.
5. Every factual claim must cite [scheme_name, section_or_page].
6. If passages are insufficient for any shortlist, respond exactly with: "{FALLBACK_MESSAGE}"
"""


def _format_passages(retrieved: list[dict]) -> str:
    lines = []
    for chunk in retrieved:
        label = f"[{chunk['scheme_name']}, {chunk['section_or_page']}]"
        lines.append(f"{label}\n{chunk['text']}")
    return "\n\n".join(lines)


def build_general_qa_prompt(question: str, retrieved: list[dict]) -> str:
    return (
        f"{GENERAL_QA_SYSTEM_RULES}\n\n"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )


def build_profile_prompt(profile: dict, retrieved: list[dict], free_text_question: str = "") -> str:
    question_line = free_text_question or "What can I get and roughly how much?"
    return (
        f"{PROFILE_SYSTEM_RULES}\n\n"
        f"User profile (bands only): {profile}\n\n"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question_line}\n"
        f"Answer:"
    )


QUERY_REWRITE_RULES = """Rewrite the user's question into a short search query for retrieving \
passages from official Singapore government scheme documents (ComCare, ElderFund, GST Voucher, \
CDC Vouchers, CHAS, Silver Support, Workfare, HDB grants, MediSave/MediShield, CPF schemes, and \
similar). Expand abbreviations and colloquial phrasing into the terms an official fact sheet would \
use. Return ONLY the rewritten query on a single line, with no preamble, quotes, or explanation."""


def build_query_rewrite_prompt(question: str) -> str:
    return f"{QUERY_REWRITE_RULES}\n\nQuestion: {question}\nRewritten query:"


def extract_cited_scheme_labels(answer: str) -> list[tuple[str, str]]:
    labels = []
    for bracket_content in re.findall(r"\[([^\[\]]+)\]", answer):
        for segment in bracket_content.split(";"):
            name, sep, location = segment.strip().partition(",")
            if sep:
                labels.append((name.strip(), location.strip()))
    return labels
