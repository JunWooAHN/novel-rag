"""Extract a few pinned page revisions from the local English Wikipedia dump.

This trial deliberately exports no other pages and does not publish ontology facts.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


TARGETS = {
    1473011: "Bloomery",
    2402602: "Munjong of Joseon",
    3121209: "Danjong of Joseon",
    3131532: "Sejo of Joseon",
    42538288: "Hangul",
}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(node: ET.Element, name: str) -> str | None:
    for child in node:
        if local(child.tag) == name:
            return child.text
    return None


def child(node: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in node if local(item.tag) == name), None)


def shard_for(dump_dir: Path, page_id: int) -> Path:
    for path in sorted(dump_dir.glob("enwiki-*.xml.bz2")):
        match = re.search(r"-p(\d+)p(\d+)\.xml\.bz2$", path.name)
        if match and int(match[1]) <= page_id <= int(match[2]):
            return path
    raise ValueError(f"No shard covers page ID {page_id}")


def extract(shard: Path, wanted: set[int]) -> dict[int, dict]:
    found: dict[int, dict] = {}
    with bz2.open(shard, "rb") as stream:
        events = ET.iterparse(stream, events=("start", "end"))
        _, root = next(events)
        for event, page in events:
            if event != "end" or local(page.tag) != "page":
                continue
            raw_id = child_text(page, "id")
            page_id = int(raw_id) if raw_id else -1
            if page_id in wanted:
                revision = child(page, "revision")
                if revision is None:
                    raise ValueError(f"Missing revision: {page_id}")
                slot = child(revision, "slots")
                if slot is not None:
                    slot = next((s for s in slot if local(s.tag) == "slot" and s.get("role", "main") == "main"), None)
                text_node = child(slot or revision, "text")
                if text_node is None or text_node.text is None:
                    raise ValueError(f"Missing main text: {page_id}")
                text = text_node.text
                if child_text(page, "ns") != "0":
                    raise ValueError(f"Unexpected namespace: {page_id}")
                found[page_id] = {
                    "page_id": page_id,
                    "title": child_text(page, "title"),
                    "revision_id": child_text(revision, "id"),
                    "revision_timestamp": child_text(revision, "timestamp"),
                    "slot_role": "main",
                    "slot_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "slot_text": text,
                    "shard_file": shard.name,
                }
            root.clear()
            if len(found) == len(wanted):
                break
    missing = wanted - found.keys()
    if missing:
        raise ValueError(f"Target page IDs absent from shard {shard.name}: {sorted(missing)}")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-dir", type=Path, default=Path("wiki-dump"))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--page-id", type=int, action="append", choices=sorted(TARGETS))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    targets = set(args.page_id) if args.page_id else set(TARGETS)
    grouped: dict[Path, set[int]] = {}
    for page_id in targets:
        grouped.setdefault(shard_for(args.dump_dir, page_id), set()).add(page_id)
    for shard, ids in grouped.items():
        for page_id, page in extract(shard, ids).items():
            if page["title"] != TARGETS[page_id]:
                raise ValueError(f"Page title differs from routing hint: {page_id}")
            target = args.out_dir / f"page-{page_id}.json"
            if target.exists():
                raise FileExistsError(target)
            target.write_text(json.dumps(page, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            print(f"{page_id}\t{page['title']}\t{page['revision_id']}\t{len(page['slot_text'].encode('utf-8'))}")


if __name__ == "__main__":
    main()
