import copy
import json
from pathlib import Path
import tempfile
import unittest

from toy_tune.adapters.outbound.files.sources import JsonSourceReader
from toy_tune.application.services.dataset_builder import build_dataset
from toy_tune.domain.errors import ValidationError
from toy_tune.domain.samples import Sample
from toy_tune.domain.experiments import Capabilities, ModelRef, validate_transition

FIXTURE = Path(__file__).parents[1] / "fixtures/synthetic-source.json"


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.reader = JsonSourceReader(FIXTURE)
        self.samples = self.reader.read()

    def build(self, samples=None, allow=False):
        return build_dataset(samples or self.samples, (1, 1, 1), allow, self.reader.snapshot())

    def changed(self, index, **fields):
        samples = list(self.samples)
        samples[index] = Sample(**(samples[index].to_dict() | fields))
        return tuple(samples)

    def test_deterministic_identity_and_source_retained(self):
        first = self.build()
        self.assertEqual(first, self.build())
        self.assertEqual(first[1]["source-bundle.json"], FIXTURE.read_bytes())
        self.assertEqual(first[2]["token_validation"], "pending")

    def test_changed_prompt_changes_dataset_identity(self):
        self.assertNotEqual(self.build()[0], self.build(self.changed(0, prompt="다른 장면 조건"))[0])

    def test_scene_cross_split_rejected(self):
        with self.assertRaises(ValidationError):
            self.build(self.changed(1, scene_id=self.samples[0].scene_id))

    def test_duplicate_target_rejected(self):
        with self.assertRaises(ValidationError):
            self.build(self.changed(1, answer=self.samples[0].answer))

    def test_target_in_own_prompt_rejected(self):
        with self.assertRaises(ValidationError):
            self.build(self.changed(0, prompt="내용: " + self.samples[0].answer))

    def test_context_overlap_requires_explicit_policy(self):
        samples = self.changed(1, prompt="이어서 쓴다: " + self.samples[0].answer)
        with self.assertRaises(ValidationError):
            self.build(samples)
        self.assertEqual(self.build(samples, allow=True)[2]["warnings"][0]["code"], "cross_split_context")

    def test_invalid_counts_and_multiple_works(self):
        with self.assertRaises(ValidationError):
            build_dataset(self.samples, (True, 1, 1), False, b"")
        with self.assertRaises(ValidationError):
            self.build(self.changed(1, work_id="another-work"))

    def test_source_hash_and_answer_range_are_verified(self):
        original = json.loads(FIXTURE.read_bytes())
        for patch in ({"source_sha256": "0" * 64}, {"answer_start": 1}, {"packet_id": "missing-packet"}):
            with self.subTest(patch=patch), tempfile.TemporaryDirectory() as directory:
                value = copy.deepcopy(original)
                value["samples"][0].update(patch)
                path = Path(directory) / "source.json"
                path.write_text(json.dumps(value))
                with self.assertRaises(ValidationError):
                    JsonSourceReader(path).read()

    def test_state_and_capability_do_not_silently_fallback(self):
        with self.assertRaises(ValidationError):
            validate_transition("created", "completed")
        with self.assertRaises(Exception) as caught:
            Capabilities("test", frozenset({"generate"}), frozenset({"gguf"}), frozenset({"q4"})).require(
                "train", ModelRef("test", "abc", "gguf"), "q4")
        self.assertEqual(type(caught.exception).__name__, "UnsupportedError")
