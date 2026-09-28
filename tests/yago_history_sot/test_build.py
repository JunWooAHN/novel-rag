"""Semantic regression checks for the world YAGO 1899 foundation policy."""

from tools.yago_history_sot.build import (
    choose_time, key_for, nominal_year, parse_fact, parse_meta,
)


def m(predicate, value):
    return (35, 1000, predicate, value, f"<<\tyago:A\tschema:memberOf\tyago:B\t>>\t{predicate}\t{value}\t.")


def test_cutoff_1899_inclusive_and_1900_excluded():
    lane, time, _ = choose_time("schema:birthDate", '"1899"^^xsd:gYear', [])
    assert (lane, time["year"]) == ("H_event", 1899)
    assert choose_time("schema:birthDate", '"1900"^^xsd:gYear', [])[0] == "excluded"


def test_early_birth_does_not_qualify_later_statement():
    assert choose_time("schema:deathDate", '"1901"^^xsd:gYear', [])[0] == "excluded"
    assert choose_time("schema:worksFor", "yago:C", [])[0] == "unknown"


def test_crossing_state_preserves_original_end_and_cutoff():
    lane, time, _ = choose_time("schema:memberOf", "yago:B", [
        m("schema:startDate", '"1890"^^xsd:gYear'),
        m("schema:endDate", '"1910"^^xsd:gYear'),
    ])
    assert lane == "H_state"
    assert time["start_year"] == 1890
    assert time["end_year"] == 1910
    assert time["scope_end_year"] == 1899


def test_single_bound_is_not_open_ended_state():
    for pred in ("schema:startDate", "schema:endDate"):
        lane, time, reason = choose_time("schema:memberOf", "yago:B", [m(pred, '"1800"^^xsd:gYear')])
        assert (lane, time["kind"], reason) == (
            "dated_boundary_candidate", "boundary_candidate", "single_meta_bound_no_state_validity")


def test_taxonomy_and_publication_do_not_become_history_event_or_state():
    bounds = [m("schema:startDate", '"1800"^^xsd:gYear'), m("schema:endDate", '"1850"^^xsd:gYear')]
    assert choose_time("rdf:type", "yago:Person", bounds)[0] == "K_taxonomy_timed"
    assert choose_time("rdf:type", "yago:Person", [m("yago:onDate", '"1800"^^xsd:gYear')])[0] == "K_taxonomy_timed"
    assert choose_time("schema:datePublished", '"1800"^^xsd:gYear', [])[0] == "K_dated"
    assert choose_time("yago:populationNumber", '"123"^^xsd:integer', [m("yago:onDate", '"1800"^^xsd:gYear')])[0] == "dated_observation_candidate"


def test_bce_signed_year_zero_and_bad_day():
    assert nominal_year('"-0044"^^xsd:gYear') == (-44, "nominal_bce_calendar_unknown")
    assert nominal_year('"-0044-03-15"^^xsd:date') == (-44, "nominal_bce_calendar_unknown")
    assert nominal_year('"-0044-02-31"^^xsd:date') == (None, "invalid_month_or_day")
    assert nominal_year('"0000"^^xsd:gYear') == (None, "year_zero_held")
    assert nominal_year('"10000"^^xsd:gYear') == (10000, "nominal_calendar_unknown")


def test_meta_parent_round_trip_and_raw_parser():
    fact = b'yago:A\tschema:memberOf\tyago:B\t.\n'
    meta = b'<<\tyago:A\tschema:memberOf\tyago:B\t>>\tschema:startDate\t"1800"^^xsd:gYear\t.\n'
    s, p, o = parse_fact(fact)
    ms, mp, mo, _, _ = parse_meta(meta)
    assert key_for(s, p, o) == key_for(ms, mp, mo)
    assert parse_fact(b'invalid\n') is None


def test_unknown_and_reversed_intervals_held():
    assert choose_time("schema:memberOf", "yago:B", [])[0] == "unknown"
    assert choose_time("schema:memberOf", "yago:B", [
        m("schema:startDate", '"1900"^^xsd:gYear'), m("schema:endDate", '"1899"^^xsd:gYear')])[2] == "reversed_interval_held"
    assert choose_time("schema:memberOf", "yago:B", [
        m("schema:startDate", '"bad"^^xsd:gYear'), m("schema:endDate", '"1850"^^xsd:gYear')])[0] == "unknown"
