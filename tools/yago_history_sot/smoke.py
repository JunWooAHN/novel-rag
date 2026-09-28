"""Run a clearly synthetic, isolated H200 PostgreSQL pipeline smoke test."""

import hashlib
import json
from pathlib import Path

import build


ROOT = build.BASE / "reality-yago46-through-1899-smoke-20260929"
SOURCE = ROOT / "fixture-source"
WORK = ROOT / "work"
DB_NAME = "reality_yago46_through_1899_smoke_20260929"

ROWS = {
    "meta": [
        '<<\tyago:State\tschema:memberOf\tyago:Empire\t>>\tschema:startDate\t"1890"^^xsd:gYear\t.',
        '<<\tyago:State\tschema:memberOf\tyago:Empire\t>>\tschema:endDate\t"1910"^^xsd:gYear\t.',
        '<<\tyago:Ghost\tschema:memberOf\tyago:Empire\t>>\tschema:startDate\t"1800"^^xsd:gYear\t.',
        '<<\tyago:A\trdf:type\tschema:Person\t>>\tschema:startDate\t"1800"^^xsd:gYear\t.',
        '<<\tyago:A\trdf:type\tschema:Person\t>>\tschema:endDate\t"1880"^^xsd:gYear\t.',
    ],
    "facts": [
        'yago:A\tschema:birthDate\t"1800"^^xsd:gYear\t.',
        'yago:A\tschema:deathDate\t"1880"^^xsd:gYear\t.',
        'yago:A\trdf:type\tschema:Person\t.',
        'yago:A\trdfs:label\t"Alpha"@en\t.',
        'yago:A\tschema:spouse\tyago:B\t.',
        'yago:State\tschema:memberOf\tyago:Empire\t.',
        'yago:War\tschema:startDate\t"1899"^^xsd:gYear\t.',
        'yago:War\tschema:endDate\t"1900"^^xsd:gYear\t.',
        'yago:Work\tschema:datePublished\t"1800"^^xsd:gYear\t.',
        'yago:D\tschema:birthDate\t"1800"^^xsd:gYear\t.',
        'yago:D\tschema:deathDate\t"1901"^^xsd:gYear\t.',
        'yago:D\tschema:worksFor\tyago:X\t.',
    ],
    "beyond-wikipedia": [
        'yago:A\tschema:birthPlace\tyago:P\t.',
        'yago:A\tschema:deathPlace\tyago:Q\t.',
        'yago:War\trdfs:label\t"War"@en\t.',
    ],
    "taxonomy": [
        'schema:Person\trdfs:subClassOf\tschema:Thing\t.',
    ],
    "labels": [
        'yago:State\trdfs:label\t"State"@en\t.',
        'yago:Work\trdfs:label\t"Work"@en\t.',
        'yago:Unrelated\trdfs:label\t"Unrelated"@en\t.',
    ],
    "beyond-wikipedia-labels": [
        'yago:War\trdfs:label\t"War event"@en\t.',
    ],
}


def main():
    build.SOURCE = SOURCE
    build.WORK = WORK
    build.DB_NAME = DB_NAME
    build.DSN = f"host=/tmp/novel-ontology-pg-1100 port=55432 dbname={DB_NAME}"
    manifest = {"files": {}}
    for kind, (folder, filename) in build.FILE_NAMES.items():
        path = build.source_path(kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ("@prefix yago: <http://yago-knowledge.org/resource/> .\n"
               + "\n".join(ROWS[kind]) + "\n").encode()
        path.write_bytes(raw)
        manifest["files"][f"{folder}.zip"] = {"entries": [{"sha256": hashlib.sha256(raw).hexdigest()}]}
    WORK.mkdir(parents=True, exist_ok=True)
    (ROOT / "SYNTHETIC_FIXTURE_ONLY.txt").write_text("Synthetic fixture for isolated pipeline test; not YAGO upstream.\n")
    (ROOT / "fixture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    build.scan_meta(manifest)
    build.scan_fact_file("facts", manifest)
    build.scan_fact_file("beyond-wikipedia", manifest)
    build.attach_meta()
    build.prepare_context_index()
    build.scan_context("facts", manifest)
    build.scan_context("beyond-wikipedia", manifest)
    for kind in ("taxonomy", "labels", "beyond-wikipedia-labels"):
        build.scan_auxiliary(kind, manifest)
    # Completed stage re-entry must verify and skip without duplicating rows.
    build.scan_meta(manifest)
    build.scan_fact_file("facts", manifest)
    build.attach_meta()
    build.prepare_context_index()
    with build.pg_connection() as pg:
        readback_sha, counts = build.database_readback(pg)
        lanes = dict(pg.execute("SELECT lane,COUNT(*) FROM claim GROUP BY lane ORDER BY lane"))
        assert pg.execute("SELECT COUNT(*) FROM meta_evidence").fetchone()[0] == 4
        assert pg.execute("SELECT COUNT(*) FROM context_anchor").fetchone()[0] == 1
        assert pg.execute("SELECT COUNT(*) FROM auxiliary WHERE source_file='labels'").fetchone()[0] == 2
        assert pg.execute("SELECT COUNT(*) FROM auxiliary WHERE source_file='taxonomy'").fetchone()[0] == 1
        assert pg.execute("SELECT COUNT(*) FROM auxiliary WHERE source_file='facts-context' AND subject='yago:D'").fetchone()[0] == 0
        state = pg.execute("SELECT time_json FROM claim WHERE subject='yago:State' AND lane='H_state'").fetchone()[0]
        assert state["start_year"] == 1890 and state["end_year"] == 1910
        assert lanes["K_taxonomy_timed"] == 1 and lanes["K_dated"] == 1
    result = {"fixture": "synthetic_only", "database": DB_NAME, "readback_sha256": readback_sha,
              "row_counts": counts, "lanes": lanes,
              "code_sha256": build.file_sha256(Path(build.__file__))}
    receipt_kinds = list(build.FILE_NAMES) + ["attach-meta", "context-index", "facts-context", "beyond-wikipedia-context"]
    receipts = {kind: json.loads(build.receipt_path(kind).read_text()) for kind in receipt_kinds}
    acceptance = {"accepted": True, "code_sha256": build.file_sha256(Path(build.__file__)),
                  "manifest_sha256": build.file_sha256(ROOT / "fixture-manifest.json"),
                  "readback_sha256": "invalid", "row_counts": counts,
                  "receipt_bundle_sha256": hashlib.sha256(json.dumps(receipts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                  "synthetic_fixture_only": True}
    acceptance_path = ROOT / "synthetic-acceptance.json"
    acceptance_path.write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n")
    try:
        build.publish(ROOT / "fixture-manifest.json", Path(build.__file__), acceptance_path)
    except RuntimeError as exc:
        assert "staging output" in str(exc)
        result["wrong_readback_rejected"] = True
    else:
        raise AssertionError("publish accepted wrong reviewed output hash")
    acceptance["readback_sha256"] = readback_sha
    acceptance_path.write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n")
    published = build.publish(ROOT / "fixture-manifest.json", Path(build.__file__), acceptance_path)
    assert published["readback_sha256"] == readback_sha
    with build.pg_connection() as pg:
        try:
            pg.execute("UPDATE claim SET reason='tampered' WHERE source_file='facts' AND line_no=2")
        except Exception:
            pg.rollback()
            result["published_update_rejected"] = True
        else:
            raise AssertionError("published claim mutation was accepted")
    result["synthetic_release_id"] = published["release_id"]
    (ROOT / "smoke-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
