"""Synthetic isolated regression: a 1905 deathPlace cannot match pre-1900 context."""

import hashlib
import json
from pathlib import Path

import smoke
import build


smoke.ROOT = build.BASE / "reality-yago46-through-1899-deathplace-smoke-20260929"
smoke.SOURCE = smoke.ROOT / "fixture-source"
smoke.WORK = smoke.ROOT / "work"
smoke.DB_NAME = "reality_yago46_through_1899_deathplace_smoke_20260929"
smoke.ROWS["facts"] = [
    row.replace('yago:D\tschema:birthDate\t"1800"', 'yago:D\tschema:birthDate\t"1880"')
       .replace('yago:D\tschema:deathDate\t"1901"', 'yago:D\tschema:deathDate\t"1905"')
    for row in smoke.ROWS["facts"]
] + ['yago:D\tschema:deathPlace\tyago:P\t.']

smoke.main()
with build.pg_connection() as pg:
    leakage = pg.execute(
        "SELECT COUNT(*) FROM auxiliary WHERE source_file='facts-context' "
        "AND subject='yago:D' AND predicate='schema:deathPlace'"
    ).fetchone()[0]
    anchors = pg.execute(
        "SELECT COUNT(*) FROM context_anchor WHERE subject='yago:D'"
    ).fetchone()[0]
    assert leakage == anchors == 0

source = build.source_path("facts")
result = {
    "fixture": "synthetic_only",
    "subject": "yago:D",
    "birth_year": 1880,
    "death_year": 1905,
    "death_place_context_matches_before_1900": leakage,
    "subject_context_anchor_rows": anchors,
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "build_code_sha256": build.file_sha256(Path(build.__file__)),
    "database": smoke.DB_NAME,
}
(smoke.ROOT / "deathplace-regression-result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(result, sort_keys=True))
