"""Freeze source, foundation, residual, and link-audit evidence for 100-unit review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from novel_factory.reality.domain import SourceUnit
from novel_factory.reality.expanded import evidence_spans


SELECTION_SHA = "45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0"
RUNS = {"A": "fixed100-YAGO-FOUNDATION-A-20260928",
        "B2": "fixed100-YAGO-FOUNDATION-B2-20260928"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dict_rows(db: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in db.execute(sql, params)]


def foundation_registry(db: sqlite3.Connection) -> dict[str, dict]:
    entities = dict_rows(db, "SELECT * FROM entity")
    if len(entities) != 5:
        raise ValueError("Foundation entity count differs")
    registry = {}
    for entity in entities:
        entity_id = entity["trial_entity_id"]
        yago_id = entity["external_yago_id"]
        source = dict_rows(db, "SELECT * FROM source_statement WHERE trial_entity_id=? ORDER BY statement_id", (entity_id,))
        meta = dict_rows(db, "SELECT * FROM source_meta WHERE base_subject=? OR base_object=? ORDER BY meta_statement_id",
                         (yago_id, yago_id))
        assertions = dict_rows(db, "SELECT * FROM structural_assertion WHERE trial_entity_id=? ORDER BY assertion_id", (entity_id,))
        for assertion in assertions:
            assertion["linked_meta"] = [row for row in meta if row["parent_statement_id"] == assertion["statement_id"]]
        registry[entity["target"]] = {"entity": entity, "source_statements": source,
                                         "structural_assertions": assertions,
                                         "meta_observations": meta}
    if sum(len(item["source_statements"]) for item in registry.values()) != 152:
        raise ValueError("Foundation source count differs")
    if sum(len(item["meta_observations"]) for item in registry.values()) != 40:
        raise ValueError("Foundation Meta count differs")
    if sum(len(item["structural_assertions"]) for item in registry.values()) != 50:
        raise ValueError("Foundation assertion count differs")
    return registry


def source_spans(unit: dict) -> list[dict]:
    source = SourceUnit(unit_id=unit["unit_id"], wiki_id=unit["wiki_id"],
                        page_id=int(unit["page_id"]), revision_id=int(unit["revision_id"]),
                        slot=unit["slot"], language=unit["language"], title=unit["page_title"],
                        start_byte=unit["start_byte"], end_byte=unit["end_byte"],
                        text=unit["source_text"], text_sha256=unit["unit_sha256"])
    source.validate()
    return [dict(span_id=s.span_id, start_byte=s.start_byte,
                 end_byte=s.end_byte, text=s.text) for s in evidence_spans(source)]


def arm_view(db: sqlite3.Connection, row: sqlite3.Row) -> dict:
    checked = json.loads(row["validation_json"]) if row["validation_json"] else None
    audit_rows = dict_rows(db, "SELECT * FROM foundation_link_audit WHERE run_id=? AND unit_id=?",
                           (row["run_id"], row["unit_id"]))
    if len(audit_rows) != 1:
        raise ValueError("Missing foundation link audit")
    proposals = dict_rows(db, "SELECT * FROM foundation_link_proposal WHERE run_id=? AND unit_id=? ORDER BY link_index",
                          (row["run_id"], row["unit_id"]))
    for item in proposals:
        item["problems"] = json.loads(item.pop("problems_json"))
        item["raw"] = json.loads(item.pop("raw_json"))
    audit = audit_rows[0]
    audit["displayed_statement_ids"] = json.loads(audit.pop("displayed_statement_ids_json"))
    audit["source_span_ids"] = json.loads(audit.pop("source_span_ids_json"))
    finish_reason = None
    if row["response_bytes"]:
        try:
            finish_reason = json.loads(row["response_bytes"])["choices"][0].get("finish_reason")
        except (ValueError, KeyError, IndexError, TypeError):
            pass
    return {"run_id": row["run_id"], "status": row["status"],
            "http_status": row["http_status"], "finish_reason": finish_reason,
            "input_tokens": row["input_tokens"], "output_tokens": row["output_tokens"],
            "prompt_sha256": row["prompt_sha256"], "response_sha256": row["response_sha256"],
            "raw_sha256": row["raw_sha256"], "error_type": row["error_type"],
            "error_detail": row["error_detail"], "raw_text": row["raw_text"],
            "validated_candidates": checked, "foundation_link_audit": audit,
            "foundation_link_proposals": proposals}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-packets", type=Path, required=True)
    parser.add_argument("--new-sqlite", type=Path, required=True)
    parser.add_argument("--foundation-sqlite", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--phase", choices=["A", "final"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Packet output already exists; immutable snapshot required")
    preflight = json.loads(args.preflight.read_text())
    if (preflight["selection_sha256"] != SELECTION_SHA or preflight["unit_count"] != 100
            or preflight["foundation_sqlite_sha256"] != sha(args.foundation_sqlite)):
        raise ValueError("Fixed source/foundation preflight differs")
    by_unit = {row["unit_id"]: row for row in preflight["units"]}
    if len(by_unit) != 100:
        raise ValueError("Repeated preflight unit")
    arms = ["A"] if args.phase == "A" else ["A", "B2"]
    old_paths = sorted(args.old_packets.glob("quality-pairs-*.json"))
    if len(old_paths) != 10:
        raise ValueError("Expected ten fixed baseline/context packets")
    with (sqlite3.connect(f"file:{args.foundation_sqlite}?mode=ro", uri=True) as foundation,
          sqlite3.connect(f"file:{args.new_sqlite}?mode=ro", uri=True) as results):
        foundation.row_factory = results.row_factory = sqlite3.Row
        if any(db.execute("PRAGMA quick_check").fetchone()[0] != "ok" for db in (foundation, results)):
            raise ValueError("Input SQLite integrity check failed")
        registry = foundation_registry(foundation)
        result_by_arm = {}
        for arm in arms:
            rows = results.execute("SELECT * FROM results WHERE run_id=? ORDER BY rank", (RUNS[arm],)).fetchall()
            if len(rows) != 100 or any(row["status"] in {"pending", "running", "raw_received"} for row in rows):
                raise ValueError(f"Arm {arm} not complete")
            result_by_arm[arm] = {row["unit_id"]: row for row in rows}
        args.output.mkdir(parents=True)
        arm_keys = {"baseline_source_only": ["A", "B2"],
                    "prior_yago_context": ["YAGO-A", "YAGO-B2"],
                    "new_foundation_residual": [f"FOUNDATION-{arm}" for arm in arms]}
        receipt = {"schema": "yago-foundation-review-packets-v1", "phase": args.phase,
                   "selection_sha256": SELECTION_SHA, "preflight_sha256": sha(args.preflight),
                   "foundation_sqlite_sha256": sha(args.foundation_sqlite),
                   "new_sqlite_sha256": sha(args.new_sqlite), "run_ids": [RUNS[arm] for arm in arms],
                   "current_arm_keys": arm_keys,
                   "files": []}
        observed = set()
        for path in old_paths:
            packet = json.loads(path.read_text())
            if packet["selection_sha256"] != SELECTION_SHA:
                raise ValueError("Old packet selection differs")
            for unit in packet["units"]:
                unit_id = unit["unit_id"]
                if unit_id in observed or unit_id not in by_unit:
                    raise ValueError("Repeated/unknown fixed source unit")
                observed.add(unit_id)
                pre = by_unit[unit_id]
                spans = source_spans(unit)
                if [s["span_id"] for s in spans] != pre["source_span_ids"]:
                    raise ValueError("Indexed source spans differ from CPU preflight")
                unit["source_spans"] = spans
                selected = pre["displayed_statement_ids"]
                reg = registry[unit["target"]]
                ids = {row["statement_id"] for row in reg["structural_assertions"]}
                if not set(selected).issubset(ids):
                    raise ValueError("Displayed row absent from structural foundation")
                unit["foundation"] = {"registry": reg, "displayed_statement_ids": selected,
                    "residual_mode": pre["residual_mode"],
                    "budget_omitted_reason": pre["budget_omitted_reason"],
                    "context_status": pre["foundation_context_status"],
                    "render_sha256": pre["foundation_render_sha256"]}
                for arm in arms:
                    row = result_by_arm[arm][unit_id]
                    if (row["rank"] != unit["rank"] or row["target"] != unit["target"]
                            or row["source_sha256"] != unit["unit_sha256"]
                            or row["prompt_sha256"] != pre["prompt_sha256"]
                            or json.loads(row["kg_statement_ids_json"]) != selected):
                        raise ValueError("Result differs from source/preflight")
                    unit["arms"][f"FOUNDATION-{arm}"] = arm_view(results, row)
            packet["schema"] = "yago-foundation-review-packet-v1"
            packet["foundation_sqlite_sha256"] = receipt["foundation_sqlite_sha256"]
            packet["current_arm_keys"] = arm_keys
            output = args.output / path.name
            output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
            receipt["files"].append({"name": output.name, "sha256": sha(output),
                                     "old_packet_sha256": sha(path),
                                     "ranks": [packet["rank_start"], packet["rank_end"]]})
    if len(observed) != 100:
        raise ValueError("Packet source denominator differs")
    (args.output / "manifest.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"phase": args.phase, "units": len(observed), "packets": len(old_paths),
                      "manifest_sha256": sha(args.output / "manifest.json")}))


if __name__ == "__main__":
    main()
