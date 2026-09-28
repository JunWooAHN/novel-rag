"""Build a five-target, KG-only ledger from fixed YAGO 4.6 line captures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SELECTION_SHA = "45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0"
MANIFEST_SHA = "da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb"
TARGETS = {
    "Munjong of Joseon": "yago:Munjong_of_Joseon",
    "Danjong of Joseon": "yago:Danjong_of_Joseon",
    "Sejo of Joseon": "yago:Sejo_of_Joseon",
    "Hangul": "yago:Hangul",
    "Bloomery": "yago:Bloomery",
}
PRIORITY = {
    "rdf:type": 0, "rdfs:subClassOf": 0,
    "schema:birthDate": 1, "schema:deathDate": 2,
    "schema:startDate": 3, "yago:creator": 4,
    "yago:hasFather": 5, "yago:hasMother": 6,
    "schema:birthPlace": 7, "schema:deathPlace": 8,
    "schema:locationCreated": 9, "schema:spouse": 10,
    "schema:inLanguage": 11, "schema:nationality": 12,
}
FILES = {
    "facts": ("yago-4.6-facts.zip", "yago-facts.ttl"),
    "meta": ("yago-4.6-meta.zip", "yago-meta.ttl"),
    "taxonomy": ("yago-4.6-taxonomy.zip", "yago-taxonomy.ttl"),
}
SOURCE_KIND = {"facts": "yago_fact", "meta": "yago_meta", "taxonomy": "yago_taxonomy"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_capture(path: Path, kind: str, manifest: dict) -> list[dict]:
    zip_name, member_name = FILES[kind]
    member = next(e for e in manifest["files"][zip_name]["entries"] if e["path"] == member_name)
    result = []
    seen = set()
    for row in path.read_text().splitlines():
        number_text, raw = row.split(":", 1)
        number = int(number_text)
        if number < 1 or number in seen:
            raise ValueError(f"Bad or repeated {kind} line: {number}")
        seen.add(number)
        fields = raw.split("\t")
        if fields[-1] != ".":
            raise ValueError(f"Incomplete Turtle line: {kind}:{number}")
        result.append({"statement_id": f"{kind}:{number}", "source_kind": SOURCE_KIND[kind],
                       "source_file": f"extracted/{zip_name.removesuffix('.zip')}/{member_name}",
                       "source_file_sha256": member["sha256"], "line": number,
                       "raw": raw, "fields": fields})
    return result


def build(manifest_path: Path, selection_path: Path, captures: dict[str, Path]) -> dict:
    if digest(manifest_path.read_bytes()) != MANIFEST_SHA:
        raise ValueError("YAGO original manifest differs")
    if digest(selection_path.read_bytes()) != SELECTION_SHA:
        raise ValueError("Fixed source selection differs")
    manifest = json.loads(manifest_path.read_text())
    if manifest["status"] != "complete" or len(manifest["files"]) != 12:
        raise ValueError("YAGO release is incomplete")
    rows = {kind: read_capture(path, kind, manifest) for kind, path in captures.items()}
    meta_by_fact: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows["meta"]:
        fields = row["fields"]
        if len(fields) != 8 or fields[0] != "<<" or fields[4] != ">>":
            raise ValueError(f"Unexpected RDF-star shape: {row['statement_id']}")
        meta_by_fact.setdefault(tuple(fields[1:4]), []).append(row)
    targets = {}
    for label, yago_id in TARGETS.items():
        facts = []
        taxonomy = []
        for kind, selected in (("facts", facts), ("taxonomy", taxonomy)):
            for row in rows[kind]:
                fields = row["fields"]
                if len(fields) != 4:
                    raise ValueError(f"Unexpected Turtle shape: {row['statement_id']}")
                if fields[0] != yago_id:
                    continue
                annotations = meta_by_fact.get(tuple(fields[:3]), []) if kind == "facts" else []
                priority = PRIORITY.get(fields[1])
                rendered = None
                if priority is not None:
                    suffix = "".join(f";{meta['fields'][5]}={meta['fields'][6]}" for meta in annotations)
                    rendered = f"{row['statement_id']} {fields[0]} {fields[1]} {fields[2]}{suffix}"
                selected.append({k: v for k, v in row.items() if k != "fields"} | {
                    "subject": fields[0], "predicate": fields[1], "object": fields[2],
                    "meta": [{k: v for k, v in m.items() if k != "fields"} for m in annotations],
                    "prompt_priority": priority, "prompt_text": rendered,
                })
        eligible = sorted((s for s in facts + taxonomy if s["prompt_text"] is not None),
                          key=lambda s: (s["prompt_priority"], -bool(s["meta"]), s["statement_id"]))
        status = "entity_facts" if facts else "class_only" if taxonomy else "no_direct_fact"
        targets[label] = {"yago_id": yago_id, "mapping_status": status,
                          "direct_fact_count": len(facts), "taxonomy_statement_count": len(taxonomy),
                          "eligible_statement_ids": [s["statement_id"] for s in eligible],
                          "statements": facts + taxonomy}
    return {"schema": "yago-5-target-kg-only-v1", "release": manifest["release"],
            "yago_manifest_sha256": MANIFEST_SHA, "selection_sha256": SELECTION_SHA,
            "capture_sha256": {k: digest(v.read_bytes()) for k, v in captures.items()},
            "targets": targets}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    for kind in FILES:
        parser.add_argument(f"--{kind}-capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    captures = {kind: getattr(args, f"{kind}_capture") for kind in FILES}
    output = build(args.manifest, args.selection, captures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: {k: target[k] for k in ("mapping_status", "direct_fact_count",
                         "taxonomy_statement_count")}
                      for name, target in output["targets"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
