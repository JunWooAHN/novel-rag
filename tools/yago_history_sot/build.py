"""Streaming YAGO 4.6 source-grounded history foundation, nominal years <= 1899.

Run on the approved H200 Storage.  Scan stages are mutable and restartable; publish
is a separate, reviewed operation.  The original extracted TTL files are read only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import resource
import sqlite3
import time as clocktime
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/work/novel-toy-tune")
SOURCE = BASE / "sources/original/yago/4.6/extracted"
WORK = BASE / "reality-yago46-through-1899-20260929"
DB_NAME = "reality_yago46_through_1899_20260929"
DSN = f"host=/tmp/novel-ontology-pg-1100 port=55432 dbname={DB_NAME}"
CUTOFF = 1899
POLICY = "yago46-world-through-1899-v1"
FILE_NAMES = {
    "meta": ("yago-4.6-meta", "yago-meta.ttl"),
    "facts": ("yago-4.6-facts", "yago-facts.ttl"),
    "beyond-wikipedia": ("yago-4.6-beyond-wikipedia", "yago-beyond-wikipedia.ttl"),
    "taxonomy": ("yago-4.6-taxonomy", "yago-taxonomy.ttl"),
    "labels": ("yago-4.6-labels", "yago-labels.ttl"),
    "beyond-wikipedia-labels": ("yago-4.6-beyond-wikipedia-labels", "yago-beyond-wikipedia-labels.ttl"),
}
YEAR_LITERAL = re.compile(r'^"([+-]?\d{4,})(?:-(\d{2})-(\d{2}))?"\^\^xsd:(gYear|date)$')
DATED_EVENT_PREDICATES = {"schema:birthDate", "schema:deathDate"}
BOUNDARY_PREDICATES = {"schema:startDate", "schema:endDate"}
KNOWLEDGE_DATE_PREDICATES = {
    "schema:datePublished", "schema:dateCreated", "schema:dateModified",
    "schema:copyrightYear", "schema:publication", "schema:releaseDate",
}
STATE_PREDICATES = {
    "schema:memberOf", "schema:worksFor", "schema:spouse", "schema:location",
    "schema:affiliation", "schema:containedInPlace", "schema:parentOrganization",
    "schema:hasOccupation", "yago:hasCapital", "yago:capital",
}
TAXONOMY_PREDICATES = {"rdf:type", "rdfs:subClassOf", "schema:parentTaxon", "rdfs:subPropertyOf"}
META_TIME_PREDICATES = {"schema:startDate", "schema:endDate", "yago:onDate"}
EXCLUDED_PREDICATES = {
    "owl:sameAs", "schema:sameAs", "schema:url", "schema:image",
    "yago:siteLinks", "rdfs:comment", "schema:alternateName",
}
BLOOM_BITS = 1 << 28  # 32 MiB, fixed memory across all source sizes.


def progress(kind: str, line_no: int, offset: int, started: float) -> None:
    if line_no % 1000000 == 0:
        elapsed = max(clocktime.monotonic() - started, 0.001)
        rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(json.dumps({"stage": kind, "lines": line_no, "bytes": offset,
                          "elapsed_sec": round(elapsed, 1), "lines_per_sec": round(line_no / elapsed),
                          "max_rss_mib": round(rss_mib)}), flush=True)


def source_path(kind: str) -> Path:
    folder, name = FILE_NAMES[kind]
    return SOURCE / folder / name


def key_for(subject: str, predicate: str, obj: str) -> bytes:
    return hashlib.blake2b(f"{subject}\t{predicate}\t{obj}".encode(), digest_size=16).digest()


def term_key(term: str) -> bytes:
    return hashlib.blake2b(term.encode(), digest_size=16).digest()


def bloom_positions(key: bytes):
    a = int.from_bytes(key[:8], "little")
    b = int.from_bytes(key[8:], "little") | 1
    for i in range(3):
        yield (a + i * b) % BLOOM_BITS


def bloom_add(bloom: bytearray, key: bytes) -> None:
    for pos in bloom_positions(key):
        bloom[pos >> 3] |= 1 << (pos & 7)


def bloom_has(bloom: bytes, key: bytes) -> bool:
    return all(bloom[pos >> 3] & (1 << (pos & 7)) for pos in bloom_positions(key))


def nominal_year(raw: str) -> tuple[int | None, str]:
    """Do not infer a historical calendar from YAGO xsd lexical dates."""
    match = YEAR_LITERAL.fullmatch(raw)
    if not match:
        return None, "unsupported_time_literal"
    value, month, day, typ = match.groups()
    if (typ == "date") != (month is not None):
        return None, "invalid_precision_for_datatype"
    year = int(value)
    if year == 0:
        return None, "year_zero_held"
    if month is not None:
        mm, dd = int(month), int(day)
        if not 1 <= mm <= 12 or not 1 <= dd <= 31:
            return None, "invalid_month_or_day"
        if year < 0:
            max_day = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[mm - 1]
            if dd > max_day:
                return None, "invalid_month_or_day"
        elif year <= 9999:
            import calendar
            if dd > calendar.monthrange(year, mm)[1]:
                return None, "invalid_month_or_day"
    return year, "nominal_bce_calendar_unknown" if year < 0 else "nominal_calendar_unknown"


def parse_fact(raw: bytes) -> tuple[str, str, str] | None:
    try:
        parts = raw.rstrip(b"\r\n").decode("utf-8").split("\t")
    except UnicodeDecodeError:
        return None
    if len(parts) != 4 or parts[-1] != "." or not all(parts[:3]):
        return None
    return parts[0], parts[1], parts[2]


def parse_meta(raw: bytes) -> tuple[str, str, str, str, str] | None:
    try:
        parts = raw.rstrip(b"\r\n").decode("utf-8").split("\t")
    except UnicodeDecodeError:
        return None
    if len(parts) != 8 or parts[0] != "<<" or parts[4] != ">>" or parts[-1] != ".":
        return None
    return parts[1], parts[2], parts[3], parts[5], parts[6]


def choose_time(predicate: str, obj: str, meta: list[tuple]) -> tuple[str, dict, str]:
    """Classify the statement's own date/Meta, never a subject's birth alone."""
    direct = nominal_year(obj) if "^^xsd:date" in obj or "^^xsd:gYear" in obj else None
    if direct is not None:
        year, status = direct
        if year is None:
            return "unknown", {"raw": obj, "calendar": "unknown"}, status
        time = {"kind": "point", "raw": obj, "year": year, "calendar": "unknown", "precision": "day" if "^^xsd:date" in obj else "year", "status": status}
        if year > CUTOFF:
            return "excluded", time, "explicit_date_after_1899"
        if predicate in DATED_EVENT_PREDICATES:
            return "H_event", time, "explicit_event_date"
        if predicate in BOUNDARY_PREDICATES:
            return "H_boundary", time, "explicit_entity_boundary"
        if predicate in KNOWLEDGE_DATE_PREDICATES:
            return "K_dated", time, "dated_knowledge_or_publication"
        return "dated_other_candidate", time, "date_predicate_requires_semantic_review"
    times: dict[str, list[dict]] = {}
    for row in meta:
        _, _, meta_predicate, meta_object, meta_raw = row
        if meta_predicate not in META_TIME_PREDICATES:
            continue
        year, status = nominal_year(meta_object)
        times.setdefault(meta_predicate, []).append({"year": year, "raw": meta_object, "status": status, "meta_raw": meta_raw})
    if not times:
        return "unknown", {}, "no_statement_time"
    all_values = [v for values in times.values() for v in values]
    if any(v["year"] is None for v in all_values):
        return "unknown", {"meta": times, "calendar": "unknown"}, "unsupported_or_invalid_meta_time"
    if "yago:onDate" in times:
        years = [v["year"] for v in times["yago:onDate"]]
        time = {"kind": "observation", "meta": times, "years": years, "calendar": "unknown"}
        if all(y > CUTOFF for y in years):
            return "excluded", time, "meta_observation_after_1899"
        if predicate in TAXONOMY_PREDICATES:
            return "K_taxonomy_timed", time, "dated_taxonomy_separate_from_history"
        return "dated_observation_candidate", time, "observation_predicate_requires_semantic_review"
    starts = [v["year"] for v in times.get("schema:startDate", [])]
    ends = [v["year"] for v in times.get("schema:endDate", [])]
    if len(starts) > 1 or len(ends) > 1:
        return "unknown", {"kind": "interval", "meta": times, "calendar": "unknown"}, "multiple_interval_bounds_held"
    start = starts[0] if starts else None
    end = ends[0] if ends else None
    time = {"kind": "interval", "start_year": start, "end_year": end,
            "scope_end_year": CUTOFF, "meta": times, "calendar": "unknown",
            "endpoint_inclusivity": "source_unspecified"}
    if start is not None and end is not None and start > end:
        return "unknown", time, "reversed_interval_held"
    if start is not None and start > CUTOFF:
        return "excluded", time, "meta_interval_starts_after_1899"
    if end is not None and end > CUTOFF and start is None:
        return "unknown", time, "only_post_cutoff_end_no_start"
    if start is None or end is None:
        time["kind"] = "boundary_candidate"
        return "dated_boundary_candidate", time, "single_meta_bound_no_state_validity"
    if predicate in TAXONOMY_PREDICATES:
        return "K_taxonomy_timed", time, "dated_taxonomy_separate_from_history"
    if predicate not in STATE_PREDICATES:
        return "dated_relation_candidate", time, "state_predicate_requires_semantic_review"
    return "H_state", time, "meta_interval_nominal_crossing" if end > CUTOFF else "meta_interval_nominal"


def stage_db() -> sqlite3.Connection:
    WORK.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(WORK / "meta-stage.sqlite3")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key BLOB NOT NULL, line_no INTEGER NOT NULL, byte_offset INTEGER NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL, raw TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS seen (key BLOB PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS subject_context (subject TEXT PRIMARY KEY, birth_year INTEGER NOT NULL, death_year INTEGER NOT NULL, basis_json TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS related_subject (subject TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS related_type (term TEXT PRIMARY KEY)")
    return conn


def expected_hashes(manifest: dict) -> dict[str, str]:
    return {kind: manifest["files"][f"{folder}.zip"]["entries"][0]["sha256"]
            for kind, (folder, _) in FILE_NAMES.items()}


def receipt_path(kind: str) -> Path:
    return WORK / f"{kind}.receipt.json"


def save_receipt(kind: str, payload: dict) -> None:
    path = receipt_path(kind)
    tmp = path.with_suffix(".json.part")
    complete = {**payload, "stage_code_sha256": file_sha256(Path(__file__))}
    tmp.write_text(json.dumps(complete, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    tmp.replace(path)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def completed_receipt(kind: str, manifest: dict, table: str | None = None, file_key: str | None = None) -> dict | None:
    path = receipt_path(kind)
    if not path.exists():
        return None
    receipt = json.loads(path.read_text())
    ledger = WORK / f"{kind}-ledger.tsv.gz"
    if not ledger.exists() or file_sha256(ledger) != receipt.get("ledger_sha256"):
        raise RuntimeError(f"{kind} ledger checkpoint missing or changed")
    original_kind = file_key or kind
    if original_kind in FILE_NAMES and receipt.get("sha256") != expected_hashes(manifest)[original_kind]:
        raise RuntimeError(f"{kind} receipt source hash mismatch")
    if original_kind == "meta":
        if not (WORK / "meta-bloom.bin").exists() or (WORK / "meta-bloom.bin").stat().st_size != BLOOM_BITS // 8:
            raise RuntimeError("meta bloom checkpoint missing")
        with stage_db() as stage:
            actual = stage.execute("SELECT COUNT(*) FROM meta").fetchone()[0]
            expected_bloom_sha = receipt.get("bloom_sha256")
            if expected_bloom_sha is None:
                # Legacy first-attempt receipt predates the bloom digest.  Rebuild
                # from indexed Meta keys without rereading the 720 MB original.
                reconstructed = bytearray(BLOOM_BITS // 8)
                key_count = 0
                for (key,) in stage.execute("SELECT DISTINCT key FROM meta ORDER BY key"):
                    bloom_add(reconstructed, key)
                    key_count += 1
                expected_bloom_sha = hashlib.sha256(reconstructed).hexdigest()
                evidence = {"stage": "meta", "stage_code_sha256": "e46070d3ef8336caefa7145c5b41e6b1be4c03cf6c5ccff58161f886bc2b1eaf",
                            "distinct_parent_keys": key_count, "reconstructed_bloom_sha256": expected_bloom_sha,
                            "original_receipt_sha256": file_sha256(path)}
                (WORK / "meta-bloom-verification.json").write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
        if actual != receipt["counts"]["mapped_meta"]:
            raise RuntimeError("meta stage row count differs from receipt")
        if file_sha256(WORK / "meta-bloom.bin") != expected_bloom_sha:
            raise RuntimeError("meta bloom differs from indexed Meta keys")
    if table:
        with pg_connection() as pg:
            actual = pg.execute(f"SELECT COUNT(*) FROM {table} WHERE source_file=%s", (kind,)).fetchone()[0]
        expected = receipt["counts"].get("mapped", receipt["counts"].get("context_hint", 0))
        if actual != expected:
            raise RuntimeError(f"{kind} PG row count {actual} differs from receipt {expected}")
    return receipt


def scan_meta(manifest: dict) -> dict:
    prior = completed_receipt("meta", manifest)
    if prior:
        return prior
    conn = stage_db()
    conn.execute("DELETE FROM meta")
    conn.execute("DELETE FROM seen")
    conn.commit()
    path = source_path("meta")
    hashobj = hashlib.sha256()
    bloom = bytearray(BLOOM_BITS // 8)
    counts = Counter()
    batch = []
    offset = 0
    started = clocktime.monotonic()
    with path.open("rb", buffering=1024 * 1024) as file, gzip.open(WORK / "meta-ledger.tsv.gz.part", "wt", compresslevel=1) as ledger:
        for line_no, raw in enumerate(file, 1):
            hashobj.update(raw)
            counts["all_lines"] += 1
            parsed = parse_meta(raw)
            if raw.startswith(b"@prefix") or not raw.strip():
                code = "excluded_header"
            elif parsed is None:
                code = "failed_parse"
            else:
                s, p, o, mp, mo = parsed
                if mp in META_TIME_PREDICATES:
                    code = "mapped_meta"
                    key = key_for(s, p, o)
                    bloom_add(bloom, key)
                    batch.append((key, line_no, offset, mp, mo, raw.rstrip(b"\r\n").decode("utf-8")))
                else:
                    code = "unknown_meta_predicate"
            counts[code] += 1
            ledger.write(f"{line_no}\t{code}\n")
            offset += len(raw)
            progress("meta", line_no, offset, started)
            if len(batch) >= 10000:
                conn.executemany("INSERT INTO meta VALUES (?,?,?,?,?,?)", batch)
                conn.commit()
                batch.clear()
    if batch:
        conn.executemany("INSERT INTO meta VALUES (?,?,?,?,?,?)", batch)
        conn.commit()
    actual = hashobj.hexdigest()
    expected = expected_hashes(manifest)["meta"]
    if actual != expected:
        raise RuntimeError(f"meta source hash mismatch {actual} != {expected}")
    conn.execute("CREATE INDEX IF NOT EXISTS meta_key_idx ON meta(key)")
    conn.commit()
    (WORK / "meta-bloom.bin").write_bytes(bloom)
    (WORK / "meta-ledger.tsv.gz.part").replace(WORK / "meta-ledger.tsv.gz")
    result = {"file": str(path), "sha256": actual, "expected_sha256": expected,
              "ledger_sha256": file_sha256(WORK / "meta-ledger.tsv.gz"),
              "bloom_sha256": file_sha256(WORK / "meta-bloom.bin"),
              "bytes": offset, "counts": dict(counts), "scanned_at_utc": datetime.now(timezone.utc).isoformat()}
    save_receipt("meta", result)
    return result


def pg_connection():
    import psycopg
    return psycopg.connect(DSN)


def init_pg() -> None:
    import psycopg
    from psycopg import sql
    with psycopg.connect("host=/tmp/novel-ontology-pg-1100 port=55432 dbname=postgres", autocommit=True) as root:
        if not root.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB_NAME,)).fetchone():
            root.execute(sql.SQL("CREATE DATABASE {}") .format(sql.Identifier(DB_NAME)))
    with pg_connection() as pg:
        pg.execute("""CREATE TABLE IF NOT EXISTS claim (
            source_file text NOT NULL, line_no bigint NOT NULL, byte_offset bigint NOT NULL,
            raw text NOT NULL, subject text NOT NULL, predicate text NOT NULL, object text NOT NULL,
            triple_key text NOT NULL, lane text NOT NULL, time_json jsonb NOT NULL, reason text NOT NULL,
            PRIMARY KEY(source_file,line_no))""")
        pg.execute("""CREATE TABLE IF NOT EXISTS meta_evidence (
            meta_line_no bigint PRIMARY KEY, byte_offset bigint NOT NULL, raw text NOT NULL,
            parent_key text NOT NULL, predicate text NOT NULL, object text NOT NULL)""")
        pg.execute("""CREATE TABLE IF NOT EXISTS auxiliary (
            source_file text NOT NULL, line_no bigint NOT NULL, raw text NOT NULL,
            subject text NOT NULL, predicate text NOT NULL, object text NOT NULL, role text NOT NULL,
            PRIMARY KEY(source_file,line_no))""")
        pg.execute("""CREATE TABLE IF NOT EXISTS context_anchor (
            subject text PRIMARY KEY, birth_year integer NOT NULL, death_year integer NOT NULL,
            basis_json jsonb NOT NULL)""")
        pg.execute("""CREATE TABLE IF NOT EXISTS source_scan (
            source_file text PRIMARY KEY, sha256 text NOT NULL, bytes bigint NOT NULL,
            counts jsonb NOT NULL, receipt_sha256 text NOT NULL)""")
        pg.execute("""CREATE TABLE IF NOT EXISTS release (
            release_id text PRIMARY KEY, policy text NOT NULL, cutoff_year integer NOT NULL,
            input_manifest_sha256 text NOT NULL, code_sha256 text NOT NULL,
            payload_sha256 text NOT NULL, published_at timestamptz NOT NULL DEFAULT now())""")
        pg.execute("CREATE INDEX IF NOT EXISTS claim_subject_idx ON claim(subject)")
        pg.execute("CREATE INDEX IF NOT EXISTS claim_lane_idx ON claim(lane)")
        pg.execute("CREATE INDEX IF NOT EXISTS auxiliary_subject_idx ON auxiliary(subject)")
        # Release rows and their selected evidence cannot change after publication.
        pg.execute("""CREATE OR REPLACE FUNCTION block_published_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF EXISTS (SELECT 1 FROM release) THEN RAISE EXCEPTION 'published SoT is immutable'; END IF;
        RETURN COALESCE(NEW, OLD); END $$""")
        for table in ("claim", "meta_evidence", "auxiliary", "context_anchor", "source_scan", "release"):
            pg.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
            pg.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION block_published_change()")
        for table in ("claim", "meta_evidence", "auxiliary", "context_anchor", "source_scan"):
            pg.execute(f"DROP TRIGGER IF EXISTS {table}_insert_guard ON {table}")
            pg.execute(f"CREATE TRIGGER {table}_insert_guard BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION block_published_change()")


def lookup_meta(conn: sqlite3.Connection, bloom: bytes, key: bytes) -> list[tuple]:
    if not bloom_has(bloom, key):
        return []
    rows = conn.execute("SELECT line_no,byte_offset,predicate,object,raw FROM meta WHERE key=? ORDER BY line_no", (key,)).fetchall()
    if rows:
        conn.execute("INSERT OR IGNORE INTO seen(key) VALUES (?)", (key,))
    return rows


def scan_fact_file(kind: str, manifest: dict) -> dict:
    prior = completed_receipt(kind, manifest, table="claim")
    if prior:
        return prior
    init_pg()
    conn = stage_db()
    bloom = (WORK / "meta-bloom.bin").read_bytes()
    path = source_path(kind)
    sha = hashlib.sha256()
    counts = Counter()
    offset = 0
    started = clocktime.monotonic()
    with pg_connection() as pg:
        if pg.execute("SELECT 1 FROM release").fetchone():
            raise RuntimeError("published DB cannot be scanned again")
        pg.execute("DELETE FROM claim WHERE source_file=%s", (kind,))
        pg.commit()
        batch = []
        with path.open("rb", buffering=1024 * 1024) as file, gzip.open(WORK / f"{kind}-ledger.tsv.gz.part", "wt", compresslevel=1) as ledger:
            for line_no, raw in enumerate(file, 1):
                sha.update(raw)
                counts["all_lines"] += 1
                parsed = parse_fact(raw)
                row = None
                if raw.startswith(b"@prefix") or not raw.strip():
                    code, reason = "excluded", "header_or_blank"
                elif parsed is None:
                    code, reason = "failed", "invalid_fact_line_or_utf8"
                else:
                    s, p, o = parsed
                    key = key_for(s, p, o)
                    meta = lookup_meta(conn, bloom, key)
                    lane, time, reason = choose_time(p, o, meta)
                    if lane == "excluded":
                        code = "excluded"
                    elif lane == "unknown":
                        code = "unknown"
                    else:
                        code = "mapped"
                        row = (kind, line_no, offset, raw.rstrip(b"\r\n").decode("utf-8"), s, p, o,
                               key.hex(), lane, json.dumps(time, ensure_ascii=False, sort_keys=True), reason)
                counts[code] += 1
                counts[reason] += 1
                ledger.write(f"{line_no}\t{code}\t{reason}\n")
                if row is not None:
                    batch.append(row)
                if len(batch) >= 10000:
                    pg.cursor().executemany("INSERT INTO claim VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)", batch)
                    pg.commit()
                    batch.clear()
                if line_no % 100000 == 0:
                    conn.commit()
                offset += len(raw)
                progress(kind, line_no, offset, started)
            if batch:
                pg.cursor().executemany("INSERT INTO claim VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)", batch)
                pg.commit()
        conn.commit()
    actual = sha.hexdigest()
    expected = expected_hashes(manifest)[kind]
    if actual != expected:
        raise RuntimeError(f"{kind} source hash mismatch {actual} != {expected}")
    (WORK / f"{kind}-ledger.tsv.gz.part").replace(WORK / f"{kind}-ledger.tsv.gz")
    result = {"file": str(path), "sha256": actual, "expected_sha256": expected,
              "ledger_sha256": file_sha256(WORK / f"{kind}-ledger.tsv.gz"),
              "bytes": offset, "counts": dict(counts), "scanned_at_utc": datetime.now(timezone.utc).isoformat()}
    save_receipt(kind, result)
    return result


def attach_meta() -> dict:
    if receipt_path("attach-meta").exists():
        receipt = json.loads(receipt_path("attach-meta").read_text())
        with stage_db() as stage, pg_connection() as pg:
            attached = pg.execute("SELECT COUNT(*) FROM meta_evidence").fetchone()[0]
            seen = stage.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
            orphan = stage.execute("SELECT COUNT(*) FROM meta m WHERE NOT EXISTS (SELECT 1 FROM seen s WHERE s.key=m.key)").fetchone()[0]
        if (attached != receipt["attached_meta_rows"] or seen != receipt["seen_parent_keys"]
                or orphan != receipt["unmatched_meta_rows"]):
            raise RuntimeError("attached Meta checkpoint differs from stage/PG")
        return receipt
    conn = stage_db()
    with pg_connection() as pg:
        pg.execute("DELETE FROM meta_evidence")
        pg.commit()
        batch = []
        count = 0
        key_count = 0
        with pg.cursor(name="claim_meta_keys") as cursor:
            cursor.execute("SELECT DISTINCT triple_key FROM claim")
            for (key_hex,) in cursor:
                key = bytes.fromhex(key_hex)
                key_count += 1
                for line, offset, pred, obj, raw in conn.execute("SELECT line_no,byte_offset,predicate,object,raw FROM meta WHERE key=?", (key,)):
                    batch.append((line, offset, raw, key_hex, pred, obj))
                    count += 1
                if len(batch) >= 10000:
                    pg.cursor().executemany("INSERT INTO meta_evidence VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", batch)
                    batch.clear()
        if batch:
            pg.cursor().executemany("INSERT INTO meta_evidence VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", batch)
            pg.commit()
    orphan = conn.execute("SELECT COUNT(*) FROM meta m WHERE NOT EXISTS (SELECT 1 FROM seen s WHERE s.key=m.key)").fetchone()[0]
    seen = conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
    result = {"attached_meta_rows": count, "unmatched_meta_rows": orphan,
              "seen_parent_keys": seen, "distinct_selected_parent_keys": key_count}
    save_receipt("attach-meta", result)
    return result


def prepare_context_index() -> dict:
    """Only a subject's own birth/death anchors can provide a context hint."""
    if receipt_path("context-index").exists():
        receipt = json.loads(receipt_path("context-index").read_text())
        if not (WORK / "context-bloom.bin").exists() or (WORK / "context-bloom.bin").stat().st_size != BLOOM_BITS // 8:
            raise RuntimeError("context bloom checkpoint missing")
        if not (WORK / "related-bloom.bin").exists() or (WORK / "related-bloom.bin").stat().st_size != BLOOM_BITS // 8:
            raise RuntimeError("related subject bloom checkpoint missing")
        if (file_sha256(WORK / "context-bloom.bin") != receipt["context_bloom_sha256"]
                or file_sha256(WORK / "related-bloom.bin") != receipt["related_bloom_sha256"]):
            raise RuntimeError("context index bloom hash mismatch")
        with stage_db() as stage, pg_connection() as pg:
            if (stage.execute("SELECT COUNT(*) FROM subject_context").fetchone()[0] != receipt["anchored_subjects"]
                    or stage.execute("SELECT COUNT(*) FROM related_subject").fetchone()[0] != receipt["related_claim_subjects"]
                    or pg.execute("SELECT COUNT(*) FROM context_anchor").fetchone()[0] != receipt["anchored_subjects"]):
                raise RuntimeError("context index checkpoint mismatch")
        return receipt
    conn = stage_db()
    context_bloom = bytearray(BLOOM_BITS // 8)
    conn.execute("DELETE FROM subject_context")
    conn.execute("DELETE FROM related_subject")
    conn.execute("DELETE FROM related_type")
    related_bloom = bytearray(BLOOM_BITS // 8)
    counts = Counter()
    with pg_connection() as pg:
        pg.execute("DELETE FROM context_anchor")
        pg.commit()
        def flush(subject: str | None, anchors: dict[str, list[dict]]) -> None:
            if subject is None:
                return
            births = anchors["schema:birthDate"]
            deaths = anchors["schema:deathDate"]
            if len(births) != 1 or len(deaths) != 1:
                counts["missing_or_conflicting_life_anchors"] += 1
                return
            birth, death = births[0], deaths[0]
            if birth["year"] > death["year"]:
                counts["reversed_life_anchors"] += 1
                return
            basis = json.dumps({"birth": birth, "death": death, "calendar": "unknown",
                                "status": "derived_context_only"}, sort_keys=True)
            conn.execute("INSERT INTO subject_context VALUES (?,?,?,?)",
                         (subject, birth["year"], death["year"], basis))
            bloom_add(context_bloom, term_key(subject))
            pg.execute("INSERT INTO context_anchor VALUES (%s,%s,%s,%s::jsonb)",
                       (subject, birth["year"], death["year"], basis))
            counts["bounded_context_subjects"] += 1
        current = None
        anchors: dict[str, list[dict]] = {"schema:birthDate": [], "schema:deathDate": []}
        with pg.cursor(name="subject_anchors") as cursor:
            cursor.execute("""SELECT subject,predicate,(time_json->>'year')::integer,source_file,line_no FROM claim
                              WHERE lane='H_event' AND predicate IN ('schema:birthDate','schema:deathDate')
                              ORDER BY subject,predicate,source_file,line_no""")
            for subject, predicate, year, source_file, line in cursor:
                if subject != current:
                    flush(current, anchors)
                    current = subject
                    anchors = {"schema:birthDate": [], "schema:deathDate": []}
                anchors[predicate].append({"year": year, "source_file": source_file, "line_no": line})
        flush(current, anchors)
        with pg.cursor(name="all_claim_subjects") as cursor:
            cursor.execute("SELECT DISTINCT subject FROM claim ORDER BY subject")
            for (subject,) in cursor:
                conn.execute("INSERT INTO related_subject VALUES (?)", (subject,))
                bloom_add(related_bloom, term_key(subject))
        pg.commit()
    conn.commit()
    (WORK / "context-bloom.bin").write_bytes(context_bloom)
    (WORK / "related-bloom.bin").write_bytes(related_bloom)
    count = conn.execute("SELECT COUNT(*) FROM subject_context").fetchone()[0]
    related_count = conn.execute("SELECT COUNT(*) FROM related_subject").fetchone()[0]
    result = {"anchored_subjects": count, "related_claim_subjects": related_count,
              "context_bloom_sha256": file_sha256(WORK / "context-bloom.bin"),
              "related_bloom_sha256": file_sha256(WORK / "related-bloom.bin"), "held": dict(counts),
              "basis": "unique same-subject explicit birth and death anchors; context_only"}
    save_receipt("context-index", result)
    return result


def scan_context(kind: str, manifest: dict) -> dict:
    """Capture undated related assertions as hints, never valid-time facts."""
    receipt_kind = kind + "-context"
    prior = completed_receipt(receipt_kind, manifest, table="auxiliary", file_key=kind)
    if prior:
        return prior
    conn = stage_db()
    bloom = (WORK / "meta-bloom.bin").read_bytes()
    context_bloom = (WORK / "context-bloom.bin").read_bytes()
    related_bloom = (WORK / "related-bloom.bin").read_bytes()
    counts = Counter()
    sha = hashlib.sha256()
    path = source_path(kind)
    started = clocktime.monotonic()
    offset = 0
    with pg_connection() as pg:
        pg.execute("DELETE FROM auxiliary WHERE source_file=%s", (receipt_kind,))
        pg.commit()
        batch = []
        with path.open("rb", buffering=1024 * 1024) as file, gzip.open(WORK / f"{receipt_kind}-ledger.tsv.gz.part", "wt", compresslevel=1) as ledger:
            for line_no, raw in enumerate(file, 1):
                sha.update(raw)
                counts["all_lines"] += 1
                parsed = parse_fact(raw)
                if parsed is None:
                    code = "not_context"
                else:
                    s, p, o = parsed
                    subject_key = term_key(s)
                    related = (conn.execute("SELECT 1 FROM related_subject WHERE subject=?", (s,)).fetchone()
                               if bloom_has(related_bloom, subject_key) else None)
                    anchor = (conn.execute("SELECT birth_year,death_year FROM subject_context WHERE subject=?", (s,)).fetchone()
                              if bloom_has(context_bloom, subject_key) else None)
                    if related is None or p in EXCLUDED_PREDICATES or "^^xsd:date" in o or "^^xsd:gYear" in o:
                        code = "not_context"
                    elif p not in {"rdf:type", "rdfs:label"} and (anchor is None or lookup_meta(conn, bloom, key_for(s, p, o))):
                        code = "not_context"
                    else:
                        code = "context_hint"
                        if p == "rdf:type":
                            conn.execute("INSERT OR IGNORE INTO related_type(term) VALUES (?)", (o,))
                            role = "taxonomy_link_auxiliary"
                        elif p == "rdfs:label":
                            role = "label"
                        else:
                            role = "undated_context_hint"
                        batch.append((receipt_kind, line_no, raw.rstrip(b"\r\n").decode("utf-8"), s, p, o, role))
                counts[code] += 1
                ledger.write(f"{line_no}\t{code}\n")
                offset += len(raw)
                progress(receipt_kind, line_no, offset, started)
                if len(batch) >= 10000:
                    pg.cursor().executemany("INSERT INTO auxiliary VALUES (%s,%s,%s,%s,%s,%s,%s)", batch)
                    pg.commit()
                    conn.commit()
                    batch.clear()
            if batch:
                pg.cursor().executemany("INSERT INTO auxiliary VALUES (%s,%s,%s,%s,%s,%s,%s)", batch)
                pg.commit()
        conn.commit()
    actual = sha.hexdigest()
    expected = expected_hashes(manifest)[kind]
    if actual != expected:
        raise RuntimeError(f"{receipt_kind} source hash mismatch")
    (WORK / f"{receipt_kind}-ledger.tsv.gz.part").replace(WORK / f"{receipt_kind}-ledger.tsv.gz")
    result = {"file": str(path), "sha256": actual, "expected_sha256": expected,
              "ledger_sha256": file_sha256(WORK / f"{receipt_kind}-ledger.tsv.gz"),
              "counts": dict(counts), "scanned_at_utc": datetime.now(timezone.utc).isoformat(),
              "accounting": "secondary related evidence; not added to base denominator or H validity"}
    save_receipt(receipt_kind, result)
    return result


def scan_auxiliary(kind: str, manifest: dict) -> dict:
    """Keep labels and taxonomy as related data, never time-valid history."""
    prior = completed_receipt(kind, manifest, table="auxiliary")
    if prior:
        return prior
    init_pg()
    path = source_path(kind)
    with stage_db() as stage:
        if kind == "taxonomy":
            selection_bloom = bytearray(BLOOM_BITS // 8)
            for (term,) in stage.execute("SELECT term FROM related_type"):
                bloom_add(selection_bloom, term_key(term))
        else:
            selection_bloom = (WORK / "related-bloom.bin").read_bytes()
    sha = hashlib.sha256()
    counts = Counter()
    offset = 0
    started = clocktime.monotonic()
    with pg_connection() as pg:
        if pg.execute("SELECT 1 FROM release").fetchone():
            raise RuntimeError("published DB cannot be scanned again")
        pg.execute("DELETE FROM auxiliary WHERE source_file=%s", (kind,))
        stage = stage_db()
        pg.commit()
        batch = []
        with path.open("rb", buffering=1024 * 1024) as file, gzip.open(WORK / f"{kind}-ledger.tsv.gz.part", "wt", compresslevel=1) as ledger:
            for line_no, raw in enumerate(file, 1):
                sha.update(raw)
                counts["all_lines"] += 1
                parsed = parse_fact(raw)
                if raw.startswith(b"@prefix") or not raw.strip():
                    code, reason = "excluded", "header_or_blank"
                elif parsed is None:
                    code, reason = "failed", "invalid_auxiliary_line_or_utf8"
                else:
                    s, p, o = parsed
                    related = bloom_has(selection_bloom, term_key(s)) and (
                        stage.execute("SELECT 1 FROM related_type WHERE term=?", (s,)).fetchone()
                        if kind == "taxonomy" else
                        stage.execute("SELECT 1 FROM related_subject WHERE subject=?", (s,)).fetchone())
                    if related:
                        code, reason = "mapped", "related_auxiliary_only"
                        batch.append((kind, line_no, raw.rstrip(b"\r\n").decode("utf-8"), s, p, o,
                                      "taxonomy" if kind == "taxonomy" else "label"))
                    else:
                        code, reason = "excluded", "not_related_to_dated_subject"
                counts[code] += 1
                counts[reason] += 1
                ledger.write(f"{line_no}\t{code}\t{reason}\n")
                if len(batch) >= 10000:
                    pg.cursor().executemany("INSERT INTO auxiliary VALUES (%s,%s,%s,%s,%s,%s,%s)", batch)
                    pg.commit()
                    batch.clear()
                offset += len(raw)
                progress(kind, line_no, offset, started)
            if batch:
                pg.cursor().executemany("INSERT INTO auxiliary VALUES (%s,%s,%s,%s,%s,%s,%s)", batch)
                pg.commit()
    actual = sha.hexdigest()
    expected = expected_hashes(manifest)[kind]
    if actual != expected:
        raise RuntimeError(f"{kind} source hash mismatch {actual} != {expected}")
    (WORK / f"{kind}-ledger.tsv.gz.part").replace(WORK / f"{kind}-ledger.tsv.gz")
    result = {"file": str(path), "sha256": actual, "expected_sha256": expected,
              "ledger_sha256": file_sha256(WORK / f"{kind}-ledger.tsv.gz"),
              "bytes": offset, "counts": dict(counts), "scanned_at_utc": datetime.now(timezone.utc).isoformat()}
    save_receipt(kind, result)
    return result


def database_readback(pg) -> tuple[str, dict]:
    """Stream all published content into a deterministic digest and count ledger."""
    digest = hashlib.sha256()
    counts = {}
    columns = {
        "claim": "source_file,line_no,byte_offset,raw,subject,predicate,object,triple_key,lane,time_json::text,reason",
        "meta_evidence": "meta_line_no,byte_offset,raw,parent_key,predicate,object",
        "auxiliary": "source_file,line_no,raw,subject,predicate,object,role",
        "context_anchor": "subject,birth_year,death_year,basis_json::text",
    }
    orders = {"claim": "source_file,line_no", "meta_evidence": "meta_line_no",
              "auxiliary": "source_file,line_no", "context_anchor": "subject"}
    for table in columns:
        count = 0
        with pg.cursor(name=f"readback_{table}") as cursor:
            cursor.execute(f"SELECT {columns[table]} FROM {table} ORDER BY {orders[table]}")
            for row in cursor:
                digest.update(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8"))
                digest.update(b"\n")
                count += 1
        counts[table] = count
    return digest.hexdigest(), counts


def publish(manifest_path: Path, code_path: Path, acceptance_path: Path) -> dict:
    """Only call after independent review and completed full scans."""
    manifest = json.loads(manifest_path.read_text())
    required = list(FILE_NAMES) + ["attach-meta", "context-index", "facts-context", "beyond-wikipedia-context"]
    receipts = {kind: json.loads(receipt_path(kind).read_text()) for kind in required}
    for kind in FILE_NAMES:
        if receipts[kind]["sha256"] != expected_hashes(manifest)[kind]:
            raise RuntimeError(f"{kind} hash unverified")
        c = receipts[kind]["counts"]
        if sum(c.get(k, 0) for k in ("mapped", "excluded", "unknown", "failed", "mapped_meta", "unknown_meta_predicate", "excluded_header", "failed_parse")) != c["all_lines"]:
            raise RuntimeError(f"{kind} denominator mismatch")
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    code_sha = hashlib.sha256(code_path.read_bytes()).hexdigest()
    acceptance = json.loads(acceptance_path.read_text())
    if (acceptance.get("accepted") is not True or acceptance.get("code_sha256") != code_sha
            or acceptance.get("manifest_sha256") != manifest_sha):
        raise RuntimeError("independent acceptance missing or bound to different code/manifest")
    with pg_connection() as pg:
        for kind in ("facts", "beyond-wikipedia"):
            if pg.execute("SELECT COUNT(*) FROM claim WHERE source_file=%s", (kind,)).fetchone()[0] != receipts[kind]["counts"].get("mapped", 0):
                raise RuntimeError(f"{kind} claim count differs from scan ledger")
        for kind in ("taxonomy", "labels", "beyond-wikipedia-labels"):
            if pg.execute("SELECT COUNT(*) FROM auxiliary WHERE source_file=%s", (kind,)).fetchone()[0] != receipts[kind]["counts"].get("mapped", 0):
                raise RuntimeError(f"{kind} auxiliary count differs from scan ledger")
        for kind in ("facts-context", "beyond-wikipedia-context"):
            if pg.execute("SELECT COUNT(*) FROM auxiliary WHERE source_file=%s", (kind,)).fetchone()[0] != receipts[kind]["counts"].get("context_hint", 0):
                raise RuntimeError(f"{kind} context count differs from scan ledger")
        if pg.execute("SELECT COUNT(*) FROM meta_evidence").fetchone()[0] != receipts["attach-meta"]["attached_meta_rows"]:
            raise RuntimeError("attached Meta count differs from PG")
        if pg.execute("SELECT COUNT(*) FROM context_anchor").fetchone()[0] != receipts["context-index"]["anchored_subjects"]:
            raise RuntimeError("context anchor count differs from PG")
        if pg.execute("SELECT COUNT(*) FROM meta_evidence m WHERE NOT EXISTS (SELECT 1 FROM claim c WHERE c.triple_key=m.parent_key)").fetchone()[0]:
            raise RuntimeError("Meta evidence has no selected parent")
        if pg.execute("SELECT COUNT(*) FROM claim WHERE lane='H_state' AND ((time_json->>'start_year')::integer > %s OR (time_json->>'end_year')::integer < (time_json->>'start_year')::integer)", (CUTOFF,)).fetchone()[0]:
            raise RuntimeError("invalid accepted H_state time")
        readback_sha, row_counts = database_readback(pg)
        if row_counts["claim"] != receipts["facts"]["counts"].get("mapped", 0) + receipts["beyond-wikipedia"]["counts"].get("mapped", 0):
            raise RuntimeError("readback claim denominator mismatch")
        receipts_sha = hashlib.sha256(json.dumps(receipts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if (acceptance.get("readback_sha256") != readback_sha
                or acceptance.get("receipt_bundle_sha256") != receipts_sha
                or acceptance.get("row_counts") != row_counts):
            raise RuntimeError("independent acceptance does not match current staging output")
        payload = {"manifest_sha256": manifest_sha, "code_sha256": code_sha, "policy": POLICY,
                   "cutoff": CUTOFF, "receipts": receipts, "readback_sha256": readback_sha,
                   "row_counts": row_counts, "receipt_bundle_sha256": receipts_sha,
                   "acceptance_sha256": file_sha256(acceptance_path)}
        payload_sha = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        release_id = f"reality:yago46:world:through1899:{payload_sha[:16]}"
        existing = pg.execute("SELECT payload_sha256 FROM release WHERE release_id=%s", (release_id,)).fetchone()
        if existing:
            if existing[0] != payload_sha:
                raise RuntimeError("release ID collision")
            return {"release_id": release_id, "created": False, "payload_sha256": payload_sha,
                    "readback_sha256": readback_sha, "row_counts": row_counts}
        if pg.execute("SELECT 1 FROM release").fetchone():
            raise RuntimeError("dedicated DB already published")
        for kind in FILE_NAMES:
            r = receipts[kind]
            receipt_sha = hashlib.sha256(receipt_path(kind).read_bytes()).hexdigest()
            pg.execute("INSERT INTO source_scan VALUES (%s,%s,%s,%s::jsonb,%s)",
                       (kind, r["sha256"], r["bytes"], json.dumps(r["counts"], sort_keys=True), receipt_sha))
        pg.execute("INSERT INTO release(release_id,policy,cutoff_year,input_manifest_sha256,code_sha256,payload_sha256) VALUES (%s,%s,%s,%s,%s,%s)",
                   (release_id, POLICY, CUTOFF, manifest_sha, code_sha, payload_sha))
    result = {"release_id": release_id, "created": True, "payload_sha256": payload_sha,
              "manifest_sha256": manifest_sha, "code_sha256": code_sha,
              "readback_sha256": readback_sha, "row_counts": row_counts,
              "receipt_bundle_sha256": receipts_sha,
              "acceptance_sha256": file_sha256(acceptance_path)}
    save_receipt("release", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["scan", "prepublish", "publish", "status", "query"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--subject")
    parser.add_argument("--year", type=int)
    parser.add_argument("--acceptance", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if args.phase == "scan":
        scan_meta(manifest)
        for kind in ("facts", "beyond-wikipedia"):
            scan_fact_file(kind, manifest)
        attach_meta()
        prepare_context_index()
        for kind in ("facts", "beyond-wikipedia"):
            scan_context(kind, manifest)
        for kind in ("taxonomy", "labels", "beyond-wikipedia-labels"):
            scan_auxiliary(kind, manifest)
    elif args.phase == "publish":
        if args.acceptance is None:
            parser.error("publish requires --acceptance from independent Sol")
        print(json.dumps(publish(args.manifest, Path(__file__), args.acceptance), ensure_ascii=False))
    elif args.phase == "prepublish":
        required = list(FILE_NAMES) + ["attach-meta", "context-index", "facts-context", "beyond-wikipedia-context"]
        receipts = {kind: json.loads(receipt_path(kind).read_text()) for kind in required}
        with pg_connection() as pg:
            readback_sha, row_counts = database_readback(pg)
        print(json.dumps({"code_sha256": file_sha256(Path(__file__)),
                          "manifest_sha256": file_sha256(args.manifest),
                          "readback_sha256": readback_sha, "row_counts": row_counts,
                          "receipt_bundle_sha256": hashlib.sha256(json.dumps(receipts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()},
                         ensure_ascii=False, sort_keys=True, indent=2))
    elif args.phase == "status":
        print(json.dumps({kind: json.loads(receipt_path(kind).read_text()) if receipt_path(kind).exists() else None
                          for kind in list(FILE_NAMES) + ["attach-meta", "context-index", "facts-context", "beyond-wikipedia-context", "release"]}, ensure_ascii=False, indent=2))
    else:
        if args.subject is None or args.year is None:
            parser.error("query requires --subject and --year")
        with pg_connection() as pg:
            if not pg.execute("SELECT 1 FROM release").fetchone():
                raise RuntimeError("unpublished draft")
            rows = pg.execute("""SELECT source_file,line_no,raw,lane,time_json,reason FROM claim
                                 WHERE subject=%s ORDER BY source_file,line_no""", (args.subject,)).fetchall()
            out = []
            for source_file, line, raw, lane, time, reason in rows:
                if lane not in {"H_event", "H_boundary", "H_state"}:
                    continue
                if time["kind"] == "point":
                    match = time["year"] == args.year
                elif time["kind"] == "interval":
                    match = (time["start_year"] is None or time["start_year"] <= args.year) and (time["end_year"] is None or time["end_year"] >= args.year)
                else:
                    match = False
                if match and args.year <= CUTOFF:
                    out.append({"source_file": source_file, "line": line, "raw": raw, "lane": lane,
                                "time": time, "reason": reason})
            print(json.dumps({"subject": args.subject, "year": args.year, "release_id": pg.execute("SELECT release_id FROM release").fetchone()[0], "claims": out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
