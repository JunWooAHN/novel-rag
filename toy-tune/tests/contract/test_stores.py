from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from toy_tune.adapters.outbound.files.storage import FilesystemArtifactStore, FilesystemRunStore, workspace_path
from toy_tune.domain.errors import ConflictError, IntegrityError, ValidationError


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve() / "workspace"
        self.store = FilesystemArtifactStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_round_trip_and_idempotent_publish(self):
        value = self.store.publish("ds-1", {"train.jsonl": b"data"}, {"version": 1})
        self.assertEqual(value, self.store.verify("ds-1"))
        self.assertEqual(value, self.store.publish("ds-1", {"train.jsonl": b"data"}, {"version": 1}))
        with self.assertRaises(ConflictError):
            self.store.publish("ds-1", {"train.jsonl": b"other"}, {"version": 1})
        self.assertEqual((self.root / "datasets/ds-1/train.jsonl").read_bytes(), b"data")

    def test_tampered_and_partial_payload_rejected(self):
        self.store.publish("ds-1", {"train.jsonl": b"data"}, {})
        path = self.root / "datasets/ds-1/train.jsonl"
        path.write_bytes(b"corrupted")
        with self.assertRaises(IntegrityError):
            self.store.verify("ds-1")
        path.unlink()
        with self.assertRaises(IntegrityError):
            self.store.verify("ds-1")

    def test_incomplete_manifest_and_extra_files_rejected(self):
        target = self.root / "datasets/ds-1"
        target.mkdir(parents=True)
        with self.assertRaises(IntegrityError):
            self.store.verify("ds-1")
        with self.assertRaises(IntegrityError):
            self.store.publish("ds-1", {"x": b"x"}, {})
        self.store.publish("ds-2", {"x": b"x"}, {})
        (self.root / "datasets/ds-2/unlisted").write_text("x")
        with self.assertRaises(IntegrityError):
            self.store.verify("ds-2")

    def test_path_traversal_and_symlinks_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.publish("../escape", {"x": b"x"}, {})
        with self.assertRaises(ValidationError):
            self.store.publish("ds-1", {"../escape": b"x"}, {})
        self.root.mkdir()
        (self.root / "datasets").symlink_to(Path(self.temp.name), target_is_directory=True)
        with self.assertRaises(ValidationError):
            self.store.publish("ds-1", {"x": b"x"}, {})

    def test_stale_lock_is_not_automatically_deleted(self):
        directory = self.root / "datasets"
        directory.mkdir(parents=True)
        (directory / "ds-1.lock").write_text("old lock")
        with self.assertRaises(ConflictError):
            self.store.publish("ds-1", {"x": b"x"}, {})
        self.assertTrue((directory / "ds-1.lock").exists())

    def test_concurrent_different_writers_never_overwrite(self):
        self.store._root(create=True)
        def write(value):
            try:
                self.store.publish("ds-race", {"x": value}, {})
                return True
            except ConflictError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(write, [b"first", b"second"]))
        self.assertEqual(sum(outcomes), 1)
        self.store.verify("ds-race")

    def test_run_state_compare_and_swap(self):
        runs = FilesystemRunStore(self.root)
        runs.create("run-1", {"dataset": "ds-1"})
        with self.assertRaises(ConflictError):
            runs.create("run-1", {})
        runs.transition("run-1", "created", "validated")
        with self.assertRaises(ConflictError):
            runs.transition("run-1", "created", "failed")
        runs.transition("run-1", "validated", "running")
        runs.transition("run-1", "running", "completed")
        with self.assertRaises(ValidationError):
            runs.transition("run-1", "completed", "running")
        self.assertEqual(len(runs.read("run-1")["history"]), 3)

    def test_workspace_rejects_checkout_and_broad_paths(self):
        for value in ("/", str(Path.home()), "relative"):
            with self.assertRaises(ValidationError):
                workspace_path(value)
        checkout = Path(self.temp.name) / "repo"
        checkout.mkdir()
        (checkout / ".git").write_text("gitdir: somewhere")
        with self.assertRaises(ValidationError):
            workspace_path(str(checkout / "private-data"))
        standalone = Path(self.temp.name) / "standalone"
        standalone.mkdir()
        (standalone / "pyproject.toml").write_text('[project]\nname="toy-tune"')
        with self.assertRaises(ValidationError):
            workspace_path(str(standalone / "workspace"))
