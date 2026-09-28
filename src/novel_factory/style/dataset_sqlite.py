"""SQLite adapter for immutable style dataset releases in the corpus DB."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from novel_factory.style.legacy_release import accepted_release
from novel_factory.style.legacy_sqlite import SQLiteLegacyStore


SCHEMA = """
CREATE TABLE IF NOT EXISTS style_dataset_releases (
  release_id TEXT PRIMARY KEY, parent_import_id TEXT NOT NULL, parent_fingerprint TEXT NOT NULL,
  role TEXT NOT NULL, purpose TEXT NOT NULL, split_semantics TEXT NOT NULL,
  fingerprint TEXT NOT NULL, counts_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(parent_import_id) REFERENCES legacy_imports(import_id)
);
CREATE TABLE IF NOT EXISTS style_dataset_items (
  release_id TEXT NOT NULL, ordinal INTEGER NOT NULL, candidate_id TEXT NOT NULL,
  selection_id TEXT NOT NULL, work_id TEXT NOT NULL, role TEXT NOT NULL, split TEXT NOT NULL,
  source_revision_id INTEGER NOT NULL, source_sha256 TEXT NOT NULL,
  segmentation_id INTEGER NOT NULL, answer_start_cp INTEGER NOT NULL, answer_end_cp INTEGER NOT NULL,
  answer_sha256 TEXT NOT NULL, prompt_sha256 TEXT NOT NULL, target_sha256 TEXT NOT NULL,
  review_sha256 TEXT NOT NULL, learning_hypothesis_sha256 TEXT NOT NULL, line_sha256 TEXT NOT NULL,
  PRIMARY KEY(release_id, ordinal), UNIQUE(release_id, candidate_id),
  FOREIGN KEY(release_id) REFERENCES style_dataset_releases(release_id)
);
"""

ITEM_COLUMNS = ("candidate_id", "selection_id", "work_id", "role", "split",
                "source_revision_id", "source_sha256", "segmentation_id", "answer_start_cp",
                "answer_end_cp", "answer_sha256", "prompt_sha256", "target_sha256",
                "review_sha256", "learning_hypothesis_sha256", "line_sha256")


class SQLiteDatasetStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def _connect(self, readonly: bool = False) -> sqlite3.Connection:
        if not self.path.is_file():
            raise ValueError("existing corpus database is required")
        conn = (sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
                if readonly else sqlite3.connect(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def read_reviewed_parent(self, import_id: str) -> dict:
        release = accepted_release(SQLiteLegacyStore(self.path), import_id)
        conn = self._connect(readonly=True)
        try:
            parent = conn.execute("SELECT fingerprint FROM legacy_imports WHERE import_id=?", (import_id,)).fetchone()
            if parent is None:
                raise ValueError("fixed parent import is missing")
            provenance = {}
            query = """SELECT c.release,c.candidate_id,c.selection_id,c.candidate_json,
                s.work_id,s.source_revision_id,s.source_sha256,s.segmentation_id,s.review_sha256,
                c.answer_start_cp,c.answer_end_cp,r.line_sha256
                FROM legacy_candidates c
                JOIN legacy_selections s ON (s.import_id,s.release,s.selection_id)=
                    (c.import_id,c.release,c.selection_id)
                JOIN legacy_export_rows r ON (r.import_id,r.release,r.candidate_id)=
                    (c.import_id,c.release,c.candidate_id)
                WHERE c.import_id=? AND c.decision='accepted'"""
            for row in conn.execute(query, (import_id,)):
                key = (row["release"], row["candidate_id"])
                if key in provenance:
                    raise ValueError("duplicate reviewed candidate provenance")
                provenance[key] = dict(row)
            rows = []
            for row in release["rows"]:
                key = (row["release"], row["record"]["sample_id"])
                meta = provenance.pop(key, None)
                if meta is None:
                    raise ValueError("accepted output lacks reviewed provenance")
                meta["candidate"] = json.loads(meta.pop("candidate_json"))
                rows.append({**row, **meta})
            if provenance:
                raise ValueError("reviewed candidate lacks accepted output")
            return {"import_id": import_id, "fingerprint": parent["fingerprint"], "rows": rows}
        finally:
            conn.close()

    def publish_dataset(self, release: dict) -> dict:
        conn = self._connect()
        try:
            conn.executescript(SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
            old = conn.execute("SELECT fingerprint FROM style_dataset_releases WHERE release_id=?",
                               (release["release_id"],)).fetchone()
            if old is not None:
                if old["fingerprint"] != release["fingerprint"]:
                    raise ValueError("same dataset release ID has different reviewed content")
                conn.rollback()
                return {**self.read_dataset(release["release_id"]), "created": False}
            conn.execute("""INSERT INTO style_dataset_releases
                (release_id,parent_import_id,parent_fingerprint,role,purpose,split_semantics,fingerprint,counts_json)
                VALUES(?,?,?,?,?,?,?,?)""", (release["release_id"], release["parent_import_id"],
                release["parent_fingerprint"], release["role"], release["purpose"],
                release["split_semantics"], release["fingerprint"],
                json.dumps(release["counts"], sort_keys=True)))
            columns = ",".join(("release_id", "ordinal", *ITEM_COLUMNS))
            marks = ",".join("?" for _ in range(2 + len(ITEM_COLUMNS)))
            conn.executemany(f"INSERT INTO style_dataset_items ({columns}) VALUES({marks})",
                ((release["release_id"], i, *(item[k] for k in ITEM_COLUMNS))
                 for i, item in enumerate(release["items"])))
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("dataset release has broken references")
            conn.commit()
            return {**self.read_dataset(release["release_id"]), "created": True}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def read_dataset(self, release_id: str) -> dict:
        conn = self._connect(readonly=True)
        try:
            row = conn.execute("SELECT * FROM style_dataset_releases WHERE release_id=?", (release_id,)).fetchone()
            if row is None:
                raise ValueError("dataset release is not registered")
            items = [dict(x) for x in conn.execute("""SELECT * FROM style_dataset_items
                WHERE release_id=? ORDER BY ordinal""", (release_id,))]
            counts = json.loads(row["counts_json"])
            if len(items) != sum(counts.values()):
                raise ValueError("dataset release item count differs")
            return {"release_id": release_id, "parent_import_id": row["parent_import_id"],
                    "parent_fingerprint": row["parent_fingerprint"], "role": row["role"],
                    "purpose": row["purpose"], "split_semantics": row["split_semantics"],
                    "fingerprint": row["fingerprint"], "counts": counts, "items": items}
        finally:
            conn.close()
