"""Read-only source-coordinate comparison of the old five-target r3 claims.

Run on H200 only after the new facts, facts-context and taxonomy receipts exist.
It does not change either database or original source files.
"""

import collections
import gzip
import hashlib
import json
from pathlib import Path

import build


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "r3-50-source-claims.json"
OUTPUT = ROOT / "r3-50-disposition.json"


def ledger_rows(kind, target_lines):
    found = {}
    last = max(target_lines)
    with gzip.open(build.WORK / f"{kind}-ledger.tsv.gz", "rt") as source:
        for row in source:
            line = int(row.split("\t", 1)[0])
            if line in target_lines:
                found[line] = row.rstrip("\n").split("\t")[1:]
            if line >= last:
                break
    assert set(found) == target_lines, (kind, sorted(target_lines - set(found)))
    return found


def main():
    input_bytes = SOURCE.read_bytes()
    request = json.loads(input_bytes)
    entries = request["rows"]
    assert len(entries) == 50
    manifest = json.loads((ROOT / "manifest-final.json").read_text())
    by_file = collections.defaultdict(set)
    for entry in entries:
        by_file[entry["source_file"]].add(entry["line_no"])
    ledgers = {}
    for kind, lines in by_file.items():
        receipt = json.loads(build.receipt_path(kind).read_text())
        assert receipt["sha256"] == build.expected_hashes(manifest)[kind]
        ledgers[kind] = ledger_rows(kind, lines)
    context_receipt = json.loads(build.receipt_path("facts-context").read_text())
    assert context_receipt["sha256"] == build.expected_hashes(manifest)["facts"]
    ledgers["facts-context"] = ledger_rows("facts-context", by_file["facts"])
    out = []
    with build.pg_connection() as pg:
        for entry in entries:
            kind, line = entry["source_file"], entry["line_no"]
            claim = pg.execute(
                "SELECT raw,lane,reason,time_json FROM claim WHERE source_file=%s AND line_no=%s",
                (kind, line),
            ).fetchone()
            auxiliary = pg.execute(
                "SELECT raw,role FROM auxiliary WHERE source_file=%s AND line_no=%s",
                (kind, line),
            ).fetchone()
            context = (pg.execute(
                "SELECT raw,role FROM auxiliary WHERE source_file='facts-context' AND line_no=%s",
                (line,),
            ).fetchone() if kind == "facts" else None)
            for row in (claim, auxiliary, context):
                if row:
                    assert row[0] == entry["raw"], entry["source_statement_id"]
            status = ledgers[kind][line]
            assert (status[0] == "mapped") == bool(claim or auxiliary)
            context_status = ledgers["facts-context"][line][0] if kind == "facts" else None
            assert (context_status == "context_hint") == bool(context)
            out.append({
                **entry,
                "new_base_status": status[0],
                "new_base_reason": status[1],
                "new_claim_lane": claim[1] if claim else None,
                "new_claim_reason": claim[2] if claim else None,
                "new_claim_time": claim[3] if claim else None,
                "new_auxiliary_role": auxiliary[1] if auxiliary else None,
                "new_context_status": context_status,
                "new_context_role": context[1] if context else None,
            })
    counts = {
        "base_status": dict(collections.Counter(r["new_base_status"] for r in out)),
        "claim_lane": dict(collections.Counter(r["new_claim_lane"] or "none" for r in out)),
        "auxiliary_role": dict(collections.Counter(r["new_auxiliary_role"] or "none" for r in out)),
        "context_role": dict(collections.Counter(r["new_context_role"] or "none" for r in out)),
    }
    result = {
        "scope": "old_r3_50_source_statements_only; not a new world-history denominator",
        "comparison_input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "build_code_sha256": build.file_sha256(Path(build.__file__)),
        "manifest_sha256": build.file_sha256(ROOT / "manifest-final.json"),
        "counts": counts,
        "rows": out,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"counts": counts, "output_sha256": build.file_sha256(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
