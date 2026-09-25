import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("publication", PROJECT / "ops/ssh/package_source.py")
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


class PublicationTests(unittest.TestCase):
    def test_published_source_runs_without_checkout_or_installed_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            archive = publication.package(PROJECT, root / "releases")
            with tarfile.open(archive) as bundle:
                for member in bundle.getmembers():
                    path = root / "unpacked" / member.name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bundle.extractfile(member).read())
            project = root / "unpacked" / archive.stem
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(project / "src")
            result = subprocess.run(
                [sys.executable, "-S", "-m", "toy_tune", "prepare", "--runtime",
                 str(project / "configs/runtimes/local-cpu.toml"), "--workspace", str(root / "workspace"),
                 "--source", str(project / "tests/fixtures/synthetic-source.json"),
                 "--split", str(project / "configs/datasets/synthetic.toml")],
                cwd=root, env=environment, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["verified"])

    def test_archive_is_self_contained_and_checksummed(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = publication.package(PROJECT, Path(directory).resolve() / "releases")
            with tarfile.open(archive) as bundle:
                manifest_file = next(name for name in bundle.getnames() if name.endswith("/source-manifest.json"))
                manifest = json.load(bundle.extractfile(manifest_file))
                for name, checksum in manifest["files"].items():
                    data = bundle.extractfile(manifest["source_id"] + "/" + name).read()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), checksum)
                self.assertIn("pyproject.toml", manifest["files"])
            with self.assertRaises(FileExistsError):
                publication.package(PROJECT, archive.parent)

    def test_all_implementation_and_contract_files_are_declared(self):
        listed = set(publication.collect(PROJECT))
        for root, pattern in (("src", "*.py"), ("schemas", "*.json"), ("configs", "*.toml"), ("tests", "*.py")):
            for path in (PROJECT / root).rglob(pattern):
                if ".local." not in path.name:
                    self.assertIn(path.relative_to(PROJECT).as_posix(), listed)
