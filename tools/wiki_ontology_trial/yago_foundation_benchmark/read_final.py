"""Read-only H200 post-run process, NFS mount, and source-PG receipt."""

import json
import subprocess
from datetime import datetime, timezone

import psycopg


def output(*argv):
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    return {"returncode": result.returncode, "stdout": result.stdout.strip()}


receipt = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "mount": output("findmnt", "-T", "/home/work/novel-toy-tune", "-n", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"),
    "gpu_memory_mib": output("nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"),
    "owned_model_pids": output("ps", "-p", "32973,33659,33917", "-o", "pid="),
}
with psycopg.connect("dbname=ontology_expanded host=/tmp/novel-ontology-pg-1100 port=55432 user=work") as conn:
    conn.execute("SET TRANSACTION READ ONLY")
    counts = {}
    for table in ("reality_source_pages", "reality_source_units", "reality_candidates", "reality_extract_attempts"):
        counts[table] = conn.execute("SELECT count(*) FROM " + table).fetchone()[0]
    counts["attempt_status"] = dict(conn.execute(
        "SELECT status,count(*) FROM reality_extract_attempts GROUP BY status").fetchall())
    counts["candidate_status"] = dict(conn.execute(
        "SELECT status,count(*) FROM reality_candidates GROUP BY status").fetchall())
    receipt["source_pg_counts"] = counts
print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
