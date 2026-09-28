"""Freeze manually selected dump excerpts with page, revision and UTF-8 spans."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pages", type=Path, required=True)
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--shard-hashes", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    chosen = json.loads(args.selection.read_bytes())
    hashes = json.loads(args.shard_hashes.read_bytes())
    units = []
    for entry in chosen:
        page = json.loads((args.pages / f"page-{entry['page_id']}.json").read_bytes())
        raw = page["slot_text"].encode("utf-8")
        if sha(raw) != page["slot_text_sha256"]:
            raise ValueError("Page slot hash differs")
        start, end = entry["slot_span_utf8"]
        if not 0 <= start < end <= len(raw):
            raise ValueError("Invalid slot span")
        text = raw[start:end].decode("utf-8")
        if len(text) > 5000:
            raise ValueError("Trial excerpt exceeds 5000 characters")
        shard = page["shard_file"]
        if shard not in hashes:
            raise ValueError("Missing verified shard SHA")
        unit_id = "wiki-" + sha(
            f"enwiki-2026-09-01:{page['page_id']}:{page['revision_id']}:{start}:{end}".encode()
        )[:20]
        units.append({
            "source_unit_id": unit_id, "source_unit_sha256": sha(text.encode("utf-8")),
            "snapshot_id": "enwiki-2026-09-01", "shard_file": shard,
            "shard_sha256": hashes[shard], "page_id": page["page_id"],
            "title": page["title"], "revision_id": page["revision_id"],
            "revision_timestamp": page["revision_timestamp"],
            "slot_role": page["slot_role"],
            "slot_text_sha256": page["slot_text_sha256"],
            "slot_span_utf8": [start, end], "selection_reason": entry["reason"],
            "text": text,
        })
    if not 3 <= len(units) <= 5 or len({u["page_id"] for u in units}) != len(units):
        raise ValueError("Trial requires one excerpt from each of 3 to 5 pages")
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.write_text(json.dumps({"units": units}, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({"units": len(units), "titles": [u["title"] for u in units],
                      "source_unit_ids": [u["source_unit_id"] for u in units]}))


if __name__ == "__main__":
    main()
