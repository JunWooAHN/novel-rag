import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]


class CliTests(unittest.TestCase):
    def command(self, *args, expected=0, cwd=None):
        result = subprocess.run([sys.executable, "-m", "toy_tune", *args],
                                text=True, capture_output=True, cwd=cwd, env=os.environ.copy())
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def test_prepare_and_verify_from_other_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ["--runtime", str(PROJECT / "configs/runtimes/local-cpu.toml"),
                    "--workspace", str(Path(directory) / "data")]
            result = self.command("prepare", *args, "--source",
                                  str(PROJECT / "tests/fixtures/synthetic-source.json"),
                                  "--split", str(PROJECT / "configs/datasets/synthetic.toml"), cwd=directory)
            manifest = json.loads(result.stdout)
            self.assertTrue(manifest["verified"])
            self.assertEqual(manifest["token_validation"], "pending")
            self.command("verify-dataset", *args, "--dataset-id", manifest["artifact_id"], cwd=directory)

    def test_doctor_does_not_claim_training_ready(self):
        result = self.command("doctor", "--runtime", str(PROJECT / "configs/runtimes/mac-mlx.toml"))
        self.assertFalse(json.loads(result.stdout)["training_ready"])

    def test_errors_do_not_expose_prose(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.json"
            source.write_text('{"SECRET_PROSE": "PRIVATE_CONTENT"}')
            result = self.command("prepare", "--runtime", str(PROJECT / "configs/runtimes/local-cpu.toml"),
                                  "--workspace", str(Path(directory) / "data"),
                                  "--source", str(source), "--split",
                                  str(PROJECT / "configs/datasets/synthetic.toml"), expected=2)
            self.assertNotIn("PRIVATE_CONTENT", result.stderr)
            self.assertNotIn("SECRET_PROSE", result.stderr)

    def test_unknown_profile_fields_and_live_db_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "runtime.toml"
            base = '[runtime]\nname="test"\nexecution="local"\nengine="none"\n'
            for extra in ('knowledge="snapshot"\npassword="secret-value"\n', 'knowledge="postgres"\n'):
                profile.write_text(base + extra)
                result = self.command("doctor", "--runtime", str(profile), expected=2)
                self.assertNotIn("secret-value", result.stderr)
