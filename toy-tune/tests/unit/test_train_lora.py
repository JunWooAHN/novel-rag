import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout

from toy_tune.adapters.outbound.hf_peft import _select_train_rows, _text_targets, verify_reload
from toy_tune.application.use_cases.train_lora import canonical, validate_offline_attempt
from toy_tune.bootstrap import _write_result_once
from toy_tune.bootstrap import main as cli_main
from toy_tune.domain.errors import ValidationError


def fixture():
    packet_hash = "a" * 64
    manifest = {"artifact_id": "prepared-1", "files": {"frozen-packet.json": packet_hash},
                "metadata": {"source_dataset_release_id": "ds-reviewed-1",
                             "source_dataset_fingerprint": "b" * 64,
                             "role": "gemma_style", "token_validation": "pending_real_tokenizer"}}
    manifest_raw = canonical(manifest)
    request = {"schema_version": 1, "run_id": "run-1", "attempt_id": "attempt-1",
               "dataset_release_id": "ds-reviewed-1", "dataset_fingerprint": "b" * 64,
               "packet_sha256": packet_hash, "prepared_dataset_id": "prepared-1",
               "prepared_manifest_path": "/original-host/manifest.json",
               "prepared_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
               "model_revision": "google/gemma-4-E2B-it@3e22461f65e89153144f8adb70e3b8c2cc9845a7",
               "scope": "real", "selected_sample_ids": ["train-short-1", "train-short-2"]}
    return request, manifest, manifest_raw


