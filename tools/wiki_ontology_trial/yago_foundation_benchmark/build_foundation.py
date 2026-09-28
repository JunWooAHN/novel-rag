"""Load the fixed five-target YAGO statements into an isolated trial SQLite."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import time


LEDGER_SHA = "b8984492124dcb8d767fd7f58d0cc4e8125064017019854bc51b2d204be26349"
MANIFEST_SHA = "da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb"
POLICY_SHA = "17c06d60d3948b06b012c112d210f5d2b3f892d2b09455cc37260e95688e0b07"
META_CAPTURE_SHA = "74f9d224fffeb4f8f9c3db43f107d3b86809580630efbf65aa16004b35ae0b50"
TARGETS = {
    "Munjong of Joseon": ("yago:Munjong_of_Joseon", 36),
    "Danjong of Joseon": ("yago:Danjong_of_Joseon", 30),
    "Sejo of Joseon": ("yago:Sejo_of_Joseon", 27),
    "Hangul": ("yago:Hangul", 23),
    "Bloomery": ("yago:Bloomery", 36),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_json(path: Path, expected: str) -> dict:
    if digest(path) != expected:
        raise ValueError(f"Pinned SHA differs: {path}")
    return json.loads(path.read_text())


def source_hashes(manifest: dict) -> dict[str, str]:
    out = {}
    for spec in manifest["files"].values():
        for member in spec["entries"]:
            out[member["path"]] = member["sha256"]
    return out


def build(ledger_path: Path, policy_path: Path, manifest_path: Path, meta_capture_path: Path,
          output: Path, receipt_path: Path) -> dict:
    started = time.perf_counter()
    ledger = pinned_json(ledger_path, LEDGER_SHA)
    manifest = pinned_json(manifest_path, MANIFEST_SHA)
    policy = pinned_json(policy_path, POLICY_SHA)
    if digest(meta_capture_path) != META_CAPTURE_SHA:
        raise ValueError("Fixed Meta capture SHA differs")
    if (ledger["yago_manifest_sha256"] != MANIFEST_SHA
            or policy["input_kg_ledger_sha256"] != LEDGER_SHA
            or policy["input_yago_manifest_sha256"] != MANIFEST_SHA
            or set(ledger["targets"]) != set(TARGETS)):
        raise ValueError("Foundation input identities differ")
    members = source_hashes(manifest)
    if output.exists() or receipt_path.exists():
        raise FileExistsError("Foundation output already exists; never overwrite it")
    output.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(output)
    try:
        db.executescript("""
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=FULL;
            CREATE TABLE input_pin (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE entity (
                trial_entity_id TEXT PRIMARY KEY, target TEXT NOT NULL UNIQUE,
                external_yago_id TEXT NOT NULL UNIQUE, mapping_status TEXT NOT NULL
            );
            CREATE TABLE source_statement (
                statement_id TEXT PRIMARY KEY, trial_entity_id TEXT NOT NULL REFERENCES entity,
                subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL,
                raw TEXT NOT NULL, source_kind TEXT NOT NULL, source_file TEXT NOT NULL,
                source_file_sha256 TEXT NOT NULL, source_line INTEGER NOT NULL,
                mapping_status TEXT NOT NULL CHECK(mapping_status IN ('mapped','unmapped','excluded')),
                mapping_role TEXT, project_relation TEXT, decision_reason TEXT,
                prompt_eligible INTEGER NOT NULL CHECK(prompt_eligible IN (0,1))
            );
            CREATE TABLE source_meta (
                meta_statement_id TEXT PRIMARY KEY, parent_statement_id TEXT REFERENCES source_statement,
                link_status TEXT NOT NULL CHECK(link_status IN ('linked','outgoing_orphan','incoming_observation')),
                base_subject TEXT NOT NULL, base_predicate TEXT NOT NULL, base_object TEXT NOT NULL,
                qualifier_predicate TEXT NOT NULL, qualifier_object TEXT NOT NULL,
                raw TEXT NOT NULL, source_kind TEXT NOT NULL, source_file TEXT NOT NULL,
                source_file_sha256 TEXT NOT NULL, source_line INTEGER NOT NULL
            );
            CREATE TABLE structural_assertion (
                assertion_id TEXT PRIMARY KEY, statement_id TEXT NOT NULL UNIQUE REFERENCES source_statement,
                trial_entity_id TEXT NOT NULL REFERENCES entity, role TEXT NOT NULL,
                project_relation TEXT NOT NULL, subject TEXT NOT NULL, object TEXT NOT NULL,
                source_kind TEXT NOT NULL, wiki_source_unit_id TEXT,
                wiki_start_byte INTEGER, wiki_end_byte INTEGER,
                CHECK(wiki_source_unit_id IS NULL AND wiki_start_byte IS NULL AND wiki_end_byte IS NULL)
            );
        """)
        db.executemany("INSERT INTO input_pin VALUES (?,?)", [
            ("kg_ledger_sha256", LEDGER_SHA), ("yago_manifest_sha256", MANIFEST_SHA),
            ("mapping_policy_sha256", POLICY_SHA), ("meta_capture_sha256", META_CAPTURE_SHA),
        ])
        statuses, roles = Counter(), Counter()
        seen_statement_ids, nested_meta = set(), {}
        by_triple = {}
        for target, (yago_id, expected_count) in TARGETS.items():
            item = ledger["targets"][target]
            statements = item["statements"]
            if (item["yago_id"] != yago_id or len(statements) != expected_count
                    or item["direct_fact_count"] + item["taxonomy_statement_count"] != expected_count):
                raise ValueError(f"Target facts differ: {target}")
            trial_id = "trial:yago46:" + yago_id.split(":", 1)[1]
            db.execute("INSERT INTO entity VALUES (?,?,?,?)",
                       (trial_id, target, yago_id, item["mapping_status"]))
            eligible = set(item["eligible_statement_ids"])
            for stmt in statements:
                sid = stmt["statement_id"]
                if (sid in seen_statement_ids or stmt["subject"] != yago_id
                        or stmt["line"] != int(sid.split(":", 1)[1])
                        or stmt["source_file_sha256"] != members.get(Path(stmt["source_file"]).name)):
                    raise ValueError(f"Statement identity/source differs: {sid}")
                seen_statement_ids.add(sid)
                triple = (stmt["subject"], stmt["predicate"], stmt["object"])
                if triple in by_triple:
                    raise ValueError(f"Duplicate exact source triple: {sid}")
                by_triple[triple] = sid
                rule = policy["predicate_rules"].get(stmt["predicate"],
                                                     {"status": policy["status_default"],
                                                      "reason": "predicate_not_in_fixed_mapping"})
                status = rule["status"]
                if status not in {"mapped", "unmapped", "excluded"}:
                    raise ValueError(f"Invalid status: {sid}")
                role = rule.get("role")
                if sid in eligible and (status != "mapped" or role in {"entity_alias", "external_identity"}
                                        or not isinstance(stmt.get("prompt_text"), str)):
                    raise ValueError(f"Invalid prompt eligibility: {sid}")
                db.execute("INSERT INTO source_statement VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (sid, trial_id, stmt["subject"], stmt["predicate"], stmt["object"],
                            stmt["raw"], stmt["source_kind"], stmt["source_file"],
                            stmt["source_file_sha256"], stmt["line"], status, role,
                            rule.get("relation"), rule.get("reason"), int(sid in eligible)))
                statuses[status] += 1
                if status == "mapped":
                    roles[role] += 1
                    if role not in {"entity_alias", "external_identity"}:
                        db.execute("INSERT INTO structural_assertion VALUES (?,?,?,?,?,?,?,?,NULL,NULL,NULL)",
                                   ("trial:assertion:" + sid, sid, trial_id, role, rule["relation"],
                                    stmt["subject"], stmt["object"], stmt["source_kind"]))
                for meta in stmt["meta"]:
                    mid = meta["statement_id"]
                    if (mid in nested_meta or meta["line"] != int(mid.split(":", 1)[1])
                            or meta["source_file_sha256"] != members.get(Path(meta["source_file"]).name)):
                        raise ValueError(f"Meta identity/source differs: {mid}")
                    nested_meta[mid] = (sid, meta)
            if eligible - seen_statement_ids:
                raise ValueError(f"Missing prompt-eligible statement: {target}")
        if len(seen_statement_ids) != 152 or len(nested_meta) != 24:
            raise ValueError("Fixed source accounting differs")
        meta_statuses = Counter()
        captured_meta_ids = set()
        meta_file = "extracted/yago-4.6-meta/yago-meta.ttl"
        meta_file_sha = members["yago-meta.ttl"]
        for line in meta_capture_path.read_text().splitlines():
            line_number, raw = line.split(":", 1)
            mid = "meta:" + line_number
            parts = raw.split("\t")
            if (mid in captured_meta_ids or len(parts) != 8 or parts[0] != "<<"
                    or parts[4] != ">>" or parts[7] != "."):
                raise ValueError(f"Invalid or duplicate Meta capture: {mid}")
            captured_meta_ids.add(mid)
            base = tuple(parts[1:4])
            parent = by_triple.get(base)
            if parent:
                link_status = "linked"
                nested_parent, nested = nested_meta[mid]
                if (nested_parent != parent or nested["raw"] != raw
                        or nested["source_file_sha256"] != meta_file_sha):
                    raise ValueError(f"Nested Meta differs from capture: {mid}")
            elif base[0] in {x[0] for x in TARGETS.values()}:
                link_status = "outgoing_orphan"
                if mid in nested_meta:
                    raise ValueError(f"Nested orphan Meta: {mid}")
            elif base[2] in {x[0] for x in TARGETS.values()}:
                link_status = "incoming_observation"
                if mid in nested_meta:
                    raise ValueError(f"Nested incoming Meta: {mid}")
            else:
                raise ValueError(f"Meta capture is outside selected subjects: {mid}")
            db.execute("INSERT INTO source_meta VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (mid, parent, link_status, *base, parts[5], parts[6], raw,
                        "yago_meta", meta_file, meta_file_sha, int(line_number)))
            meta_statuses[link_status] += 1
        if (len(captured_meta_ids) != 40 or set(nested_meta) !=
                {mid for mid, (parent, _) in nested_meta.items() if mid in captured_meta_ids}
                or meta_statuses != {"linked": 24, "outgoing_orphan": 5,
                                     "incoming_observation": 11}):
            raise ValueError("Fixed Meta capture accounting differs")
        db.commit()
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Foundation SQLite quick_check failed")
        assertion_count = db.execute("SELECT count(*) FROM structural_assertion").fetchone()[0]
    except BaseException:
        db.close()
        output.unlink(missing_ok=True)
        raise
    db.close()
    receipt = {"schema": "yago-foundation-load-v1", "fixed_targets": len(TARGETS),
               "source_statement_count": len(seen_statement_ids), "meta_row_count": len(captured_meta_ids),
               "meta_link_status_counts": dict(meta_statuses),
               "status_counts": dict(statuses), "mapped_role_counts": dict(roles),
               "structural_assertion_count": assertion_count,
               "kg_ledger_sha256": LEDGER_SHA, "yago_manifest_sha256": MANIFEST_SHA,
               "mapping_policy_sha256": POLICY_SHA, "meta_capture_sha256": META_CAPTURE_SHA,
               "sqlite_sha256": digest(output),
               "build_seconds": round(time.perf_counter() - started, 3),
               "historical_release_or_wiki_span": False}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kg-ledger", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--yago-manifest", type=Path, required=True)
    p.add_argument("--meta-capture", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(args.kg_ledger, args.policy, args.yago_manifest, args.meta_capture,
                           args.output, args.receipt), ensure_ascii=False))


if __name__ == "__main__":
    main()
