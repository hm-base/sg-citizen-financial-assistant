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
5. If the user describes their personal situation and asks what they may qualify for / be \
eligible for / get: do NOT use the fallback merely because the knowledge base is incomplete \
for every scheme or every household detail. From the passages, list schemes that appear \
relevant to the facts they stated; for each, say which stated facts match published criteria \
and what is unknown. Never say they are approved, will receive, or definitely qualify. Use \
the fallback only when no passage is relevant to any of their stated facts.
"""

#: Grouping is derived in code from each entry's `conditions`, never taken from the
#: model's prose -- see generation.pipeline._derive_group. The model only reports
#: per-condition state; it does not decide which bucket an entry lands in.
PROFILE_SHORTLIST_SYSTEM_RULES = """You help a Singapore resident understand which schemes in the \
provided passages they may be eligible for, based only on the profile and passages given.

Output ONLY a raw JSON array (no markdown code fences, no commentary, no text before or after it). \
Each element is an object with exactly these fields:

{
  "scheme": string -- the scheme's plain name (not the document title),
  "reason": string -- ONE plain-language sentence, sentence case, under 25 words, no markdown, \
stating what about this profile matched or did not match. Do not restate the criteria as a \
question ("you may be eligible if..."); say what matched. Expand any acronym the first time it \
appears in the sentence.,
  "amount": string or null -- a dollar figure or payout tier, ONLY if the passages state one \
verbatim. null if no figure is stated -- do not describe benefit types here.,
  "conditions": [ {"label": string, "state": "met" | "not_met" | "not_checked"} ] -- every \
eligibility criterion the passages state for this scheme, each judged against the profile. Use \
"not_checked" only when the profile has no information to judge that criterion. Use an empty list \
only if the passages state no evaluable criteria at all for this scheme.,
  "changer": string -- ONE plain-language sentence: what fact, if different, would change this \
scheme's assessment.,
  "citation_chunk_ids": [string, ...] -- the exact chunk id(s) (from the "Allowed chunk ids" list \
below) that support this entry. Every id you use MUST come from that list -- never invent, guess, \
or reuse an id that is not listed. List each distinct source only once.
}

Rules:
1. Use ONLY the numbered context passages below. No outside knowledge, no invented schemes.
2. Every entry's citation_chunk_ids must be a subset of the allowed chunk ids provided. Do not cite \
a chunk id that is not in that list.
3. Never say "you are approved" or "you will receive."
4. If the passages are insufficient to produce any entry, return an empty JSON array: []
"""


def _format_passages(retrieved: list[dict]) -> str:
    lines = []
    for chunk in retrieved:
        name = chunk.get("display_name") or chunk["scheme_name"]
        label = f"[{name}, {chunk['section_or_page']}]"
        lines.append(f"{label}\n{chunk['text']}")
    return "\n\n".join(lines)


def _format_passages_with_chunk_ids(retrieved: list[dict]) -> str:
    lines = []
    for chunk in retrieved:
        name = chunk.get("display_name") or chunk["scheme_name"]
        label = f"[chunk_id: {chunk['chunk_id']} | {name}, {chunk['section_or_page']}]"
        lines.append(f"{label}\n{chunk['text']}")
    return "\n\n".join(lines)


def build_general_qa_prompt(question: str, retrieved: list[dict]) -> str:
    return (
        f"{GENERAL_QA_SYSTEM_RULES}\n\n"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )


def build_profile_shortlist_prompt(
    profile: dict, retrieved: list[dict], free_text_question: str = ""
) -> str:
    question_line = free_text_question or "What can I get and roughly how much?"
    allowed_ids = ", ".join(chunk["chunk_id"] for chunk in retrieved)
    return (
        f"{PROFILE_SHORTLIST_SYSTEM_RULES}\n\n"
        f"User profile (bands only): {profile}\n\n"
        f"Allowed chunk ids: [{allowed_ids}]\n\n"
        f"Context passages:\n{_format_passages_with_chunk_ids(retrieved)}\n\n"
        f"Question: {question_line}\n"
        f"JSON array:"
    )


QUERY_REWRITE_SCHEMA_RULES = """Rewrite the resident's question into terms official Singapore \
government scheme documents use, so retrieval can find the right passages.

Output ONLY a raw JSON object (no markdown code fences, no commentary, no text before or after it):

{
  "rewritten": string -- one dense query in scheme terminology, optimized for retrieval,
  "subQueries": [string, ...] -- 2-4 facet queries covering distinct aspects (e.g. eligibility, \
amount, application process). Empty array if the question is already narrow and single-facet.,
  "ops": [ {"kind": "expanded" | "resolved" | "named" | "added" | "dropped", "detail": string} ] \
-- one entry per real change you made. Empty array if the question was already precise -- do not \
pad it with invented changes.,
  "inferredSchemes": [string, ...] -- likely scheme name(s) this question is about, if identifiable.
}

Rules:
1. Expand relationship and colloquial terms into scheme vocabulary (e.g. "my mother" -> parent/\
recipient, "top up" -> cash top-up to CPF Retirement Account, "my flat" -> housing type / annual \
value).
2. Name the likely scheme(s) in "rewritten" so exact-match keyword search can find it.
3. Add implied facets the answer needs even if unstated (caps, citizenship conditions, qualifying \
period, Year of Assessment) -- but never invent constraints the resident did not state.
4. If the question is already precise, return it unchanged in "rewritten" with an empty ops array.
"""


def build_query_rewrite_prompt(question: str, profile: dict | None = None) -> str:
    profile_line = (
        f"\n\nResident profile (bands only, in scope for this rewrite): {profile}" if profile else ""
    )
    return f"{QUERY_REWRITE_SCHEMA_RULES}{profile_line}\n\nQuestion: {question}\nJSON object:"


def extract_cited_scheme_labels(answer: str) -> list[tuple[str, str]]:
    labels = []
    for bracket_content in re.findall(r"\[([^\[\]]+)\]", answer):
        for segment in bracket_content.split(";"):
            name, sep, location = segment.strip().partition(",")
            if sep:
                labels.append((name.strip(), location.strip()))
    return labels
