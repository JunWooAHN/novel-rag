"""Read-only, bounded staging/release readback for independent Sol review.

Run on H200 after the selected scan finishes. It prints evidence only and never
creates an acceptance file or changes the PostgreSQL database.
"""

import argparse
import hashlib
import json
from pathlib import Path

import psycopg


FILES = {
    "meta": "yago-4.6-meta.zip",
    "facts": "yago-4.6-facts.zip",
    "beyond-wikipedia": "yago-4.6-beyond-wikipedia.zip",
    "taxonomy": "yago-4.6-taxonomy.zip",
    "labels": "yago-4.6-labels.zip",
    "beyond-wikipedia-labels": "yago-4.6-beyond-wikipedia-labels.zip",
}
STAGES = tuple(FILES) + (
    "attach-meta", "context-index", "facts-context", "beyond-wikipedia-context",
)
READBACK = {
    "claim": ("source_file,line_no,byte_offset,raw,subject,predicate,object,triple_key,lane,time_json::text,reason", "source_file,line_no"),
    "meta_evidence": ("meta_line_no,byte_offset,raw,parent_key,predicate,object", "meta_line_no"),
    "auxiliary": ("source_file,line_no,raw,subject,predicate,object,role", "source_file,line_no"),
    "context_anchor": ("subject,birth_year,death_year,basis_json::text", "subject"),
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", required=True, help="Dedicated PG DSN; never printed")
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    receipts = {kind: json.loads((args.work / f"{kind}.receipt.json").read_text())
                for kind in STAGES}
    source_sha_match = {kind: receipts[kind]["sha256"] ==
                        manifest["files"][name]["entries"][0]["sha256"]
                        for kind, name in FILES.items()}
    digest = hashlib.sha256()
    row_counts = {}
    with psycopg.connect(args.dsn) as pg:
        pg.execute("SET TRANSACTION READ ONLY")
        for table, (columns, order) in READBACK.items():
            count = 0
            with pg.cursor(name=f"independent_{table}") as cursor:
                cursor.execute(f"SELECT {columns} FROM {table} ORDER BY {order}")
                for row in cursor:
                    digest.update(json.dumps(row, ensure_ascii=False, default=str,
                                             separators=(",", ":")).encode("utf-8"))
                    digest.update(b"\n")
                    count += 1
            row_counts[table] = count
        checks = {}
        queries = {
            "postcutoff_h_points": "SELECT COUNT(*) FROM claim WHERE lane IN ('H_event','H_boundary') AND (time_json->>'year')::integer > 1899",
            "invalid_h_state": "SELECT COUNT(*) FROM claim WHERE lane='H_state' AND ((time_json->>'start_year')::integer > 1899 OR (time_json->>'end_year')::integer < (time_json->>'start_year')::integer OR time_json->>'start_year' IS NULL OR time_json->>'end_year' IS NULL)",
            "crossing_h_states": "SELECT COUNT(*) FROM claim WHERE lane='H_state' AND (time_json->>'start_year')::integer <= 1899 AND (time_json->>'end_year')::integer > 1899",
            "bce_h_points": "SELECT COUNT(*) FROM claim WHERE lane IN ('H_event','H_boundary') AND (time_json->>'year')::integer < 0",
            "bce_h_states": "SELECT COUNT(*) FROM claim WHERE lane='H_state' AND (time_json->>'start_year')::integer < 0",
            "orphan_context_hints": "SELECT COUNT(*) FROM auxiliary a WHERE a.source_file IN ('facts-context','beyond-wikipedia-context') AND NOT EXISTS (SELECT 1 FROM context_anchor c WHERE c.subject=a.subject)",
            "hangul_start_boundary": "SELECT COUNT(*) FROM claim WHERE subject='yago:Hangul' AND predicate='schema:startDate' AND lane='H_boundary'",
            "fiction_direct_aux_type_hints": "SELECT COUNT(*) FROM auxiliary WHERE predicate='rdf:type' AND object='yago:FictionalEntity'",
            "fiction_direct_claim_type_hints": "SELECT COUNT(*) FROM claim WHERE predicate='rdf:type' AND object='yago:FictionalEntity' AND lane='K_taxonomy_timed'",
            "fiction_direct_h_subjects": "SELECT COUNT(DISTINCT h.subject) FROM claim h WHERE h.lane IN ('H_event','H_state','H_boundary') AND (EXISTS (SELECT 1 FROM auxiliary a WHERE a.subject=h.subject AND a.predicate='rdf:type' AND a.object='yago:FictionalEntity') OR EXISTS (SELECT 1 FROM claim t WHERE t.subject=h.subject AND t.predicate='rdf:type' AND t.object='yago:FictionalEntity' AND t.lane='K_taxonomy_timed'))",
        }
        for key, sql in queries.items():
            checks[key] = pg.execute(sql).fetchone()[0]
        samples = {}
        sample_queries = {
            "year_1899": "SELECT source_file,line_no,subject,predicate,object,lane,time_json::text FROM claim WHERE lane IN ('H_event','H_boundary') AND (time_json->>'year')::integer=1899 ORDER BY source_file,line_no LIMIT 3",
            "crossing": "SELECT source_file,line_no,subject,predicate,object,lane,time_json::text FROM claim WHERE lane='H_state' AND (time_json->>'end_year')::integer>1899 ORDER BY source_file,line_no LIMIT 3",
            "bce": "SELECT source_file,line_no,subject,predicate,object,lane,time_json::text FROM claim WHERE (time_json->>'year')::integer<0 OR (time_json->>'start_year')::integer<0 ORDER BY source_file,line_no LIMIT 3",
            "knowledge": "SELECT source_file,line_no,subject,predicate,object,lane,time_json::text FROM claim WHERE lane LIKE 'K_%' ORDER BY source_file,line_no LIMIT 3",
            "hangul_start": "SELECT source_file,line_no,subject,predicate,object,lane,time_json::text FROM claim WHERE subject='yago:Hangul' AND predicate='schema:startDate' ORDER BY source_file,line_no LIMIT 3",
            "fiction_direct_h": "SELECT h.source_file,h.line_no,h.subject,h.predicate,h.object,h.lane,h.time_json::text FROM claim h WHERE h.lane IN ('H_event','H_state','H_boundary') AND (EXISTS (SELECT 1 FROM auxiliary a WHERE a.subject=h.subject AND a.predicate='rdf:type' AND a.object='yago:FictionalEntity') OR EXISTS (SELECT 1 FROM claim t WHERE t.subject=h.subject AND t.predicate='rdf:type' AND t.object='yago:FictionalEntity' AND t.lane='K_taxonomy_timed')) ORDER BY h.source_file,h.line_no LIMIT 3",
        }
        for key, sql in sample_queries.items():
            samples[key] = pg.execute(sql).fetchall()
        releases = pg.execute("SELECT release_id,payload_sha256,input_manifest_sha256,code_sha256 FROM release ORDER BY release_id").fetchall()
    result = {
        "code_sha256": sha(args.code),
        "manifest_sha256": sha(args.manifest),
        "source_receipt_sha_match": source_sha_match,
        "receipt_bundle_sha256": hashlib.sha256(json.dumps(
            receipts, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
        "readback_sha256": digest.hexdigest(),
        "row_counts": row_counts,
        "semantic_checks": checks,
        "samples": samples,
        "releases": releases,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str, sort_keys=True))


if __name__ == "__main__":
    main()
