"""SQLite adapter for one pinned, bounded analysis workflow.

The existing source/segmentation tables remain immutable. Analysis tables are
added only by the explicit ``init`` command, normally against a backup copy.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3

from novel_factory.contracts import SourceSpan
from novel_factory.style.workflow import (PreparedInput, Selection,
    check_review_transition, check_submission_transition)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_schema_meta (version INTEGER PRIMARY KEY CHECK(version=1));
INSERT OR IGNORE INTO analysis_schema_meta(version) VALUES(1);
CREATE TABLE IF NOT EXISTS analysis_windows (
  window_id TEXT PRIMARY KEY,
  work_id TEXT NOT NULL REFERENCES works(work_id),
  source_revision_id INTEGER NOT NULL REFERENCES source_revisions(id),
  source_sha256 TEXT NOT NULL,
  segmentation_id INTEGER NOT NULL REFERENCES segmentations(id),
  start_cp INTEGER NOT NULL,
  end_cp INTEGER NOT NULL,
  text_sha256 TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('gemma_style','sota_planning','chapter_analysis')),
  split TEXT NOT NULL CHECK(split IN ('none','train','development_validation','development_holdout')),
  workflow_kind TEXT NOT NULL CHECK(workflow_kind IN ('reverse_window','reverse_section')),
  approval_ref TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  CHECK(start_cp >= 0 AND end_cp > start_cp)
);
CREATE TABLE IF NOT EXISTS analysis_tasks (
  task_id TEXT PRIMARY KEY,
  work_id TEXT NOT NULL REFERENCES works(work_id),
  source_revision_id INTEGER NOT NULL REFERENCES source_revisions(id),
  source_sha256 TEXT NOT NULL,
  segmentation_id INTEGER NOT NULL REFERENCES segmentations(id),
  selection_kind TEXT NOT NULL CHECK(selection_kind IN ('chapter','window')),
  selection_id TEXT NOT NULL,
  workflow_kind TEXT NOT NULL,
  role TEXT NOT NULL,
  split TEXT NOT NULL,
  start_cp INTEGER NOT NULL,
  end_cp INTEGER NOT NULL,
  text_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK(start_cp >= 0 AND end_cp > start_cp)
);
CREATE TABLE IF NOT EXISTS analysis_submissions (
  id INTEGER PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES analysis_tasks(task_id),
  submission_id TEXT NOT NULL,
  submitted_by TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(task_id,submission_id)
);
CREATE TABLE IF NOT EXISTS analysis_reviews (
  id INTEGER PRIMARY KEY,
  task_id TEXT NOT NULL,
  submission_id TEXT NOT NULL,
  review_id TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  decision TEXT NOT NULL CHECK(decision IN ('accepted','rejected','hold')),
  reason TEXT NOT NULL,
  submission_sha256 TEXT NOT NULL,
  review_sha256 TEXT NOT NULL,
  previous_review_sha256 TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(task_id,review_id),
  FOREIGN KEY(task_id,submission_id) REFERENCES analysis_submissions(task_id,submission_id)
);
CREATE INDEX IF NOT EXISTS analysis_submissions_task ON analysis_submissions(task_id,id);
CREATE INDEX IF NOT EXISTS analysis_reviews_submission ON analysis_reviews(task_id,submission_id,id);
"""


