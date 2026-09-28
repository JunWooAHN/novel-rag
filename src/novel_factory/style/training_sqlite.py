"""Single-writer SQLite adapter for offline run attempts and artifact registration."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from novel_factory.style.dataset_release import canonical, frozen_style_packet, sha
from novel_factory.style.dataset_sqlite import SQLiteDatasetStore
from novel_factory.style.training_contract import validate_request, validate_result


SCHEMA = """
CREATE TABLE IF NOT EXISTS style_training_runs (
  run_id TEXT PRIMARY KEY, dataset_release_id TEXT NOT NULL, dataset_fingerprint TEXT NOT NULL,
  model_revision TEXT NOT NULL, scope TEXT NOT NULL, state TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(dataset_release_id) REFERENCES style_dataset_releases(release_id)
);
CREATE TABLE IF NOT EXISTS style_training_attempts (
  run_id TEXT NOT NULL, attempt_id TEXT NOT NULL, request_sha256 TEXT NOT NULL,
  request_json TEXT NOT NULL, state TEXT NOT NULL, result_sha256 TEXT, result_json TEXT,
  PRIMARY KEY(run_id,attempt_id), FOREIGN KEY(run_id) REFERENCES style_training_runs(run_id)
);
CREATE TABLE IF NOT EXISTS style_model_artifacts (
  artifact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
  dataset_release_id TEXT NOT NULL, model_revision TEXT NOT NULL, scope TEXT NOT NULL,
  artifact_path TEXT NOT NULL, artifact_sha256 TEXT NOT NULL, result_sha256 TEXT NOT NULL,
  writing_eligible INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id,attempt_id),
  FOREIGN KEY(run_id,attempt_id) REFERENCES style_training_attempts(run_id,attempt_id)
);
"""


class SQLiteTrainingStore:
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

    def create_attempt(self, request: dict, request_sha256: str) -> dict:
        if validate_request(request) != request_sha256:
            raise ValueError("training request hash differs")
        conn = self._connect()
        try:
            conn.executescript(SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
            ds = conn.execute("""SELECT fingerprint,role,purpose FROM style_dataset_releases
                WHERE release_id=?""", (request["dataset_release_id"],)).fetchone()
            if (ds is None or ds["fingerprint"] != request["dataset_fingerprint"]
                    or ds["role"] != "gemma_style" or ds["purpose"] != "style_training_candidate"):
                raise ValueError("training request does not reference a style dataset release")
            if request["scope"] == "real":
                selected = request["selected_sample_ids"]
                marks = ",".join("?" for _ in selected)
                rows = conn.execute(f"""SELECT candidate_id,split FROM style_dataset_items
                    WHERE release_id=? AND candidate_id IN ({marks})""",
                    (request["dataset_release_id"], *selected)).fetchall()
                if len(rows) != len(selected) or any(row["split"] != "train" for row in rows):
                    raise ValueError("selected training IDs must belong to the pinned train split")
            packet = frozen_style_packet(SQLiteDatasetStore(self.path), request["dataset_release_id"])
            if sha(canonical(packet)) != request["packet_sha256"]:
                raise ValueError("training request packet differs from the DB release")
            run = conn.execute("SELECT * FROM style_training_runs WHERE run_id=?",
                               (request["run_id"],)).fetchone()
            if run is None:
                conn.execute("""INSERT INTO style_training_runs
                    (run_id,dataset_release_id,dataset_fingerprint,model_revision,scope,state)
                    VALUES(?,?,?,?,?,'created')""", (request["run_id"], request["dataset_release_id"],
                    request["dataset_fingerprint"], request["model_revision"], request["scope"]))
            elif (run["dataset_release_id"] != request["dataset_release_id"]
                  or run["dataset_fingerprint"] != request["dataset_fingerprint"]
                  or run["model_revision"] != request["model_revision"]
                  or run["scope"] != request["scope"]):
                raise ValueError("run identity has a different pinned request")
            attempt = conn.execute("""SELECT request_sha256,state FROM style_training_attempts
                WHERE run_id=? AND attempt_id=?""", (request["run_id"], request["attempt_id"])).fetchone()
            if attempt is not None:
                if attempt["request_sha256"] != request_sha256:
                    raise ValueError("same attempt ID has different request content")
                conn.rollback()
                return {"run_id": request["run_id"], "attempt_id": request["attempt_id"],
                        "request_sha256": request_sha256, "state": attempt["state"], "created": False}
            if run is not None and run["state"] == "completed":
                raise ValueError("completed run cannot start a new attempt")
            if conn.execute("""SELECT 1 FROM style_training_attempts
                WHERE run_id=? AND state='created'""", (request["run_id"],)).fetchone():
                raise ValueError("another attempt is still open")
            conn.execute("""INSERT INTO style_training_attempts
                (run_id,attempt_id,request_sha256,request_json,state) VALUES(?,?,?,?,'created')""",
                (request["run_id"], request["attempt_id"], request_sha256,
                 canonical(request).decode("utf-8")))
            conn.execute("UPDATE style_training_runs SET state='created' WHERE run_id=?", (request["run_id"],))
            conn.commit()
            return {"run_id": request["run_id"], "attempt_id": request["attempt_id"],
                    "request_sha256": request_sha256, "state": "created", "created": True}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def import_attempt_result(self, result: dict, result_sha256: str) -> dict:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            attempt = conn.execute("""SELECT * FROM style_training_attempts
                WHERE run_id=? AND attempt_id=?""", (result["run_id"], result["attempt_id"])).fetchone()
            if attempt is None:
                raise ValueError("requested attempt is missing")
            request = json.loads(attempt["request_json"])
            if validate_result(result, request) != result_sha256:
                raise ValueError("result hash or pinned request differs")
            if attempt["result_sha256"] is not None:
                if attempt["result_sha256"] != result_sha256:
                    raise ValueError("attempt already has a different result")
                conn.rollback()
                return {"run_id": result["run_id"], "attempt_id": result["attempt_id"],
                        "result_sha256": result_sha256, "state": attempt["state"], "created": False}
            artifact_id = None
            if result["status"] == "completed" and result["training_completed"] and result["reload_verified"]:
                prefix = "demo-model-" if request["scope"] == "demo" else "model-"
                artifact_id = prefix + sha(canonical({"request_sha256": attempt["request_sha256"],
                    "result_sha256": result_sha256, "artifact_sha256": result["artifact_sha256"]}))[:24]
                conn.execute("""INSERT INTO style_model_artifacts
                    (artifact_id,run_id,attempt_id,dataset_release_id,model_revision,scope,
                     artifact_path,artifact_sha256,result_sha256,writing_eligible)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""", (artifact_id, result["run_id"], result["attempt_id"],
                    request["dataset_release_id"], request["model_revision"], request["scope"],
                    result["artifact_path"], result["artifact_sha256"], result_sha256, 0))
            conn.execute("""UPDATE style_training_attempts SET state=?,result_sha256=?,result_json=?
                WHERE run_id=? AND attempt_id=?""", (result["status"], result_sha256,
                canonical(result).decode("utf-8"), result["run_id"], result["attempt_id"]))
            conn.execute("UPDATE style_training_runs SET state=? WHERE run_id=?",
                         (result["status"], result["run_id"]))
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("training result has broken references")
            conn.commit()
            return {"run_id": result["run_id"], "attempt_id": result["attempt_id"],
                    "result_sha256": result_sha256, "state": result["status"],
                    "model_artifact_id": artifact_id, "writing_eligible": False,
                    "created": True}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def read_run(self, run_id: str) -> dict:
        conn = self._connect(readonly=True)
        try:
            run = conn.execute("SELECT * FROM style_training_runs WHERE run_id=?", (run_id,)).fetchone()
            if run is None:
                raise ValueError("training run is not registered")
            attempts = [dict(row) for row in conn.execute("""SELECT attempt_id,request_sha256,state,
                result_sha256 FROM style_training_attempts WHERE run_id=? ORDER BY rowid""", (run_id,))]
            artifacts = [dict(row) for row in conn.execute("""SELECT artifact_id,attempt_id,
                artifact_sha256,scope,writing_eligible FROM style_model_artifacts
                WHERE run_id=? ORDER BY rowid""", (run_id,))]
            return {"run_id": run_id, "dataset_release_id": run["dataset_release_id"],
                    "dataset_fingerprint": run["dataset_fingerprint"], "scope": run["scope"],
                    "model_revision": run["model_revision"], "state": run["state"],
                    "attempts": attempts, "model_artifacts": artifacts}
        finally:
            conn.close()
