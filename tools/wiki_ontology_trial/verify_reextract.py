"""Check only source pins, output shape and exact quotes in the paired trial."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from reextract import MODEL, REVISION, evidence_for, make_prompt
from verify import mapping_ids


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object in model output") from None
        return json.loads(raw[start:end + 1])


def source_metadata(unit: dict, extra: dict | None, pages: Path) -> dict[str, dict]:
    sources = {unit["source_unit_id"]: {
        "source_id": unit["source_unit_id"], "kind": "baseline_wiki_excerpt",
        "source_sha256": unit["source_unit_sha256"],
        "text": unit["text"],
        "snapshot_id": unit["snapshot_id"], "shard_file": unit["shard_file"],
        "shard_sha256": unit["shard_sha256"], "page_id": unit["page_id"],
        "revision_id": unit["revision_id"], "slot_role": unit["slot_role"],
        "slot_text_sha256": unit["slot_text_sha256"],
        "slot_span_utf8": unit["slot_span_utf8"],
    }}
    for item in (extra or {}).get(unit["source_unit_id"], []):
        sources[item["source_id"]] = item
    for item in sources.values():
        if sha(item["text"].encode("utf-8")) != item["source_sha256"]:
            raise ValueError(f"Evidence content hash mismatch: {item['source_id']}")
        if item["kind"] in {"baseline_wiki_excerpt", "same_wiki_revision"}:
            page = json.loads((pages / f"page-{item['page_id']}.json").read_bytes())
            slot = page["slot_text"].encode("utf-8")
            start, end = item["slot_span_utf8"]
            if (page["revision_id"] != item["revision_id"]
                    or sha(slot) != item["slot_text_sha256"]
                    or slot[start:end] != item["text"].encode("utf-8")):
                raise ValueError(f"Wiki source span differs: {item['source_id']}")
    return sources


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--mode", choices=["wiki_only", "enriched"], required=True)
    p.add_argument("--extra-evidence", type=Path)
    p.add_argument("--pages", type=Path, required=True)
    p.add_argument("--result-dir", type=Path, required=True)
    p.add_argument("--mapping-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.mode == "enriched") != (args.extra_evidence is not None):
        raise ValueError("Only enriched mode takes extra evidence")
    if args.out.exists():
        raise FileExistsError(args.out)
    packet_raw = args.packet.read_bytes()
    packet = json.loads(packet_raw)
    extra_raw = args.extra_evidence.read_bytes() if args.extra_evidence else None
    extra = json.loads(extra_raw) if extra_raw else None
    known = mapping_ids(args.mapping_dir)
    units = []
    for unit in packet["units"]:
        sources = source_metadata(unit, extra, args.pages)
        prompt = make_prompt(unit, evidence_for(unit, extra))
        path = args.result_dir / f"{unit['source_unit_id']}.json"
        raw_result = path.read_bytes()
        result = json.loads(raw_result)
        if (result.get("source_unit_id") != unit["source_unit_id"]
                or result.get("source_unit_sha256") != unit["source_unit_sha256"]
                or result.get("packet_sha256") != sha(packet_raw)
                or result.get("extra_evidence_sha256") != (sha(extra_raw) if extra_raw else None)
                or result.get("mode") != args.mode
                or result.get("model") != MODEL or result.get("model_revision") != REVISION
                or result.get("prompt_sha256") != sha(prompt.encode("utf-8"))):
            raise ValueError(f"Result input or model pin differs: {path}")
        try:
            parsed = parse_response(result["raw_response"])
            if parsed.get("source_unit_id") != unit["source_unit_id"]:
                raise ValueError("Response source unit ID differs")
            if not all(isinstance(parsed.get(layer), list) for layer in ("K", "H", "B")):
                raise ValueError("Response H/K/B arrays are missing")
            parse_error = None
        except (ValueError, json.JSONDecodeError) as exc:
            parsed = {"K": [], "H": [], "B": [], "unresolved": []}
            parse_error = str(exc)
        k_ids = {item.get("id") for item in parsed["K"] if isinstance(item, dict)}
        seen_ids: set[str] = set()
        checked = []
        for layer in ("K", "H", "B"):
            for item in parsed[layer]:
                problems = []
                if not isinstance(item, dict):
                    checked.append({"layer": layer, "candidate": item,
                                    "status": "held", "problems": ["not_an_object"],
                                    "evidence_links": []})
                    continue
                identifier = item.get("id")
                if not isinstance(identifier, str) or identifier in seen_ids:
                    problems.append("missing_or_duplicate_local_id")
                else:
                    seen_ids.add(identifier)
                refs = item.get("mapping_refs")
                if not isinstance(refs, list) or any(ref not in known for ref in refs):
                    problems.append("unknown_mapping_ref")
                if layer == "B" and item.get("knowledge_ref") not in k_ids:
                    problems.append("bridge_without_local_K")
                if layer in {"H", "B"} and item.get("time_role") not in {
                    "event_time", "reign_interval", "other", "unknown"
                }:
                    problems.append("invalid_time_role")
                evidence = item.get("evidence")
                if not isinstance(evidence, list) or not evidence:
                    problems.append("no_evidence")
                    evidence = []
                links = []
                for link in evidence:
                    if not isinstance(link, dict) or link.get("source_id") not in sources:
                        problems.append("unknown_source_id")
                        continue
                    source = sources[link["source_id"]]
                    quote = link.get("quote")
                    if not isinstance(quote, str) or not quote.strip():
                        problems.append("missing_quote")
                        continue
                    text = source["text"]
                    if text.count(quote) != 1:
                        problems.append("quote_not_unique_in_source")
                        continue
                    local_start = len(text[:text.index(quote)].encode("utf-8"))
                    local_end = local_start + len(quote.encode("utf-8"))
                    base = source.get("slot_span_utf8", [0])[0]
                    links.append({"source_id": source["source_id"],
                                  "source_kind": source["kind"],
                                  "evidence_span_utf8": [base + local_start, base + local_end]})
                checked.append({"layer": layer, "candidate": item,
                                "status": "quote_linked_unreviewed" if not problems else "held",
                                "problems": sorted(set(problems)), "evidence_links": links})
        units.append({"source_unit_id": unit["source_unit_id"], "title": unit["title"],
                      "model_result_sha256": sha(raw_result), "parse_error": parse_error,
                      "sources_F": [{k: v for k, v in source.items() if k != "text"}
                                    for source in sources.values()],
                      "candidates": checked, "unresolved": parsed.get("unresolved", [])})
    report = {"mode": args.mode, "packet_sha256": sha(packet_raw),
              "extra_evidence_sha256": sha(extra_raw) if extra_raw else None,
              "model": MODEL, "model_revision": REVISION, "units": units,
              "release_status": "trial_candidates_only_no_reality_release"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "units": len(units),
                      "candidates": sum(len(u["candidates"]) for u in units),
                      "quote_linked": sum(c["status"] == "quote_linked_unreviewed"
                                          for u in units for c in u["candidates"]),
                      "parse_errors": sum(bool(u["parse_error"]) for u in units)}))


if __name__ == "__main__":
    main()
