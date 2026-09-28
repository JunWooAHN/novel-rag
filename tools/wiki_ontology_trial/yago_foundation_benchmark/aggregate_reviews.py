"""Count only completed, source-linked reviews of the fixed foundation 100 trial."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import sqlite3


ROOT = Path("data/analysis/private/yago-foundation-100-20260928")
RUNS = {"A": "fixed100-YAGO-FOUNDATION-A-20260928",
        "B2": "fixed100-YAGO-FOUNDATION-B2-20260928"}
FINAL_DB_SHA = "6625d081ff4439ab7f0413a66997127a03b3d9d14fb9c3e7984c6d05bc88f2d7"
PACKET_SHA = "4c653f9128b09f27b5102459600c56d4daa14b1a98a57fd09bb785715ddf66f5"
VERDICTS = {"supported", "extraction_error", "insufficient_evidence"}
LINK_VERDICTS = {"justified_same", "justified_extends", "justified_conflicts",
                 "unsafe_same", "invalid", "insufficient"}
PREFLIGHT_SHA = "4fae0bec190a574377992bc02112cfe9bf44f2b0612b5b6c1f8b037979d3689b"
FOUNDATION_SHA = "640261c0eea9d3b064aba865f78c6d3c905098d63635fb8ea3deebfc0d551b14"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_completed_reviews() -> tuple[list[dict], list[dict]]:
    paths = [ROOT / "quality-review/semantic-001-050.json",
             ROOT / "quality-review/semantic-051-100.json"]
    reviews = [json.loads(path.read_text()) for path in paths]
    for path, review in zip(paths, reviews, strict=True):
        if review.get("complete") is not True or len(review.get("rows", [])) != 50:
            raise ValueError(f"Review incomplete; no final aggregate: {path}")
    if [row["rank"] for review in reviews for row in review["rows"]] != list(range(1, 101)):
        raise ValueError("Review rank denominator differs")
    return reviews, [{"path": str(path), "sha256": sha(path)} for path in paths]


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def checked_link_verdict(item: dict) -> str:
    verdict = item.get("verdict")
    if (not isinstance(verdict, str) or verdict not in LINK_VERDICTS
            or not nonempty(item.get("reason"))):
        raise ValueError("Link verdict/reason missing/unknown")
    return verdict


def zero_kind(value: object, *, status: str, candidate_count: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Zero judgement missing/unknown")
    tag, separator, explanation = value.partition(":")
    if separator and not explanation.strip():
        raise ValueError("Zero judgement explanation is empty")
    if value == "not_zero":
        kind = "not_zero"
    elif value == "justified_zero_categories_only_no_supported_HKB" or tag == "justified_zero":
        kind = "justified_zero"
    elif tag == "unjustified_zero":
        kind = "unjustified_zero"
    elif value == "contract_failure_not_zero":
        kind = "contract_failure_not_zero"
    elif value == "candidate_unjustified_zero_preferable":
        kind = "candidate_present_expected_zero"
    else:
        raise ValueError("Zero judgement missing/unknown")
    if ((kind == "not_zero" and (status != "validated" or candidate_count == 0))
            or (kind in {"justified_zero", "unjustified_zero"}
                and (status != "validated" or candidate_count != 0))
            or (kind == "contract_failure_not_zero" and status != "failed")
            or (kind == "candidate_present_expected_zero"
                and (status != "validated" or candidate_count == 0))):
        raise ValueError("Zero judgement conflicts with measured result")
    return kind


def main() -> None:
    reviews, inputs = load_completed_reviews()
    db_path = ROOT / "foundation-results-final.sqlite3"
    if sha(db_path) != FINAL_DB_SHA or sha(ROOT / "quality-packets-final/manifest.json") != PACKET_SHA:
        raise ValueError("Fixed result/packet SHA differs")
    preflight_path = ROOT / "preflight.json"
    foundation_path = ROOT / "foundation.sqlite3"
    if sha(preflight_path) != PREFLIGHT_SHA or sha(foundation_path) != FOUNDATION_SHA:
        raise ValueError("Fixed preflight/foundation SHA differs")
    preflight = json.loads(preflight_path.read_text())
    prep_rows = preflight["units"]
    if (preflight["unit_count"] != 100 or len(prep_rows) != 100
            or len({x["unit_id"] for x in prep_rows}) != 100):
        raise ValueError("Preflight unit denominator differs")
    residual_ranks = [i for i, x in enumerate(prep_rows, 1) if x["residual_mode"]]
    fallback_ranks = [i for i, x in enumerate(prep_rows, 1) if not x["residual_mode"]]
    displayed = [sid for row in prep_rows for sid in row["displayed_statement_ids"]]
    if (len(residual_ranks), fallback_ranks, len(displayed), len(set(displayed))) != (99, [62], 870, 44):
        raise ValueError("Preflight residual/displayed denominators differ")
    with sqlite3.connect(f"file:{foundation_path}?mode=ro", uri=True) as foundation:
        foundation_ids = {row[0] for row in foundation.execute("SELECT statement_id FROM structural_assertion")}
    if len(foundation_ids) != 50 or not set(displayed).issubset(foundation_ids):
        raise ValueError("Foundation assertion/displayed ID denominator differs")
    counts = {arm: {"candidate_verdicts": collections.Counter(),
                    "link_verdicts": collections.Counter(),
                    "link_mechanical_status": collections.Counter(),
                    "zero_judgements": collections.Counter(),
                    "observed_output_status": collections.Counter(),
                    "important_omission_items": 0,
                    "important_omission_units": 0,
                    "candidate_rows": 0,
                    "link_rows": 0,
                    "raw_same_without_candidate": 0,
                    "raw_same_with_candidate": 0,
                    "reviewed_units": 0} for arm in RUNS}
    pair = collections.Counter()
    packet_units = {}
    manifest = json.loads((ROOT / "quality-packets-final/manifest.json").read_text())
    for item in manifest["files"]:
        path = ROOT / "quality-packets-final" / item["name"]
        if sha(path) != item["sha256"]:
            raise ValueError("Review packet SHA differs")
        packet = json.loads(path.read_text())
        for unit in packet["units"]:
            if unit["unit_id"] in packet_units:
                raise ValueError("Repeated packet unit")
            packet_units[unit["unit_id"]] = unit
    if len(packet_units) != 100:
        raise ValueError("Packet source denominator differs")
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Results SQLite quick_check failed")
        for review_index, review in enumerate(reviews):
            pins = review["source_hashes"]
            if review_index == 0:
                if (pins["final_packet_manifest_sha256"] != PACKET_SHA
                        or pins["final_output_sqlite_sha256"] != FINAL_DB_SHA):
                    raise ValueError("1–50 final source pins differ")
                source_hash_key, span_key, mechanical_key, status_key = (
                    "unit_sha256", "evidence_span_id", "mechanical_status", "raw_status")
            else:
                if (pins["final_packet_manifest_sha256"] != PACKET_SHA
                        or pins["final_sqlite_sha256"] != FINAL_DB_SHA
                        or review["completed_A_ranks"] != list(range(51, 101))
                        or review["completed_B2_ranks"] != list(range(51, 101))):
                    raise ValueError("51–100 final source pins/completed ranks differ")
                source_hash_key, span_key, mechanical_key, status_key = (
                    "source_unit_sha256", "span_id", "machine_status", "status")
            for unit in review["rows"]:
                packet = packet_units[unit["unit_id"]]
                if (packet["rank"] != unit["rank"] or packet["unit_sha256"] !=
                        unit[source_hash_key]):
                    raise ValueError("Reviewed source identity differs")
                preference = unit["pair_preference"]
                value = preference["preferred" if review_index == 0 else "winner"]
                pair_map = {"FOUNDATION-A": "A", "FOUNDATION-B2": "B2", "A": "A", "B2": "B2", "tie": "tie"}
                if value not in pair_map:
                    raise ValueError("Pair preference missing/unknown")
                pair[pair_map[value]] += 1
                for arm, run_id in RUNS.items():
                    arm_review = unit["arms"][arm]
                    if review_index == 0:
                        if arm_review["review_complete"] is not True:
                            raise ValueError("1–50 arm review incomplete")
                    elif arm_review["arm_key"] != f"FOUNDATION-{arm}":
                        raise ValueError("51–100 review used a previous arm key")
                    result = db.execute("SELECT * FROM results WHERE run_id=? AND unit_id=?",
                                        (run_id, unit["unit_id"])).fetchone()
                    if result is None or arm_review.get("raw_sha256") != result["raw_sha256"]:
                        raise ValueError("Raw response SHA differs from review")
                    if arm_review.get("response_sha256") != result["response_sha256"]:
                        raise ValueError("HTTP response SHA differs from review")
                    if arm_review[status_key] != result["status"]:
                        raise ValueError("Reviewed arm status differs")
                    checked = json.loads(result["validation_json"])["candidates"] if result["validation_json"] else []
                    candidate_reviews = arm_review["candidate_reviews"]
                    if len(candidate_reviews) != len(checked):
                        raise ValueError("Candidate review denominator differs")
                    tally = counts[arm]
                    tally["reviewed_units"] += 1
                    tally["candidate_rows"] += len(candidate_reviews)
                    for ordinal, (item, candidate) in enumerate(zip(candidate_reviews, checked, strict=True)):
                        payload = candidate["payload"]
                        if (item.get("ordinal") != ordinal or item.get("layer") != payload.get("layer")
                                or item.get("predicate") != payload.get("predicate")
                                or item.get("evidence_span_id") != payload.get("evidence_span_id")
                                or item.get("evidence_quote") != payload.get("evidence_quote")):
                            raise ValueError("Candidate ordinal/source fields differ")
                        verdict = item.get("verdict")
                        if not isinstance(verdict, str) or verdict not in VERDICTS:
                            raise ValueError("Candidate verdict missing/unknown")
                        if not nonempty(item.get("reason")):
                            raise ValueError("Candidate review reason missing")
                        tally["candidate_verdicts"][verdict] += 1
                    proposals = db.execute("SELECT * FROM foundation_link_proposal WHERE run_id=? AND unit_id=? "
                                           "ORDER BY link_index", (run_id, unit["unit_id"])).fetchall()
                    links = arm_review["foundation_link_reviews"]
                    if len(links) != len(proposals):
                        raise ValueError("Link review denominator differs")
                    tally["link_rows"] += len(links)
                    for index, (item, proposal) in enumerate(zip(links, proposals, strict=True)):
                        raw = json.loads(proposal["raw_json"])
                        if (item.get("link_index") != index or item.get("statement_id") != raw.get("statement_id")
                                or item.get("relation") != raw.get("relation")
                                or item.get("candidate_ordinal") != raw.get("candidate_ordinal")
                                or item.get("source_claim") != raw.get("source_claim")
                                or item[span_key] != raw.get("evidence_span_id")
                                or item[mechanical_key] != proposal["status"]):
                            raise ValueError("Link review differs from raw proposal")
                        tally["link_verdicts"][checked_link_verdict(item)] += 1
                        tally["link_mechanical_status"][proposal["status"]] += 1
                        if raw.get("relation") == "same":
                            tally["raw_same_without_candidate" if raw.get("candidate_ordinal") is None
                                  else "raw_same_with_candidate"] += 1
                    omissions = arm_review.get("important_omissions")
                    if not isinstance(omissions, list):
                        raise ValueError("Omission audit missing")
                    if review_index == 0:
                        if any(not isinstance(item, dict) or not nonempty(item.get("reason")) for item in omissions):
                            raise ValueError("1–50 omission reason missing")
                        audit = arm_review.get("source_relation_audit")
                        if (not isinstance(audit, dict) or any(not nonempty(audit.get(key))
                                for key in ("observed", "covered", "omitted"))):
                            raise ValueError("1–50 source relation audit missing")
                    else:
                        if any(not nonempty(item) for item in omissions):
                            raise ValueError("51–100 omission reason missing")
                        if not nonempty(arm_review.get("source_relation_audit")):
                            raise ValueError("51–100 source relation audit missing")
                    tally["important_omission_items"] += len(omissions)
                    tally["important_omission_units"] += bool(omissions)
                    tally["zero_judgements"][zero_kind(arm_review.get("zero_judgement"),
                                                        status=result["status"],
                                                        candidate_count=len(checked))] += 1
                    tally["observed_output_status"][
                        "failed" if result["status"] == "failed" else
                        "validated_zero_candidate" if not checked else "validated_nonzero_candidate"] += 1
    if any(tally["reviewed_units"] != 100 for tally in counts.values()):
        raise ValueError("Reviewed unit denominator differs")
    if (counts["A"]["candidate_rows"], counts["B2"]["candidate_rows"]) != (542, 540):
        raise ValueError("Official validated candidate denominators differ")
    if (counts["A"]["link_rows"], counts["B2"]["link_rows"]) != (105, 96):
        raise ValueError("Raw link proposal denominators differ")
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        failed = db.execute("SELECT rank,status,raw_text FROM results WHERE run_id=? AND rank=61",
                            (RUNS["B2"],)).fetchone()
    if failed is None or failed[0] != 61 or failed[1] != "failed":
        raise ValueError("B2 rank61 failure differs")
    raw_candidates = json.loads(failed[2]).get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) != 11:
        raise ValueError("B2 failed raw candidate count differs")
    out = {"schema": "yago-foundation-semantic-aggregate-v1", "fixed_results_sha256": FINAL_DB_SHA,
           "fixed_packets_sha256": PACKET_SHA, "semantic_reviews": inputs,
           "foundation_unique_assertions": 50,
           "preflight_denominators": {"source_units": len(prep_rows), "residual_mode_units": len(residual_ranks),
                                      "fallback_ranks": fallback_ranks,
                                      "displayed_statement_occurrences": len(displayed),
                                      "distinct_displayed_statement_ids": len(set(displayed)),
                                      "foundation_structural_assertions_not_displayed": len(foundation_ids-set(displayed))},
           "B2_failed_raw_audit": {"rank": failed[0], "official_candidate_contribution": 0,
                                   "raw_unvalidated_candidates": len(raw_candidates)},
           "denominator_note": "KG 50 unique structural assertions; A/B2 candidate and link counts are per-arm proposals, not historical truth or global distinct claims. B2 failed rank61 raw 11 candidates are separate from official 540 validated candidates.",
           "arm_counts": {arm: {key: dict(value) if isinstance(value, collections.Counter) else value
                                for key, value in tally.items()} for arm, tally in counts.items()},
           "pair_preference": dict(pair)}
    path = ROOT / "semantic-aggregate-final.json"
    if path.exists():
        raise ValueError("Final semantic aggregate already exists; never overwrite")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"path": str(path), "sha256": sha(path),
                      "A": out["arm_counts"]["A"], "B2": out["arm_counts"]["B2"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
