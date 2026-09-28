import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from toy_tune.application.services.frozen_packet import (
    build_frozen_packet, validate_supervised_labels, verify_frozen_derivation)
from toy_tune.application.use_cases.prepare_dataset import prepare_reviewed_packet
from toy_tune.adapters.outbound.files.storage import FilesystemArtifactStore
from toy_tune.domain.errors import ValidationError


def fixture():
    samples = []
    for i, split in enumerate(("train", "development_validation", "development_holdout")):
        answer = f"reviewed source answer {i}"
        digest = hashlib.sha256(answer.encode()).hexdigest()
        samples.append({"sample_id": f"sample-{i}", "work_id": "test-work", "split": split,
                        "prompt": f"write a distinct scene {i}", "answer": answer,
                        "source_pin": {"source_revision_id": 1, "source_sha256": "a" * 64,
                                       "segmentation_id": 2, "answer_start_cp": i * 50,
                                       "answer_end_cp": i * 50 + len(answer), "answer_sha256": digest},
                        "review_sha256": "b" * 64, "learning_hypothesis_sha256": "c" * 64,
                        "line_sha256": "d" * 64})
    return {"schema_version": 1, "packet_kind": "novel_factory_style_dataset",
            "dataset_release_id": "ds-style-fixture", "dataset_fingerprint": "e" * 64,
            "parent_import_id": "reviewed-parent", "role": "gemma_style",
            "split_semantics": "development_holdout_is_not_unseen_final_test",
            "counts": {split: 1 for split in ("train", "development_validation", "development_holdout")},
            "hypothesis_status": "reviewed_learning_input_not_author_intent_or_story_canon",
            "token_validation": "pending_real_tokenizer",
            "loss_mask_validation": "pending_real_tokenizer", "samples": samples}


def raw(packet):
    return (json.dumps(packet, ensure_ascii=False, sort_keys=True) + "\n").encode()


class FrozenPacketTests(unittest.TestCase):
    def test_explicit_reviewed_splits_survive_prepare_and_verify(self):
        packet = fixture()
        with tempfile.TemporaryDirectory() as directory:
            store = FilesystemArtifactStore(Path(directory) / "artifacts")
            manifest = prepare_reviewed_packet(raw(packet), store)
            self.assertEqual(store.verify(manifest["artifact_id"]), manifest)
            self.assertEqual(manifest["metadata"]["counts"], packet["counts"])
            self.assertEqual(manifest["metadata"]["token_validation"], "pending_real_tokenizer")
            self.assertEqual(manifest["metadata"]["loss_mask_validation"], "pending_real_tokenizer")
            self.assertEqual(manifest["metadata"]["split_policy"], "frozen_reviewed_assignment_no_repartition")
            self.assertEqual(prepare_reviewed_packet(raw(packet), store), manifest)

    def test_planning_role_changed_split_and_target_leak_fail_closed(self):
        def duplicate_cross_split_target(packet):
            answer = packet["samples"][0]["answer"]
            packet["samples"][1]["answer"] = answer
            packet["samples"][1]["source_pin"]["answer_sha256"] = hashlib.sha256(answer.encode()).hexdigest()

        for mutate in (
            lambda p: p.update(role="sota_planning"),
            lambda p: p["samples"][0].update(split="development_holdout"),
            lambda p: p["samples"][0].update(prompt=p["samples"][0]["answer"]),
            lambda p: p["samples"][0]["source_pin"].update(answer_sha256="0" * 64),
            duplicate_cross_split_target,
        ):
            packet = fixture()
            mutate(packet)
            with self.subTest(mutate=mutate), self.assertRaises(ValidationError):
                build_frozen_packet(raw(packet))

    def test_cpu_label_contract_is_not_real_tokenizer_validation(self):
        validate_supervised_labels([11, 12, 21, 22], [-100, -100, 21, 22], 2)
        for labels in ([11, -100, 21, 22], [-100, -100, -100, 22], [-100, -100, 21]):
            with self.subTest(labels=labels), self.assertRaises(ValidationError):
                validate_supervised_labels([11, 12, 21, 22], labels, 2)

    def test_rehashed_train_file_cannot_diverge_from_frozen_packet(self):
        packet_raw = raw(fixture())
        artifact_id, files, metadata = build_frozen_packet(packet_raw)
        manifest = {"artifact_id": artifact_id, "metadata": metadata,
                    "files": {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}}
        verify_frozen_derivation(packet_raw, manifest)
        changed = dict(manifest)
        changed["files"] = {**manifest["files"],
                            "train.jsonl": hashlib.sha256(b"different train output\n").hexdigest()}
        with self.assertRaisesRegex(ValidationError, "not derived"):
            verify_frozen_derivation(packet_raw, changed)
