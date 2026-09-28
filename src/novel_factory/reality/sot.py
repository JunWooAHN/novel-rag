"""Deterministic, bounded YAGO-to-RealityRelease mapping and temporal queries."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date
from pathlib import Path


FOUNDATION_SHA = "640261c0eea9d3b064aba865f78c6d3c905098d63635fb8ea3deebfc0d551b14"
MAPPING_POLICY = "yago5-deterministic-v1"
MAPPING_POLICY_V2 = "yago5-deterministic-v2"
MAPPING_POLICY_V3 = "yago5-temporal-context-v1"
QUERY_POLICY = "nominal-temporal-v1"
QUERY_POLICY_V3 = "nominal-temporal-context-v1"
RELEASE_ID = "reality:yago46:five:" + FOUNDATION_SHA[:16]
RELEASE_ID_V2 = RELEASE_ID + ":r2"
RELEASE_ID_V3 = RELEASE_ID + ":r3"
DATE_LITERAL = re.compile(r'^"(\d{4}(?:-\d{2}-\d{2})?)"\^\^xsd:(date|gYear)$')
YEAR = re.compile(r"^\d{4}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1")]


def parse_time(raw: str | None) -> dict:
    """Preserve YAGO lexical type; normalized dates are only nominal comparisons."""
    result = {"raw": raw, "precision": "unknown", "calendar": "unknown",
              "nominal_start": None, "nominal_end": None}
    match = DATE_LITERAL.fullmatch(raw or "")
    if match is None:
        return result
    value, typ = match.groups()
    try:
        if typ == "date" and DAY.fullmatch(value):
            date.fromisoformat(value)
            result.update(precision="day", nominal_start=value, nominal_end=value)
        elif typ == "gYear" and YEAR.fullmatch(value):
            date(int(value), 1, 1)
            result.update(precision="year", nominal_start=value + "-01-01",
                          nominal_end=value + "-12-31")
    except ValueError:
        pass
    return result


def load_foundation(path: Path, expected_sha: str = FOUNDATION_SHA) -> dict:
    raw = path.read_bytes()
    actual_sha = _sha(raw)
    if actual_sha != expected_sha:
        raise ValueError("Foundation SQLite SHA-256 differs from pinned input")
    # Inspect the exact bytes already hashed; reopening the path would permit
    # a replacement between verification and import.
    with sqlite3.connect(":memory:") as conn:
        conn.deserialize(raw)
        conn.row_factory = sqlite3.Row
        entities = _rows(conn, "entity")
        statements = _rows(conn, "source_statement")
        meta = _rows(conn, "source_meta")
        assertions = _rows(conn, "structural_assertion")
        pins = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM input_pin")}
    if (len(entities), len(statements), len(meta), len(assertions)) != (5, 152, 40, 50):
        raise ValueError("Foundation denominator mismatch")
    if len({x["statement_id"] for x in statements}) != 152 or len({x["meta_statement_id"] for x in meta}) != 40:
        raise ValueError("Duplicate source identity")
    source_ids = {x["statement_id"] for x in statements}
    for row in statements:
        prefix, sep, line = row["statement_id"].partition(":")
        if not sep or not line.isdecimal() or int(line) != row["source_line"]:
            raise ValueError("Statement ID/line mismatch")
        if not row["source_file_sha256"] or not row["raw"] or not row["source_kind"]:
            raise ValueError("Incomplete source provenance")
        if row["raw"] != "\t".join((row["subject"], row["predicate"], row["object"], ".")):
            raise ValueError("Statement raw triple mismatch")
    for row in meta:
        if row["link_status"] == "linked" and row["parent_statement_id"] not in source_ids:
            raise ValueError("Dangling linked Meta")
        if row["link_status"] != "linked" and row["parent_statement_id"] is not None:
            raise ValueError("Orphan Meta unexpectedly linked")
    structural_ids = {x["statement_id"] for x in assertions}
    if len(structural_ids) != 50:
        raise ValueError("Duplicate structural mapping")
    by_id = {x["statement_id"]: x for x in statements}
    for row in assertions:
        source = by_id.get(row["statement_id"])
        if not source or source["mapping_status"] != "mapped" or source["mapping_role"] != row["role"]:
            raise ValueError("Structural mapping/source mismatch")
        for key in ("trial_entity_id", "subject", "object", "project_relation", "source_kind"):
            if source[key] != row[key]:
                raise ValueError("Structural assertion differs from source mapping")
    return {"foundation_sha256": actual_sha, "entities": entities, "source_statements": statements,
            "source_meta": meta, "structural_assertions": assertions, "input_pins": pins}


def _classify(assertion: dict, linked: list[dict]) -> tuple[str, dict, str]:
    role = assertion["role"]
    relation = assertion["project_relation"]
    qualifiers = {x["qualifier_predicate"]: x for x in linked}
    if role == "knowledge_attribute" or assertion["trial_entity_id"].endswith((":Hangul", ":Bloomery")):
        return "knowledge_or_taxonomy", {}, "Knowledge/classification is not a dated use or adoption bridge"
    if role == "classification" and linked:
        if set(qualifiers) == {"schema:startDate", "schema:endDate"} and len(linked) == 2:
            start = parse_time(qualifiers["schema:startDate"]["qualifier_object"])
            end = parse_time(qualifiers["schema:endDate"]["qualifier_object"])
            if start["nominal_start"] and end["nominal_end"] and start["nominal_start"] <= end["nominal_end"]:
                return "H_state", {"start": start, "end": end}, "Dated class membership forms a bounded role state only for this source interval"
        return "temporal_unknown", {}, "Unsupported or incomplete class interval Meta"
    if relation == "spouse_claim" and linked:
        if set(qualifiers) == {"schema:startDate", "schema:endDate"} and len(linked) == 2:
            start = parse_time(qualifiers["schema:startDate"]["qualifier_object"])
            end = parse_time(qualifiers["schema:endDate"]["qualifier_object"])
            if start["nominal_start"] and end["nominal_end"] and start["nominal_start"] <= end["nominal_end"]:
                return "H_state", {"start": start, "end": end}, "Spouse relation has its own bounded source interval"
        return "temporal_unknown", {}, "Unsupported or incomplete spouse interval Meta"
    if relation in {"birth_date_claim", "death_date_claim"}:
        event_time = parse_time(assertion["object"])
        if event_time["nominal_start"]:
            return "H_event", {"event": event_time}, "Dated occurrence, not a persistent current state"
    return "temporal_unknown", {}, "No source-backed current-state interval; timeless validity not inferred"


def make_release(foundation: dict, revision: str = "v1") -> dict:
    if revision not in {"v1", "v2", "v3"}:
        raise ValueError("Unknown bounded YAGO mapping revision")
    meta_by_parent: dict[str, list[dict]] = {}
    for row in foundation["source_meta"]:
        if row["link_status"] == "linked":
            meta_by_parent.setdefault(row["parent_statement_id"], []).append(row)
    claims = []
    decisions = []
    for assertion in foundation["structural_assertions"]:
        linked = sorted(meta_by_parent.get(assertion["statement_id"], []), key=lambda x: x["meta_statement_id"])
        lane, time, rationale = _classify(assertion, linked)
        claim_id = "sot:claim:" + assertion["statement_id"]
        claims.append({"claim_id": claim_id, "source_statement_id": assertion["statement_id"],
                       "entity_id": assertion["trial_entity_id"], "subject": assertion["subject"],
                       "predicate": assertion["project_relation"], "object": assertion["object"],
                       "role": assertion["role"], "lane": lane, "time": time,
                       "meta_ids": [x["meta_statement_id"] for x in linked],
                       "basis_kind": "yago_derived_fact", "source_kind": assertion["source_kind"]})
        decisions.append({"decision_id": "sot:decision:" + assertion["statement_id"],
                          "claim_id": claim_id, "actor_type": "policy", "policy_version": MAPPING_POLICY,
                          "scope": "five-target YAGO 4.6 structural source claim only",
                          "decision": "source_grounded_pilot_include", "rationale": rationale,
                          "historical_truth_review": "not_performed", "work_scope_review": "not_performed"})
    counts = {lane: sum(x["lane"] == lane for x in claims)
              for lane in ("H_state", "H_event", "knowledge_or_taxonomy", "temporal_unknown")}
    release = {"release_id": RELEASE_ID, "foundation_sha256": foundation["foundation_sha256"],
               "input_pins": foundation["input_pins"], "mapping_policy": MAPPING_POLICY,
               "query_policy": QUERY_POLICY, "scope": "five selected YAGO 4.6 entities only",
               "source_counts": {"entities": 5, "source_statements": 152, "source_meta": 40,
                                 "structural_claims": 50, "linked_meta": 24,
                                 "excluded_statements": 22},
               "claim_lane_counts": counts, "source_grounded_not_truth": True,
               "work_review_scope_eligible": False, "author_history_locked": False,
               "time_basis": "YAGO raw typed values; nominal ISO comparison only; original calendar, rank, original precision and repeated periods unknown"}
    if sum(counts.values()) != 50:
        raise ValueError("Claim lane denominator mismatch")
    if revision in {"v2", "v3"}:
        # The first published release retained this raw K date only in its
        # KGStatementSource. A new claim revision exposes its precision and
        # unknown calendar without turning it into 1450 use/adoption history.
        old_id = "sot:claim:facts:46623039"
        corrected = next(x for x in claims if x["claim_id"] == old_id)
        corrected["claim_id"] = old_id + ":r2"
        corrected["time"] = {"origin": parse_time(corrected["object"])}
        decision = next(x for x in decisions if x["claim_id"] == old_id)
        decision["claim_id"] = corrected["claim_id"]
        decision["decision_id"] += ":r2"
        decision["policy_version"] = MAPPING_POLICY_V2
        decision["rationale"] = "K-origin candidate retains raw gYear precision and unknown calendar; no B or dated use inferred"
        release["release_id"] = RELEASE_ID_V2
        release["mapping_policy"] = MAPPING_POLICY_V2
        release["supersedes_release_id"] = RELEASE_ID
        release["policy_delta"] = "Only Hangul startDate claim/decision revised to expose K-origin raw time; 49 claim/decision IDs carried forward"
    if revision == "v3":
        event_by_subject = {(x["subject"], x["predicate"]): x for x in claims
                            if x["lane"] == "H_event"}
        decision_by_claim = {x["claim_id"]: x for x in decisions}
        for claim in claims:
            if claim["lane"] != "temporal_unknown":
                continue
            birth = event_by_subject.get((claim["subject"], "birth_date_claim"))
            death = event_by_subject.get((claim["subject"], "death_date_claim"))
            old_id = claim["claim_id"]
            claim["claim_id"] = old_id + ":r3"
            claim["supersedes_claim_id"] = old_id
            birth_time = birth["time"]["event"] if birth else None
            death_time = death["time"]["event"] if death else None
            anchored = (birth_time is not None and death_time is not None
                        and birth_time["nominal_start"] is not None
                        and death_time["nominal_end"] is not None
                        and birth_time["nominal_start"] <= death_time["nominal_end"])
            event_relation = None
            if anchored:
                claim["context_range"] = {
                    "start_year": int(birth_time["nominal_start"][:4]),
                    "end_year_exclusive": int(death_time["nominal_end"][:4]) + 1,
                    "nominal_start": birth_time["nominal_start"],
                    "nominal_end": death_time["nominal_end"],
                    "basis_claim_ids": [birth["claim_id"], death["claim_id"]],
                    "basis_source_statement_ids": [birth["source_statement_id"], death["source_statement_id"]],
                    "derivation_rule": "same_subject_life_events_for_discovery_only",
                    "rule_version": "v1", "precision": "year_bucket", "anchor_precision": "day_lexical",
                    "calendar": "unknown", "status": "derived_context_only",
                }
                event_relation = {"birth_place_claim": (birth, "birth"),
                                  "death_place_claim": (death, "death")}.get(claim["predicate"])
                if event_relation:
                    event, event_kind = event_relation
                    event_time = event["time"]["event"]
                    claim["inferred_event_bound"] = {
                        "start_year": int(event_time["nominal_start"][:4]),
                        "end_year_exclusive": int(event_time["nominal_end"][:4]) + 1,
                        "nominal_start": event_time["nominal_start"],
                        "nominal_end": event_time["nominal_end"],
                        "basis_claim_id": event["claim_id"],
                        "basis_source_statement_id": event["source_statement_id"],
                        "derivation_rule": "same_subject_" + event_kind + "_place_to_" + event_kind + "_date",
                        "rule_version": "v1", "precision": "year_bucket",
                        "anchor_precision": event_time["precision"],
                        "calendar": event_time["calendar"],
                        "status": "derived_occurrence_candidate",
                    }
            else:
                claim["temporal_basis_status"] = "missing_or_invalid_same_subject_life_anchors"
            decision = decision_by_claim[old_id]
            decision["claim_id"] = claim["claim_id"]
            decision["decision_id"] += ":r3"
            decision["supersedes_decision_id"] = decision["decision_id"][:-3]
            decision["policy_version"] = MAPPING_POLICY_V3
            decision["rationale"] = (
                "Person life dates bound only era discovery; source valid time remains unknown. "
                + ("Same-subject place/date join is a derived event candidate."
                   if event_relation else "No event occurrence inferred for this relation."
                   if anchored else "No valid same-subject life anchors; temporal basis remains unknown.")
            )
        release["release_id"] = RELEASE_ID_V3
        release["mapping_policy"] = MAPPING_POLICY_V3
        release["query_policy"] = QUERY_POLICY_V3
        release["supersedes_release_id"] = RELEASE_ID_V2
        release["policy_delta"] = ("Add source-linked context ranges to 23 undated person claims and narrower "
                                   "derived occurrence candidates to six birth/death place claims; valid time stays unknown")
    return {"release": release, "entities": foundation["entities"],
            "source_statements": foundation["source_statements"], "source_meta": foundation["source_meta"],
            "claims": claims, "decisions": decisions}


def query_interval(as_of: str) -> tuple[str, str, str]:
    if YEAR.fullmatch(as_of):
        date(int(as_of), 1, 1)
        return as_of + "-01-01", as_of + "-12-31", "year_interval"
    if DAY.fullmatch(as_of):
        date.fromisoformat(as_of)
        return as_of, as_of, "exact_day"
    raise ValueError("as_of must be YYYY or YYYY-MM-DD")


def temporal_bucket(claim: dict, query_start: str, query_end: str) -> str:
    if claim["lane"] != "H_state":
        return "not_state"
    time = claim["time"]
    start = time["start"]["nominal_start"]
    end = time["end"]["nominal_end"]
    if start is None or end is None:
        return "temporal_unknown"
    if start > query_end:
        return "future"
    if end < query_start:
        return "past"
    if query_start == query_end and query_start in (start, end):
        return "possible_boundary"
    if start <= query_start and end >= query_end:
        return "supported_nominal"
    return "possible_nominal"


def evidence_packet(snapshot: dict, entity_id: str, as_of: str) -> dict:
    start, end, kind = query_interval(as_of)
    release = snapshot["release"]
    if entity_id not in {x["trial_entity_id"] for x in snapshot["entities"]}:
        raise ValueError("Entity outside bounded release")
    sources = {x["statement_id"]: x for x in snapshot["source_statements"]}
    claims_by_id = {x["claim_id"]: x for x in snapshot["claims"]}
    meta = {x["meta_statement_id"]: x for x in snapshot["source_meta"]}
    decisions = {x["claim_id"]: x for x in snapshot["decisions"]}
    buckets = {name: [] for name in ("supported_nominal", "possible_nominal", "possible_boundary",
                                    "future", "past", "temporal_unknown", "event_in_interval",
                                    "future_events", "past_events", "knowledge_or_taxonomy")}
    for claim in snapshot["claims"]:
        if claim["entity_id"] != entity_id:
            continue
        if claim["lane"] == "H_state":
            bucket = temporal_bucket(claim, start, end)
        elif claim["lane"] == "H_event":
            event = claim["time"]["event"]
            if event["nominal_start"] > end:
                bucket = "future_events"
            elif event["nominal_end"] < start:
                bucket = "past_events"
            else:
                bucket = "event_in_interval"
        elif claim["lane"] == "knowledge_or_taxonomy":
            bucket = "knowledge_or_taxonomy"
        else:
            bucket = "temporal_unknown"
        source = sources[claim["source_statement_id"]]
        item = {"claim": claim, "decision": decisions[claim["claim_id"]],
                "source": source, "meta": [meta[x] for x in claim["meta_ids"]]}
        if "context_range" in claim:
            item["basis_events"] = [
                {"claim": claims_by_id[basis_id],
                 "source": sources[claims_by_id[basis_id]["source_statement_id"]]}
                for basis_id in claim["context_range"]["basis_claim_ids"]
            ]
        if bucket == "temporal_unknown" and "inferred_event_bound" in claim:
            bound = claim["inferred_event_bound"]
            item["inferred_occurrence_relative_to_query"] = (
                "future" if bound["nominal_start"] > end else
                "past" if bound["nominal_end"] < start else "overlaps"
            )
        buckets[bucket].append(item)
    current = [item["claim"] for lane in ("supported_nominal", "possible_nominal", "possible_boundary")
               for item in buckets[lane]]
    competition = []
    for i, left in enumerate(current):
        for right in current[i + 1:]:
            if left["subject"] != right["subject"] or left["predicate"] != right["predicate"] or left["object"] == right["object"]:
                continue
            left_start, left_end = left["time"]["start"]["nominal_start"], left["time"]["end"]["nominal_end"]
            right_start, right_end = right["time"]["start"]["nominal_start"], right["time"]["end"]["nominal_end"]
            if max(left_start, right_start) <= min(left_end, right_end):
                competition.append({"claim_ids": [left["claim_id"], right["claim_id"]],
                                    "status": "potential_competition_only",
                                    "reason": "Exclusive relation semantics and source boundary inclusion are unverified"})
    return {"mode": "reality_state_with_separate_claim_lanes", "release_id": release["release_id"],
            "entity_id": entity_id, "as_of": as_of, "query_kind": kind,
            "nominal_query_interval": [start, end], "time_basis": release["time_basis"],
            "historical_truth_review": "not_performed", "work_review_scope_eligible": False,
            "witness_count": "not_inferred_from_yago_derivation", "lanes": buckets,
            "potential_competition": competition}


def era_interval(period: str) -> tuple[str, str]:
    """Convert a year or inclusive year range to nominal comparison bounds."""
    first, sep, last = period.partition("..")
    if not YEAR.fullmatch(first) or (sep and not YEAR.fullmatch(last)):
        raise ValueError("period must be YYYY or YYYY..YYYY")
    end_year = last if sep else first
    date(int(first), 1, 1)
    date(int(end_year), 12, 31)
    if first > end_year:
        raise ValueError("period start is after end")
    return first + "-01-01", end_year + "-12-31"


def era_packet(snapshot: dict, period: str) -> dict:
    """Find era candidates without changing the then-current state contract."""
    start, end = era_interval(period)
    start_year, end_year_exclusive = int(start[:4]), int(end[:4]) + 1
    sources = {x["statement_id"]: x for x in snapshot["source_statements"]}
    claims_by_id = {x["claim_id"]: x for x in snapshot["claims"]}
    decisions = {x["claim_id"]: x for x in snapshot["decisions"]}
    lanes = {key: [] for key in ("explicit_dated_overlap", "inferred_occurrence_candidate",
                                "contextual_era_match", "no_temporal_basis",
                                "outside_period")}
    knowledge_excluded = 0
    for claim in snapshot["claims"]:
        if claim["lane"] == "knowledge_or_taxonomy":
            knowledge_excluded += 1
            continue
        if claim["lane"] in {"H_state", "H_event"}:
            if claim["lane"] == "H_state":
                left = claim["time"]["start"]["nominal_start"]
                right = claim["time"]["end"]["nominal_end"]
            else:
                left = claim["time"]["event"]["nominal_start"]
                right = claim["time"]["event"]["nominal_end"]
            lane = "explicit_dated_overlap" if left <= end and start <= right else "outside_period"
        elif "inferred_event_bound" in claim:
            bound = claim["inferred_event_bound"]
            lane = ("inferred_occurrence_candidate" if bound["start_year"] < end_year_exclusive
                    and start_year < bound["end_year_exclusive"] else "outside_period")
        elif "context_range" in claim:
            context = claim["context_range"]
            lane = ("contextual_era_match" if context["start_year"] < end_year_exclusive
                    and start_year < context["end_year_exclusive"] else "outside_period")
        else:
            lane = "no_temporal_basis"
        item = {"claim": claim, "decision": decisions[claim["claim_id"]],
                "source": sources[claim["source_statement_id"]]}
        if "context_range" in claim:
            item["basis_events"] = [
                {"claim": claims_by_id[basis_id],
                 "source": sources[claims_by_id[basis_id]["source_statement_id"]]}
                for basis_id in claim["context_range"]["basis_claim_ids"]
            ]
        lanes[lane].append(item)
    return {"mode": "era_discovery_not_current_state", "release_id": snapshot["release"]["release_id"],
            "period": period, "nominal_query_interval": [start, end],
            "historical_truth_review": "not_performed", "work_review_scope_eligible": False,
            "time_basis": snapshot["release"]["time_basis"], "lanes": lanes,
            "counts": {key: len(value) for key, value in lanes.items()},
            "knowledge_or_taxonomy_excluded_count": knowledge_excluded}


def temporal_ledger(snapshot: dict) -> list[dict]:
    """Release-scoped human ledger rows for the original 23 undated claims."""
    sources = {x["statement_id"]: x for x in snapshot["source_statements"]}
    claims_by_id = {x["claim_id"]: x for x in snapshot["claims"]}
    decisions = {x["claim_id"]: x for x in snapshot["decisions"]}
    rows = []
    for claim in snapshot["claims"]:
        if claim["lane"] != "temporal_unknown":
            continue
        rows.append({"release_id": snapshot["release"]["release_id"],
                     "claim_id": claim["claim_id"], "subject": claim["subject"],
                     "predicate": claim["predicate"], "object": claim["object"],
                     "valid_time": claim["time"], "context_range": claim.get("context_range"),
                     "inferred_event_bound": claim.get("inferred_event_bound"),
                     "source_statement_id": claim["source_statement_id"],
                     "source_file": sources[claim["source_statement_id"]]["source_file"],
                     "source_file_sha256": sources[claim["source_statement_id"]]["source_file_sha256"],
                     "source_line": sources[claim["source_statement_id"]]["source_line"],
                     "source_raw": sources[claim["source_statement_id"]]["raw"],
                     "decision_id": decisions[claim["claim_id"]]["decision_id"],
                     "basis_events": [
                         {"claim_id": basis_id,
                          "source_statement_id": claims_by_id[basis_id]["source_statement_id"],
                          "raw_time": claims_by_id[basis_id]["time"]["event"]["raw"],
                          "source_raw": sources[claims_by_id[basis_id]["source_statement_id"]]["raw"]}
                         for basis_id in claim.get("context_range", {}).get("basis_claim_ids", [])
                     ]})
    return sorted(rows, key=lambda x: (x["subject"], x["source_statement_id"]))
