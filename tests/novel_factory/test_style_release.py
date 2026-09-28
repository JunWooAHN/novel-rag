import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from novel_factory.style.dataset_release import canonical, frozen_style_packet, release_dataset, sha
from novel_factory.style.dataset_sqlite import SCHEMA as DATASET_SCHEMA
from novel_factory.style.training_contract import request_attempt
from novel_factory.style.training_sqlite import SQLiteTrainingStore


def reviewed_row(role, split, order):
    ident = f"{role}-{order}"
    source = f"source answer {ident}"
    target = source if role == "gemma_style" else f"reviewed plan {ident}"
    meta = {"role": role, "split": split, "work_id": "sample-work",
            "source_sha256": "a" * 64, "segmentation_id": 2,
            "answer_start_cp": order * 100, "answer_end_cp": order * 100 + len(source),
            "answer_sha256": sha(source.encode()), "target_basis":
            "observed_exact_source_slice" if role == "gemma_style"
            else "reviewed_reconstruction_not_author_intent"}
    record = {"sample_id": ident, "metadata": meta,
              "messages": [{"role": "user", "content": f"distinct scene prompt {ident}"},
                           {"role": "assistant", "content": target}]}
    line = json.dumps(record, sort_keys=True) + "\n"
    return {"release": "initial", "record": record, "raw_line": line,
            "source_answer": source, "candidate_id": ident, "selection_id": f"selection-{order}",
            "source_revision_id": 1, "source_sha256": "a" * 64, "segmentation_id": 2,
            "answer_start_cp": meta["answer_start_cp"], "answer_end_cp": meta["answer_end_cp"],
            "review_sha256": "b" * 64, "line_sha256": sha(line.encode()),
            "candidate": {"writer_input" if role == "gemma_style" else "planner_input":
                          {"goal": f"hypothesis {ident}"}}}


class MemoryReleaseStore:
    def __init__(self):
        splits = ("train", "development_validation", "development_holdout")
        self.parent = {"import_id": "parent-review", "fingerprint": "f" * 64,
                       "rows": [reviewed_row(role, split, i + (0 if role == "gemma_style" else 3))
                                for role in ("gemma_style", "sota_planning")
                                for i, split in enumerate(splits)]}
        self.releases = {}

    def read_reviewed_parent(self, import_id):
        assert import_id == self.parent["import_id"]
        return self.parent

    def publish_dataset(self, release):
        old = self.releases.get(release["release_id"])
        if old and old["fingerprint"] != release["fingerprint"]:
            raise ValueError("changed release")
        self.releases[release["release_id"]] = release
        return {**release, "created": old is None}

    def read_dataset(self, release_id):
        return self.releases[release_id]


class DatasetReleaseTests(unittest.TestCase):
    def test_reviewed_role_and_split_are_frozen_without_promoting_planning(self):
        store = MemoryReleaseStore()
        style = release_dataset(store, "parent-review", "gemma_style")
        planning = release_dataset(store, "parent-review", "sota_planning")
        self.assertEqual(style["counts"], {s: 1 for s in
            ("train", "development_validation", "development_holdout")})
        self.assertEqual(planning["purpose"], "planning_research_only")
        self.assertFalse(release_dataset(store, "parent-review", "gemma_style")["created"])
        packet = frozen_style_packet(store, style["release_id"])
        self.assertEqual(len(packet["samples"]), 3)
        self.assertEqual(packet["hypothesis_status"],
                         "reviewed_learning_input_not_author_intent_or_story_canon")
        with self.assertRaisesRegex(ValueError, "planning research"):
            frozen_style_packet(store, planning["release_id"])
        store.parent["rows"][0]["source_answer"] = "different text"
        with self.assertRaisesRegex(ValueError, "source pin or answer hash"):
            frozen_style_packet(store, style["release_id"])

    def test_complete_target_in_prompt_is_rejected(self):
        store = MemoryReleaseStore()
        row = store.parent["rows"][0]
        row["record"]["messages"][0]["content"] = "prompt includes " + row["source_answer"]
        with self.assertRaisesRegex(ValueError, "complete target"):
            release_dataset(store, "parent-review", "gemma_style")


class TrainingAttemptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "style.sqlite3"
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE legacy_imports(import_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO legacy_imports VALUES('parent-review')")
        conn.executescript(DATASET_SCHEMA)
        conn.execute("""INSERT INTO style_dataset_releases
            (release_id,parent_import_id,parent_fingerprint,role,purpose,split_semantics,fingerprint,counts_json)
            VALUES(?,?,?,?,?,?,?,?)""", ("ds-fixture", "parent-review", "f" * 64,
            "gemma_style", "style_training_candidate", "development_holdout_is_not_unseen_final_test",
            "a" * 64, '{"train":1,"development_validation":1,"development_holdout":1}'))
        for ordinal, candidate_id, split in ((1, "train-short-1", "train"),
                                              (2, "holdout-1", "development_holdout")):
            conn.execute("""INSERT INTO style_dataset_items
                (release_id,ordinal,candidate_id,selection_id,work_id,role,split,
                 source_revision_id,source_sha256,segmentation_id,answer_start_cp,answer_end_cp,
                 answer_sha256,prompt_sha256,target_sha256,review_sha256,
                 learning_hypothesis_sha256,line_sha256)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("ds-fixture", ordinal, candidate_id, "selection", "work", "gemma_style", split,
                 1, "0" * 64, 1, 0, 1, "0" * 64, "0" * 64, "0" * 64,
                 "0" * 64, "0" * 64, "0" * 64))
        conn.commit();conn.close()
        self.store = SQLiteTrainingStore(self.db)
        self.packet = {"fixture": "DB-reviewed packet"}
        self.packet_sha = sha(canonical(self.packet))
        resolver = patch("novel_factory.style.training_sqlite.frozen_style_packet",
                         return_value=self.packet)
        resolver.start()
        self.addCleanup(resolver.stop)
        bundle = self.root / "prepared-fixture"
        bundle.mkdir()
        (bundle / "frozen-packet.json").write_bytes(canonical(self.packet))
        manifest = {"artifact_id": "prepared-fixture", "metadata": {
            "source_dataset_release_id": "ds-fixture", "source_dataset_fingerprint": "a" * 64},
            "files": {"frozen-packet.json": self.packet_sha}}
        self.manifest = bundle / "manifest.json"
        self.manifest.write_text(json.dumps(manifest))
        self.request = {"schema_version": 1, "run_id": "demo:run", "attempt_id": "attempt-1",
                        "dataset_release_id": "ds-fixture", "dataset_fingerprint": "a" * 64,
                        "packet_sha256": self.packet_sha, "prepared_dataset_id": "prepared-fixture",
                        "prepared_manifest_path": str(self.manifest),
                        "prepared_manifest_sha256": sha(self.manifest.read_bytes()),
                        "model_revision": "synthetic-only", "scope": "demo"}
        self.artifact = self.root / "fake-model.bin"
        self.artifact.write_bytes(b"CPU fixture; not real weights\n")

    def result(self):
        return {"schema_version": 1, "run_id": "demo:run", "attempt_id": "attempt-1",
                "request_sha256": sha(canonical(self.request)), "status": "completed",
                "artifact_path": str(self.artifact), "artifact_sha256": sha(self.artifact.read_bytes()),
                "validation_scope": "synthetic_contract", "training_completed": True,
                "reload_verified": True, "token_validation": "synthetic_contract_only",
                "loss_mask_validation": "synthetic_contract_only"}

    def test_idempotent_result_and_demo_model_cannot_be_adopted(self):
        self.assertTrue(request_attempt(self.store, self.request)["created"])
        self.assertFalse(request_attempt(self.store, self.request)["created"])
        result = self.result()
        first = self.store.import_attempt_result(result, sha(canonical(result)))
        self.assertTrue(first["created"])
        self.assertFalse(first["writing_eligible"])
        self.assertTrue(first["model_artifact_id"].startswith("demo-model-"))
        self.assertFalse(self.store.import_attempt_result(result, sha(canonical(result)))["created"])
        self.assertEqual(self.store.read_run("demo:run")["model_artifacts"][0]["writing_eligible"], 0)
        changed = {**result, "token_validation": "changed"}
        with self.assertRaisesRegex(ValueError, "different result"):
            self.store.import_attempt_result(changed, sha(canonical(changed)))

    def test_failed_attempt_retry_and_real_scope_rejects_synthetic_validation(self):
        request_attempt(self.store, self.request)
        failed = {**self.result(), "status": "failed", "artifact_path": None,
                  "artifact_sha256": None, "training_completed": False, "reload_verified": False}
        failed_record = self.store.import_attempt_result(failed, sha(canonical(failed)))
        self.assertFalse(failed_record["writing_eligible"])
        self.assertIsNone(failed_record["model_artifact_id"])
        retry = {**self.request, "attempt_id": "attempt-2"}
        self.assertTrue(request_attempt(self.store, retry)["created"])
        self.assertEqual(self.store.read_run("demo:run")["state"], "created")
        real = {**self.request, "run_id": "real-run", "scope": "real",
                "selected_sample_ids": ["train-short-1"]}
        request_attempt(self.store, real)
        with self.assertRaisesRegex(ValueError, "distinct, explicitly selected"):
            request_attempt(self.store, {**real, "attempt_id": "attempt-bad",
                                         "selected_sample_ids": ["train-short-1", "train-short-1"]})
        with self.assertRaisesRegex(ValueError, "pinned train split"):
            request_attempt(self.store, {**real, "attempt_id": "attempt-holdout",
                                         "selected_sample_ids": ["holdout-1"]})
        bad = {**self.result(), "run_id": "real-run", "request_sha256": sha(canonical(real)),
               "validation_scope": "real_tokenizer_and_reload",
               "token_validation": "passed_real_tokenizer",
               "loss_mask_validation": "passed_real_tokenizer"}
        with self.assertRaisesRegex(ValueError, "lacks verified training and reload evidence"):
            self.store.import_attempt_result(bad, sha(canonical(bad)))
        self.assertEqual(self.store.read_run("real-run")["model_artifacts"], [])
        real_failed = {**bad, "status": "failed", "artifact_path": None,
                       "artifact_sha256": None, "training_completed": False,
                       "reload_verified": False}
        real_failure = self.store.import_attempt_result(real_failed, sha(canonical(real_failed)))
        self.assertFalse(real_failure["writing_eligible"])
        self.assertIsNone(real_failure["model_artifact_id"])

    def test_manifest_hash_and_artifact_hash_must_match(self):
        bad = {**self.request, "prepared_manifest_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "manifest hash differs"):
            request_attempt(self.store, bad)
        request_attempt(self.store, self.request)
        result = {**self.result(), "artifact_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "artifact hash differs"):
            self.store.import_attempt_result(result, sha(canonical(result)))

    def test_real_candidate_requires_matching_train_and_reload_sidecars(self):
        real = {**self.request, "run_id": "real-reviewed", "scope": "real",
                "selected_sample_ids": ["train-short-1"],
                "model_revision": "provider/model@" + "1" * 40}
        request_attempt(self.store, real)
        directory = self.root / "real-attempt"
        directory.mkdir()
        archive = directory / "adapter.tar"
        archive.write_bytes(b"synthetic sidecar fixture; not real model weights")
        result = {**self.result(), "run_id": real["run_id"],
                  "request_sha256": sha(canonical(real)),
                  "artifact_path": str(archive), "artifact_sha256": sha(archive.read_bytes()),
                  "validation_scope": "real_tokenizer_and_reload",
                  "token_validation": "passed_real_tokenizer",
                  "loss_mask_validation": "passed_real_tokenizer"}
        train = {"run_id": real["run_id"], "attempt_id": real["attempt_id"],
                 "request_sha256": result["request_sha256"], "dataset_id": real["prepared_dataset_id"],
                 "model_repository": "provider/model", "model_revision": "1" * 40,
                 "selected_sample_ids": real["selected_sample_ids"],
                 "token_validation": "passed_real_tokenizer",
                 "loss_mask_validation": "passed_real_tokenizer", "changed_lora_elements": 1,
                 "trainable_parameters": 1, "max_steps": 1, "losses": [0.5],
                 "target_modules": ["model.language_model.layers.0.self_attn.q_proj"]}
        reload = {"run_id": real["run_id"], "attempt_id": real["attempt_id"],
                  "request_sha256": result["request_sha256"], "model_revision": "1" * 40,
                  "reload_verified": True, "generated_token_count": 1,
                  "artifact_sha256": result["artifact_sha256"]}
        for name, value in (("run-request.json", real), ("train-report.json", train),
                            ("reload-report.json", reload),
                            ("result.json", {**result, "artifact_path": "/remote/adapter.tar"})):
            (directory / name).write_bytes(canonical(value))
        (directory / "train-report.json").write_bytes(canonical({
            **train, "selected_sample_ids": ["holdout-1"]}))
        with self.assertRaisesRegex(ValueError, "sidecars differ"):
            self.store.import_attempt_result(result, sha(canonical(result)))
        (directory / "train-report.json").write_bytes(canonical(train))
        imported = self.store.import_attempt_result(result, sha(canonical(result)))
        self.assertEqual(imported["state"], "completed")
        self.assertFalse(imported["writing_eligible"])
        self.assertTrue(imported["model_artifact_id"].startswith("model-"))

    def test_request_rejects_packet_not_matching_db_release(self):
        other = b'{"fixture":"different packet"}\n'
        packet_file = self.manifest.parent / "frozen-packet.json"
        packet_file.write_bytes(other)
        manifest = json.loads(self.manifest.read_bytes())
        manifest["files"]["frozen-packet.json"] = sha(other)
        self.manifest.write_text(json.dumps(manifest))
        request = {**self.request, "packet_sha256": sha(other),
                   "prepared_manifest_sha256": sha(self.manifest.read_bytes())}
        with self.assertRaisesRegex(ValueError, "packet differs from the DB release"):
            request_attempt(self.store, request)

    def test_request_rejects_modified_prepared_payload(self):
        (self.manifest.parent / "frozen-packet.json").write_bytes(b"changed after prepare")
        with self.assertRaisesRegex(ValueError, "payload hash differs"):
            request_attempt(self.store, self.request)
