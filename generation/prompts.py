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
6. If the user mentions several life situations in one message (for example unemployment, a \
young child, and caregiving), cover each situation that has supporting passages — do not \
answer only the single best-matching scheme and ignore the others.
7. Prior chat turns (if any) are only for resolving references such as "that scheme" or \
"how much is it?". Do not treat prior assistant text as evidence. Eligibility and amounts \
must still come from the passages below.
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
4. Cover EACH profile facet that has a matching passage — do not skip a facet because another is \
stronger. In particular: employment Unemployed -> include ComCare / SkillsFuture / Career Conversion \
/ Workfare when those passages are present; Has young child(ren) -> Baby Bonus when present; \
Caregiver -> Home Caregiving Grant when present.
5. Prefer listing schemes from the passages that relate to any stated profile facet (age, child, \
caregiver, housing, income, employment). Use condition state "not_checked" when the profile lacks \
a fact needed to judge a criterion. Return [] only when no passage is about any scheme relevant to \
the profile or free-text question.
6. Prior chat turns (if any) are only for resolving references. Do not copy schemes from prior \
assistant text unless the passages below also support them.
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


def format_chat_history(history: list[dict] | None, *, max_chars_per_turn: int = 600) -> str:
    """Compact prior turns for prompts. Empty string when there is no history."""
    if not history:
        return ""
    lines: list[str] = []
    for turn in history:
        role = str(turn.get("role") or "").strip().lower()
        content = " ".join(str(turn.get("content") or "").split())
        if role not in ("user", "assistant") or not content:
            continue
        if len(content) > max_chars_per_turn:
            content = content[: max_chars_per_turn - 1].rstrip() + "…"
        label = "Resident" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    if not lines:
        return ""
    return "Prior conversation (for reference resolution only):\n" + "\n".join(lines)


def build_general_qa_prompt(
    question: str,
    retrieved: list[dict],
    history: list[dict] | None = None,
) -> str:
    history_block = format_chat_history(history)
    history_section = f"{history_block}\n\n" if history_block else ""
    return (
        f"{GENERAL_QA_SYSTEM_RULES}\n\n"
        f"{history_section}"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )


def build_profile_shortlist_prompt(
    profile: dict,
    retrieved: list[dict],
    free_text_question: str = "",
    history: list[dict] | None = None,
) -> str:
    question_line = free_text_question or "What can I get and roughly how much?"
    allowed_ids = ", ".join(chunk["chunk_id"] for chunk in retrieved)
    history_block = format_chat_history(history)
    history_section = f"{history_block}\n\n" if history_block else ""
    return (
        f"{PROFILE_SHORTLIST_SYSTEM_RULES}\n\n"
        f"User profile (bands only): {profile}\n\n"
        f"{history_section}"
        f"Allowed chunk ids: [{allowed_ids}]\n\n"
        f"Context passages:\n{_format_passages_with_chunk_ids(retrieved)}\n\n"
        f"Question: {question_line}\n"
        f"JSON array:"
    )


PROFILE_EXTRACT_SYSTEM_RULES = """Extract a structured resident profile from the free-text \
question below, as if filling the Personal eligibility shortlist form.

Output ONLY a raw JSON object (no markdown code fences, no commentary, no text before or after it) \
with exactly these fields:

{
  "citizenship": "Singapore Citizen" | "PR" | "Other" | null,
  "age": integer or null,
  "household_size": integer or null,
  "monthly_income_band": "<$1.5k" | "$1.5-3k" | "$3-6k" | ">$6k" | "Prefer not to say" | null,
  "housing": "HDB" | "Private" | "Rental" | "Other" | "Prefer not to say" | null,
  "employment": "Employed" | "Self-employed" | "Unemployed" | "Retired" | "Student" | "Platform worker" | null,
  "life_stage_tags": [string, ...]
}

life_stage_tags may only use values from this closed list:
"Has young child(ren)", "Caregiver", "Senior (65+)", "Pioneer/Merdeka Generation",
"I have a disability", "PWD in household", "Own more than 1 property".

Rules:
1. Infer only what the text clearly supports. Use null / [] when unknown -- do not guess.
2. "I am unemployed" / looking for work / retrenched -> employment "Unemployed". A working spouse \
does NOT make the resident Employed.
3. Caring for a parent / dementia / regular caregiving -> include "Caregiver".
4. Young child / toddler / baby / "N yo son/daughter" (about age 7 or under) -> include \
"Has young child(ren)".
5. Resident age 65 or above -> include "Senior (65+)".
6. Do not invent income or housing if not stated.
7. If prior conversation is provided, you may carry forward profile facts the resident already \
stated earlier in this chat, unless the latest message clearly overrides them.
"""


