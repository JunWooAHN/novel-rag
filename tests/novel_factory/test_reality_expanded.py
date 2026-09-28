import json
import unittest

from novel_factory.reality.domain import SourceUnit, digest
from novel_factory.reality.expanded import (
    check_indexed_response, evidence_spans, indexed_prompt_sha,
    make_indexed_prompt, plan_embedding_spans, split_full_slot,
    validate_fixture_inventory,
)


def fixture(text: str) -> dict:
    return {
        "wiki_id": "kowiki", "page_id": 10, "revision_id": 20,
        "slot": "main", "language": "ko", "title": "문종",
        "wikitext": text, "content_sha256": digest(text.encode("utf-8")),
    }


def item(span_id: str, **changes) -> dict:
    result = {
        "layer": "H", "mapping_refs": ["EX-001"], "subject": "문종",
        "predicate": "died", "object": None, "actor": None, "affected": "문종",
        "place": None, "time_text": None, "calendar_basis": None,
        "force": None, "uncertainty": None, "evidence_span_id": span_id,
        "temporal_scope": "pre_1950",
        "related_candidate_index": None,
    }
    result.update(changes)
    return result


class FullSlotContractTests(unittest.TestCase):
    def test_full_utf8_coverage_with_stable_nonoverlapping_units(self):
        text = "한글 " * 100 + "\n" + "Munjong was forced to abdicate. " * 20
        source = fixture(text)
        units = split_full_slot(source, max_bytes=128)
        self.assertGreater(len(units), 2)
        self.assertEqual(units, split_full_slot(source, max_bytes=128))
        self.assertEqual(units[0].start_byte, 0)
        self.assertEqual(units[-1].end_byte, len(text.encode("utf-8")))
        for left, right in zip(units, units[1:]):
            self.assertEqual(left.end_byte, right.start_byte)
        self.assertEqual(b"".join(u.text.encode("utf-8") for u in units), text.encode("utf-8"))
        self.assertEqual(split_full_slot(fixture("")), [])

    def test_model_cites_id_and_parser_attaches_exact_source_bytes(self):
        text = "문종은 1452년 음력 5월에 승하하였다.\n후대의 주장은 미상이다."
        source = split_full_slot(fixture(text))[0]
        spans = evidence_spans(source)
        self.assertGreaterEqual(len(spans), 2)
        self.assertIn("s000", make_indexed_prompt(source, {"EX-001"}))
        self.assertEqual(indexed_prompt_sha(source, {"EX-001"}), digest(make_indexed_prompt(source, {"EX-001"}).encode("utf-8")))
        result, _ = check_indexed_response(json.dumps({
            "source_unit_id": source.unit_id,
            "language_handling": "processed",
            "candidates": [item("s000", time_text="1452년 음력 5월", calendar_basis="lunar")],
        }), source, {"EX-001"})
        self.assertEqual(result[0].status, "candidate_unreviewed")
        self.assertEqual(result[0].payload["evidence_quote"], spans[0].text)
        raw = text.encode("utf-8")
        self.assertEqual(raw[result[0].evidence_start_byte:result[0].evidence_end_byte], spans[0].text.encode("utf-8"))

    def test_forced_lunar_and_place_omissions_are_held(self):
        source = split_full_slot(fixture("문종은 1452년 음력 5월 경복궁에서 승하하였다.\nHe was forced to abdicate."))[0]
        result, _ = check_indexed_response(json.dumps({
            "source_unit_id": source.unit_id,
            "language_handling": "processed",
            "candidates": [
                item("s000", object="경복궁", place="경복궁", time_text="1452년 음력 5월"),
                item("s001", subject="He", predicate="abdicated"),
                item("absent"),
            ],
        }), source, {"EX-001"})
        self.assertEqual([x.status for x in result], ["held"] * 3)
        self.assertIn("missing_lunar_basis", result[0].problems)
        self.assertIn("place_as_object", result[0].problems)
        self.assertIn("missing_forced_qualifier", result[1].problems)
        self.assertIn("unknown_evidence_span_id", result[2].problems)

    def test_zero_candidate_is_legitimate_and_bad_knowledge_holds_bridge(self):
        source = split_full_slot(fixture("한글은 문자다.\n세종이 만들었다."))[0]
        empty, _ = check_indexed_response(json.dumps({"source_unit_id":source.unit_id,"language_handling":"processed","candidates":[]}), source, {"EX-001"})
        self.assertEqual(empty, [])
        k = item("missing", layer="K", subject="한글", predicate="is", object="문자")
        b = item("s001", layer="B", subject="세종", predicate="created", object="한글", related_candidate_index=0)
        checked, _ = check_indexed_response(json.dumps({"source_unit_id":source.unit_id,"language_handling":"processed","candidates":[k,b]}), source, {"EX-001"})
        self.assertEqual([x.status for x in checked], ["held", "held"])
        self.assertIn("bridge_to_held_K", checked[1].problems)

    def test_embedding_plan_has_exact_source_bytes_and_token_bisection(self):
        unit = split_full_slot(fixture("한글 관련 지식 " * 70))[0]
        spans = plan_embedding_spans(unit, lambda text: len(text) + 2, max_bytes=200)
        self.assertGreater(len(spans), 2)
        self.assertTrue(all(len(text) + 2 <= 512 for _, _, text in spans))
        raw = unit.text.encode("utf-8")
        for start, end, text in spans:
            self.assertEqual(raw[start:end], text.encode("utf-8"))

    def test_post_1950_and_unresolved_time_are_held(self):
        unit = split_full_slot(fixture("현대 지식이 2020년에 확산되었다."))[0]
        items = [item("s000", temporal_scope="post_1950"), item("s000", temporal_scope="unknown")]
        checked, _ = check_indexed_response(json.dumps({"source_unit_id":unit.unit_id,"language_handling":"processed","candidates":items}), unit, {"EX-001"})
        self.assertEqual([x.status for x in checked], ["held", "held"])
        self.assertIn("out_of_scope_after_rough_1950", checked[0].problems)
        self.assertIn("temporal_scope_unresolved", checked[1].problems)

    def test_unsupported_language_is_deferred_not_zero_claim_success(self):
        unit = split_full_slot(fixture("알 수 없는 언어 표기"))[0]
        checked, notes = check_indexed_response(json.dumps({
            "source_unit_id": unit.unit_id, "language_handling": "unsupported",
            "language_reason": "cannot reliably interpret", "candidates": [],
        }), unit, {"EX-001"})
        self.assertEqual(checked, [])
        self.assertIn("LANGUAGE_UNSUPPORTED", notes)

    def test_cross_unit_B_keeps_evidence_as_held_without_inventing_K(self):
        unit = split_full_slot(fixture("훈민정음은 1446년에 반포되었다."))[0]
        b = item("s000", layer="B", subject="훈민정음", predicate="promulgated",
                 object="문자", related_knowledge_hint="훈민정음 문자", related_candidate_index=None)
        checked, _ = check_indexed_response(json.dumps({
            "source_unit_id":unit.unit_id,"language_handling":"processed","candidates":[b],
        }), unit, {"EX-001"})
        self.assertEqual(checked[0].status, "held")
        self.assertIn("cross_unit_K_unresolved", checked[0].problems)
        self.assertEqual(checked[0].payload["evidence_quote"].strip(), unit.text)

    def test_frozen_sitelink_denominator_catches_missing_relation(self):
        catalog = {"targets":[{"target":"Munjong","qid":"Q1","wikipedia_sitelink_count":2,
                              "wikipedia_sitelinks":{"enwiki":{"title":"Munjong"},
                                                     "kowiki":{"title":"문종"}}}]}
        receipts = [
            {"target":"Munjong","wiki_id":"enwiki","requested_title":"Munjong",
             "status":"success","qid":"Q1","source_file":"en.json","source_sha256":"a"},
            {"target":"Munjong","wiki_id":"kowiki","requested_title":"문종",
             "status":"pending","qid":"Q1"},
        ]
        manifest = [{"source_file":"en.json","source_sha256":"a"}]
        self.assertEqual(validate_fixture_inventory(catalog,receipts,manifest),
                         {"expected_relations":2,"successful_sources":1})
        with self.assertRaisesRegex(ValueError,"denominator"):
            validate_fixture_inventory(catalog,receipts[:-1],manifest)
        with self.assertRaisesRegex(ValueError,"manifest"):
            validate_fixture_inventory(catalog,receipts,[])

    def test_blank_K_object_is_held_even_with_local_B(self):
        unit = split_full_slot(fixture("한글 문자 체계가 선포되었다."))[0]
        k = item("s000",layer="K",subject="한글",predicate="is",object=" ")
        b = item("s000",layer="B",subject="세종",predicate="announced",object="한글",
                 related_candidate_index=0)
        checked,_=check_indexed_response(json.dumps({
            "source_unit_id":unit.unit_id,"language_handling":"processed","candidates":[k,b],
        }),unit,{"EX-001"})
        self.assertEqual([x.status for x in checked],["held","held"])
        self.assertIn("missing_knowledge_object",checked[0].problems)
        self.assertIn("bridge_to_held_K",checked[1].problems)


if __name__ == "__main__":
    unittest.main()
