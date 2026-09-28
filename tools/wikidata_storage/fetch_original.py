#!/usr/bin/env python3
"""Resume and verify one fixed, official Wikidata full-entity snapshot."""

from __future__ import annotations

import bz2
import datetime as dt
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request


DEST = Path("/home/work/novel-toy-tune/sources/original/wikidata/20260922")
MOUNT = Path("/home/work/novel-toy-tune")
NAME = "wikidata-20260922-all.json.bz2"
URL = "https://dumps.wikimedia.org/wikidatawiki/entities/20260921/" + NAME
SUMS_NAME = "wikidata-20260922-sha1sums.txt"
SUMS_URL = "https://dumps.wikimedia.org/wikidatawiki/entities/20260921/" + SUMS_NAME
SIZE = 103_222_517_992
SHA1 = "c5bfd59f16c6cdf906ead1190d99729108e961be"
ETAG = '"6ab4b319-18088aa0e8"'
LAST_MODIFIED = "Thu, 24 Sep 2026 05:20:25 GMT"
RESERVE = 100_000_000_000
USER_AGENT = "novel-project-source-archiver/1.0"
PART = DEST / (NAME + ".part")
SIDECAR = DEST / (NAME + ".part.json")
FINAL = DEST / NAME
MANIFEST = DEST / "manifest.json"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def request(url: str, method: str = "GET", headers: dict[str, str] | None = None):
    return urllib.request.urlopen(
        urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, **(headers or {})}),
        timeout=120,
    )


def atomic_json(path: Path, value: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, sort_keys=True)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)


def metadata() -> dict:
    with request(URL, "HEAD") as response:
        result = {
            "url": response.geturl(),
            "status": response.status,
            "content_length": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "accept_ranges": response.headers.get("Accept-Ranges"),
        }
    expected = (URL, 200, str(SIZE), ETAG, LAST_MODIFIED, "bytes")
    actual = tuple(result.values())
    if actual != expected:
        raise RuntimeError(f"official snapshot metadata changed: {result!r}")
    return result


def check_path_and_space(part_size: int) -> None:
    if not MOUNT.is_mount():
        raise RuntimeError(f"expected persistent Storage mount absent: {MOUNT}")
    for path in (MOUNT / "sources", MOUNT / "sources/original", DEST.parent, DEST, PART, FINAL):
        if path.is_symlink():
            raise RuntimeError(f"symlink in destination path: {path}")
    space = os.statvfs(MOUNT).f_bavail * os.statvfs(MOUNT).f_frsize
    if space < SIZE - part_size + RESERVE:
        raise RuntimeError(f"insufficient available bytes: {space}; need {SIZE - part_size + RESERVE}")


def official_checksum() -> dict:
    with request(SUMS_URL) as response:
        if response.status != 200 or response.geturl() != SUMS_URL:
            raise RuntimeError("checksum response changed")
        body = response.read(16_384)
        if len(body) >= 16_384:
            raise RuntimeError("checksum response unexpectedly large")
        info = {"url": SUMS_URL, "etag": response.headers.get("ETag"), "last_modified": response.headers.get("Last-Modified"), "sha256": hashlib.sha256(body).hexdigest()}
    matching = [line for line in body.decode("utf-8").splitlines() if line.split()[-1:] == [NAME]]
    if len(matching) != 1 or matching[0].split()[0] != SHA1:
        raise RuntimeError("official SHA1 list does not match fixed snapshot")
    saved = DEST / SUMS_NAME
    if saved.exists() and saved.read_bytes() != body:
        raise RuntimeError("saved checksum file differs from official source")
    if not saved.exists():
        with saved.open("xb") as out:
            out.write(body)
        saved.chmod(0o444)
    return info


def identity() -> dict:
    return {"snapshot_date": "2026-09-22", "directory_date": "2026-09-21", "url": URL, "filename": NAME, "size_bytes": SIZE, "sha1": SHA1, "etag": ETAG, "last_modified": LAST_MODIFIED}


def prepare_sidecar() -> None:
    if SIDECAR.exists():
        if json.loads(SIDECAR.read_text(encoding="utf-8")) != identity():
            raise RuntimeError("partial file identity differs; refusing append")
    elif PART.exists():
        raise RuntimeError("partial file lacks identity sidecar; refusing append")
    else:
        atomic_json(SIDECAR, identity())


def manifest(status: str, checksum: dict, **extra) -> None:
    value = {
        "status": status, "updated_at_utc": now(), "source": identity(),
        "format": "Wikidata full current-entity JSON, bzip2 compressed; not truthy RDF or revision history",
        "license": {"structured_data": "CC0 1.0", "url": "https://www.wikidata.org/wiki/Wikidata:Licensing"},
        "relationship_to_yago_4_6": "Separate 2026-09-22 Wikidata input snapshot for future enrichment; individual YAGO 4.6 source statement revisions have not been matched.",
        "official_checksum": checksum, "original_designation": "ORIGINAL_UPSTREAM.txt",
        "destination": str(FINAL), "reserve_bytes": RESERVE, **extra,
    }
    atomic_json(MANIFEST, value)


