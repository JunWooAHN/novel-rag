#!/usr/bin/env python3
"""Archive the unchanged upstream YAGO 4.6 ZIPs and their extracted contents."""

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile
import zlib


SPEC = json.loads(Path(__file__).with_name("release.json").read_text())
TOTAL_BYTES = sum(f["compressed_bytes"] + f["uncompressed_bytes"] for f in SPEC["files"])
CHUNK = 4 * 1024 * 1024


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def digest_crc(path):
    h = hashlib.sha256()
    crc = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            h.update(block)
            crc = zlib.crc32(block, crc)
    return h.hexdigest(), f"{crc & 0xffffffff:08x}"


def save_json(path, value):
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=path.name + ".", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def preflight(base, root, expected_target=None):
    if root.is_symlink():
        raise RuntimeError("original root cannot be a symlink")
    base = base.resolve(strict=True)
    root = root.resolve(strict=False)
    if root == base or not root.is_relative_to(base):
        raise RuntimeError("original root must be below the Storage mount")
    if root.exists() and root.is_symlink():
        raise RuntimeError("original root cannot be a symlink")
    result = subprocess.run(
        ["findmnt", "--json", "-T", str(base), "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"],
        check=True, capture_output=True, text=True,
    )
    mount = json.loads(result.stdout)["filesystems"][0]
    target = mount["target"]
    if target == "/" or mount["fstype"] in {"overlay", "tmpfs"}:
        raise RuntimeError("Storage base resolves to a session filesystem")
    if expected_target is not None and target != expected_target:
        raise RuntimeError(f"unexpected mount target: {target}")
    fs = os.statvfs(base)
    free = fs.f_bavail * fs.f_frsize
    return {"base": str(base), "root": str(root), "mount": mount,
            "free_bytes": free, "required_initial_bytes": TOTAL_BYTES + 5_000_000_000}


def head(url, expected_size):
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "novel-yago-original/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"HEAD returned {response.status}: {url}")
        size = int(response.headers["Content-Length"])
        if size != expected_size:
            raise RuntimeError(f"upstream size changed for {url}: {size} != {expected_size}")
        return {"etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "compressed_bytes": size}


def transfer(url, part, sidecar, final, headers):
    if final.exists():
        if final.is_symlink():
            raise RuntimeError(f"refusing symlink: {final}")
        if not sidecar.exists() or json.loads(sidecar.read_text()) != headers:
            raise RuntimeError(f"completed ZIP provenance is missing or changed: {final}")
        return False
    if part.exists() and not sidecar.exists():
        raise RuntimeError(f"partial file has no pinned upstream headers: {part}")
    if sidecar.exists():
        previous = json.loads(sidecar.read_text())
        if previous != headers:
            raise RuntimeError(f"upstream validators changed; preserve partial file for inspection: {part}")
    else:
        save_json(sidecar, headers)
    if not part.exists():
        part.touch(exist_ok=False)
    if part.is_symlink():
        raise RuntimeError(f"refusing symlink: {part}")
    expected = headers["compressed_bytes"]
    for attempt in range(3):
        offset = part.stat().st_size
        if offset > expected:
            raise RuntimeError(f"partial file is too large: {part}")
        if offset == expected:
            break
        request_headers = {"User-Agent": "novel-yago-original/1"}
        if offset:
            validator = headers["etag"]
            if validator and validator.startswith("W/"):
                validator = None
            validator = validator or headers["last_modified"]
            if not validator:
                raise RuntimeError(f"cannot safely resume without upstream validator: {part}")
            request_headers.update({"Range": f"bytes={offset}-", "If-Range": validator})
        try:
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=90) as response:
                if offset:
                    value = response.headers.get("Content-Range", "")
                    if response.status != 206 or not re.fullmatch(
                        rf"bytes {offset}-{expected - 1}/{expected}", value
                    ):
                        raise RuntimeError(f"unsafe resume response for {part}: {response.status} {value}")
                elif response.status != 200 or int(response.headers["Content-Length"]) != expected:
                    raise RuntimeError(f"unexpected full response for {part}")
                with part.open("ab") as output:
                    last_report = time.monotonic()
                    while block := response.read(CHUNK):
                        output.write(block)
                        if time.monotonic() - last_report >= 30:
                            print(f"download {part.name}: {output.tell()}/{expected}", flush=True)
                            last_report = time.monotonic()
                    output.flush()
                    os.fsync(output.fileno())
            if part.stat().st_size == expected:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt == 2:
                raise RuntimeError(f"download interrupted after 3 attempts: {part}") from error
            print(f"retry {part.name}: {type(error).__name__}", flush=True)
            time.sleep(2 ** attempt)
    if part.stat().st_size != expected:
        raise RuntimeError(f"incomplete download retained at {part}")
    check_zip(part)
    if final.exists():
        raise RuntimeError(f"completed ZIP appeared concurrently: {final}")
    os.rename(part, final)
    return True


