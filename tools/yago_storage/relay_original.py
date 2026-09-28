#!/usr/bin/env python3
"""Resume official YAGO ZIPs with four local Range streams and relay to H200 Storage."""

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request

from fetch_original import SPEC, check_zip, checked_members, digest, head, save_json, stamp


CHUNK = 4 * 1024 * 1024
REMOTE_TOOL = "/home/work/novel-toy-tune/tools/yago_storage/20260928/fetch_original.py"
REMOTE_BASE = "/home/work/novel-toy-tune"
REMOTE_ROOT = REMOTE_BASE + "/sources/original/yago/4.6"


def ssh_prefix(args):
    return ["ssh", "-i", str(args.key), "-p", str(args.port), "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=yes",
            "-o", "UserKnownHostsFile=" + str(args.known_hosts), args.host]


def remote(args, argv, stream=False, input_file=None):
    command = ssh_prefix(args) + [shlex.join(argv)]
    if stream:
        proc = subprocess.Popen(command, stdin=input_file or subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            print("H200: " + line.rstrip(), flush=True)
        if proc.wait() != 0:
            raise RuntimeError(f"remote command exited {proc.returncode}")
        return ""
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    return result.stdout.strip()


def remote_stored(args, name):
    code = ("import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); "
            "m=json.loads(p.read_text()) if p.exists() else {}; "
            "print('yes' if sys.argv[2] in m.get('files',{}) else 'no')")
    return remote(args, ["python3", "-c", code, REMOTE_ROOT + "/manifest.json", name]) == "yes"


def get_range(url, headers, index, length, fd):
    start = index * CHUNK
    end = start + length - 1
    request_headers = {"User-Agent": "novel-yago-original-relay/1",
                       "Range": f"bytes={start}-{end}"}
    validator = headers["etag"]
    if validator and validator.startswith("W/"):
        validator = None
    validator = validator or headers["last_modified"]
    if not validator:
        raise RuntimeError("upstream has no validator for ranged relay")
    request_headers["If-Range"] = validator
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=request_headers), timeout=120) as response:
                wanted = f"bytes {start}-{end}/{headers['compressed_bytes']}"
                if response.status != 206 or response.headers.get("Content-Range") != wanted:
                    raise RuntimeError(f"unexpected Range response for chunk {index}")
                if (response.headers.get("ETag") != headers["etag"]
                        or response.headers.get("Last-Modified") != headers["last_modified"]):
                    raise RuntimeError(f"upstream validators changed for chunk {index}")
                data = response.read(length + 1)
                if len(data) != length:
                    raise RuntimeError(f"wrong Range length for chunk {index}: {len(data)}")
            written = 0
            while written < length:
                written += os.pwrite(fd, data[written:], start + written)
            return index, hashlib.sha256(data).hexdigest()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt == 2:
                raise RuntimeError(f"Range chunk {index} failed 3 times") from error
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def local_zip(args, spec):
    name = spec["name"]
    url = SPEC["base_url"] + name
    headers = head(url, spec["compressed_bytes"])
    path = args.work_dir / name
    part = args.work_dir / (name + ".part")
    state_path = args.work_dir / (name + ".state.json")
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state["url"] != url or state["headers"] != headers or state["chunk_bytes"] != CHUNK:
            raise RuntimeError(f"upstream metadata changed; preserving local files: {name}")
    else:
        if path.exists() or part.exists():
            raise RuntimeError(f"untracked local ZIP/partial: {name}")
        state = {"url": url, "headers": headers, "chunk_bytes": CHUNK,
                 "started_at": stamp(), "done": {}, "status": "in_progress"}
        save_json(state_path, state)
    if path.exists():
        if path.stat().st_size != spec["compressed_bytes"]:
            raise RuntimeError(f"completed local ZIP changed: {name}")
        if "sha256" not in state:
            check_zip(path)
            state.update({"status": "complete", "sha256": digest(path), "completed_at": stamp()})
            save_json(state_path, state)
        if digest(path) != state["sha256"]:
            raise RuntimeError(f"completed local ZIP changed: {name}")
        return path, headers, state["sha256"]
    if not part.exists():
        with part.open("xb") as output:
            output.truncate(spec["compressed_bytes"])
    if part.stat().st_size != spec["compressed_bytes"]:
        raise RuntimeError(f"local sparse partial has wrong size: {name}")
    count = (spec["compressed_bytes"] + CHUNK - 1) // CHUNK
    fd = os.open(part, os.O_RDWR)
    try:
        for key, expected in list(state["done"].items()):
            index = int(key)
            length = min(CHUNK, spec["compressed_bytes"] - index * CHUNK)
            data = os.pread(fd, length, index * CHUNK)
            if len(data) != length or hashlib.sha256(data).hexdigest() != expected:
                del state["done"][key]
        save_json(state_path, state)
        missing = [index for index in range(count) if str(index) not in state["done"]]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            todo = iter(missing)
            pending = {}
            def submit_next():
                index = next(todo, None)
                if index is not None:
                    task = pool.submit(get_range, url, headers, index,
                                       min(CHUNK, spec["compressed_bytes"] - index * CHUNK), fd)
                    pending[task] = index
            for _ in range(args.workers):
                submit_next()
            last_report = time.monotonic()
            while pending:
                finished, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in finished:
                    del pending[future]
                    try:
                        index, sha = future.result()
                    except Exception:
                        for remaining in pending:
                            remaining.cancel()
                        raise
                    state["done"][str(index)] = sha
                    save_json(state_path, state)
                    if time.monotonic() - last_report >= 30 or len(state["done"]) == count:
                        print(f"download {name}: {len(state['done'])}/{count} ranges", flush=True)
                        last_report = time.monotonic()
                    submit_next()
        os.fsync(fd)
    finally:
        os.close(fd)
    check_zip(part)
    with __import__("zipfile").ZipFile(part) as archive:
        checked_members(archive, spec["uncompressed_bytes"])
    sha = digest(part)
    os.rename(part, path)
    state.update({"status": "complete", "sha256": sha, "completed_at": stamp()})
    save_json(state_path, state)
    print(f"local ZIP verified {name} sha256={sha}", flush=True)
    return path, headers, sha