def get_once(offset: int, checksum: dict) -> int:
    headers = {"Range": f"bytes={offset}-", "If-Range": ETAG} if offset else {}
    with request(URL, headers=headers) as response:
        if response.geturl() != URL or response.headers.get("ETag") != ETAG or response.headers.get("Last-Modified") != LAST_MODIFIED:
            raise RuntimeError("download response identity changed")
        if offset:
            wanted = f"bytes {offset}-{SIZE - 1}/{SIZE}"
            if response.status != 206 or response.headers.get("Content-Range") != wanted:
                raise RuntimeError("server did not honor exact resumable range")
            if response.headers.get("Content-Length") != str(SIZE - offset):
                raise RuntimeError("resumed response size mismatch")
        elif response.status != 200 or response.headers.get("Content-Length") != str(SIZE):
            raise RuntimeError("initial response size mismatch")
        with PART.open("ab") as out:
            last_log = time.monotonic()
            while True:
                block = response.read(8 * 1024 * 1024)
                if not block:
                    break
                available = os.statvfs(MOUNT).f_bavail * os.statvfs(MOUNT).f_frsize
                if available < RESERVE + len(block):
                    raise RuntimeError(f"storage reserve would be breached: {available} available")
                out.write(block)
                offset += len(block)
                if offset > SIZE:
                    raise RuntimeError("download exceeded pinned size")
                if time.monotonic() - last_log >= 60:
                    out.flush()
                    print(json.dumps({"event": "progress", "at_utc": now(), "bytes": offset, "total": SIZE}), flush=True)
                    manifest("downloading", checksum, downloaded_bytes=offset)
                    last_log = time.monotonic()
            out.flush()
            os.fsync(out.fileno())
    return offset


def digests() -> tuple[str, str]:
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with PART.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            sha1.update(block)
            sha256.update(block)
    return sha1.hexdigest(), sha256.hexdigest()


def parse_sample() -> list[str]:
    ids = []
    with bz2.open(PART, "rb") as stream:
        first = stream.readline().strip()
        if first != b"[":
            raise RuntimeError("JSON dump does not begin with array")
        for _ in range(3):
            raw = stream.readline().rstrip(b"\r\n,")
            entity = json.loads(raw)
            if not isinstance(entity, dict) or not isinstance(entity.get("id"), str) or "claims" not in entity:
                raise RuntimeError("entity sample lacks id or claims")
            ids.append(entity["id"])
    return ids


def run() -> int:
    if FINAL.exists():
        raise RuntimeError("final archive already exists; refusing overwrite")
    part_size = PART.stat().st_size if PART.exists() else 0
    if part_size > SIZE:
        raise RuntimeError("partial file exceeds expected size")
    check_path_and_space(part_size)
    metadata()
    DEST.mkdir(parents=True, exist_ok=True)
    checksum = official_checksum()
    prepare_sidecar()
    designation = DEST / "ORIGINAL_UPSTREAM.txt"
    designation_text = f"ORIGINAL compressed upstream bytes; no transformation.\n{URL}\nSHA1 {SHA1}\nChecksum source: {SUMS_URL}\n"
    if designation.exists() and designation.read_text(encoding="utf-8") != designation_text:
        raise RuntimeError("existing ORIGINAL designation differs")
    if not designation.exists():
        designation.write_text(designation_text, encoding="utf-8")
        designation.chmod(0o444)
    manifest("downloading", checksum, downloaded_bytes=part_size)
    failures = 0
    while part_size < SIZE:
        try:
            metadata()
            new_size = get_once(part_size, checksum)
            if new_size == part_size:
                raise OSError("no download progress")
            part_size = PART.stat().st_size
            failures = 0
        except (OSError, urllib.error.URLError, http.client.IncompleteRead, TimeoutError) as exc:
            part_size = PART.stat().st_size if PART.exists() else 0
            failures += 1
            print(json.dumps({"event": "retry", "at_utc": now(), "attempt": failures, "bytes": part_size, "error": str(exc)}), flush=True)
            manifest("downloading", checksum, downloaded_bytes=part_size, last_error=str(exc))
            if failures >= 40:
                raise RuntimeError("40 consecutive download failures") from exc
            time.sleep(min(60, 2 ** min(failures, 6)))
    manifest("verifying", checksum, downloaded_bytes=SIZE)
    if PART.stat().st_size != SIZE:
        raise RuntimeError("final size mismatch")
    actual_sha1, actual_sha256 = digests()
    if actual_sha1 != SHA1:
        raise RuntimeError(f"official SHA1 mismatch: {actual_sha1}")
    sample_ids = parse_sample()
    os.replace(PART, FINAL)
    FINAL.chmod(0o444)
    manifest("complete", checksum, size_bytes=SIZE, sha1=actual_sha1, sha256=actual_sha256, json_sample_entity_ids=sample_ids, verified_at_utc=now(), full_bzip2_decompression_test=False)
    print(json.dumps({"event": "complete", "at_utc": now(), "size": SIZE, "sha1": actual_sha1, "sha256": actual_sha256, "sample": sample_ids}), flush=True)
    return 0


def main() -> int:
    if not MOUNT.is_mount():
        raise RuntimeError(f"expected persistent Storage mount absent: {MOUNT}")
    for path in (MOUNT / "sources", MOUNT / "sources/original", DEST.parent, DEST):
        if path.is_symlink():
            raise RuntimeError(f"symlink in destination path: {path}")
    DEST.mkdir(parents=True, exist_ok=True)
    with (DEST / ".fetch.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another Wikidata download writer holds the lock") from exc
        return run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"event": "stopped", "at_utc": now(), "error": str(error)}), file=sys.stderr, flush=True)
        raise
