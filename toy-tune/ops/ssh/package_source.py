"""Build an immutable source archive from a reviewed allowlist. No SSH or uploads."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

PROJECT = Path(__file__).resolve().parents[2]


def collect(project: Path) -> dict[str, bytes]:
    names = (project / "ops/ssh/source-files.txt").read_text().splitlines()
    payloads = {}
    for name in names:
        if not name or name.startswith("#"):
            continue
        path = project / name
        if Path(name).is_absolute() or ".." in Path(name).parts or name in payloads:
            raise ValueError("Invalid or duplicate source allowlist path.")
        if name != ".gitignore" and any(part.startswith(".") for part in Path(name).parts):
            raise ValueError("Hidden files cannot be included in the source archive.")
        if path.suffix in {".key", ".pem", ".sqlite", ".gguf", ".safetensors"} or ".local." in name:
            raise ValueError("Private file type cannot be included in the source archive.")
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != project.parent):
            raise ValueError("Source symlinks are not supported.")
        if not path.is_file() or not path.resolve().is_relative_to(project.resolve()):
            raise ValueError("Source allowlist references a missing or external file.")
        payloads[name] = path.read_bytes()
    return payloads


def package(project: Path, output: Path) -> Path:
    output = output.expanduser().resolve()
    if any((parent / ".git").exists() for parent in (output, *output.parents)) or output.is_relative_to(project):
        raise ValueError("Place source archives outside Git checkouts.")
    payloads = collect(project)
    checksums = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payloads.items())}
    encoded = json.dumps(checksums, sort_keys=True).encode()
    source_id = "src-" + hashlib.sha256(encoded).hexdigest()[:24]
    manifest = {"schema_version": 1, "source_id": source_id, "files": checksums}
    payloads["source-manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    target = output / (source_id + ".tar")
    # Exclusive creation prevents silently replacing an existing release.
    with target.open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in sorted(payloads.items()):
            info = tarfile.TarInfo(source_id + "/" + name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(package(PROJECT, args.output))
    except (OSError, ValueError):
        parser.exit(2, "Source publication failed; check allowlist, output permissions and duplicate release.\n")