class OfflineAttemptTests(unittest.TestCase):
    def test_verify_lora_cli_returns_reload_state_not_dataset_manifest(self):
        request, _, _ = fixture()
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder).resolve()
            output = workspace / "attempt"
            output.mkdir()
            (output / "run-request.json").write_bytes(canonical(request))
            proof = {"artifact_path": str(output / "adapter.tar"),
                     "artifact_sha256": "c" * 64, "generated_token_count": 2}
            stdout = io.StringIO()
            with (patch("toy_tune.bootstrap.load_runtime", return_value=SimpleNamespace(
                    workspace_root=str(workspace), engine="hf-peft")),
                  patch("toy_tune.bootstrap.workspace_path", return_value=workspace),
                  patch("toy_tune.bootstrap.FilesystemArtifactStore"),
                  patch("toy_tune.adapters.outbound.hf_peft.verify_reload", return_value=proof),
                  redirect_stdout(stdout)):
                code = cli_main(["verify-lora", "--runtime", "unused.toml", "--workspace",
                                 str(workspace), "--output-dir", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["state"],
                             "reload_verified_pending_product_review")
            self.assertEqual(json.loads((output / "result.json").read_bytes())["attempt_id"],
                             request["attempt_id"])

    def test_explicit_train_ids_keep_request_order_and_reject_missing_or_duplicate(self):
        rows = [{"sample_id": "train-b"}, {"sample_id": "train-a"}]
        self.assertEqual([row["sample_id"] for row in _select_train_rows(
            rows, ("train-a", "train-b"))], ["train-a", "train-b"])
        with self.assertRaisesRegex(ValidationError, "absent"):
            _select_train_rows(rows, ("holdout-id",))
        with self.assertRaisesRegex(ValidationError, "distinct"):
            _select_train_rows(rows, ("train-a", "train-a"))

    def test_gemma4_clippable_text_targets_exclude_vision(self):
        class Linear:
            pass

        class Model:
            def named_modules(self):
                return iter((
                    ("model.language_model.layers.0.self_attn.q_proj", Linear()),
                    ("model.language_model.layers.0.self_attn.v_proj", Linear()),
                    ("model.language_model.layers.1.self_attn.q_proj", object()),
                    ("model.language_model.layers.1.self_attn.q_proj.linear", Linear()),
                    ("model.language_model.layers.1.self_attn.v_proj.linear", Linear()),
                    ("model.vision_tower.layers.0.self_attn.q_proj.linear", Linear()),
                ))

        torch = SimpleNamespace(nn=SimpleNamespace(Linear=Linear))
        self.assertEqual(_text_targets(Model(), torch), [
            "model.language_model.layers.0.self_attn.q_proj",
            "model.language_model.layers.0.self_attn.v_proj",
            "model.language_model.layers.1.self_attn.q_proj.linear",
            "model.language_model.layers.1.self_attn.v_proj.linear",
        ])

    def test_remote_path_may_change_but_manifest_and_model_are_pinned(self):
        request, manifest, manifest_raw = fixture()
        parsed, original, digest = validate_offline_attempt(
            canonical(request), manifest_raw, manifest, "prepared-1", 2,
            request["model_revision"], request["selected_sample_ids"])
        self.assertEqual(parsed.model.revision, "3e22461f65e89153144f8adb70e3b8c2cc9845a7")
        self.assertEqual(parsed.dataset_id, "prepared-1")
        self.assertEqual(original, request)
        self.assertEqual(digest, hashlib.sha256(canonical(request)).hexdigest())

    def test_changed_packet_manifest_or_model_is_rejected(self):
        request, manifest, manifest_raw = fixture()
        for changed_request, changed_manifest in (
            ({**request, "packet_sha256": "0" * 64}, manifest),
            (request, {**manifest, "artifact_id": "other"}),
            ({**request, "model_revision": "google/gemma-4-E2B-it@main"}, manifest),
            ({**request, "scope": "demo"}, manifest),
        ):
            with self.subTest(value=changed_request["model_revision"]), self.assertRaises(ValidationError):
                validate_offline_attempt(canonical(changed_request), manifest_raw,
                                         changed_manifest, "prepared-1", 2,
                                         request["model_revision"], request["selected_sample_ids"])
        with self.assertRaises(ValidationError):
            validate_offline_attempt(canonical(request), manifest_raw, manifest,
                                     "prepared-1", 2, request["model_revision"], ["other"])

    def test_reload_rejects_another_attempt_before_loading_cuda(self):
        request, _, _ = fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "adapter").mkdir()
            (root / "run-request.json").write_bytes(canonical(request))
            report = {"run_id": request["run_id"], "attempt_id": "another-attempt",
                      "request_sha256": hashlib.sha256(canonical(request)).hexdigest(),
                      "selected_sample_ids": request["selected_sample_ids"],
                      "dataset_id": request["prepared_dataset_id"],
                      "model_repository": "google/gemma-4-E2B-it",
                      "model_revision": request["model_revision"].split("@", 1)[1]}
            (root / "train-report.json").write_bytes(canonical(report))
            with self.assertRaisesRegex(ValidationError, "pinned request differ"):
                verify_reload(root)

    def test_reload_proof_can_recreate_same_result_after_crash(self):
        request, _, _ = fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "adapter").mkdir()
            archive = root / "adapter.tar"
            archive.write_bytes(b"fixed-adapter-archive")
            (root / "run-request.json").write_bytes(canonical(request))
            report = {"run_id": request["run_id"], "attempt_id": request["attempt_id"],
                      "request_sha256": hashlib.sha256(canonical(request)).hexdigest(),
                      "selected_sample_ids": request["selected_sample_ids"],
                      "dataset_id": request["prepared_dataset_id"],
                      "model_repository": "google/gemma-4-E2B-it",
                      "model_revision": request["model_revision"].split("@", 1)[1]}
            (root / "train-report.json").write_bytes(canonical(report))
            proof = {"schema_version": 1, "run_id": request["run_id"],
                     "attempt_id": request["attempt_id"],
                     "request_sha256": report["request_sha256"],
                     "model_revision": report["model_revision"], "reload_verified": True,
                     "generated_token_count": 2,
                     "artifact_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
            (root / "reload-report.json").write_bytes(canonical(proof))
            resumed = verify_reload(root)
            self.assertEqual(resumed["artifact_sha256"], proof["artifact_sha256"])
            self.assertTrue(resumed["training_completed"])
            with patch("toy_tune.adapters.outbound.files.atomic.os.link", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    _write_result_once(root / "result.json", resumed)
            self.assertFalse((root / "result.json").exists())
            self.assertEqual(list(root.glob(".result-*")), [])
            _write_result_once(root / "result.json", resumed)
            _write_result_once(root / "result.json", resumed)
            changed_report = {**report, "selected_sample_ids": ["another-train-id"]}
            (root / "train-report.json").write_bytes(canonical(changed_report))
            with self.assertRaisesRegex(ValidationError, "pinned request differ"):
                verify_reload(root)
            (root / "train-report.json").write_bytes(canonical(report))
            with self.assertRaisesRegex(ValidationError, "Existing result differs"):
                _write_result_once(root / "result.json", {**resumed, "attempt_id": "other"})
            archive.write_bytes(b"changed")
            with self.assertRaisesRegex(ValidationError, "Existing reload proof differs"):
                verify_reload(root)
