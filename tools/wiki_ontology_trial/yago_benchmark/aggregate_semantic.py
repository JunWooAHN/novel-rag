"""Join the two fixed semantic reviews to the final 100-unit candidate packets."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/analysis/private/yago-benchmark-100-20260928"
REVIEW_HASHES = {
    "semantic-001-050.json": "a7c63db087d616c29b5ffeb907f5c6683cf977dea76eeb5b2fd04326108291e5",
    "semantic-051-100.json": "33a46ff1b81fc58424f84aa8153d49cb00866151182973014e43b56e79f0f89c",
}
PACKET_HASH = "fb190384224eda3bc7abf9ae952f15b5177fbc4bf51dbe867cef1cfc17736b86"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest_path = DATA / "quality-packets-final/manifest.json"
    if sha(manifest_path) != PACKET_HASH:
        raise ValueError("Final packet manifest changed")
    manifest = json.loads(manifest_path.read_text())
    packets = {}
    for spec in manifest["files"]:
        path = manifest_path.parent / spec["path"]
        if sha(path) != spec["sha256"]:
            raise ValueError("Packet changed: " + spec["path"])
        for unit in json.loads(path.read_text())["units"]:
            if unit["rank"] in packets:
                raise ValueError("Duplicate packet rank")
            packets[unit["rank"]] = unit
    if set(packets) != set(range(1, 101)):
        raise ValueError("Packets do not cover exactly ranks 1-100")

    reviews = []
    for name, expected in REVIEW_HASHES.items():
        path = DATA / "quality-review" / name
        if sha(path) != expected:
            raise ValueError("Semantic review changed: " + name)
        body = json.loads(path.read_text())
        if (not body["review_status"].startswith("complete")
                or body["final_packet_manifest_sha256"] != PACKET_HASH
                or body["final_sqlite_sha256"] != manifest["new_sqlite_sha256"]):
            raise ValueError("Review does not bind to final packets/results")
        reviews += body["units"]
    if len(reviews) != 100 or {x["rank"] for x in reviews} != set(range(1, 101)):
        raise ValueError("Semantic reviews do not cover 100 unique ranks")

    counts = {name: {"verdicts": Counter(), "layers": Counter(),
                     "error_issue_types": Counter(), "candidate_status_verdicts": Counter(),
                     "important_omission_items": 0, "units_with_important_omission": 0,
                     "zero_candidate_ranks": [], "failed_ranks": []}
              for name in ("baseline_A", "baseline_B2", "YAGO_A", "YAGO_B2")}
    pair = Counter()
    for unit in sorted(reviews, key=lambda x: x["rank"]):
        rank = unit["rank"]
        source = packets[rank]
        if (unit["unit_id"] != source["unit_id"] or unit["target"] != source["target"]
                or unit["language"] != source["language"]
                or unit["source_ref"]["unit_sha256"] != source["unit_sha256"]):
            raise ValueError(f"Review source differs at rank {rank}")
        winner = unit["pair_preference"]["winner"].replace("YAGO-", "")
        if winner not in {"A", "B2", "tie", "undecidable"}:
            raise ValueError(f"Unknown pair verdict at rank {rank}")
        pair[winner] += 1
        for name in counts:
            arm = unit[name]
            is_new = name.startswith("YAGO_")
            arm_packet = source["arms"][name.replace("YAGO_", "YAGO-") if is_new
                                         else name.replace("baseline_", "")]
            status = arm["output_status"]
            if status != arm_packet["status"]:
                raise ValueError(f"Status differs at {rank}/{name}")
            candidates = (arm_packet.get("validated_candidates") or {}).get("candidates", [])
            review_items = arm["candidate_reviews"] if is_new else arm["candidate_verdicts"]
            reviewed_count = len(review_items) if is_new else sum(review_items.values())
            if len(candidates) != reviewed_count:
                raise ValueError(f"Candidate count differs at {rank}/{name}")
            omissions = arm.get("important_omissions", [])
            counts[name]["important_omission_items"] += len(omissions)
            counts[name]["units_with_important_omission"] += bool(omissions)
            if status == "failed":
                counts[name]["failed_ranks"].append(rank)
            elif not candidates:
                counts[name]["zero_candidate_ranks"].append(rank)
            if not is_new:
                counts[name]["verdicts"].update(review_items)
                counts[name]["layers"].update(c["payload"]["layer"] for c in candidates)
                continue
            by_ordinal = {c["ordinal"]: c for c in candidates}
            if len(by_ordinal) != len(candidates):
                raise ValueError(f"Duplicate candidate ordinal at {rank}/{name}")
            for review in review_items:
                ordinal = review["ordinal"]
                candidate = by_ordinal.pop(ordinal, None)
                if candidate is None:
                    raise ValueError(f"Missing candidate at {rank}/{name}/{ordinal}")
                payload = candidate["payload"]
                if (review["layer"] != payload["layer"]
                        or review["db_status"] != candidate["status"]):
                    raise ValueError(f"Layer/status differs at {rank}/{name}/{ordinal}")
                if is_new:
                    for key, expected_value in (
                        ("evidence_span_id", payload.get("evidence_span_id")),
                        ("evidence_start_byte", candidate.get("evidence_start_byte")),
                        ("evidence_end_byte", candidate.get("evidence_end_byte")),
                        ("source_quote", payload.get("evidence_quote")),
                    ):
                        if review.get(key) != expected_value:
                            raise ValueError(f"Evidence {key} differs at {rank}/{name}/{ordinal}")
                verdict = review["verdict"]
                if verdict not in {"supported", "material_error", "insufficient_context"}:
                    raise ValueError(f"Invalid verdict at {rank}/{name}/{ordinal}")
                counts[name]["verdicts"][verdict] += 1
                counts[name]["layers"][payload["layer"]] += 1
                counts[name]["candidate_status_verdicts"][(candidate["status"], verdict)] += 1
                if verdict == "material_error":
                    counts[name]["error_issue_types"].update(review.get("issue_types", []))
            if by_ordinal:
                raise ValueError(f"Unreviewed candidate at {rank}/{name}")

    def serialise(value):
        return {k: v for k, v in value.items()}

    result = {"schema": "yago-benchmark-semantic-aggregate-v1",
              "review_sha256": REVIEW_HASHES,
              "packet_manifest_sha256": PACKET_HASH,
              "result_sqlite_sha256": manifest["new_sqlite_sha256"],
              "unit_count": 100,
              "pair_preference_counts": serialise(pair),
              "arms": {}}
    for name, values in counts.items():
        result["arms"][name] = {
            "candidate_count": sum(values["verdicts"].values()),
            "verdict_counts": serialise(values["verdicts"]),
            "layer_counts": serialise(values["layers"]),
            "material_error_issue_type_mentions": serialise(values["error_issue_types"]),
            "candidate_status_verdict_counts": {
                f"{status}:{verdict}": n
                for (status, verdict), n in values["candidate_status_verdicts"].items()},
            "important_omission_items": values["important_omission_items"],
            "units_with_important_omission": values["units_with_important_omission"],
            "zero_candidate_ranks": values["zero_candidate_ranks"],
            "failed_ranks": values["failed_ranks"],
        }
    output = DATA / "semantic-aggregate-final.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: row["verdict_counts"] for name, row in result["arms"].items()}))


if __name__ == "__main__":
    main()