class SQLiteAnalysisStore:
    def __init__(self, db: Path | str):
        self.db = Path(db)

    @contextmanager
    def _connect(self):
        if not self.db.is_file():
            raise ValueError(f"corpus DB does not exist: {self.db}")
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("unsupported corpus schema version")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("analysis schema violates foreign keys")

    @staticmethod
    def _check_schema(conn: sqlite3.Connection) -> None:
        try:
            version = conn.execute("SELECT version FROM analysis_schema_meta").fetchone()
        except sqlite3.OperationalError as exc:
            raise ValueError("analysis schema missing; run init on a corpus DB copy") from exc
        if version is None or version[0] != 1:
            raise ValueError("unsupported analysis schema")

    @staticmethod
    def _pin(conn: sqlite3.Connection, work_id: str, revision_id: int,
             source_sha256: str, segmentation_id: int) -> None:
        row = conn.execute("""SELECT sr.sha256_raw FROM source_revisions sr
            JOIN segmentations sg ON sg.source_revision_id=sr.id
            WHERE sr.work_id=? AND sr.id=? AND sg.id=?""",
            (work_id, revision_id, segmentation_id)).fetchone()
        if row is None or row[0] != source_sha256:
            raise ValueError("work/source revision/segmentation/SHA pin differs")

    @staticmethod
    def _span_text(conn: sqlite3.Connection, segmentation_id: int,
                   start: int, end: int) -> str:
        if start < 0 or end <= start:
            raise ValueError("invalid bounded CP span")
        rows = conn.execute("""SELECT start_cp,end_cp,text_sha256,body FROM segments
            WHERE segmentation_id=? AND end_cp>? AND start_cp<? ORDER BY start_cp""",
            (segmentation_id, start, end)).fetchall()
        cursor = start
        parts: list[str] = []
        for row in rows:
            a, b, digest, body = row
            if a > cursor or len(body) != b - a or _sha(body) != digest:
                raise ValueError("segment gap or body hash mismatch")
            lo, hi = max(cursor, a), min(end, b)
            if hi > lo:
                parts.append(body[lo - a:hi - a])
                cursor = hi
        if cursor != end:
            raise ValueError("requested CP range is not covered by pinned segmentation")
        result = "".join(parts)
        if len(result) != end - start:
            raise ValueError("CP range length mismatch")
        return result

    @staticmethod
    def _decision(conn: sqlite3.Connection, window_id: str) -> str | None:
        row = conn.execute("""SELECT t.task_id FROM analysis_tasks t
            WHERE t.selection_kind='window' AND t.selection_id=?""", (window_id,)).fetchone()
        if row is None:
            return None
        latest = SQLiteAnalysisStore._latest_submission(conn, row["task_id"])
        if latest is None:
            return None
        review = SQLiteAnalysisStore._latest_review(conn, row["task_id"], latest["submission_id"])
        return review["decision"] if review else None

    @staticmethod
    def _check_window_access(conn: sqlite3.Connection, window_id: str) -> None:
        """Keep the legacy full-window sequential reading rule at every DB body entry."""
        match = re.fullmatch(r"(.+)-b(0[1-6])-w(0[1-8]):(primary|alternative)", window_id)
        if match is None:
            return  # Independently approved, non-sequential selection.
        work, band, slot, portion = match.groups()
        position = (int(band) - 1) * 8 + int(slot)
        for earlier in range(1, position):
            previous = f"{work}-b{(earlier - 1)//8 + 1:02d}-w{(earlier - 1)%8 + 1:02d}"
            if not any(SQLiteAnalysisStore._decision(conn, previous + ':' + part) in ('accepted', 'hold')
                       for part in ('primary', 'alternative')):
                raise ValueError(f"previous DB window not independently reviewed: {previous}")
        if portion == 'alternative' and SQLiteAnalysisStore._decision(conn, window_id[:-12] + ':primary') != 'hold':
            raise ValueError("alternative requires independent primary hold in DB")

    @staticmethod
    def _check_task_window_access(conn: sqlite3.Connection, task: sqlite3.Row) -> None:
        if task["selection_kind"] == "window":
            registered = conn.execute("SELECT * FROM analysis_windows WHERE window_id=?",
                                      (task["selection_id"],)).fetchone()
            if registered is None or any(task[k] != registered[k] for k in
                    ("work_id", "source_revision_id", "source_sha256", "segmentation_id",
                     "start_cp", "end_cp", "text_sha256", "role", "split", "workflow_kind")):
                raise ValueError("task differs from approved DB window")
            SQLiteAnalysisStore._check_window_access(conn, task["selection_id"])

    def register_window(self, *, window_id: str, work_id: str, source_revision_id: int,
                        source_sha256: str, segmentation_id: int, start_cp: int,
                        end_cp: int, text_sha256: str, role: str, split: str,
                        workflow_kind: str, approval_ref: str, approved_by: str) -> dict:
        if not window_id or not approval_ref or not approved_by:
            raise ValueError("approved window ID, decision reference and approver are required")
        if workflow_kind not in ("reverse_window", "reverse_section"):
            raise ValueError("invalid reverse workflow kind")
        if role not in ("gemma_style", "sota_planning"):
            raise ValueError("invalid role")
        if split not in ("train", "development_validation", "development_holdout"):
            raise ValueError("invalid split")
        legacy_role = {"gogjong": "gemma_style", "goryeo": "sota_planning",
                       "poland": "sota_planning"}.get(work_id)
        if legacy_role is not None and legacy_role != role:
            raise ValueError("reverse role differs from existing work role")
        with self._connect() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            self._pin(conn, work_id, source_revision_id, source_sha256, segmentation_id)
            body = self._span_text(conn, segmentation_id, start_cp, end_cp)
            if _sha(body) != text_sha256:
                raise ValueError("approved window span SHA differs")
            values = (window_id, work_id, source_revision_id, source_sha256, segmentation_id,
                      start_cp, end_cp, text_sha256, role, split, workflow_kind,
                      approval_ref, approved_by)
            old = conn.execute("SELECT * FROM analysis_windows WHERE window_id=?", (window_id,)).fetchone()
            if old is None:
                conn.execute("""INSERT INTO analysis_windows(window_id,work_id,source_revision_id,
                    source_sha256,segmentation_id,start_cp,end_cp,text_sha256,role,split,
                    workflow_kind,approval_ref,approved_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
            elif tuple(old[k] for k in ("window_id", "work_id", "source_revision_id", "source_sha256",
                  "segmentation_id", "start_cp", "end_cp", "text_sha256", "role", "split",
                  "workflow_kind", "approval_ref", "approved_by")) != values:
                raise ValueError("same window ID has a different approved selection")
            return {"window_id": window_id, "text_sha256": text_sha256, "registered": old is None}

    def _resolve(self, conn: sqlite3.Connection, selection: Selection) -> tuple[str, str, str, int, int, str]:
        self._pin(conn, selection.work_id, selection.source_revision_id,
                  selection.source_sha256, selection.segmentation_id)
        if selection.kind == "chapter":
            rows = conn.execute("""SELECT id,kind,boundary_status,start_cp,end_cp,text_sha256,body
                FROM segments WHERE segmentation_id=? AND number_claimed=?""",
                (selection.segmentation_id, selection.number_or_id)).fetchall()
            if len(rows) != 1 or rows[0]["kind"] != "numbered" or rows[0]["boundary_status"] != "confirmed":
                raise ValueError("chapter is not uniquely mapped and confirmed in pinned segmentation")
            row = rows[0]
            body = row["body"]
            if len(body) != row["end_cp"] - row["start_cp"] or _sha(body) != row["text_sha256"]:
                raise ValueError("chapter body hash differs")
            return str(selection.number_or_id), "chapter_analysis", "none", row["start_cp"], row["end_cp"], body
        row = conn.execute("SELECT * FROM analysis_windows WHERE window_id=?", (selection.number_or_id,)).fetchone()
        if row is None or (row["work_id"], row["source_revision_id"], row["source_sha256"],
                           row["segmentation_id"], row["workflow_kind"]) != (
                           selection.work_id, selection.source_revision_id, selection.source_sha256,
                           selection.segmentation_id, selection.workflow_kind):
            raise ValueError("approved window missing or pinned identity differs")
        if row["role"] not in ("gemma_style", "sota_planning") or row["split"] == "none":
            raise ValueError("approved window has inconsistent role or split")
        self._check_window_access(conn, row["window_id"])
        body = self._span_text(conn, row["segmentation_id"], row["start_cp"], row["end_cp"])
        if _sha(body) != row["text_sha256"]:
            raise ValueError("approved window body hash differs")
        return row["window_id"], row["role"], row["split"], row["start_cp"], row["end_cp"], body

    def prepare(self, selection: Selection) -> PreparedInput:
        with self._connect() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            selection_id, role, split, start, end, body = self._resolve(conn, selection)
            body_sha = _sha(body)
            identity = json.dumps(["analysis-v1", selection.work_id, selection.source_revision_id,
                selection.source_sha256, selection.segmentation_id, selection.kind, selection_id,
                selection.workflow_kind, role, split, start, end, body_sha], separators=(",", ":"))
            task_id = "analysis:" + hashlib.sha256(identity.encode()).hexdigest()
            span = SourceSpan(selection.work_id, selection.source_revision_id,
                              selection.source_sha256, selection.segmentation_id, start, end, body_sha)
            values = (task_id, selection.work_id, selection.source_revision_id, selection.source_sha256,
                      selection.segmentation_id, selection.kind, selection_id,
                      selection.workflow_kind, role, split, start, end, body_sha)
            old = conn.execute("SELECT * FROM analysis_tasks WHERE task_id=?", (task_id,)).fetchone()
            if old is None:
                conn.execute("""INSERT INTO analysis_tasks(task_id,work_id,source_revision_id,
                    source_sha256,segmentation_id,selection_kind,selection_id,workflow_kind,
                    role,split,start_cp,end_cp,text_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
            elif tuple(old[k] for k in ("task_id", "work_id", "source_revision_id", "source_sha256",
                  "segmentation_id", "selection_kind", "selection_id", "workflow_kind", "role",
                  "split", "start_cp", "end_cp", "text_sha256")) != values:
                raise ValueError("same task ID has different pinned input")
            return PreparedInput(task_id, selection.workflow_kind, selection.kind,
                                 selection_id, role, split, span, body)

    def prepare_window_id(self, window_id: str) -> PreparedInput:
        """Use only an explicitly registered selection; legacy JSON is not a body fallback."""
        with self._connect() as conn:
            self._check_schema(conn)
            row = conn.execute("SELECT * FROM analysis_windows WHERE window_id=?", (window_id,)).fetchone()
            if row is None:
                raise ValueError("window is not registered as an approved DB selection")
            selection = Selection(row["work_id"], row["source_revision_id"],
                                  row["source_sha256"], row["segmentation_id"],
                                  "window", window_id, row["workflow_kind"])
        return self.prepare(selection)

    def get_input(self, task_id: str) -> PreparedInput:
        with self._connect() as conn:
            self._check_schema(conn)
            row = conn.execute("SELECT * FROM analysis_tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError("unknown analysis task")
            self._check_task_window_access(conn, row)
            self._pin(conn, row["work_id"], row["source_revision_id"],
                      row["source_sha256"], row["segmentation_id"])
            body = self._span_text(conn, row["segmentation_id"], row["start_cp"], row["end_cp"])
            if _sha(body) != row["text_sha256"]:
                raise ValueError("pinned input body SHA differs")
            span = SourceSpan(row["work_id"], row["source_revision_id"], row["source_sha256"],
                              row["segmentation_id"], row["start_cp"], row["end_cp"], row["text_sha256"])
            return PreparedInput(task_id, row["workflow_kind"], row["selection_kind"],
                                 row["selection_id"], row["role"], row["split"], span, body)

    def get_submission(self, task_id: str, submission_id: str) -> dict:
        """Return the exact submitted JSON and decision metadata from the DB SoT."""
        with self._connect() as conn:
            self._check_schema(conn)
            task = conn.execute("SELECT * FROM analysis_tasks WHERE task_id=?", (task_id,)).fetchone()
            if task is None:
                raise ValueError("unknown analysis task")
            self._check_task_window_access(conn, task)
            submission = conn.execute("""SELECT * FROM analysis_submissions
                WHERE task_id=? AND submission_id=?""", (task_id, submission_id)).fetchone()
            if submission is None:
                raise ValueError("submission does not belong to this task")
            if _sha(submission["payload_json"]) != submission["payload_sha256"]:
                raise ValueError("stored submission bytes differ from SHA-256")
            review = self._latest_review(conn, task_id, submission_id)
            return {"task_id": task_id, "submission_id": submission_id,
                    "work_id": task["work_id"],
                    "source_revision_id": task["source_revision_id"],
                    "selection_kind": task["selection_kind"],
                    "selection_id": task["selection_id"],
                    "workflow_kind": task["workflow_kind"], "role": task["role"],
                    "split": task["split"], "source_sha256": task["source_sha256"],
                    "segmentation_id": task["segmentation_id"],
                    "start_cp": task["start_cp"], "end_cp": task["end_cp"],
                    "submitted_by": submission["submitted_by"],
                    "payload_sha256": submission["payload_sha256"],
                    "payload_json": submission["payload_json"],
                    "review_id": review["review_id"] if review else None,
                    "review_sha256": review["review_sha256"] if review else None,
                    "review_decision": review["decision"] if review else None}

    @staticmethod
    def _latest_submission(conn: sqlite3.Connection, task_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM analysis_submissions WHERE task_id=? ORDER BY id DESC LIMIT 1",
                            (task_id,)).fetchone()

    @staticmethod
    def _latest_review(conn: sqlite3.Connection, task_id: str, submission_id: str) -> sqlite3.Row | None:
        return conn.execute("""SELECT * FROM analysis_reviews WHERE task_id=? AND submission_id=?
            ORDER BY id DESC LIMIT 1""", (task_id, submission_id)).fetchone()

    def submit(self, task_id: str, submission_id: str, actor: str, payload: str, sha256: str) -> dict:
        with self._connect() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute("SELECT * FROM analysis_tasks WHERE task_id=?", (task_id,)).fetchone()
            if task is None:
                raise ValueError("unknown analysis task")
            self._check_task_window_access(conn, task)
            old = conn.execute("SELECT * FROM analysis_submissions WHERE task_id=? AND submission_id=?",
                               (task_id, submission_id)).fetchone()
            if old is not None:
                if (old["submitted_by"], old["payload_sha256"], old["payload_json"]) != (actor, sha256, payload):
                    raise ValueError("same submission ID has different payload")
                return {"task_id": task_id, "submission_id": submission_id,
                        "submission_sha256": sha256, "created": False}
            latest = self._latest_submission(conn, task_id)
            if latest is not None:
                review = self._latest_review(conn, task_id, latest["submission_id"])
                check_submission_transition(review["decision"] if review else None, review is None)
            conn.execute("""INSERT INTO analysis_submissions(task_id,submission_id,submitted_by,
                payload_json,payload_sha256) VALUES(?,?,?,?,?)""",
                (task_id, submission_id, actor, payload, sha256))
            return {"task_id": task_id, "submission_id": submission_id,
                    "submission_sha256": sha256, "created": True}

    def review(self, task_id: str, submission_id: str, review_id: str, reviewer: str,
               decision: str, reason: str, submission_sha256: str,
               previous_review_sha256: str | None) -> dict:
        review_data = json.dumps([task_id, submission_id, review_id, reviewer,
                                  decision, reason, submission_sha256, previous_review_sha256],
                                 ensure_ascii=False, separators=(",", ":"))
        review_sha = _sha(review_data)
        with self._connect() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            latest = self._latest_submission(conn, task_id)
            if latest is None or latest["submission_id"] != submission_id:
                raise ValueError("review requires the latest exact submission")
            task = conn.execute("SELECT * FROM analysis_tasks WHERE task_id=?", (task_id,)).fetchone()
            self._check_task_window_access(conn, task)
            old = conn.execute("SELECT * FROM analysis_reviews WHERE task_id=? AND review_id=?",
                               (task_id, review_id)).fetchone()
            if old is not None:
                if old["review_sha256"] != review_sha:
                    raise ValueError("same review ID has different decision payload")
                return {"task_id": task_id, "review_id": review_id,
                        "review_sha256": review_sha, "decision": decision, "created": False}
            previous = self._latest_review(conn, task_id, submission_id)
            expected = previous["review_sha256"] if previous else None
            check_review_transition(latest["submitted_by"], reviewer,
                latest["payload_sha256"], submission_sha256,
                expected, previous_review_sha256)
            conn.execute("""INSERT INTO analysis_reviews(task_id,submission_id,review_id,reviewer,
                decision,reason,submission_sha256,review_sha256,previous_review_sha256)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (task_id, submission_id, review_id, reviewer, decision, reason,
                 submission_sha256, review_sha, previous_review_sha256))
            return {"task_id": task_id, "review_id": review_id,
                    "review_sha256": review_sha, "decision": decision, "created": True}

    def resume(self, task_id: str | None = None) -> list[dict]:
        with self._connect() as conn:
            self._check_schema(conn)
            rows = conn.execute("""SELECT * FROM analysis_tasks
                WHERE (? IS NULL OR task_id=?) ORDER BY created_at,task_id""",
                (task_id, task_id)).fetchall()
            if task_id and not rows:
                raise ValueError("unknown analysis task")
            result = []
            for task in rows:
                submission = self._latest_submission(conn, task["task_id"])
                review = (self._latest_review(conn, task["task_id"], submission["submission_id"])
                          if submission else None)
                state = ("prepared" if submission is None else "needs_review" if review is None
                         else "complete" if review["decision"] == "accepted" else "needs_revision")
                try:
                    self._check_task_window_access(conn, task)
                except ValueError:
                    state = "blocked_prerequisite"
                result.append({k: task[k] for k in ("task_id", "work_id", "selection_kind",
                    "selection_id", "workflow_kind", "role", "split", "text_sha256")}
                    | {"state": state,
                               "submission_id": submission["submission_id"] if submission else None,
                               "submission_sha256": submission["payload_sha256"] if submission else None,
                               "review_id": review["review_id"] if review else None,
                               "review_sha256": review["review_sha256"] if review else None,
                               "review_decision": review["decision"] if review else None})
            return result

    def window_review_decision(self, window_id: str) -> str | None:
        """Read a registered window's latest independent decision, if any."""
        with self._connect() as conn:
            self._check_schema(conn)
            return self._decision(conn, window_id)
