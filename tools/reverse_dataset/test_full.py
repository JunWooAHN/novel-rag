import base64
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import full


class WholeWorkWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.policy = full.frozen()

    def test_frozen_windows_cover_six_progress_bands_without_overlap(self):
        for wid, work in self.manifest['works'].items():
            text = full.source(work)
            windows = [full.window_at(wid, band, slot)
                       for band in range(1, 7) for slot in range(1, 9)]
            self.assertEqual(len(windows), 48)
            self.assertTrue(all(windows[i]['end_cp'] <= windows[i+1]['start_cp']
                                for i in range(47)))
            self.assertGreaterEqual(windows[0]['start_cp'], work['first_50_end_cp'])
            for window in windows:
                band = self.policy['works'][wid]['bands'][window['band']-1]
                self.assertLessEqual(band['start_cp'], window['start_cp'])
                self.assertLessEqual(window['end_cp'], band['end_cp'])
                self.assertEqual(window['primary']['end_cp'],
                                 window['alternative']['start_cp'])
                self.assertTrue(all(u['boundary_status'] == 'confirmed'
                                    for u in window['units']))
                self.assertEqual(full.sha(text[window['start_cp']:window['end_cp']].encode()),
                                 window['window_sha256'])

    def test_review_requires_exact_attempt_references(self):
        window = full.window_at('goryeo', 1, 1)
        review = {'schema_version': 1, 'window_id': window['window_id'],
                  'work_id': 'goryeo', 'source_sha256': window['source_sha256'],
                  'segmentation_id': window['segmentation_id'],
                  'attempts': [{'window_id': window['window_id'], 'status': 'proposed',
                                'portion': 'primary', 'candidate_ids': ['missing']}],
                  'candidates': []}
        with self.assertRaisesRegex(ValueError, 'attempt/candidate references mismatch'):
            full.validate_review(window, review, b'', self.manifest, self.policy)

    def test_review_cannot_use_another_partition(self):
        window = dict(full.window_at('poland', 5, 1))
        window['end_cp'] = self.policy['works']['poland']['bands'][4]['end_cp'] + 1
        with self.assertRaisesRegex(ValueError, 'window escapes frozen source/partition'):
            full.validate_review(window, {}, b'', self.manifest, self.policy)

    def test_full_review_rejects_malformed_planner_payload(self):
        window = full.window_at('goryeo', 1, 1)
        text = full.source(self.manifest['works']['goryeo'])
        a = next(i for i in range(window['primary']['start_cp'],
                                  window['primary']['end_cp']) if text[i].strip())
        candidate_id = window['window_id'] + '-c01'
        review = {'schema_version': 1, 'window_id': window['window_id'],
                  'work_id': 'goryeo', 'source_sha256': window['source_sha256'],
                  'segmentation_id': window['segmentation_id'],
                  'attempts': [{'window_id': window['window_id'], 'status': 'proposed',
                                'portion': 'primary', 'candidate_ids': [candidate_id]}],
                  'candidates': [{'candidate_id': candidate_id,
                                  'answer_start_cp': a, 'answer_end_cp': a + 1,
                                  'prior_start_cp': window['primary']['start_cp'],
                                  'prior_end_cp': window['primary']['start_cp'],
                                  'review_record': {'observed': [{'claim': 'one character',
                                      'start_cp': a, 'end_cp': a+1}],
                                      'reconstructed_assumptions': [],
                                      'boundary_reason': 'fixture', 'scene_function': 'fixture',
                                      'selection_reason': 'fixture', 'leakage_check': 'pass'},
                                  'planner_input': {'prior_state': 'before', 'goal': 'event',
                                                    'constraints': ['limit']},
                                  'plan_target': {'virtual_history': 'malformed',
                                                  'character_knowledge': [],
                                                  'scene_spec': {}}}]}
        with self.assertRaisesRegex(ValueError, 'planner payload shape invalid'):
            full.validate_review(window, review, b'', self.manifest, self.policy)

    def test_save_review_requires_primary_before_alternative(self):
        window = full.window_at('goryeo', 1, 1)
        review = {'schema_version': 1, 'window_id': window['window_id'],
                  'work_id': 'goryeo', 'source_sha256': window['source_sha256'],
                  'segmentation_id': window['segmentation_id'],
                  'attempts': [{'window_id': window['window_id'], 'status': 'hold',
                                'portion': 'alternative', 'candidate_ids': [],
                                'reason': 'No complete action',
                                'primary_hold_reason': 'No complete action'}],
                  'candidates': []}
        original_out = full.OUT
        with tempfile.TemporaryDirectory() as tmp:
            full.OUT = Path(tmp)
            try:
                for relative in ('source-manifest.json', 'split-policy.json',
                                 'private/windows/goryeo-b01-w01.json'):
                    source = original_out / relative
                    target = full.OUT / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
                proposal = full.OUT / 'proposal.json'
                proposal.write_text(json.dumps(review), encoding='utf-8')
                args = SimpleNamespace(work='goryeo', band=1, slot=1, input=str(proposal))
                with self.assertRaisesRegex(ValueError, 'alternative requires a saved primary hold'):
                    full.save(args)
                review['attempts'][0].pop('primary_hold_reason')
                review['attempts'][0]['portion'] = 'primary'
                proposal.write_text(json.dumps(review), encoding='utf-8')
                with contextlib.redirect_stdout(io.StringIO()):
                    full.save(args)
                self.assertTrue((full.OUT / 'private/reviews/goryeo-b01-w01.json').exists())
            finally:
                full.OUT = original_out

    def test_corrected_review_requires_current_sha_and_preserves_previous_bytes(self):
        window = full.window_at('goryeo', 1, 1)
        review = {'schema_version': 1, 'window_id': window['window_id'],
                  'work_id': 'goryeo', 'source_sha256': window['source_sha256'],
                  'segmentation_id': window['segmentation_id'],
                  'attempts': [{'window_id': window['window_id'], 'status': 'hold',
                                'portion': 'primary', 'candidate_ids': [],
                                'reason': 'Initial boundary doubt'}], 'candidates': []}
        original_out = full.OUT
        with tempfile.TemporaryDirectory() as tmp:
            full.OUT = Path(tmp)
            try:
                for relative in ('source-manifest.json', 'split-policy.json',
                                 'private/windows/goryeo-b01-w01.json'):
                    target = full.OUT / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((original_out / relative).read_bytes())
                proposal = full.OUT / 'proposal.json'
                proposal.write_text(json.dumps(review), encoding='utf-8')
                args = SimpleNamespace(work='goryeo', band=1, slot=1, input=str(proposal),
                                       replace_review_sha=None, correction_reason=None)
                with contextlib.redirect_stdout(io.StringIO()):
                    full.save(args)
                saved = full.OUT / 'private/reviews/goryeo-b01-w01.json'
                old_bytes = saved.read_bytes()
                old_sha = full.sha(old_bytes)
                review['attempts'][0]['reason'] = 'Confirmed no complete action'
                proposal.write_text(json.dumps(review), encoding='utf-8')
                args.replace_review_sha = '0' * 64
                args.correction_reason = 'Independent reviewer found a boundary error'
                with self.assertRaisesRegex(ValueError, 'current review SHA'):
                    full.save(args)
                self.assertEqual(saved.read_bytes(), old_bytes)
                self.assertFalse((full.OUT / 'private/review-revisions').exists())
                args.replace_review_sha = old_sha
                args.correction_reason = ''
                with self.assertRaisesRegex(ValueError, 'correction reason'):
                    full.save(args)
                self.assertEqual(saved.read_bytes(), old_bytes)
                args.correction_reason = 'Independent reviewer found a boundary error'
                decision = full.OUT / 'private/decisions/goryeo-b01-w01.json'
                decision.parent.mkdir(parents=True, exist_ok=True)
                decision_bytes = json.dumps({'review_sha256': old_sha}).encode()
                decision.write_bytes(decision_bytes)
                with patch.object(full.os, 'replace', side_effect=OSError('atomic replace failed')):
                    with self.assertRaisesRegex(OSError, 'atomic replace failed'):
                        full.save(args)
                self.assertEqual(saved.read_bytes(), old_bytes)
                self.assertEqual(decision.read_bytes(), decision_bytes)
                with contextlib.redirect_stdout(io.StringIO()):
                    full.save(args)
                self.assertNotEqual(saved.read_bytes(), old_bytes)
                self.assertEqual(decision.read_bytes(), decision_bytes)
                self.assertNotEqual(full.sha(saved.read_bytes()), old_sha)
                audits = list((full.OUT / 'private/review-revisions/goryeo-b01-w01').glob('*.json'))
                self.assertEqual(len(audits), 1)
                audit = json.loads(audits[0].read_text())
                self.assertEqual(base64.b64decode(audit['previous_review_base64']), old_bytes)
                self.assertEqual(audit['previous_review_sha256'], old_sha)
                self.assertEqual(audit['new_review_sha256'], full.sha(saved.read_bytes()))
                self.assertNotEqual(old_sha, full.sha(saved.read_bytes()))
            finally:
                full.OUT = original_out


if __name__ == '__main__':
    unittest.main()
