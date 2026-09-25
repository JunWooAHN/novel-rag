from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile

from toy_tune.domain.errors import ConflictError, IntegrityError, ValidationError
from toy_tune.domain.experiments import validate_transition
from toy_tune.domain.samples import identifier


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def workspace_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValidationError("Workspace must be an absolute path outside any Git checkout.")
    path = path.resolve()
    if path == Path(path.anchor) or path == Path.home().resolve():
        raise ValidationError("Choose a dedicated workspace directory.")
    if any((parent / ".git").exists() or (parent / "pyproject.toml").exists()
           for parent in (path, *path.parents)):
        raise ValidationError("Workspace must be outside Git checkouts and Python source projects.")
    return path


def child(root: Path, name: str) -> Path:
    identifier(name)
    path = root / name
    if path.is_symlink() or path.resolve().parent != root.resolve():
        raise ValidationError("Symlinks are not allowed in managed workspace paths.")
    return path


@contextmanager
def exclusive_lock(root: Path, name: str):
    identifier(name)
    lock = root / (name + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ConflictError("Resource is locked; inspect the existing writer before recovery.") from None
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def atomic_json(path: Path, value: dict):
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encode(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError):
        raise IntegrityError("Cannot read a valid manifest.") from None
    if not isinstance(value, dict):
        raise IntegrityError("Manifest must be an object.")
    return value


class FilesystemArtifactStore:
    """Single-host publication contract; shared filesystem semantics require validation."""

    def __init__(self, workspace: Path, collection: str = "datasets"):
        self.workspace = workspace_path(str(workspace))
        self.collection = identifier(collection)

    def _root(self, create: bool = False) -> Path:
        root = child(self.workspace, self.collection)
        if create:
            self.workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
            root.mkdir(exist_ok=True, mode=0o700)
        return root

    def publish(self, artifact_id: str, files: dict[str, bytes], metadata: dict) -> dict:
        identifier(artifact_id)
        if not files or "manifest.json" in files:
            raise ValidationError("A bundle needs payload files; manifest.json is reserved.")
        for name, value in files.items():
            identifier(name)
            if not isinstance(value, bytes):
                raise ValidationError("Bundle payloads must be bytes.")
        root = self._root(create=True)
        target = child(root, artifact_id)
        manifest = {"schema_version": 1, "artifact_id": artifact_id, "collection": self.collection,
                    "files": {name: hashlib.sha256(value).hexdigest() for name, value in files.items()},
                    "metadata": metadata}
        with exclusive_lock(root, artifact_id):
            if target.exists():
                existing = self.verify(artifact_id)
                if existing != manifest:
                    raise ConflictError("Immutable artifact ID already contains different content.")
                return existing
            with tempfile.TemporaryDirectory(prefix=".pending-", dir=root) as temporary:
                stage = Path(temporary) / "bundle"
                stage.mkdir(mode=0o700)
                for name, value in files.items():
                    with (stage / name).open("xb") as stream:
                        stream.write(value)
                        stream.flush()
                        os.fsync(stream.fileno())
                atomic_json(stage / "manifest.json", manifest)
                stage.rename(target)
        return self.verify(artifact_id)

    def verify(self, artifact_id: str) -> dict:
        root = self._root()
        target = child(root, artifact_id)
        manifest = read_json(child(target, "manifest.json"))
        if (manifest.get("schema_version") != 1 or manifest.get("artifact_id") != artifact_id
                or manifest.get("collection") != self.collection or not isinstance(manifest.get("files"), dict)
                or not manifest["files"]):
            raise IntegrityError("Artifact manifest identity or file index is invalid.")
        for name, expected in manifest["files"].items():
            if name == "manifest.json":
                raise IntegrityError("Manifest cannot list itself as a payload.")
            path = child(target, name)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise IntegrityError("Artifact payload checksum mismatch or missing file.")
        actual = {p.name for p in target.iterdir()}
        if actual != set(manifest["files"]) | {"manifest.json"}:
            raise IntegrityError("Artifact contains unlisted files.")
        return manifest


class FilesystemRunStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace_path(str(workspace))

    def _root(self) -> Path:
        root = child(self.workspace, "runs")
        self.workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.mkdir(exist_ok=True, mode=0o700)
        return root

    def create(self, run_id: str, specification: dict) -> dict:
        root = self._root()
        target = child(root, run_id)
        with exclusive_lock(root, identifier(run_id)):
            if target.exists():
                raise ConflictError("Run already exists; use a new run ID.")
            manifest = {"schema_version": 1, "run_id": run_id, "state": "created",
                        "specification": specification, "history": []}
            with tempfile.TemporaryDirectory(prefix=".pending-", dir=root) as temporary:
                stage = Path(temporary) / "run"
                stage.mkdir(mode=0o700)
                atomic_json(stage / "manifest.json", manifest)
                stage.rename(target)
            return manifest

    def read(self, run_id: str) -> dict:
        root = child(self.workspace, "runs")
        value = read_json(child(child(root, run_id), "manifest.json"))
        if value.get("schema_version") != 1 or value.get("run_id") != run_id:
            raise IntegrityError("Run manifest identity mismatch.")
        return value

    def transition(self, run_id: str, expected: str, following: str) -> dict:
        root = self._root()
        with exclusive_lock(root, identifier(run_id)):
            manifest = self.read(run_id)
            if manifest["state"] != expected:
                raise ConflictError("Run state has changed since it was read.")
            validate_transition(expected, following)
            manifest["state"] = following
            manifest["history"].append({"from": expected, "to": following})
            atomic_json(child(root, run_id) / "manifest.json", manifest)
            return manifest
