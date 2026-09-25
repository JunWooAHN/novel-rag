import unittest
import json

from export import digest, ensure_unique_target, validate_batch


class ExportContractTest(unittest.TestCase):
    def setUp(self):
        self.text = '이전.완결 장면.'
        self.bundle = {'batch_id': 'fixture-001-001', 'work_id': 'gogjong',
                       'source_sha256': 'a' * 64, 'segmentation_id': 1,
                       'split': 'train',
                       'excerpt_start_cp': 0, 'excerpt_end_cp': len(self.text),
                       'units': [{'section_order': 1, 'start_cp': 3, 'end_cp': len(self.text)}]}
        self.review = {'schema_version': 1, 'batch_id': self.bundle['batch_id'],
                       'work_id': 'gogjong', 'source_sha256': 'a' * 64, 'segmentation_id': 1,
                       'attempts': [{'section_order': 1, 'status': 'proposed',
                                     'candidate_ids': ['c1'], 'reason': ''}],
                       'candidates': [{'candidate_id': 'c1', 'covered_section_orders': [1],
                                       'answer_start_cp': 3, 'answer_end_cp': len(self.text),
                                       'prior_start_cp': 0, 'prior_end_cp': 3,
                                       'review_record': {'observed': [{'claim': '이전 상태', 'start_cp': 0, 'end_cp': 3}],
                                                         'reconstructed_assumptions': [],
                                                         'boundary_reason': '완결', 'leakage_check': 'pass'},
                                       'writer_input': {'prior_context': '이전 사건', 'virtual_history': [],
                                                        'character_knowledge': [], 'scene_spec': {'purpose': '결과'}}}]}
        self.decision = {'schema_version': 2, 'batch_id': self.bundle['batch_id'],
                         'reviewer': 'independent-sol', 'accepted_candidate_ids': ['c1'],
                         'hold_candidate_ids': [], 'rejected_candidate_ids': []}
        self.work = {'source_path': 'refs/fixture.txt', 'source_sha256': 'a' * 64,
                     'segmentation_id': 1, 'role': 'gemma_style'}
        self.split = {'start_cp': 0, 'end_cp': len(self.text)}

    def bind_review(self):
        self.decision['review_sha256'] = digest(json.dumps(
            self.review, ensure_ascii=False, sort_keys=True).encode('utf-8'))

    def test_gemma_target_is_exact_source_slice(self):
        self.bind_review()
        rows, counts = validate_batch(self.bundle, self.review, self.decision,
                                      self.work, self.split, self.text)
        self.assertEqual(rows[0]['messages'][1]['content'], self.text[3:])
        self.assertEqual(rows[0]['metadata']['target_basis'], 'observed_exact_source_slice')
        self.assertFalse(rows[0]['metadata']['truncated'])
        self.assertEqual(counts['attempted_units'], 1)

    def test_planner_target_is_reviewed_plan_not_raw_prose(self):
        self.work['role'] = 'sota_planning'
        candidate = self.review['candidates'][0]
        del candidate['writer_input']
        candidate['planner_input'] = {'prior_state': '이전 상태', 'goal': '사건 결정', 'constraints': ['모순 금지']}
        candidate['plan_target'] = {'virtual_history': [{'event': '결정'}],
                                    'character_knowledge': [], 'scene_spec': {'purpose': '결정'}}
        self.bind_review()
        rows, _ = validate_batch(self.bundle, self.review, self.decision,
                                 self.work, self.split, self.text)
        self.assertNotIn(self.text[3:], rows[0]['messages'][1]['content'])
        self.assertEqual(rows[0]['metadata']['target_basis'], 'reviewed_reconstruction_not_author_intent')

    def test_cross_split_context_is_rejected(self):
        self.split['start_cp'] = 3
        self.bind_review()
        with self.assertRaisesRegex(ValueError, 'escapes split'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)

    def test_changed_review_invalidates_acceptance(self):
        self.bind_review()
        self.review['candidates'][0]['writer_input']['scene_spec']['purpose'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'review hash mismatch'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)

    def test_nested_provenance_is_rejected_but_fictional_dates_are_allowed(self):
        payload = self.review['candidates'][0]['writer_input']
        payload['virtual_history'] = [{'year': 1691, 'character_id': '얀',
                                       'resource': '철', 'event': '훈련'}]
        self.bind_review()
        validate_batch(self.bundle, self.review, self.decision, self.work, self.split, self.text)
        payload['character_knowledge'] = [{'known': ['이전 사건'], 'evidence_cp': [0, 3]}]
        self.bind_review()
        with self.assertRaisesRegex(ValueError, 'provenance key'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)

    def test_writer_payload_shape_rejects_string_history_or_scene(self):
        writer = self.review['candidates'][0]['writer_input']
        for key, bad in [('virtual_history', 'history text'),
                         ('character_knowledge', ['knowledge text']),
                         ('scene_spec', 'scene text'), ('prior_context', ['prior'])]:
            with self.subTest(key=key):
                original = writer[key]
                writer[key] = bad
                self.bind_review()
                with self.assertRaisesRegex(ValueError, 'writer payload shape invalid'):
                    validate_batch(self.bundle, self.review, self.decision,
                                   self.work, self.split, self.text)
                writer[key] = original

    def test_planner_payload_shape_rejects_malformed_fields(self):
        self.work['role'] = 'sota_planning'
        candidate = self.review['candidates'][0]
        del candidate['writer_input']
        candidate['planner_input'] = {'prior_state': '이전', 'goal': '결정', 'constraints': ['모순 금지']}
        candidate['plan_target'] = {'virtual_history': [], 'character_knowledge': [], 'scene_spec': {}}
        for group, key, bad in [('planner_input', 'constraints', 'plain text'),
                                ('planner_input', 'prior_state', ['state']),
                                ('plan_target', 'virtual_history', 'plan text'),
                                ('plan_target', 'character_knowledge', ['knowledge text']),
                                ('plan_target', 'scene_spec', 'scene text')]:
            with self.subTest(group=group, key=key):
                original = candidate[group][key]
                candidate[group][key] = bad
                self.bind_review()
                with self.assertRaisesRegex(ValueError, 'planner payload shape invalid'):
                    validate_batch(self.bundle, self.review, self.decision,
                                   self.work, self.split, self.text)
                candidate[group][key] = original

    def test_camel_case_and_reversed_cp_keys_are_rejected_recursively(self):
        nested = self.review['candidates'][0]['writer_input']['scene_spec']
        for key, value in [('sourcePath', 'other/source.txt'), ('cp_start', 3),
                           ('cpEnd', 6), ('sourceId', 's1')]:
            with self.subTest(key=key):
                nested[key] = value
                self.bind_review()
                with self.assertRaisesRegex(ValueError, 'provenance key'):
                    validate_batch(self.bundle, self.review, self.decision,
                                   self.work, self.split, self.text)
                del nested[key]

    def test_planner_target_rejects_nested_provenance(self):
        self.work['role'] = 'sota_planning'
        candidate = self.review['candidates'][0]
        del candidate['writer_input']
        candidate['planner_input'] = {'prior_state': '이전', 'goal': '결정', 'constraints': ['연도 1691']}
        candidate['plan_target'] = {'virtual_history': [{'event': '결정', 'sourcePath': 'elsewhere.txt'}],
                                    'character_knowledge': [], 'scene_spec': {}}
        self.bind_review()
        with self.assertRaisesRegex(ValueError, 'provenance key'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)

    def test_unresolved_unit_must_be_held_and_cannot_be_targeted(self):
        self.bundle['units'][0]['boundary_status'] = 'hold'
        self.bundle['units'][0]['kind'] = 'unresolved'
        self.bind_review()
        with self.assertRaisesRegex(ValueError, 'unresolved unit must remain hold'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)
        self.review['attempts'][0] = {'section_order': 1, 'status': 'hold',
                                      'candidate_ids': [], 'reason': '경계 미확정'}
        self.bind_review()
        with self.assertRaisesRegex(ValueError, 'unreferenced candidate'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)

    def test_candidate_cannot_reuse_held_unresolved_text_from_adjacent_unit(self):
        self.bundle['units'] = [
            {'section_order': 1, 'start_cp': 0, 'end_cp': 3,
             'boundary_status': 'hold', 'kind': 'unresolved'},
            {'section_order': 2, 'start_cp': 3, 'end_cp': len(self.text),
             'boundary_status': 'confirmed', 'kind': 'numbered'}]
        self.review['attempts'] = [
            {'section_order': 1, 'status': 'hold', 'candidate_ids': [], 'reason': '경계 미확정'},
            {'section_order': 2, 'status': 'proposed', 'candidate_ids': ['c1'], 'reason': ''}]
        candidate = self.review['candidates'][0]
        candidate['covered_section_orders'] = [1, 2]
        candidate['answer_start_cp'] = 2
        candidate['prior_end_cp'] = 2
        self.bind_review()
        with self.assertRaisesRegex(ValueError, 'held/unreferenced unit'):
            validate_batch(self.bundle, self.review, self.decision,
                           self.work, self.split, self.text)

    def test_duplicate_target_text_at_different_coordinates_is_rejected(self):
        seen = set()
        ensure_unique_target('같은\r\n 문장', 'train', seen)
        with self.assertRaisesRegex(ValueError, 'duplicate normalized target'):
            ensure_unique_target('같은 문장', 'development_holdout', seen)


if __name__ == '__main__':
    unittest.main()
