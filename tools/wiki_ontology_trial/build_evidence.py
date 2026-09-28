"""Freeze a handful of extra source excerpts for the paired 31B trial."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


WIKI_SELECTIONS = {
    2402602: [(
        "Munjong died on 10 June 1452",
        "who became [[Sejo of Joseon|King Sejo]].",
        "Death and succession in the same pinned article",
    )],
    3121209: [
        (
            "| succession        = [[List of kings of Joseon|King of Joseon]]",
            "| coronation        = 14 June 1452",
            "King's reign and separate coronation in the infobox",
        ),
        (
            "Initially, Sejo was hesitant to execute Danjong",
            "Sejo is not directly responsible for his death.",
            "Conflicting accounts of Danjong's death; no forced single cause",
        ),
    ],
    3131532: [(
        "In order to court the support of the [[Ming dynasty]]",
        "then sentencing him to death.",
        "1453 coup actors and affected people, distinct from 1455 abdication",
    )],
    42538288: [
        (
            "Hangul was first introduced, likely in a mostly complete form",
            "the first ever piece of Hangul literature.",
            "Introduction to court versus subsequent applications",
        ),
        (
            "In the 9th month of 1446",
            "''[[Hunminjeongeum Haerye]].",
            "Publication by explanatory texts; article markup retained exactly",
        ),
    ],
}


WEB_EXCERPTS = [
    {
        "url": "https://www.hangeul.go.kr/exhi/dailyExhibition.do?curr_menu_cd=0102010000",
        "title": "훈민정음, 천년의 문자 계획", "publisher": "National Hangeul Museum",
        "text": "1443년 세종은 우리의 문자 ‘훈민정음’을 만들었습니다.1446년에는 새 문자를 만든 목적과 원리를 밝힌 책 『훈민정음』을 만들었고,",
        "context_summary": "Museum page distinguishes the script's creation from the later explanatory book; the excerpt does not date an audience or day.",
    },
    {
        "url": "https://www.unesco.org/en/memory-world/hunminjeongum-manuscript?hub=1081",
        "title": "Hunminjeongum Manuscript", "publisher": "UNESCO",
        "text": "The manuscript published in the ninth lunar month of 1446",
        "context_summary": "UNESCO describes the manuscript; this excerpt concerns manuscript publication, not the script's creation.",
    },
    {
        "url": "https://www.unesco.org/en/memory-world/hunminjeongum-manuscript?hub=1081",
        "title": "Hunminjeongum Manuscript", "publisher": "UNESCO",
        "text": "(reigned 1418-1450)",
        "context_summary": "This is Sejong's reign interval, not the date of creating Hangul.",
    },
    {
        "url": "https://www.unesco.org/en/memory-world/hunminjeongum-manuscript?hub=1081",
        "title": "Hunminjeongum Manuscript", "publisher": "UNESCO",
        "text": "the development of which he completed in 1443.",
        "context_summary": "In the directly read UNESCO page this phrase refers to the script's development; it is a separate non-contiguous excerpt.",
    },
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--pages", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    packet = json.loads(args.packet.read_bytes())
    by_page = {unit["page_id"]: unit for unit in packet["units"]}
    extra: dict[str, list[dict]] = {unit["source_unit_id"]: [] for unit in packet["units"]}
    for page_id, selections in WIKI_SELECTIONS.items():
        unit = by_page[page_id]
        page = json.loads((args.pages / f"page-{page_id}.json").read_bytes())
        if (page["revision_id"] != unit["revision_id"]
                or sha(page["slot_text"].encode("utf-8")) != unit["slot_text_sha256"]):
            raise ValueError(f"Pinned page differs: {page_id}")
        full = page["slot_text"]
        raw = full.encode("utf-8")
        for beginning, ending, reason in selections:
            start_char = full.index(beginning)
            end_char = full.index(ending, start_char) + len(ending)
            start = len(full[:start_char].encode("utf-8"))
            end = len(full[:end_char].encode("utf-8"))
            text = raw[start:end].decode("utf-8")
            identifier = "wiki-extra-" + sha(
                f"{page_id}:{page['revision_id']}:{start}:{end}".encode())[:16]
            extra[unit["source_unit_id"]].append({
                "source_id": identifier, "kind": "same_wiki_revision",
                "snapshot_id": unit["snapshot_id"], "shard_file": unit["shard_file"],
                "shard_sha256": unit["shard_sha256"], "page_id": page_id,
                "revision_id": page["revision_id"], "slot_role": "main",
                "slot_text_sha256": unit["slot_text_sha256"],
                "slot_span_utf8": [start, end], "source_sha256": sha(text.encode("utf-8")),
                "text": text, "context_summary": reason,
            })
    hangul = by_page[42538288]["source_unit_id"]
    for excerpt in WEB_EXCERPTS:
        item = dict(excerpt)
        item["source_id"] = "web-extra-" + sha(
            (item["url"] + "\n" + item["text"]).encode("utf-8"))[:16]
        item["kind"] = "external_source_directly_read_by_root"
        item["retrieved_date"] = "2026-09-27"
        item["source_sha256"] = sha(item["text"].encode("utf-8"))
        extra[hangul].append(item)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(extra, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_units": len(extra),
                      "extra_snippets": sum(map(len, extra.values())),
                      "extra_bytes": sum(len(i["text"].encode("utf-8")) for x in extra.values() for i in x)}))


if __name__ == "__main__":
    main()
