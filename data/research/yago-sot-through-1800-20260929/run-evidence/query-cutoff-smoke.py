"""Read-only CLI regression against the isolated synthetic published DB."""

import contextlib
import io
import json
import sys
from pathlib import Path

import build


root = build.BASE / "reality-yago46-through-1899-smoke-20260929"
build.DB_NAME = "reality_yago46_through_1899_smoke_20260929"
build.DSN = f"host=/tmp/novel-ontology-pg-1100 port=55432 dbname={build.DB_NAME}"
queries = {}
for year in (1899, 1900):
    sys.argv = ["build.py", "query", "--manifest", str(root / "fixture-manifest.json"),
                "--subject", "yago:State", "--year", str(year)]
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        build.main()
    queries[year] = json.loads(captured.getvalue())
assert any(row["lane"] == "H_state" for row in queries[1899]["claims"])
assert queries[1900]["claims"] == []
result = {"fixture": "synthetic_only", "build_code_sha256": build.file_sha256(Path(build.__file__)),
          "database": build.DB_NAME,
          "year_1899_h_state_matches": sum(row["lane"] == "H_state" for row in queries[1899]["claims"]),
          "year_1900_claims": len(queries[1900]["claims"]), "queries": queries}
print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
