"""SQLite persistence for immutable imported reverse-review releases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

from novel_factory.style.sqlite_store import SQLiteAnalysisStore, _sha


LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS legacy_imports (
 import_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, accepted_count INTEGER NOT NULL,
 candidate_count INTEGER NOT NULL, selection_count INTEGER NOT NULL,
 source_hashes_json TEXT NOT NULL, selection_policy_hashes_json TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS legacy_artifacts (
 import_id TEXT NOT NULL REFERENCES legacy_imports(import_id),
 release TEXT NOT NULL, relative_path TEXT NOT NULL, sha256 TEXT NOT NULL,
 raw_bytes BLOB NOT NULL, PRIMARY KEY(import_id,release,relative_path)
);
CREATE TABLE IF NOT EXISTS legacy_selections (
 import_id TEXT NOT NULL REFERENCES legacy_imports(import_id),
 release TEXT NOT NULL, selection_id TEXT NOT NULL, work_id TEXT NOT NULL,
 role TEXT NOT NULL, split TEXT NOT NULL, source_revision_id INTEGER NOT NULL,
 source_sha256 TEXT NOT NULL, segmentation_id INTEGER NOT NULL,
 start_cp INTEGER NOT NULL, end_cp INTEGER NOT NULL,
 review_sha256 TEXT NOT NULL, decision_sha256 TEXT NOT NULL,
 PRIMARY KEY(import_id,release,selection_id)
);
CREATE TABLE IF NOT EXISTS legacy_attempts (
 import_id TEXT NOT NULL, release TEXT NOT NULL, selection_id TEXT NOT NULL,
 attempt_key TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL,
 portion TEXT, start_cp INTEGER NOT NULL, end_cp INTEGER NOT NULL,
 text_sha256 TEXT NOT NULL, candidate_ids_json TEXT NOT NULL,
 PRIMARY KEY(import_id,release,selection_id,attempt_key),
 FOREIGN KEY(import_id,release,selection_id)
 REFERENCES legacy_selections(import_id,release,selection_id)
);
CREATE TABLE IF NOT EXISTS legacy_review_revisions (
 import_id TEXT NOT NULL REFERENCES legacy_imports(import_id),
 release TEXT NOT NULL, selection_id TEXT NOT NULL,
 artifact_path TEXT NOT NULL, previous_review_sha256 TEXT NOT NULL,
 new_review_sha256 TEXT NOT NULL, correction_reason TEXT NOT NULL,
 PRIMARY KEY(import_id,release,artifact_path),
 FOREIGN KEY(import_id,release,selection_id)
 REFERENCES legacy_selections(import_id,release,selection_id)
);
CREATE TABLE IF NOT EXISTS legacy_candidates (
 import_id TEXT NOT NULL, release TEXT NOT NULL, selection_id TEXT NOT NULL,
 candidate_id TEXT NOT NULL, decision TEXT NOT NULL,
 answer_start_cp INTEGER NOT NULL, answer_end_cp INTEGER NOT NULL,
 prior_start_cp INTEGER NOT NULL, prior_end_cp INTEGER NOT NULL,
 candidate_json TEXT NOT NULL,
 PRIMARY KEY(import_id,release,candidate_id),
 FOREIGN KEY(import_id,release,selection_id)
 REFERENCES legacy_selections(import_id,release,selection_id)
);
CREATE TABLE IF NOT EXISTS legacy_export_rows (
 import_id TEXT NOT NULL, release TEXT NOT NULL, work_id TEXT NOT NULL,
 split TEXT NOT NULL, ordinal INTEGER NOT NULL, candidate_id TEXT NOT NULL,
 raw_line BLOB NOT NULL, line_sha256 TEXT NOT NULL,
 PRIMARY KEY(import_id,release,work_id,split,ordinal),
 UNIQUE(import_id,release,candidate_id),
 FOREIGN KEY(import_id,release,candidate_id)
 REFERENCES legacy_candidates(import_id,release,candidate_id)
);
CREATE INDEX IF NOT EXISTS legacy_rows_order ON legacy_export_rows(import_id,release,work_id,split,ordinal);
"""


class SQLiteLegacyStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)

    def _connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        if not self.db_path.is_file():
            raise ValueError(f"corpus DB does not exist: {self.db_path}")
        uri = f"file:{self.db_path}?mode=ro" if readonly else str(self.db_path)
        conn = sqlite3.connect(uri, uri=readonly)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
            conn.close()
            raise ValueError("unsupported corpus schema version")
        return conn

    def has_import_schema(self) -> bool:
        conn = self._connect(readonly=True)
        try:
            return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='legacy_imports'").fetchone() is not None
        finally:
            conn.close()

    def _imported(self, conn: sqlite3.Connection, import_id: str) -> None:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='legacy_imports'").fetchone() is None:
            raise ValueError("fixed legacy import release is unavailable; file fallback is disabled")
        row = conn.execute("SELECT 1 FROM legacy_imports WHERE import_id=?", (import_id,)).fetchone()
        if row is None:
            raise ValueError("legacy import release is unavailable; file fallback is disabled")

    def get_legacy_section(self, import_id: str, work_id: str, order: int) -> dict:
        """One historical initial section; imported review is not a new analysis approval."""
        conn = self._connect(readonly=True)
        try:
            self._imported(conn, import_id)
            rows = conn.execute("""SELECT a.*,s.work_id,s.role,s.split,s.source_revision_id,
                s.source_sha256,s.segmentation_id FROM legacy_attempts a
                JOIN legacy_selections s ON (s.import_id,s.release,s.selection_id)=
                (a.import_id,a.release,a.selection_id)
                WHERE a.import_id=? AND a.release='initial' AND s.work_id=? AND a.attempt_key=?""",
                (import_id, work_id, str(order))).fetchall()
            if len(rows) != 1:
                raise ValueError("historical section is not uniquely imported")
            row = rows[0]
            SQLiteAnalysisStore._pin(conn, work_id, row["source_revision_id"],
                row["source_sha256"], row["segmentation_id"])
            body = SQLiteAnalysisStore._span_text(conn, row["segmentation_id"],
                row["start_cp"], row["end_cp"])
            if _sha(body) != row["text_sha256"]:
                raise ValueError("imported section body SHA differs")
            return {"work_id": work_id, "section_order": order,
                "source_sha256": row["source_sha256"],
                "segmentation_id": row["segmentation_id"],
                "section_start_cp": row["start_cp"], "section_end_cp": row["end_cp"],
                "role": row["role"], "split": row["split"],
                "import_id": import_id, "legacy_attempt_status": row["status"],
                "task_id": None, "section_text": body}
        finally:
            conn.close()

    def get_legacy_window(self, import_id: str, work_id: str, band: int, slot: int,
                          *, alternative: bool = False, inspect: bool = False) -> dict:
        """Full-window historical source from DB only, with legacy sequence guard."""
        if not 1 <= band <= 6 or not 1 <= slot <= 8:
            raise ValueError("invalid full window position")
        window_id = f"{work_id}-b{band:02d}-w{slot:02d}"
        conn = self._connect(readonly=True)
        try:
            self._imported(conn, import_id)
            row = conn.execute("""SELECT s.*,a.status,a.portion,a.start_cp AS portion_start_cp,
                a.end_cp AS portion_end_cp,a.text_sha256,a.candidate_ids_json
                FROM legacy_selections s JOIN legacy_attempts a ON
                (s.import_id,s.release,s.selection_id)=(a.import_id,a.release,a.selection_id)
                WHERE s.import_id=? AND s.release='full' AND s.selection_id=? AND s.work_id=?""",
                (import_id, window_id, work_id)).fetchone()
            if row is None:
                raise ValueError("historical full window is not imported")
            portion = "alternative" if alternative else "primary"
            artifact = conn.execute("""SELECT raw_bytes FROM legacy_artifacts
                WHERE import_id=? AND release='full' AND relative_path=?""",
                (import_id, f"private/windows/{window_id}.json")).fetchone()
            if artifact is None:
                raise ValueError("frozen window selection metadata missing in DB")
            frozen = json.loads(bytes(artifact[0]))
            bounds = frozen[portion]
            result = {"window_id": window_id, "portion": portion,
                "split": row["split"], "source_sha256": row["source_sha256"],
                "start_cp": bounds["start_cp"], "end_cp": bounds["end_cp"],
                "section_orders": bounds["section_orders"],
                "review_decision": (None if row["portion"] != portion else
                    "accepted" if conn.execute("""SELECT 1 FROM legacy_candidates WHERE import_id=?
                        AND release='full' AND selection_id=? AND decision='accepted' LIMIT 1""",
                        (import_id, window_id)).fetchone() else "hold")}
            if inspect:
                return result
            if row["portion"] != portion:
                raise ValueError("requested portion was not the imported reviewed selection")
            position = (band - 1) * 8 + slot
            for earlier in range(1, position):
                previous = f"{work_id}-b{(earlier - 1)//8+1:02d}-w{(earlier - 1)%8+1:02d}"
                if conn.execute("""SELECT 1 FROM legacy_selections WHERE import_id=?
                    AND release='full' AND selection_id=?""", (import_id, previous)).fetchone() is None:
                    raise ValueError(f"previous DB window not independently imported: {previous}")
            SQLiteAnalysisStore._pin(conn, work_id, row["source_revision_id"],
                row["source_sha256"], row["segmentation_id"])
            body = SQLiteAnalysisStore._span_text(conn, row["segmentation_id"],
                row["portion_start_cp"], row["portion_end_cp"])
            if (_sha(body) != row["text_sha256"] or
                (row["portion_start_cp"], row["portion_end_cp"]) !=
                (bounds["start_cp"], bounds["end_cp"])):
                raise ValueError("imported full portion differs from DB source")
            return {**result, "import_id": import_id, "task_id": None, "text": body}
        finally:
            conn.close()

    def import_bundle(self, bundle: dict) -> dict:
        """All normalized state and exact legacy artifacts commit together."""
        conn = self._connect()
        try:
            conn.executescript(LEGACY_SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT fingerprint FROM legacy_imports WHERE import_id=?",
                                    (bundle["import_id"],)).fetchone()
            if existing is not None:
                if existing[0] != bundle["fingerprint"]:
                    raise ValueError("same import ID has different legacy payload")
                return {"import_id": bundle["import_id"], "created": False,
                        "accepted": bundle["accepted_count"]}
            conn.execute("""INSERT INTO legacy_imports(import_id,fingerprint,accepted_count,
                candidate_count,selection_count,source_hashes_json,selection_policy_hashes_json)
                VALUES(?,?,?,?,?,?,?)""", (bundle["import_id"], bundle["fingerprint"],
                bundle["accepted_count"], len(bundle["candidates"]), len(bundle["selections"]),
                json.dumps(bundle["source_hashes"], sort_keys=True),
                json.dumps(bundle["selection_policy_hashes"], sort_keys=True)))
            conn.executemany("INSERT INTO legacy_artifacts VALUES(?,?,?,?,?)",
                             ((bundle["import_id"], *row) for row in bundle["artifacts"]))
            conn.executemany("INSERT INTO legacy_selections VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             ((bundle["import_id"], *row) for row in bundle["selections"]))
            conn.executemany("INSERT INTO legacy_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                             ((bundle["import_id"], *row) for row in bundle["attempts"]))
            conn.executemany("INSERT INTO legacy_review_revisions VALUES(?,?,?,?,?,?,?)",
                             ((bundle["import_id"], *row) for row in bundle["review_revisions"]))
            conn.executemany("INSERT INTO legacy_candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
                             ((bundle["import_id"], *row) for row in bundle["candidates"]))
            conn.executemany("INSERT INTO legacy_export_rows VALUES(?,?,?,?,?,?,?,?)",
                             ((bundle["import_id"], *row) for row in bundle["rows"]))
            counts = tuple(conn.execute("SELECT COUNT(*) FROM " + table + " WHERE import_id=?",
                                        (bundle["import_id"],)).fetchone()[0]
                           for table in ("legacy_selections", "legacy_attempts",
                                         "legacy_candidates", "legacy_export_rows"))
            expected = tuple(len(bundle[k]) for k in ("selections", "attempts", "candidates", "rows"))
            if counts != expected or counts[-1] != bundle["accepted_count"]:
                raise ValueError("legacy import row accounting differs")
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("legacy import foreign key violation")
            conn.commit()
            return {"import_id": bundle["import_id"], "created": True,
                    "accepted": bundle["accepted_count"]}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def load_accepted_release(self, import_id: str) -> dict:
        conn = self._connect(readonly=True)
        try:
            self._imported(conn, import_id)
            release = conn.execute("SELECT * FROM legacy_imports WHERE import_id=?", (import_id,)).fetchone()
            if release is None:
                raise ValueError("fixed legacy import release is unavailable")
            rows = []
            query = """SELECT r.*, c.decision, c.answer_start_cp, c.answer_end_cp,
                s.role,s.source_revision_id,s.source_sha256,s.segmentation_id
                FROM legacy_export_rows r
                JOIN legacy_candidates c ON (c.import_id,c.release,c.candidate_id)=
                    (r.import_id,r.release,r.candidate_id)
                JOIN legacy_selections s ON (s.import_id,s.release,s.selection_id)=
                    (c.import_id,c.release,c.selection_id)
                WHERE r.import_id=? ORDER BY
                  CASE r.work_id WHEN 'gogjong' THEN 0 WHEN 'goryeo' THEN 1 ELSE 2 END,
                  CASE r.split WHEN 'train' THEN 0 WHEN 'development_validation' THEN 1 ELSE 2 END,
                  CASE r.release WHEN 'initial' THEN 0 ELSE 1 END,r.ordinal"""
            for row in conn.execute(query, (import_id,)):
                if row["decision"] != "accepted" or row["work_id"] is None:
                    raise ValueError("export row has no accepted candidate")
                raw = bytes(row["raw_line"])
                if hashlib.sha256(raw).hexdigest() != row["line_sha256"] or raw.endswith(b"\n"):
                    raise ValueError("stored legacy JSONL line differs")
                record = json.loads(raw)
                metadata = record["metadata"]
                if (record["sample_id"], metadata["work_id"], metadata["role"],
                    metadata["split"], metadata["source_sha256"], metadata["segmentation_id"],
                    metadata["answer_start_cp"], metadata["answer_end_cp"]) != (
                    row["candidate_id"], row["work_id"], row["role"], row["split"],
                    row["source_sha256"], row["segmentation_id"],
                    row["answer_start_cp"], row["answer_end_cp"]):
                    raise ValueError("export metadata differs from normalized candidate")
                SQLiteAnalysisStore._pin(conn, row["work_id"], row["source_revision_id"],
                                         row["source_sha256"], row["segmentation_id"])
                answer = SQLiteAnalysisStore._span_text(conn, row["segmentation_id"],
                    row["answer_start_cp"], row["answer_end_cp"])
                if _sha(answer) != metadata["answer_sha256"]:
                    raise ValueError("legacy answer span SHA differs from pinned DB source")
                rows.append({"release": row["release"], "record": record,
                             "raw_line": raw.decode("utf-8"), "source_answer": answer})
            return {"release_id": import_id, "source_hashes": json.loads(release["source_hashes_json"]),
                    "selection_policy_hashes": json.loads(release["selection_policy_hashes_json"]),
                    "accepted_count": release["accepted_count"], "rows": rows}
        finally:
            conn.close()

    def load_status(self, import_id: str, work_id: str | None = None,
                    selection_id: str | None = None) -> list[dict]:
        """Expose held/unmade decisions and historical review revisions without payloads."""
        conn = self._connect(readonly=True)
        try:
            self._imported(conn, import_id)
            selections = conn.execute("""SELECT * FROM legacy_selections
                WHERE import_id=? AND (? IS NULL OR work_id=?)
                AND (? IS NULL OR selection_id=?)
                ORDER BY work_id,release,selection_id""",
                (import_id, work_id, work_id, selection_id, selection_id)).fetchall()
            if selection_id and not selections:
                raise ValueError("historical selection is not in this fixed release")
            result = []
            for selection in selections:
                release, sid = selection["release"], selection["selection_id"]
                attempts = [dict(row) for row in conn.execute("""SELECT attempt_key,status,reason,
                    portion,start_cp,end_cp,text_sha256,candidate_ids_json
                    FROM legacy_attempts WHERE import_id=? AND release=? AND selection_id=?
                    ORDER BY CAST(attempt_key AS INTEGER),attempt_key""", (import_id, release, sid))]
                for attempt in attempts:
                    attempt["candidate_ids"] = json.loads(attempt.pop("candidate_ids_json"))
                candidates = [dict(row) for row in conn.execute("""SELECT candidate_id,decision,
                    answer_start_cp,answer_end_cp FROM legacy_candidates
                    WHERE import_id=? AND release=? AND selection_id=? ORDER BY candidate_id""",
                    (import_id, release, sid))]
                revisions = [dict(row) for row in conn.execute("""SELECT artifact_path,
                    previous_review_sha256,new_review_sha256,correction_reason
                    FROM legacy_review_revisions WHERE import_id=? AND release=? AND selection_id=?
                    ORDER BY artifact_path""", (import_id, release, sid))]
                held = sum(x["decision"] == "hold" for x in candidates)
                unmade = sum(x["status"] == "hold" and not x["candidate_ids"] for x in attempts)
                result.append({"import_id": import_id, "release": release,
                    "selection_id": sid, "work_id": selection["work_id"],
                    "role": selection["role"], "split": selection["split"],
                    "source_revision_id": selection["source_revision_id"],
                    "source_sha256": selection["source_sha256"],
                    "segmentation_id": selection["segmentation_id"],
                    "start_cp": selection["start_cp"], "end_cp": selection["end_cp"],
                    "review_sha256": selection["review_sha256"],
                    "decision_sha256": selection["decision_sha256"],
                    "accepted": sum(x["decision"] == "accepted" for x in candidates),
                    "held": held, "unmade_attempts": unmade,
                    "next_action": ("new DB review task needed; imported release is immutable"
                                    if held or unmade else "none"),
                    "attempts": attempts, "candidates": candidates,
                    "review_revisions": revisions})
            return result
        finally:
            conn.close()
