"""Join fixed old A/B2 review packets to the new YAGO A/B2 result rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


SELECTION_SHA = "45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0"
NEW_RUNS = {"YAGO-A": "fixed100-YAGO-A-20260928",
            "YAGO-B2": "fixed100-YAGO-B2-20260928"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arm_view(row: sqlite3.Row) -> dict:
    checked = json.loads(row["validation_json"]) if row["validation_json"] else None
    raw = row["raw_text"] if checked is None else None
    finish_reason = None
    if row["response_bytes"]:
        try:
            finish_reason = json.loads(row["response_bytes"])["choices"][0].get("finish_reason")
        except (ValueError, KeyError, IndexError, TypeError):
            pass
    return {"status": row["status"], "http_status": row["http_status"],
            "finish_reason": finish_reason, "output_tokens": row["output_tokens"],
            "input_tokens": row["input_tokens"], "baseline_input_tokens": row["baseline_input_tokens"],
            "prompt_sha256": row["prompt_sha256"], "response_sha256": row["response_sha256"],
            "error_type": row["error_type"], "error_detail": row["error_detail"],
            "validated_candidates": checked, "raw_text_if_unparsed": raw}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-packets", type=Path, required=True)
    parser.add_argument("--new-sqlite", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--kg-context", type=Path, required=True)
    parser.add_argument("--phase", choices=["A", "final"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight = json.loads(args.preflight.read_text())
    context = json.loads(args.kg_context.read_text())
    if preflight["selection_sha256"] != SELECTION_SHA or preflight["kg_context_sha256"] != sha(args.kg_context):
        raise ValueError("Preflight/context differs")
    preflight_by_id = {row["unit_id"]: row for row in preflight["units"]}
    runs = ["YAGO-A"] if args.phase == "A" else list(NEW_RUNS)
    with sqlite3.connect(f"file:{args.new_sqlite}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("New benchmark SQLite quick_check failed")
        new = {}
        for arm in runs:
            rows = db.execute("SELECT * FROM results WHERE run_id=?", (NEW_RUNS[arm],)).fetchall()
            if len(rows) != 100 or any(row["status"] in {"pending", "running", "raw_received"} for row in rows):
                raise ValueError(f"New arm not complete: {arm}")
            new[arm] = {row["unit_id"]: row for row in rows}
    files = sorted(args.old_packets.glob("quality-pairs-*.json"))
    if len(files) != 10:
        raise ValueError("Need exactly ten fixed old quality packets")
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "yago-benchmark-quality-packets-v1", "phase": args.phase,
               "selection_sha256": SELECTION_SHA, "kg_context_sha256": sha(args.kg_context),
               "preflight_sha256": sha(args.preflight), "new_sqlite_sha256": sha(args.new_sqlite),
               "old_semantic_reviews": [
                   "data/analysis/private/ontology-benchmark-100-20260928/quality-review/semantic-001-050.json",
                   "data/analysis/private/ontology-benchmark-100-20260928/quality-review/semantic-051-100.json"],
               "files": []}
    observed = set()
    for path in files:
        packet = json.loads(path.read_text())
        if packet["selection_sha256"] != SELECTION_SHA:
            raise ValueError(f"Old packet selection differs: {path}")
        for unit in packet["units"]:
            unit_id = unit["unit_id"]
            if unit_id in observed or unit_id not in preflight_by_id:
                raise ValueError("Repeated or unknown source unit")
            observed.add(unit_id)
            target = context["targets"][unit["target"]]
            by_statement = {s["statement_id"]: s for s in target["statements"]}
            chosen = preflight_by_id[unit_id]["kg_statement_ids"]
            unit["yago_context"] = {"mapping_status": target["mapping_status"],
                "selected_statement_ids": chosen,
                "statements": [by_statement[statement_id] for statement_id in chosen]}
            for arm in runs:
                row = new[arm][unit_id]
                if (row["rank"] != unit["rank"] or row["target"] != unit["target"]
                        or row["source_sha256"] != unit["unit_sha256"]
                        or row["prompt_sha256"] != preflight_by_id[unit_id]["prompt_sha256"]
                        or json.loads(row["kg_statement_ids_json"]) != chosen):
                    raise ValueError(f"New row differs from fixed source/preflight: {unit_id}")
                unit["arms"][arm] = arm_view(row)
        packet["schema"] = "yago-benchmark-quality-packet-v1"
        packet["kg_context_sha256"] = receipt["kg_context_sha256"]
        output_path = args.output / path.name
        output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
        receipt["files"].append({"path": output_path.name, "sha256": sha(output_path),
                                 "old_packet_sha256": sha(path),
                                 "ranks": [packet["rank_start"], packet["rank_end"]]})
    if len(observed) != 100:
        raise ValueError("Old packets do not cover all 100 units")
    (args.output / "manifest.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"phase": args.phase, "unit_count": len(observed),
                      "packets": len(files), "new_arms": runs}, ensure_ascii=False))


if __name__ == "__main__":
    main()