def checked_members(archive, expected_uncompressed):
    members = []
    paths = set()
    for info in archive.infolist():
        name = PurePosixPath(info.filename)
        if (name.is_absolute() or not name.parts or ".." in name.parts
                or "\\" in info.filename or info.flag_bits & 1
                or stat.S_ISLNK(info.external_attr >> 16)):
            raise RuntimeError(f"unsafe ZIP member: {info.filename}")
        if info.is_dir():
            continue
        if str(name) in paths:
            raise RuntimeError(f"duplicate ZIP member: {info.filename}")
        paths.add(str(name))
        members.append((info, name))
    if sum(info.file_size for info, _ in members) != expected_uncompressed:
        raise RuntimeError("ZIP uncompressed byte total differs from release inventory")
    return members


def check_zip(path):
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failure in {path}: {bad}")


def extracted_entries(zippath, target, expected_uncompressed, make_readonly=False):
    with zipfile.ZipFile(zippath) as archive:
        members = checked_members(archive, expected_uncompressed)
        if target.exists():
            if target.is_symlink() or not target.is_dir():
                raise RuntimeError(f"unsafe extracted destination: {target}")
        else:
            temporary = target.with_name("." + target.name + ".extracting")
            if temporary.exists():
                if temporary.is_symlink() or not temporary.is_dir():
                    raise RuntimeError(f"unsafe extraction staging: {temporary}")
                shutil.rmtree(temporary)  # Only this incomplete derived staging directory.
            temporary.mkdir(parents=True)
            for info, name in members:
                output = temporary.joinpath(*name.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("xb") as sink:
                    last_report = time.monotonic()
                    while block := source.read(CHUNK):
                        sink.write(block)
                        if time.monotonic() - last_report >= 30:
                            print(f"extract {name}: {sink.tell()}/{info.file_size}", flush=True)
                            last_report = time.monotonic()
                if output.stat().st_size != info.file_size:
                    raise RuntimeError(f"extracted size mismatch: {output}")
            if target.exists():
                raise RuntimeError(f"extracted destination appeared concurrently: {target}")
            os.rename(temporary, target)
        entries = []
        observed = list(target.rglob("*"))
        if any(path.is_symlink() for path in observed):
            raise RuntimeError(f"symlink in extracted destination: {target}")
        existing = {str(path.relative_to(target)) for path in observed if path.is_file()}
        if existing != {str(name) for _, name in members}:
            raise RuntimeError(f"extra/missing extracted members: {target}")
        for info, name in members:
            output = target.joinpath(*name.parts)
            if output.is_symlink() or not output.is_file() or output.stat().st_size != info.file_size:
                raise RuntimeError(f"extracted member mismatch: {output}")
            sha, crc = digest_crc(output)
            if crc != f"{info.CRC:08x}":
                raise RuntimeError(f"extracted CRC mismatch: {output}")
            if make_readonly:
                output.chmod(0o444)
            entries.append({"path": str(name), "bytes": info.file_size,
                            "crc32": crc, "sha256": sha,
                            "mode": f"{stat.S_IMODE(output.stat().st_mode):04o}"})
        return entries


def verify(root, manifest):
    if manifest.get("status") != "complete" or len(manifest.get("files", {})) != len(SPEC["files"]):
        raise RuntimeError("archive manifest is incomplete")
    compressed = uncompressed = 0
    for spec in SPEC["files"]:
        name = spec["name"]
        item = manifest["files"][name]
        zippath = root / "zip" / name
        if (zippath.is_symlink() or zippath.stat().st_size != spec["compressed_bytes"]
                or digest(zippath) != item["sha256"]
                or f"{stat.S_IMODE(zippath.stat().st_mode):04o}" != item["zip_mode"]):
            raise RuntimeError(f"ZIP hash/size mismatch: {name}")
        check_zip(zippath)
        with zipfile.ZipFile(zippath) as archive:
            members = checked_members(archive, spec["uncompressed_bytes"])
            expected = {str(path): info for info, path in members}
        destination = root / "extracted" / name.removesuffix(".zip")
        if destination.is_symlink() or not destination.is_dir():
            raise RuntimeError(f"unsafe extracted destination: {destination}")
        observed = list(destination.rglob("*"))
        if any(path.is_symlink() for path in observed):
            raise RuntimeError(f"symlink in extracted destination: {destination}")
        actual = {str(path.relative_to(destination)) for path in observed if path.is_file()}
        if actual != set(expected):
            raise RuntimeError(f"extra/missing extracted members: {destination}")
        if set(expected) != {entry["path"] for entry in item["entries"]}:
            raise RuntimeError(f"extracted member list mismatch: {name}")
        for entry in item["entries"]:
            member = root / "extracted" / name.removesuffix(".zip") / entry["path"]
            if member.is_symlink() or not member.is_file() or member.stat().st_size != entry["bytes"]:
                raise RuntimeError(f"extracted member missing/size mismatch: {member}")
            sha, crc = digest_crc(member)
            if (sha != entry["sha256"] or crc != entry["crc32"]
                    or crc != f"{expected[entry['path']].CRC:08x}"
                    or f"{stat.S_IMODE(member.stat().st_mode):04o}" != entry["mode"]):
                raise RuntimeError(f"extracted hash/size mismatch: {member}")
        compressed += spec["compressed_bytes"]
        uncompressed += spec["uncompressed_bytes"]
        print(f"verified {name}", flush=True)
    return {"verified_at": stamp(), "zip_count": len(SPEC["files"]),
            "compressed_bytes": compressed, "uncompressed_bytes": uncompressed}


def stage_relay(root, spec, expected_sha, source_etag, source_last_modified):
    """Promote a fully transferred, locally sourced official ZIP to fetch's partial slot."""
    name = spec["name"]
    url = SPEC["base_url"] + name
    headers = head(url, spec["compressed_bytes"])
    if not (source_etag or source_last_modified):
        raise RuntimeError("relay requires a pinned upstream ETag or Last-Modified")
    if source_etag != headers["etag"] or source_last_modified != headers["last_modified"]:
        raise RuntimeError(f"local and H200 upstream validators differ: {name}")
    folder = root / "zip"
    if folder.is_symlink() or folder.resolve(strict=True).parent != root.resolve(strict=True):
        raise RuntimeError("unsafe ZIP directory")
    final = folder / name
    if final.exists():
        if final.is_symlink() or digest(final) != expected_sha:
            raise RuntimeError(f"existing original differs from relay: {name}")
        print(f"already stored {name}", flush=True)
        return
    incoming = folder / (name + ".relay.part")
    if incoming.is_symlink() or incoming.stat().st_size != spec["compressed_bytes"]:
        raise RuntimeError(f"incomplete relay stage: {incoming}")
    if digest(incoming) != expected_sha:
        raise RuntimeError(f"relay SHA-256 mismatch: {incoming}")
    check_zip(incoming)
    part = folder / (name + ".part")
    sidecar = folder / (name + ".part.json")
    if part.exists() and part.stat().st_size == spec["compressed_bytes"] and digest(part) == expected_sha:
        if sidecar.exists() and json.loads(sidecar.read_text()) != headers:
            raise RuntimeError(f"existing complete partial has different provenance: {part}")
        if not sidecar.exists():
            save_json(sidecar, headers)
        print(f"already staged {name}", flush=True)
        return
    backup_id = "direct-preserved-" + uuid.uuid4().hex
    if part.exists():
        if part.is_symlink():
            raise RuntimeError(f"refusing symlink: {part}")
        os.rename(part, folder / (name + "." + backup_id + ".part"))
    if sidecar.exists():
        if sidecar.is_symlink():
            raise RuntimeError(f"refusing symlink: {sidecar}")
        os.rename(sidecar, folder / (name + "." + backup_id + ".part.json"))
    save_json(sidecar, headers)
    os.rename(incoming, part)
    print(f"staged {name} sha256={expected_sha}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "fetch", "verify", "stage"])
    parser.add_argument("--storage-base", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-mount-target")
    parser.add_argument("--only", choices=[file["name"] for file in SPEC["files"]],
                        action="append", help="process one or more already staged official ZIPs")
    parser.add_argument("--name", choices=[file["name"] for file in SPEC["files"]])
    parser.add_argument("--expected-sha")
    parser.add_argument("--source-etag")
    parser.add_argument("--source-last-modified")
    args = parser.parse_args()
    state = preflight(args.storage_base, args.root, args.expected_mount_target)
    if args.action == "preflight":
        print(json.dumps(state, indent=2))
        return
    if args.expected_mount_target is None:
        raise RuntimeError("fetch/verify require --expected-mount-target from preflight")
    root = Path(state["root"])
    if args.action == "verify":
        print(json.dumps(verify(root, json.loads((root / "manifest.json").read_text())), indent=2))
        return
    if args.action == "stage":
        if not args.name or not args.expected_sha or not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha):
            raise RuntimeError("stage requires --name and a lowercase SHA-256")
        with (root / ".fetch.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            spec = next(file for file in SPEC["files"] if file["name"] == args.name)
            stage_relay(root, spec, args.expected_sha,
                        args.source_etag, args.source_last_modified)
        return
    if state["free_bytes"] < state["required_initial_bytes"] and not root.exists():
        raise RuntimeError("insufficient persistent Storage free space")
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".fetch.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for child_name in ("zip", "extracted"):
            child = root / child_name
            if child.is_symlink():
                raise RuntimeError(f"refusing symlink: {child}")
            child.mkdir(exist_ok=True)
            if child.is_symlink() or child.resolve(strict=True).parent != root.resolve(strict=True):
                raise RuntimeError(f"storage child escapes original root: {child}")
        marker = root / "ORIGINAL_UPSTREAM.txt"
        label = ("YAGO 4.6 ORIGINAL UPSTREAM ARCHIVE\n"
                 "Source: https://yago-knowledge.org/data/yago4.6/\n"
                 "zip/ retains the unchanged downloaded ZIP bytes. extracted/ contains only their\n"
                 "decompressed members. Put indexes, conversions, and other derivatives elsewhere.\n")
        if marker.exists():
            if marker.read_text() != label:
                raise RuntimeError("original marker differs; refusing to overwrite")
        else:
            marker.write_text(label)
        path = root / "manifest.json"
        manifest = json.loads(path.read_text()) if path.exists() else {
            "release": SPEC["release"], "kind": "original_upstream_unchanged",
            "base_url": SPEC["base_url"], "created_at": stamp(),
            "mount": state["mount"], "status": "in_progress", "files": {}}
        if manifest["release"] != SPEC["release"] or manifest["base_url"] != SPEC["base_url"]:
            raise RuntimeError("existing manifest belongs to a different upstream release")
        selected = [spec for spec in SPEC["files"] if not args.only or spec["name"] in args.only]
        for spec in selected:
            name = spec["name"]
            url = SPEC["base_url"] + name
            print(f"processing {name}", flush=True)
            final = root / "zip" / name
            destination = root / "extracted" / name.removesuffix(".zip")
            if name in manifest["files"]:
                previous = manifest["files"][name]
                if final.stat().st_size != spec["compressed_bytes"] or digest(final) != previous["sha256"]:
                    raise RuntimeError(f"existing original differs: {name}")
                if extracted_entries(final, destination, spec["uncompressed_bytes"]) != previous["entries"]:
                    raise RuntimeError(f"existing extraction differs: {name}")
                print(f"retained verified original {name}", flush=True)
                continue
            headers = head(url, spec["compressed_bytes"])
            newly_downloaded = transfer(url, final.with_name(name + ".part"),
                     final.with_name(name + ".part.json"), final, headers)
            if final.stat().st_size != spec["compressed_bytes"]:
                raise RuntimeError(f"completed ZIP has wrong size: {final}")
            if not newly_downloaded:
                check_zip(final)
            entries = extracted_entries(final, destination,
                                        spec["uncompressed_bytes"], make_readonly=True)
            final.chmod(0o444)
            item = {"url": url, "received_at": stamp(), "etag": headers["etag"],
                    "last_modified": headers["last_modified"],
                    "compressed_bytes": spec["compressed_bytes"],
                    "uncompressed_bytes": spec["uncompressed_bytes"],
                    "sha256": digest(final), "zip_crc_verified": True,
                    "zip_mode": f"{stat.S_IMODE(final.stat().st_mode):04o}",
                    "entries": entries}
            if name in manifest["files"] and manifest["files"][name]["sha256"] != item["sha256"]:
                raise RuntimeError(f"existing original hash differs: {name}")
            manifest["files"][name] = item
            save_json(path, manifest)
            print(f"stored {name}", flush=True)
        if len(manifest["files"]) == len(SPEC["files"]):
            manifest["status"] = "complete"
            manifest["completed_at"] = stamp()
            save_json(path, manifest)
            print(json.dumps(verify(root, manifest), indent=2), flush=True)
        else:
            print(f"stored {len(manifest['files'])}/{len(SPEC['files'])} archives", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
