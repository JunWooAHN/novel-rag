import json
import unittest

from novel_factory.reality.application import can_schedule_attempt, check_response, make_prompt, prompt_sha
from novel_factory.reality.domain import SourceUnit, digest


def unit() -> SourceUnit:
    text = "문종은 1452년 음력 5월에 승하하였다."
    return SourceUnit("kowiki:1:2:main:u1", "kowiki", 1, 2, "main", "ko", "문종", 10,
                      10 + len(text.encode("utf-8")), text, digest(text.encode("utf-8")))


class RealityTrialContractTests(unittest.TestCase):
    def test_utf8_span_and_prompt_are_pinned(self):
        source = unit()
        source.validate()
        self.assertIn(source.unit_id, make_prompt(source))
        self.assertEqual(prompt_sha(source), digest(make_prompt(source).encode("utf-8")))
        self.assertRaises(ValueError, SourceUnit(**{**source.__dict__, "end_byte": 20}).validate)

    def test_exact_quote_maps_to_original_utf8_bytes(self):
        source = unit()
        item = {"layer":"H","mapping_refs":["EX-001"],"subject":"문종",
                "predicate":"died","object":"문종의 사망","time_text":"1452년 음력 5월",
                "evidence_source_unit_id":source.unit_id,"evidence_quote":"1452년 음력 5월",
                "related_candidate_index":None,"uncertainty":None}
        checked, _ = check_response(json.dumps({"source_unit_id":source.unit_id,"candidates":[item]}),source,{"EX-001"})
        self.assertEqual(checked[0].status,"candidate_unreviewed")
        expected = source.start_byte + len("문종은 ".encode("utf-8"))
        self.assertEqual((checked[0].evidence_start_byte,checked[0].evidence_end_byte),
                         (expected,expected+len("1452년 음력 5월".encode("utf-8"))))

    def test_bad_quote_and_invalid_bridge_are_held(self):
        source=unit()
        item={"layer":"B","mapping_refs":["EX-001"],"subject":"문종",
              "predicate":"transmitted","object":"철기","evidence_source_unit_id":source.unit_id,
              "evidence_quote":"문종은 철기를 전파했다","related_candidate_index":0}
        checked,_=check_response(json.dumps({"source_unit_id":source.unit_id,"candidates":[item]}),source,{"EX-001"})
        self.assertEqual(checked[0].status,"held")
        self.assertIn("bridge_without_local_K",checked[0].problems)
        self.assertIn("quote_not_unique_in_unit",checked[0].problems)

    def test_wrong_source_unit_fails_closed(self):
        source=unit()
        with self.assertRaisesRegex(ValueError,"source_unit_id"):
            check_response(json.dumps({"source_unit_id":"other","candidates":[]}),source,set())

    def test_raw_failure_is_preserved_and_not_scheduled_again(self):
        self.assertTrue(can_schedule_attempt(None,False,False))
        self.assertTrue(can_schedule_attempt("failed",False,True))
        self.assertFalse(can_schedule_attempt("failed",True,True))
        self.assertFalse(can_schedule_attempt("completed",True,True))
        self.assertFalse(can_schedule_attempt("running",False,False))

    def test_bridge_to_held_knowledge_is_held(self):
        source=unit()
        k={"layer":"K","mapping_refs":["EX-001"],"subject":"철기","predicate":"is",
           "object":"공정","evidence_source_unit_id":source.unit_id,"evidence_quote":"없는 인용",
           "related_candidate_index":None}
        b={"layer":"B","mapping_refs":["EX-001"],"subject":"문종","predicate":"used",
           "object":"철기","evidence_source_unit_id":source.unit_id,
           "evidence_quote":"문종은","related_candidate_index":0}
        checked,_=check_response(json.dumps({"source_unit_id":source.unit_id,"candidates":[k,b]}),source,{"EX-001"})
        self.assertEqual([c.status for c in checked],["held","held"])
        self.assertIn("bridge_to_held_K",checked[1].problems)


if __name__ == "__main__":
    unittest.main()
