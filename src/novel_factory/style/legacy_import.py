"""Validate and normalize the two frozen reverse-review corpora before one DB commit.

File input is permitted only for this explicit migration. Consumer reads never
fall back to these files after a release is imported.
"""
from __future__ import annotations

import hashlib
import base64
import json
from pathlib import Path
import sqlite3

from novel_factory.style.sqlite_store import SQLiteAnalysisStore, _sha
from novel_factory.style.legacy_sqlite import SQLiteLegacyStore


IMPORT_ID = "reverse-20260925-i1"
EXPECTED_ARTIFACT_FINGERPRINT = "1f5519ec2644b8865503dd8f5e0ea64cadff6c64909e996e646d96f02ed5f01b"
SPLITS = ("train", "development_validation", "development_holdout")
EXPECTED = {"initial": {"selections": 30, "attempts": 150, "candidates": 152,
                        "accepted": 150, "hold": 2, "attempt_hold": 2},
            "full": {"selections": 144, "attempts": 144, "candidates": 141,
                     "accepted": 122, "hold": 19, "attempt_hold": 3}}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes, label: str) -> dict:
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError(f"legacy object expected: {label}")
    return result


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _artifact_snapshot(roots: dict[str, Path]) -> tuple[list[tuple], dict[tuple[str, str], bytes]]:
    artifacts, lookup = [], {}
    for release, root in roots.items():
        _require(root.is_dir(), f"legacy root missing: {root}")
        for path in sorted(root.rglob("*")):
            if not path.is_file() or "private/viewer/" in path.relative_to(root).as_posix():
                continue
            relative = path.relative_to(root).as_posix()
            raw = path.read_bytes()
            lookup[release, relative] = raw
            artifacts.append((release, relative, sha(raw), raw))
    return artifacts, lookup


def _from(lookup: dict, release: str, path: str) -> tuple[dict, bytes]:
    try:
        raw = lookup[release, path]
    except KeyError as exc:
        raise ValueError(f"frozen legacy artifact missing: {release}/{path}") from exc
    return _json(raw, f"{release}/{path}"), raw


def _source_pin(conn: sqlite3.Connection, work: str, manifest_work: dict) -> None:
    SQLiteAnalysisStore._pin(conn, work, manifest_work["source_revision_id"],
                             manifest_work["source_sha256"], manifest_work["segmentation_id"])
    source = conn.execute("SELECT byte_size,codepoint_length FROM source_revisions WHERE id=?",
                          (manifest_work["source_revision_id"],)).fetchone()
    _require(source is not None and (source[0], source[1]) ==
             (manifest_work["source_bytes"], manifest_work["source_codepoints"]),
             f"source revision size differs: {work}")


def _decision_sets(decision: dict, candidates: list[dict], label: str) -> dict[str, str]:
    ids = [c.get("candidate_id") for c in candidates]
    _require(len(ids) == len(set(ids)) and all(isinstance(x, str) and x for x in ids),
             f"duplicate candidate ID: {label}")
    result = {}
    for status, key in (("accepted", "accepted_candidate_ids"),
                        ("hold", "hold_candidate_ids"),
                        ("rejected", "rejected_candidate_ids")):
        for cid in decision.get(key, []):
            _require(cid not in result, f"multiple candidate decisions: {label}/{cid}")
            result[cid] = status
    _require(set(result) == set(ids), f"unaccounted candidate decision: {label}")
    return result


def _split_for_initial(policy: dict, work: str, batch: dict) -> bool:
    lo, hi = min(u["section_order"] for u in batch["units"]), max(u["section_order"] for u in batch["units"])
    return any(s["name"] == batch["split"] and
               s["section_order_start"] <= lo <= hi <= s["section_order_end"]
               for s in policy["works"][work]["splits"])


def _validate_export_record(record: dict, candidate: dict, selection: tuple,
                            reviewer: str, answer: str) -> None:
    release, selection_id, work, role, split, _, source_sha, segmentation, _, _, _, _ = selection
    metadata = record.get("metadata", {})
    cid = candidate["candidate_id"]
    _require((record.get("sample_id"), metadata.get("work_id"), metadata.get("role"),
              metadata.get("split"), metadata.get("source_sha256"),
              metadata.get("segmentation_id"), metadata.get("answer_start_cp"),
              metadata.get("answer_end_cp"), metadata.get("reviewed_by")) ==
             (cid, work, role, split, source_sha, segmentation,
              candidate["answer_start_cp"], candidate["answer_end_cp"], reviewer),
             f"export metadata differs from reviewed candidate: {release}/{cid}")
    _require(metadata.get("answer_sha256") == _sha(answer),
             f"export target SHA differs: {release}/{cid}")
    model_input = candidate["writer_input"] if role == "gemma_style" else candidate["planner_input"]
    expected_user = json.dumps(model_input, ensure_ascii=False, sort_keys=True)
    expected_assistant = (answer if role == "gemma_style" else
                          json.dumps(candidate["plan_target"], ensure_ascii=False, sort_keys=True))
    _require(record.get("messages") == [{"role": "user", "content": expected_user},
                                          {"role": "assistant", "content": expected_assistant}],
             f"export content differs from accepted candidate: {release}/{cid}")
    _require(expected_assistant not in expected_user,
             f"target leaked into model input: {release}/{cid}")