def remote_stage_size(args, path):
    code = ("import os,pathlib,sys; r=pathlib.Path(sys.argv[1]); z=r/'zip'; p=pathlib.Path(sys.argv[2]); "
            "assert not r.is_symlink() and not z.is_symlink() and z.resolve().parent==r.resolve() "
            "and not p.is_symlink() and p.parent==z, 'unsafe relay path'; "
            "print(os.path.getsize(p) if p.exists() else 0)")
    return int(remote(args, ["python3", "-c", code, REMOTE_ROOT, path]))


def upload(args, local_path, name):
    target = REMOTE_ROOT + "/zip/" + name + ".relay.part"
    size = local_path.stat().st_size
    remote(args, remote_fetch_args("preflight"))
    offset = remote_stage_size(args, target)
    if offset > size:
        raise RuntimeError(f"remote relay partial too large: {name}")
    if offset == size:
        return
    print(f"relay {name}: resume at {offset}/{size}", flush=True)
    command = ssh_prefix(args) + ["cat >> " + shlex.quote(target)]
    with local_path.open("rb") as source:
        source.seek(offset)
        proc = subprocess.Popen(command, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        last_report = time.monotonic()
        try:
            while block := source.read(CHUNK):
                proc.stdin.write(block)
                if time.monotonic() - last_report >= 30:
                    print(f"relay {name}: {source.tell()}/{size}", flush=True)
                    last_report = time.monotonic()
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError(f"relay SSH failed: {proc.stderr.read(200).decode(errors='replace')}")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    if remote_stage_size(args, target) != size:
        raise RuntimeError(f"remote relay size mismatch: {name}")


def remote_fetch_args(action):
    return ["python3", "-u", REMOTE_TOOL, action, "--storage-base", REMOTE_BASE,
            "--root", REMOTE_ROOT, "--expected-mount-target", REMOTE_BASE]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    parser.add_argument("--host", default="work@proxy1.ainexus.ktcloud.com")
    parser.add_argument("--port", type=int, default=10659)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    processed = 0
    for spec in SPEC["files"]:
        name = spec["name"]
        if remote_stored(args, name):
            print(f"already recorded on H200: {name}", flush=True)
            continue
        path, headers, sha = local_zip(args, spec)
        upload(args, path, name)
        stage = remote_fetch_args("stage") + ["--name", name, "--expected-sha", sha]
        if headers["etag"]:
            stage += ["--source-etag", headers["etag"]]
        if headers["last_modified"]:
            stage += ["--source-last-modified", headers["last_modified"]]
        remote(args, stage, stream=True)
        remote(args, remote_fetch_args("fetch") + ["--only", name], stream=True)
        processed += 1
    if processed == 0:
        remote(args, remote_fetch_args("verify"), stream=True)
    print("ALL 12 ORIGINAL YAGO ZIPs VERIFIED ON H200", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
