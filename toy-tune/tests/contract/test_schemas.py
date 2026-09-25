from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from toy_tune.adapters.outbound.files.storage import FilesystemArtifactStore, FilesystemRunStore
from toy_tune.adapters.outbound.files.sources import JsonSourceReader
from toy_tune.application.use_cases.prepare_dataset import prepare_dataset
from toy_tune.domain.knowledge import KnowledgeQuery, RetrievalPacket, Evidence

PROJECT = Path(__file__).resolve().parents[2]


class SchemaTests(unittest.TestCase):
    def validate(self, name, value):
        schema = json.loads((PROJECT / "schemas" / (name + ".schema.json")).read_bytes())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)

    def test_source_and_serialized_samples(self):
        path = PROJECT / "tests/fixtures/synthetic-source.json"
        self.validate("source-bundle", json.loads(path.read_bytes()))
        for sample in JsonSourceReader(path).read():
            self.validate("training-sample", sample.to_dict())

    def test_dataset_and_run_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "workspace"
            value = prepare_dataset(JsonSourceReader(PROJECT / "tests/fixtures/synthetic-source.json"),
                                    FilesystemArtifactStore(root), (1, 1, 1))
            self.validate("dataset-manifest", value)
            self.validate("run-manifest", FilesystemRunStore(root).create("run-test", {}))

    def test_packet_serialization(self):
        packet = RetrievalPacket("packet-test", KnowledgeQuery("work", "r1", "original-1", "1450", "pov"),
                                 (Evidence("fact-1", "합성 근거", "active", "source"),))
        self.validate("retrieval-packet", json.loads(json.dumps(asdict(packet))))