def build_profile_extract_prompt(question: str, history: list[dict] | None = None) -> str:
    history_block = format_chat_history(history)
    history_section = f"\n\n{history_block}" if history_block else ""
    return (
        f"{PROFILE_EXTRACT_SYSTEM_RULES}{history_section}\n\n"
        f"Question: {question}\nJSON object:"
    )


GENERAL_QA_FROM_SHORTLIST_SYSTEM_RULES = f"""You answer questions about Singapore government \
subsidy schemes and tax reliefs using ONLY:
(1) the eligibility shortlist below (already assessed against an inferred profile), and
(2) the context passages provided.

Each passage is labeled with a source ID.

Rules:
1. Answer the user's question in plain language. Prefer covering schemes from the shortlist that \
relate to their question or situation.
2. For every factual claim, cite the source ID(s) it came from, in the form [scheme_name, section_or_page].
3. Never say they are approved, will receive, or definitely qualify. Use the shortlist group and \
condition states to qualify language (for example "may be relevant", "unclear because…").
4. If the shortlist and passages together do not support an answer, respond with exactly: \
"{FALLBACK_MESSAGE}" Do not guess.
5. If several life situations appear (for example unemployment, a young child, and caregiving), \
cover each that has shortlist or passage support -- do not collapse to a single scheme.
6. Keep answers concise and suitable for a member of the public.
7. Prior chat turns (if any) are only for resolving references. Do not treat them as evidence.
"""


def _format_shortlist_for_prompt(shortlist: list[dict]) -> str:
    lines = []
    for entry in shortlist:
        conditions = entry.get("conditions") or []
        cond_bits = [
            f"{c.get('label')}: {c.get('state')}"
            for c in conditions
            if isinstance(c, dict) and c.get("label")
        ]
        lines.append(
            f"- [{entry.get('group', 'not_assessed')}] {entry.get('scheme', '')}\n"
            f"  reason: {entry.get('reason', '')}\n"
            f"  amount: {entry.get('amount')}\n"
            f"  conditions: {'; '.join(cond_bits) if cond_bits else '(none stated)'}\n"
            f"  changer: {entry.get('changer', '')}"
        )
    return "\n".join(lines) if lines else "(empty shortlist)"


def build_general_qa_from_shortlist_prompt(
    question: str,
    profile: dict,
    shortlist: list[dict],
    retrieved: list[dict],
    history: list[dict] | None = None,
) -> str:
    history_block = format_chat_history(history)
    history_section = f"{history_block}\n\n" if history_block else ""
    return (
        f"{GENERAL_QA_FROM_SHORTLIST_SYSTEM_RULES}\n\n"
        f"{history_section}"
        f"Inferred profile (bands only): {profile}\n\n"
        f"Eligibility shortlist:\n{_format_shortlist_for_prompt(shortlist)}\n\n"
        f"Context passages:\n{_format_passages(retrieved)}\n\n"
        f"Question: {question}\n"
        f"Answer:"
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
5. If prior conversation is provided, resolve pronouns and follow-ups ("that one", "how much", \
"am I eligible") into a standalone rewritten query naming the scheme and facet. Do not leave \
underspecified references in "rewritten".
"""


def build_query_rewrite_prompt(
    question: str,
    profile: dict | None = None,
    history: list[dict] | None = None,
) -> str:
    profile_line = (
        f"\n\nResident profile (bands only, in scope for this rewrite): {profile}" if profile else ""
    )
    history_block = format_chat_history(history)
    history_section = f"\n\n{history_block}" if history_block else ""
    return (
        f"{QUERY_REWRITE_SCHEMA_RULES}{profile_line}{history_section}\n\n"
        f"Question: {question}\nJSON object:"
    )


def extract_cited_scheme_labels(answer: str) -> list[tuple[str, str]]:
    labels = []
    for bracket_content in re.findall(r"\[([^\[\]]+)\]", answer):
        for segment in bracket_content.split(";"):
            name, sep, location = segment.strip().partition(",")
            if sep:
                labels.append((name.strip(), location.strip()))
    return labels
