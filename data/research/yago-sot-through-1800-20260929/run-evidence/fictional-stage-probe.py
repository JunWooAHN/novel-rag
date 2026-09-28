"""Read-only narrow probe of currently selected draft claims, not all facts."""

import json
from pathlib import Path

import build


with build.pg_connection() as pg:
    fiction_types = pg.execute(
        "SELECT subject,line_no,raw FROM claim "
        "WHERE predicate='rdf:type' AND object='yago:FictionalEntity' "
        "ORDER BY source_file,line_no LIMIT 5"
    ).fetchall()
    sample = []
    for subject, line, raw in fiction_types:
        births = pg.execute(
            "SELECT line_no,raw,lane,time_json FROM claim "
            "WHERE subject=%s AND predicate='schema:birthDate' "
            "ORDER BY source_file,line_no LIMIT 5", (subject,)
        ).fetchall()
        sample.append({"subject": subject, "fictional_type_line": line,
                       "fictional_type_raw": raw,
                       "selected_birth_claims": [
                           {"line": x[0], "raw": x[1], "lane": x[2], "time": x[3]}
                           for x in births]})
    result = {"scope": "currently mapped claim table only, not all undated facts or final output",
              "code_sha256": build.file_sha256(Path(build.__file__)),
              "mapped_fictional_type_sample_count": len(sample),
              "sample": sample}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
