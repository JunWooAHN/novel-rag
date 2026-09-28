"""Meaningful boundary and lineage checks for the fixed five-target pilot."""

from copy import deepcopy
from pathlib import Path

import pytest

from novel_factory.reality.sot import (
    FOUNDATION_SHA, RELEASE_ID, RELEASE_ID_V2, RELEASE_ID_V3, era_packet, evidence_packet,
    load_foundation, make_release, parse_time, query_interval, temporal_ledger,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/analysis/private/yago-foundation-100-20260928/foundation.sqlite3"


@pytest.fixture(scope="module")
def release():
    return make_release(load_foundation(SOURCE))


def ids(packet, lane):
    return {item["claim"]["source_statement_id"] for item in packet["lanes"][lane]}


def test_fixed_capture_preserves_source_and_orphan_meta(release):
    assert release["release"]["foundation_sha256"] == FOUNDATION_SHA
    assert release["release"]["release_id"] == RELEASE_ID
    assert len(release["entities"]) == 5
    assert len(release["source_statements"]) == 152
    assert len(release["source_meta"]) == 40
    assert len(release["claims"]) == len(release["decisions"]) == 50
    assert sum(x["link_status"] == "linked" for x in release["source_meta"]) == 24
    assert sum(x["link_status"] != "linked" for x in release["source_meta"]) == 16
    assert all(x["historical_truth_review"] == "not_performed" for x in release["decisions"])


def test_hash_mismatch_rejected_before_mapping(tmp_path):
    wrong = tmp_path / "foundation.sqlite3"
    wrong.write_bytes(SOURCE.read_bytes() + b"alteration")
    with pytest.raises(ValueError, match="SHA-256"):
        load_foundation(wrong)


def test_year_is_interval_and_raw_precision_calendar_survives():
    assert query_interval("1450") == ("1450-01-01", "1450-12-31", "year_interval")
    assert query_interval("1450-07-01") == ("1450-07-01", "1450-07-01", "exact_day")
    assert parse_time('"1443"^^xsd:gYear') == {
        "raw": '"1443"^^xsd:gYear', "precision": "year", "calendar": "unknown",
        "nominal_start": "1443-01-01", "nominal_end": "1443-12-31",
    }
    with pytest.raises(ValueError):
        query_interval("1450-02-30")


def test_1450_reign_transition_and_future_leak_prevention(release):
    munjong = evidence_packet(release, "trial:yago46:Munjong_of_Joseon", "1450")
    assert {"facts:28729033", "facts:28729034"} <= ids(munjong, "possible_nominal")
    assert "facts:28729038" in ids(munjong, "future_events")
    assert "facts:28729045" in ids(munjong, "temporal_unknown")
    assert munjong["potential_competition"][0]["status"] == "potential_competition_only"

    danjong = evidence_packet(release, "trial:yago46:Danjong_of_Joseon", "1450")
    assert "facts:47318069" in ids(danjong, "possible_nominal")
    assert {"facts:47318070", "facts:47318073", "facts:47318074"} <= ids(danjong, "future")
    assert "facts:47318067" in ids(danjong, "future_events")
    assert "facts:47318075" in ids(danjong, "temporal_unknown")

    sejo = evidence_packet(release, "trial:yago46:Sejo_of_Joseon", "1450")
    assert "facts:9920154" in ids(sejo, "future")
    assert "facts:9920156" in ids(sejo, "future_events")
    assert "facts:9920171" in ids(sejo, "temporal_unknown")


def test_explicit_day_boundary_and_positive_provenance(release):
    early = evidence_packet(release, "trial:yago46:Danjong_of_Joseon", "1450-01-01")
    assert "facts:47318069" in ids(early, "future")
    late = evidence_packet(release, "trial:yago46:Danjong_of_Joseon", "1450-12-31")
    assert "facts:47318069" in ids(late, "supported_nominal")
    at_boundary = evidence_packet(release, "trial:yago46:Munjong_of_Joseon", "1450-03-03")
    assert {"facts:28729033", "facts:28729034"} <= ids(at_boundary, "possible_boundary")
    item = next(x for x in late["lanes"]["supported_nominal"]
                if x["claim"]["source_statement_id"] == "facts:47318069")
    assert item["source"]["source_line"] == 47318069
    assert item["source"]["source_file_sha256"]
    assert len(item["meta"]) == 2
    assert item["decision"]["actor_type"] == "policy"
    assert late["historical_truth_review"] == "not_performed"


def test_knowledge_and_taxonomy_do_not_become_current_state(release):
    for name, expected in (("Hangul", 7), ("Bloomery", 2)):
        packet = evidence_packet(release, "trial:yago46:" + name, "1450")
        assert len(packet["lanes"]["knowledge_or_taxonomy"]) == expected
        assert not packet["lanes"]["supported_nominal"]
        assert not packet["lanes"]["possible_nominal"]
    hangul = evidence_packet(release, "trial:yago46:Hangul", "1450")
    date_claim = next(x for x in hangul["lanes"]["knowledge_or_taxonomy"]
                      if x["claim"]["source_statement_id"] == "facts:46623039")
    assert date_claim["source"]["object"] == '"1443"^^xsd:gYear'


def test_v2_revises_only_hangul_knowledge_origin_claim(release):
    corrected = make_release(load_foundation(SOURCE), revision="v2")
    assert corrected["release"]["release_id"] == RELEASE_ID_V2
    assert corrected["release"]["supersedes_release_id"] == RELEASE_ID
    old_ids = {x["claim_id"] for x in release["claims"]}
    new_ids = {x["claim_id"] for x in corrected["claims"]}
    assert old_ids - new_ids == {"sot:claim:facts:46623039"}
    assert new_ids - old_ids == {"sot:claim:facts:46623039:r2"}
    old_source = release["source_statements"]
    assert corrected["source_statements"] == old_source
    assert corrected["source_meta"] == release["source_meta"]
    packet = evidence_packet(corrected, "trial:yago46:Hangul", "1450")
    claim = next(x["claim"] for x in packet["lanes"]["knowledge_or_taxonomy"]
                 if x["claim"]["source_statement_id"] == "facts:46623039")
    assert claim["time"]["origin"]["raw"] == '"1443"^^xsd:gYear'
    assert claim["time"]["origin"]["precision"] == "year"
    assert claim["time"]["origin"]["calendar"] == "unknown"
    assert not packet["lanes"]["supported_nominal"]
    assert not packet["lanes"]["possible_nominal"]


def test_v3_has_23_source_linked_contexts_and_six_narrow_place_candidates():
    source = load_foundation(SOURCE)
    r2 = make_release(source, revision="v2")
    r3 = make_release(source, revision="v3")
    assert r3["release"]["release_id"] == RELEASE_ID_V3
    assert r3["release"]["supersedes_release_id"] == RELEASE_ID_V2
    assert r3["source_statements"] == r2["source_statements"]
    assert r3["source_meta"] == r2["source_meta"]
    old = {x["claim_id"]: x for x in r2["claims"]}
    unchanged = [x for x in r3["claims"] if x["claim_id"] in old]
    assert len(unchanged) == 27
    assert all(x == old[x["claim_id"]] for x in unchanged)
    unknown = [x for x in r3["claims"] if x["lane"] == "temporal_unknown"]
    assert len(unknown) == 23
    assert sum("inferred_event_bound" in x for x in unknown) == 6
    claims = {x["claim_id"]: x for x in r3["claims"]}
    source_ids = {x["statement_id"] for x in r3["source_statements"]}
    for claim in unknown:
        assert claim["time"] == {}
        assert claim["claim_id"] == claim["supersedes_claim_id"] + ":r3"
        context = claim["context_range"]
        assert context["status"] == "derived_context_only"
        assert context["calendar"] == "unknown"
        assert context["precision"] == "year_bucket"
        birth, death = (claims[x] for x in context["basis_claim_ids"])
        assert birth["subject"] == death["subject"] == claim["subject"]
        assert birth["predicate"] == "birth_date_claim"
        assert death["predicate"] == "death_date_claim"
        assert context["basis_source_statement_ids"] == [birth["source_statement_id"],
                                                         death["source_statement_id"]]
        assert set(context["basis_source_statement_ids"]) <= source_ids
        assert context["start_year"] == int(birth["time"]["event"]["nominal_start"][:4])
        assert context["end_year_exclusive"] == int(death["time"]["event"]["nominal_end"][:4]) + 1
        event = claim.get("inferred_event_bound")
        if event:
            relation = "birth_date_claim" if claim["predicate"] == "birth_place_claim" else "death_date_claim"
            assert claim["predicate"] in {"birth_place_claim", "death_place_claim"}
            basis = claims[event["basis_claim_id"]]
            assert basis["subject"] == claim["subject"]
            assert basis["predicate"] == relation
            assert event["basis_source_statement_id"] == basis["source_statement_id"]
            assert event["calendar"] == "unknown"
            assert event["status"] == "derived_occurrence_candidate"
    assert len(temporal_ledger(r3)) == 23


def test_v3_era_discovery_never_mixes_context_with_current_state():
    r3 = make_release(load_foundation(SOURCE), revision="v3")
    broad = era_packet(r3, "1400..1499")
    assert broad["knowledge_or_taxonomy_excluded_count"] == 9
    assert broad["counts"]["inferred_occurrence_candidate"] == 6
    assert broad["counts"]["contextual_era_match"] == 17
    assert broad["counts"]["no_temporal_basis"] == 0
    year = era_packet(r3, "1450")
    assert year["counts"]["inferred_occurrence_candidate"] == 0
    assert year["counts"]["contextual_era_match"] == 17
    for period in ("1200", "1890"):
        distant = era_packet(r3, period)
        assert distant["counts"]["inferred_occurrence_candidate"] == 0
        assert distant["counts"]["contextual_era_match"] == 0
    danjong = evidence_packet(r3, "trial:yago46:Danjong_of_Joseon", "1450")
    death_place = next(x for x in danjong["lanes"]["temporal_unknown"]
                       if x["claim"]["predicate"] == "death_place_claim")
    assert death_place["inferred_occurrence_relative_to_query"] == "future"
    assert not any(x["claim"]["predicate"] == "death_place_claim"
                   for lane in ("supported_nominal", "possible_nominal", "possible_boundary")
                   for x in danjong["lanes"][lane])
    with pytest.raises(ValueError):
        era_packet(r3, "1499..1400")


def test_synthetic_missing_anchor_stays_unknown_without_invented_range():
    # Isolated synthetic mapping case; this altered assertion is never published.
    synthetic = deepcopy(load_foundation(SOURCE))
    birth = next(x for x in synthetic["structural_assertions"]
                 if x["statement_id"] == "facts:47318066")
    birth["object"] = '"invalid"^^xsd:date'
    release = make_release(synthetic, revision="v3")
    unknown = [x for x in release["claims"]
               if x["subject"] == "yago:Danjong_of_Joseon" and x["lane"] == "temporal_unknown"]
    assert len(unknown) == 8
    assert all(x["time"] == {} and "context_range" not in x
               and "inferred_event_bound" not in x for x in unknown)
    assert all(x["temporal_basis_status"] == "missing_or_invalid_same_subject_life_anchors"
               for x in unknown)
    no_basis = {x["claim"]["source_statement_id"]
                for x in era_packet(release, "1450")["lanes"]["no_temporal_basis"]}
    assert "facts:47318075" in no_basis
