"""Link trial candidates back to exact UTF-8 spans; never release them as facts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from run import MODEL, REVISION, make_prompt


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def mapping_ids(folder: Path) -> set[str]:
    ids: set[str] = set()
    for file in folder.glob("*.csv"):
        with file.open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                if row:
                    ids.add(row[0])
    return ids


def decode_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        first, last = raw.find("{"), raw.rfind("}")
        if first < 0 or last <= first:
            raise ValueError("Model returned no JSON object") from None
        return json.loads(raw[first : last + 1])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--result-dir", type=Path, required=True)
    p.add_argument("--mapping-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    packet_raw = args.packet.read_bytes()
    packet = json.loads(packet_raw)
    known = mapping_ids(args.mapping_dir)
    verified = []
    for unit in packet["units"]:
        path = args.result_dir / f"{unit['source_unit_id']}.json"
        raw = path.read_bytes()
        result = json.loads(raw)
        if (result["source_unit_id"] != unit["source_unit_id"]
                or result["source_unit_sha256"] != unit["source_unit_sha256"]
                or unit["source_unit_sha256"] != sha(unit["text"].encode("utf-8"))
                or result["packet_sha256"] != sha(packet_raw)
                or result.get("model") != MODEL
                or result.get("model_revision") != REVISION
                or result.get("prompt_sha256") != sha(make_prompt(unit).encode("utf-8"))):
            raise ValueError(f"Pinned input mismatch: {path}")
        try:
            parsed = decode_response(result["raw_response"])
        except (ValueError, json.JSONDecodeError):
            parsed = {"source_unit_id": unit["source_unit_id"], "candidates": [],
                      "parse_error": "Model response was not valid JSON"}
        if parsed.get("source_unit_id") != unit["source_unit_id"]:
            raise ValueError(f"Model source unit ID differs: {path}")
        candidates = []
        for item in parsed.get("candidates", []):
            quote = item.get("evidence_quote")
            refs = item.get("mapping_refs", [])
            problems = []
            if item.get("layer") not in {"H", "K", "B"}:
                problems.append("unknown_layer")
            if not isinstance(refs, list) or any(ref not in known for ref in refs):
                problems.append("unknown_mapping_ref")
            if not isinstance(quote, str) or not quote.strip():
                problems.append("missing_evidence_quote")
                positions = []
            else:
                text = unit["text"]
                positions = []
                start = 0
                while (at := text.find(quote, start)) >= 0:
                    positions.append(at)
                    start = at + 1
            if len(positions) != 1:
                problems.append("evidence_quote_not_unique_in_unit")
            span = None
            if len(positions) == 1:
                start_byte = len(unit["text"][: positions[0]].encode("utf-8"))
                span = [unit["slot_span_utf8"][0] + start_byte,
                        unit["slot_span_utf8"][0] + start_byte + len(quote.encode("utf-8"))]
            candidates.append({"candidate": item, "slot_evidence_span_utf8": span,
                               "status": "candidate_unreviewed" if not problems else "held",
                               "problems": problems})
        verified.append({
            "source_unit_id": unit["source_unit_id"],
            "page_title": unit["title"],
            "F_provenance": {key: unit[key] for key in (
                "snapshot_id", "shard_file", "shard_sha256", "page_id", "revision_id",
                "revision_timestamp", "slot_role", "slot_text_sha256", "slot_span_utf8")},
            "model_result_sha256": sha(raw),
            "parse_error": parsed.get("parse_error"),
            "candidates": candidates,
            "unmapped_notes": parsed.get("unmapped_notes", []),
        })
    report = {"packet_sha256": sha(packet_raw), "units": verified,
              "release_status": "trial_candidates_only_no_reality_release"}
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"units": len(verified),
                      "candidates": sum(len(x["candidates"]) for x in verified),
                      "held": sum(c["status"] == "held" for x in verified for c in x["candidates"])}))


if __name__ == "__main__":
    main()
