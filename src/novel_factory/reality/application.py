"""Prompt and evidence checks shared by the model and PostgreSQL adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .domain import SourceUnit, digest


INSTRUCTIONS = """Extract candidate claims from this one Wikipedia source unit in its original language.
Return one JSON object only. Wikipedia prose is attributed source material, not accepted historical truth.
Use existing project mapping IDs when supported: SD-PEOPLE-01, SD-PEOPLE-02,
SD-POLITY-04, SD-TECH-01, SD-LANG-01, SD-LANG-02, EX-001, EX-005,
EX-012, EX-029, EX-031, RM-POWER-01, RM-CONCEPT-05, RM-TECH-04,
RM-TECH-07, IN-055, IN-060. Never invent a mapping ID.
H = historical event/state. K = independent knowledge/concept/content version.
B = a historical formulation, transmission, adoption, or actual application of K.
Keep a knowledge object distinct from when/where/who knew or used it; a script
and a book about that script are separate candidates. Do not equate a reign
period with a creation/publication date. Actor and affected person differ.
Only propose claims about events or human knowledge roughly before 1950.
Unclear dates remain unclear; later-written text can describe earlier history.
Do not fill gaps from memory. Do not assume a translated name is the same person.
Every candidate must cite this exact source_unit_id and a short, contiguous,
verbatim evidence_quote copied from SOURCE, including markup. If the source
does not support a detail, leave it unknown or omit that candidate.
Only propose B when the same unit supports a K candidate. For B,
related_candidate_index must point to that K's 0-based position in the list.
If no K is supported, omit B rather than inventing or leaving its link null.
Output {"source_unit_id":"...","candidates":[{"layer":"H|K|B",
"mapping_refs":["existing ID"],"subject":"...","predicate":"...",
"object":"...","time_text":null,"evidence_source_unit_id":"...",
"evidence_quote":"exact substring","related_candidate_index":null,
"uncertainty":null}],"unmapped_notes":[]}.
Return 0 to 6 candidates. No markdown fences."""


def make_prompt(unit: SourceUnit) -> str:
    unit.validate()
    return (
        INSTRUCTIONS + "\nsource_unit_id: " + unit.unit_id
        + "\nwiki_id: " + unit.wiki_id + "\nlanguage: " + unit.language
        + "\npage_title: " + unit.title + "\nSOURCE:\n" + unit.text
    )


def prompt_sha(unit: SourceUnit) -> str:
    return digest(make_prompt(unit).encode("utf-8"))


def can_schedule_attempt(status: str | None, has_raw_response: bool, retry_no_raw_failure: bool) -> bool:
    """A failed raw model output is evidence, not a replaceable retry slot."""
    return status is None or (retry_no_raw_failure and status in {"failed", "running"} and not has_raw_response)


@dataclass(frozen=True)
class CheckedCandidate:
    ordinal: int
    payload: dict
    status: str
    problems: tuple[str, ...]
    evidence_start_byte: int | None
    evidence_end_byte: int | None


def _decode(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        first, last = raw.find("{"), raw.rfind("}")
        if first < 0 or last <= first:
            raise ValueError("Model did not return a JSON object") from None
        parsed = json.loads(raw[first:last + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON root is not an object")
    return parsed


def check_response(raw: str, unit: SourceUnit, mapping_ids: set[str]) -> tuple[list[CheckedCandidate], list[str]]:
    parsed = _decode(raw)
    if parsed.get("source_unit_id") != unit.unit_id:
        raise ValueError("Model source_unit_id differs from DB source")
    items = parsed.get("candidates")
    if not isinstance(items, list) or len(items) > 6:
        raise ValueError("Model candidate list is missing or exceeds six")
    checked: list[CheckedCandidate] = []
    for ordinal, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("Candidate is not an object")
        problems: list[str] = []
        layer = item.get("layer")
        refs = item.get("mapping_refs")
        quote = item.get("evidence_quote")
        if layer not in {"H", "K", "B"}:
            problems.append("invalid_layer")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in mapping_ids for x in refs):
            problems.append("invalid_mapping_refs")
        if item.get("evidence_source_unit_id") != unit.unit_id:
            problems.append("wrong_evidence_unit")
        if any(not isinstance(item.get(x), str) or not item[x].strip() for x in ("subject", "predicate", "object")):
            problems.append("incomplete_relation")
        related = item.get("related_candidate_index")
        if layer == "B" and (not isinstance(related, int) or isinstance(related, bool) or related < 0 or related >= len(items) or not isinstance(items[related], dict) or items[related].get("layer") != "K"):
            problems.append("bridge_without_local_K")
        if related is not None and layer != "B":
            problems.append("unexpected_related_candidate")
        if not isinstance(quote, str) or not quote.strip():
            problems.append("missing_exact_quote")
            at = -1
        else:
            at = unit.text.find(quote)
            if at < 0 or unit.text.find(quote, at + 1) >= 0:
                problems.append("quote_not_unique_in_unit")
        start = unit.start_byte + len(unit.text[:at].encode("utf-8")) if at >= 0 and "quote_not_unique_in_unit" not in problems else None
        end = start + len(quote.encode("utf-8")) if start is not None else None
        checked.append(CheckedCandidate(ordinal, item, "held" if problems else "candidate_unreviewed", tuple(problems), start, end))
    for candidate in checked:
        if candidate.payload.get("layer") == "B" and candidate.status == "candidate_unreviewed":
            related = candidate.payload["related_candidate_index"]
            if checked[related].status == "held":
                problems = candidate.problems + ("bridge_to_held_K",)
                checked[candidate.ordinal] = CheckedCandidate(candidate.ordinal, candidate.payload, "held", problems, candidate.evidence_start_byte, candidate.evidence_end_byte)
    notes = parsed.get("unmapped_notes", [])
    return checked, [str(x) for x in notes] if isinstance(notes, list) else []
