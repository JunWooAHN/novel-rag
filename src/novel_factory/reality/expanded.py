"""Pure full-slot segmentation and source-span candidate contract.

The source page, not the model output, owns byte coordinates and quote text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .application import CheckedCandidate, _decode
from .domain import SourceUnit, digest


SEGMENTATION_VERSION = "full-slot-utf8-v1"
PROMPT_VERSION = "indexed-evidence-v1"


def validate_fixture_inventory(expected_links: dict, receipts: list[dict],
                               manifest: list[dict]) -> dict:
    """Match the frozen five-target relation denominator before any DB write."""
    expected = {}
    for target in expected_links["targets"]:
        links = target["wikipedia_sitelinks"]
        if len(links) != target["wikipedia_sitelink_count"]:
            raise ValueError("Frozen sitelink target count differs from entries")
        expected.update({(target["target"],wiki_id,link["title"]):target["qid"]
                         for wiki_id,link in links.items()})
    received = [(x["target"],x["wiki_id"],x["requested_title"]) for x in receipts]
    if len(received) != len(set(received)) or set(received) != set(expected):
        raise ValueError(f"Receipt denominator differs from frozen sitelinks: expected={len(expected)}, got={len(received)}")
    if any(x.get("qid") != expected[(x["target"],x["wiki_id"],x["requested_title"])] for x in receipts):
        raise ValueError("Receipt QID differs from frozen external sitelink identity")
    if any(not x.get("source_file") or not x.get("source_sha256") for x in receipts
           if x["status"] == "success"):
        raise ValueError("Successful relation lacks a pinned source file")
    successful_files = {}
    for item in receipts:
        if item["status"] != "success":
            continue
        old=successful_files.get(item["source_file"])
        if old is not None and old != item["source_sha256"]:
            raise ValueError("Same source file has different receipt SHA")
        successful_files[item["source_file"]]=item["source_sha256"]
    manifest_files = {x["source_file"]:x["source_sha256"] for x in manifest}
    if len(manifest_files) != len(manifest) or manifest_files != successful_files:
        raise ValueError("Source manifest differs from successful receipt files")
    return {"expected_relations":len(expected),"successful_sources":len(manifest_files)}


def split_full_slot(source: dict, max_bytes: int = 1800) -> list[SourceUnit]:
    """Cover every UTF-8 byte exactly once, preferring line boundaries."""
    if max_bytes < 128:
        raise ValueError("max_bytes is too small for a full-slot source unit")
    raw = source["wikitext"].encode("utf-8")
    if digest(raw) != source["content_sha256"]:
        raise ValueError("Full slot SHA differs from fixed source")
    units: list[SourceUnit] = []
    start = 0
    while start < len(raw):
        end = min(start + max_bytes, len(raw))
        if end < len(raw):
            while end > start and raw[end] & 0xC0 == 0x80:
                end -= 1
            if end <= start:
                raise ValueError("Cannot find UTF-8 boundary in unit")
            line_end = raw.rfind(b"\n", start + max_bytes // 2, end)
            if line_end >= 0:
                end = line_end + 1
        chunk = raw[start:end].decode("utf-8")
        identity = ":".join(str(source[k]) for k in ("wiki_id", "page_id", "revision_id", "slot"))
        unit = SourceUnit(
            unit_id=f"{identity}:byte-{start}-{end}",
            wiki_id=source["wiki_id"], page_id=int(source["page_id"]),
            revision_id=int(source["revision_id"]), slot=source["slot"],
            language=source["language"], title=source["title"],
            start_byte=start, end_byte=end, text=chunk, text_sha256=digest(raw[start:end]),
        )
        unit.validate()
        units.append(unit)
        start = end
    if b"".join(unit.text.encode("utf-8") for unit in units) != raw:
        raise AssertionError("Segmenter did not cover source bytes exactly")
    return units


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    start_byte: int
    end_byte: int
    text: str


def evidence_spans(unit: SourceUnit) -> list[EvidenceSpan]:
    """Use stable, short line/sentence spans; blank bytes remain in the source unit."""
    spans: list[EvidenceSpan] = []
    start_char = 0
    boundaries = [m.end() for m in re.finditer(r"[.!?。！？](?=\s|$)|\n", unit.text)]
    if not boundaries or boundaries[-1] != len(unit.text):
        boundaries.append(len(unit.text))
    for end_char in boundaries:
        left = start_char
        while left < end_char:
            right = min(left + 600, end_char)
            while len(unit.text[left:right].encode("utf-8")) > 600:
                right -= 1
            if right <= left:
                raise ValueError("Cannot split evidence at UTF-8 boundary")
            part = unit.text[left:right]
            if part.strip():
                start_byte = unit.start_byte + len(unit.text[:left].encode("utf-8"))
                end_byte = unit.start_byte + len(unit.text[:right].encode("utf-8"))
                spans.append(EvidenceSpan(f"s{len(spans):03d}", start_byte, end_byte, part))
            left = right
        start_char = end_char
    return spans


INSTRUCTIONS = """Extract H/K/B candidates from this ONE fixed Wikipedia source unit, in its original language.
The text is a source claim, not accepted historical truth. Return JSON only.
H = historical event/state; K = independent knowledge/concept/content version;
B = a specific historical formulation, transmission, adoption, or application of K.
Use only facts supported by the numbered SOURCE_SPANS; do not fill gaps from memory.
For evidence, return evidence_span_id exactly, never retype a quote. The program
will attach the original UTF-8 text and byte range. If a claim needs more than
one noncontiguous span, leave it unresolved instead of citing too little.
Preserve qualifiers such as forced, likely, uncertainty, actor vs affected,
place vs object, and original calendar wording. A death has no required object;
do not put the place or date into object. A reign period is not a creation date.
The source may name an entity differently in another language; do not merge it.
Only propose claims about events or human knowledge roughly before 1950.
Unclear dates remain unclear, and later-written prose may describe earlier history.
Mark temporal_scope as pre_1950, post_1950, or unknown for the CLAIMED event
or knowledge version, never for the Wikipedia revision date. Omit clear later
claims. If a boundary cannot be supported, say unknown; it will be held.
For B, related_candidate_index points to a K candidate in THIS response when
one is supported here. If K was defined in another unit, keep the B evidence
as a HELD candidate with related_candidate_index=null and a short
related_knowledge_hint. Do not invent K merely to create B. A later review
must resolve the cross-unit identity before B can become an active relation.
Use only provided mapping IDs. Return zero candidates when no claim is supported.
If you cannot interpret the original language well enough, set language_handling
to unsupported; if uncertain, set uncertain. Neither is a zero-claim success.
Output {"source_unit_id":"...","candidates":[{"layer":"H|K|B",
"mapping_refs":["existing mapping ID"],"subject":"...","predicate":"...",
"object":null,"actor":null,"affected":null,"place":null,
"time_text":null,"calendar_basis":null,"force":null,"uncertainty":null,
"temporal_scope":"pre_1950|post_1950|unknown",
"evidence_span_id":"s000","related_candidate_index":null,
"related_knowledge_hint":null}],
"language_handling":"processed|unsupported|uncertain",
"language_reason":null,"unmapped_notes":[]}.
Return at most 10 candidates. No markdown fences."""


def make_indexed_prompt(unit: SourceUnit, mapping_ids: set[str]) -> str:
    unit.validate()
    spans = evidence_spans(unit)
    return (
        INSTRUCTIONS + "\nsource_unit_id: " + unit.unit_id
        + "\nwiki_id: " + unit.wiki_id + "\nlanguage: " + unit.language
        + "\npage_title: " + unit.title
        + "\nmapping_ids: " + ", ".join(sorted(mapping_ids))
        + "\nSOURCE_SPANS:\n"
        + json.dumps([{"id": span.span_id, "text": span.text} for span in spans], ensure_ascii=False)
    )


def indexed_prompt_sha(unit: SourceUnit, mapping_ids: set[str]) -> str:
    return digest(make_indexed_prompt(unit, mapping_ids).encode("utf-8"))


def plan_embedding_spans(unit: SourceUnit, token_length, max_bytes: int = 600) -> list[tuple[int, int, str]]:
    """Plan exact source spans of at most 512 E5 tokens, without truncation."""
    if max_bytes < 16:
        raise ValueError("Embedding span size is too small")
    result: list[tuple[int, int, str]] = []

    def add(text: str, start: int) -> None:
        raw = text.encode("utf-8")
        if not text.strip():
            return
        if token_length(text) > 512:
            if len(text) < 2:
                raise ValueError("Single character exceeds E5 token limit")
            mid = len(text) // 2
            add(text[:mid], start)
            add(text[mid:], start + len(text[:mid].encode("utf-8")))
            return
        result.append((start, start + len(raw), text))

    raw = unit.text.encode("utf-8")
    at = 0
    while at < len(raw):
        end = min(at + max_bytes, len(raw))
        if end < len(raw):
            while end > at and raw[end] & 0xC0 == 0x80:
                end -= 1
        if end <= at:
            raise ValueError("Cannot split embedding span at UTF-8 boundary")
        add(raw[at:end].decode("utf-8"), unit.start_byte + at)
        at = end
    return result


def check_indexed_response(
    raw: str, unit: SourceUnit, mapping_ids: set[str]
) -> tuple[list[CheckedCandidate], list[str]]:
    parsed = _decode(raw)
    if parsed.get("source_unit_id") != unit.unit_id:
        raise ValueError("Model source_unit_id differs from DB source")
    items = parsed.get("candidates")
    if not isinstance(items, list) or len(items) > 10:
        raise ValueError("Model candidate list is missing or exceeds ten")
    spans = {s.span_id: s for s in evidence_spans(unit)}
    language_handling = parsed.get("language_handling")
    if language_handling not in {"processed", "unsupported", "uncertain"}:
        language_handling = "uncertain"
    checked: list[CheckedCandidate] = []
    for ordinal, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("Candidate is not an object")
        problems: list[str] = []
        if language_handling != "processed":
            problems.append("language_" + language_handling)
        layer = item.get("layer")
        refs = item.get("mapping_refs")
        if layer not in {"H", "K", "B"}:
            problems.append("invalid_layer")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in mapping_ids for x in refs):
            problems.append("invalid_mapping_refs")
        if not all(isinstance(item.get(x), str) and item[x].strip() for x in ("subject", "predicate")):
            problems.append("incomplete_relation")
        if layer in {"K", "B"} and (not isinstance(item.get("object"), str)
                                     or not item["object"].strip()):
            problems.append("missing_knowledge_object")
        for field in ("object", "actor", "affected", "place", "time_text", "calendar_basis", "uncertainty"):
            if item.get(field) is not None and not isinstance(item[field], str):
                problems.append("invalid_" + field)
        if item.get("force") not in {None, "forced", "voluntary", "unknown"}:
            problems.append("invalid_force")
        if item.get("temporal_scope") == "post_1950":
            problems.append("out_of_scope_after_rough_1950")
        elif item.get("temporal_scope") != "pre_1950":
            problems.append("temporal_scope_unresolved")
        span_id = item.get("evidence_span_id")
        span = spans.get(span_id) if isinstance(span_id, str) else None
        if span is None:
            problems.append("unknown_evidence_span_id")
        else:
            if re.search(r"\bforced\b", span.text, flags=re.I) and item.get("force") != "forced":
                problems.append("missing_forced_qualifier")
            if re.search(r"\blikely\b", span.text, flags=re.I) and not item.get("uncertainty"):
                problems.append("missing_likely_qualifier")
            if "음력" in span.text and item.get("time_text") and item.get("calendar_basis") != "lunar":
                problems.append("missing_lunar_basis")
        if layer == "H" and item.get("place") and item.get("object") == item.get("place"):
            problems.append("place_as_object")
        related = item.get("related_candidate_index")
        if layer == "B":
            if related is None and isinstance(item.get("related_knowledge_hint"), str) and item["related_knowledge_hint"].strip():
                problems.append("cross_unit_K_unresolved")
            elif (not isinstance(related, int) or isinstance(related, bool)
                  or related < 0 or related >= len(items) or not isinstance(items[related], dict)
                  or items[related].get("layer") != "K"):
                problems.append("bridge_without_local_K")
        if layer != "B" and related is not None:
            problems.append("unexpected_related_candidate")
        payload = dict(item)
        payload["evidence_source_unit_id"] = unit.unit_id
        payload["evidence_quote"] = span.text if span else None
        checked.append(CheckedCandidate(
            ordinal, payload, "held" if problems else "candidate_unreviewed", tuple(problems),
            span.start_byte if span else None, span.end_byte if span else None,
        ))
    for candidate in tuple(checked):
        if candidate.payload.get("layer") == "B" and candidate.status == "candidate_unreviewed":
            related = candidate.payload["related_candidate_index"]
            if checked[related].status == "held":
                checked[candidate.ordinal] = CheckedCandidate(
                    candidate.ordinal, candidate.payload, "held",
                    candidate.problems + ("bridge_to_held_K",),
                    candidate.evidence_start_byte, candidate.evidence_end_byte,
                )
    notes = parsed.get("unmapped_notes", [])
    output_notes = [str(x) for x in notes] if isinstance(notes, list) else []
    if language_handling != "processed":
        output_notes.append("LANGUAGE_" + language_handling.upper())
        if parsed.get("language_reason"):
            output_notes.append(str(parsed["language_reason"])[:500])
    return checked, output_notes