def build_bundle(db_path: Path | str, roots: dict[str, Path],
                 *, import_id: str = IMPORT_ID, expected: dict = EXPECTED,
                 expected_fingerprint: str | None = EXPECTED_ARTIFACT_FINGERPRINT) -> dict:
    """Read immutable legacy files and DB source metadata; return no model-visible text."""
    _require(set(roots) == {"initial", "full"}, "both legacy release roots are required")
    artifacts, lookup = _artifact_snapshot(roots)
    fingerprint = sha("".join(f"{r}/{p}:{h}\n" for r, p, h, _ in artifacts).encode())
    if expected_fingerprint is not None:
        _require(fingerprint == expected_fingerprint,
                 "frozen legacy artifact path/hash inventory differs")
    bundle = {"import_id": import_id, "fingerprint": fingerprint,
              "artifacts": artifacts, "selections": [], "attempts": [],
              "candidates": [], "rows": [], "review_revisions": [], "source_hashes": {},
              "selection_policy_hashes": {}, "accepted_count": 0}
    candidate_index: dict[tuple[str, str], tuple[dict, tuple, str]] = {}
    read_db = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    try:
        for release in ("initial", "full"):
            manifest, manifest_raw = _from(lookup, release, "source-manifest.json")
            policy, policy_raw = _from(lookup, release, "split-policy.json")
            _require(policy["source_manifest_sha256"] == sha(manifest_raw),
                     f"manifest/policy SHA differs: {release}")
            bundle["selection_policy_hashes"][release] = sha(policy_raw)
            for work, source in manifest["works"].items():
                _source_pin(read_db, work, source)
                previous = bundle["source_hashes"].setdefault(work, source["source_sha256"])
                _require(previous == source["source_sha256"], f"source changed between releases: {work}")
            folder = "batches" if release == "initial" else "windows"
            paths = sorted(p for r, p in lookup if r == release and
                           p.startswith(f"private/{folder}/") and p.endswith(".json"))
            for path in paths:
                selection, _ = _from(lookup, release, path)
                sid = selection["batch_id"] if release == "initial" else selection["window_id"]
                work = selection["work_id"]
                source = manifest["works"][work]
                role, split = source["role"], selection["split"]
                _require((selection["source_sha256"], selection["segmentation_id"],
                          selection["role"], split) ==
                         (source["source_sha256"], source["segmentation_id"],
                          role, split) and split in SPLITS,
                         f"selection source/role/split differs: {release}/{sid}")
                if release == "initial":
                    _require(_split_for_initial(policy, work, selection),
                             f"initial split differs: {sid}")
                    start, end = selection["excerpt_start_cp"], selection["excerpt_end_cp"]
                else:
                    band = policy["works"][work]["bands"][selection["band"] - 1]
                    _require(band["split"] == split and
                             band["start_cp"] <= selection["start_cp"] < selection["end_cp"] <= band["end_cp"],
                             f"full band/split differs: {sid}")
                    start, end = selection["start_cp"], selection["end_cp"]
                    _require(_sha(SQLiteAnalysisStore._span_text(read_db, source["segmentation_id"],
                              start, end)) == selection["window_sha256"],
                             f"full window DB span differs: {sid}")
                _require(0 <= start < end <= source["source_codepoints"],
                         f"selection CP span invalid: {release}/{sid}")
                review, raw_review = _from(lookup, release, f"private/reviews/{sid}.json")
                decision, raw_decision = _from(lookup, release, f"private/decisions/{sid}.json")
                _require((review.get("work_id"), review.get("source_sha256"),
                          review.get("segmentation_id")) ==
                         (work, source["source_sha256"], source["segmentation_id"]),
                         f"review pin differs: {release}/{sid}")
                key = "batch_id" if release == "initial" else "window_id"
                _require(review.get(key) == sid and decision.get(key) == sid and
                         decision.get("review_sha256") == sha(raw_review) and
                         bool(decision.get("reviewer")),
                         f"independent decision/review SHA differs: {release}/{sid}")
                selected = (release, sid, work, role, split, source["source_revision_id"],
                            source["source_sha256"], source["segmentation_id"], start, end,
                            sha(raw_review), sha(raw_decision))
                bundle["selections"].append(selected)
                candidates = review.get("candidates", [])
                decisions = _decision_sets(decision, candidates, f"{release}/{sid}")
                candidate_ids = {c["candidate_id"] for c in candidates}
                attempt_ids = set()
                referenced_ids = set()
                for attempt in review.get("attempts", []):
                    akey = (str(attempt["section_order"]) if release == "initial" else sid)
                    _require(akey not in attempt_ids and attempt["status"] in ("proposed", "hold", "reject"),
                             f"invalid/duplicate attempt: {release}/{sid}/{akey}")
                    attempt_ids.add(akey)
                    ids = attempt.get("candidate_ids", [])
                    _require(isinstance(ids, list) and len(ids) == len(set(ids)) and
                             set(ids) <= candidate_ids,
                             f"attempt candidate IDs duplicate/unknown: {release}/{sid}/{akey}")
                    referenced_ids.update(ids)
                    _require(bool(ids) == (attempt["status"] == "proposed"),
                             f"attempt candidate status differs: {release}/{sid}/{akey}")
                    if release == "initial":
                        units = [u for u in selection["units"] if u["section_order"] == int(akey)]
                        _require(len(units) == 1, f"frozen section unit missing: {sid}/{akey}")
                        unit = units[0]
                        aa, bb, expected_sha = unit["start_cp"], unit["end_cp"], unit["text_sha256"]
                    else:
                        _require(attempt.get("portion") in ("primary", "alternative"),
                                 f"frozen window portion missing: {sid}")
                        portion = selection[attempt["portion"]]
                        aa, bb = portion["start_cp"], portion["end_cp"]
                        expected_sha = _sha(SQLiteAnalysisStore._span_text(
                            read_db, source["segmentation_id"], aa, bb))
                    _require(start <= aa < bb <= end and
                             _sha(SQLiteAnalysisStore._span_text(read_db, source["segmentation_id"],
                                                                  aa, bb)) == expected_sha,
                             f"attempt unit DB span differs: {release}/{sid}/{akey}")
                    bundle["attempts"].append((release, sid, akey, attempt["status"],
                        attempt.get("reason", ""), attempt.get("portion") if release == "full" else None,
                        aa, bb, expected_sha,
                        json.dumps(ids, ensure_ascii=False, separators=(",", ":"))))
                _require(len(attempt_ids) == (len(selection["units"]) if release == "initial" else 1),
                         f"attempt unit accounting differs: {release}/{sid}")
                _require(referenced_ids == candidate_ids,
                         f"review candidate lacks attempt: {release}/{sid}")
                for candidate in candidates:
                    cid = candidate["candidate_id"]
                    a, b = candidate["answer_start_cp"], candidate["answer_end_cp"]
                    pa, pb = candidate["prior_start_cp"], candidate["prior_end_cp"]
                    _require(start <= pa <= pb <= a < b <= end and
                             candidate["review_record"].get("leakage_check") == "pass",
                             f"candidate CP/leakage validation differs: {release}/{cid}")
                    if release == "full":
                        portion = selection[review["attempts"][0]["portion"]]
                        _require(portion["start_cp"] <= pa <= pb <= a < b <= portion["end_cp"],
                                 f"candidate escaped full portion: {cid}")
                    else:
                        covered = candidate["covered_section_orders"]
                        linked = {a["section_order"] for a in review["attempts"]
                                  if cid in a.get("candidate_ids", [])}
                        _require(bool(covered) and set(covered) == linked and
                                 len(covered) == len(set(covered)),
                                 f"candidate section coverage differs: {cid}")
                    index_key = (release, cid)
                    _require(index_key not in candidate_index, f"same candidate ID repeated: {cid}")
                    candidate_index[index_key] = (candidate, selected, decision["reviewer"])
                    bundle["candidates"].append((release, sid, cid, decisions[cid], a, b, pa, pb,
                        json.dumps(candidate, ensure_ascii=False, sort_keys=True)))
        revisions = sorted(p for r, p in lookup if r == "full" and
                           p.startswith("private/review-revisions/") and p.endswith(".json"))
        revision_edges: dict[str, dict[str, str]] = {}
        for path in revisions:
            revision, _ = _from(lookup, "full", path)
            previous = base64.b64decode(revision["previous_review_base64"], validate=True)
            previous_record = _json(previous, f"review revision previous/{path}")
            _require(sha(previous) == revision["previous_review_sha256"] and
                     previous_record.get("window_id") == revision["window_id"] and
                     bool(revision.get("correction_reason")) and
                     revision["window_id"] in {s[1] for s in bundle["selections"] if s[0] == "full"},
                     f"review revision old SHA/selection differs: {path}")
            old_sha, new_sha, wid = (revision["previous_review_sha256"],
                                     revision["new_review_sha256"], revision["window_id"])
            _require(path == f"private/review-revisions/{wid}/{old_sha}-{new_sha}.json" and
                     len(old_sha) == len(new_sha) == 64,
                     f"review revision path/SHA differs: {path}")
            edges = revision_edges.setdefault(wid, {})
            _require(old_sha not in edges, f"review revision branches: {wid}")
            edges[old_sha] = new_sha
            bundle["review_revisions"].append(("full", revision["window_id"], path,
                revision["previous_review_sha256"], revision["new_review_sha256"],
                revision["correction_reason"]))
        final_sha = {s[1]: s[10] for s in bundle["selections"] if s[0] == "full"}
        for wid, edges in revision_edges.items():
            roots = set(edges) - set(edges.values())
            _require(len(roots) == 1, f"review revision has no unique origin: {wid}")
            cursor, visited = next(iter(roots)), set()
            while cursor in edges and cursor not in visited:
                visited.add(cursor)
                cursor = edges[cursor]
            _require(len(visited) == len(edges) and cursor == final_sha[wid],
                     f"review revision chain does not end at current review: {wid}")
        accepted = {(r, cid) for r, _, cid, status, *_ in bundle["candidates"] if status == "accepted"}
        seen_rows: set[tuple[str, str]] = set()
        for release in ("initial", "full"):
            for work in sorted(bundle["source_hashes"]):
                for split in SPLITS:
                    path = f"private/export/{work}/{split}.jsonl"
                    try:
                        raw_file = lookup[release, path]
                    except KeyError as exc:
                        raise ValueError(f"legacy JSONL missing: {release}/{path}") from exc
                    _require(not raw_file or raw_file.endswith(b"\n"),
                             f"legacy JSONL missing trailing newline: {release}/{path}")
                    lines = raw_file.splitlines()
                    for ordinal, raw_line in enumerate(lines, 1):
                        record = _json(raw_line, f"{release}/{path}:{ordinal}")
                        cid = record.get("sample_id")
                        key = (release, cid)
                        _require(key in accepted and key not in seen_rows,
                                 f"export row is not one accepted candidate: {release}/{cid}")
                        seen_rows.add(key)
                        candidate, selection, reviewer = candidate_index[key]
                        answer = SQLiteAnalysisStore._span_text(read_db, selection[7],
                            candidate["answer_start_cp"], candidate["answer_end_cp"])
                        _validate_export_record(record, candidate, selection, reviewer, answer)
                        _require((selection[2], selection[4]) == (work, split),
                                 f"export path differs from candidate role: {release}/{cid}")
                        bundle["rows"].append((release, work, split, ordinal, cid, raw_line, sha(raw_line)))
                    report, _ = _from(lookup, release, "quality-report.json")
                    _require(sha(raw_file) == report["works"][work][split]["jsonl_sha256"],
                             f"quality report/JSONL SHA differs: {release}/{work}/{split}")
        _require(seen_rows == accepted, "accepted candidates and export rows are not identical")
        bundle["accepted_count"] = len(accepted)
        for release, required in expected.items():
            selections = [x for x in bundle["selections"] if x[0] == release]
            attempts = [x for x in bundle["attempts"] if x[0] == release]
            candidates = [x for x in bundle["candidates"] if x[0] == release]
            counts = {"selections": len(selections), "attempts": len(attempts),
                      "candidates": len(candidates),
                      "accepted": sum(x[3] == "accepted" for x in candidates),
                      "hold": sum(x[3] == "hold" for x in candidates),
                      "attempt_hold": sum(x[3] == "hold" and x[9] == "[]" for x in attempts)}
            _require(counts == required, f"legacy normalized count differs: {release}/{counts}")
        return bundle
    finally:
        read_db.close()


def import_legacy_release(db_path: Path | str, initial_root: Path | str,
                          full_root: Path | str, import_id: str = IMPORT_ID) -> dict:
    bundle = build_bundle(db_path, {"initial": Path(initial_root), "full": Path(full_root)},
                          import_id=import_id)
    return SQLiteLegacyStore(db_path).import_bundle(bundle)
