import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import full


class WholeWorkWindowTest(unittest.TestCase):
    def test_archived_cli_review_writer_is_blocked(self):
        result = subprocess.run([sys.executable, str(Path(full.__file__)),
                                 'checkpoint', 'goryeo'], capture_output=True,
                                text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('legacy file review writer is archived', result.stderr)

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

    def test_show_window_reads_only_imported_db_selection(self):
        args = SimpleNamespace(work='poland', band=1, slot=1, alternative=False,
                               inspect=False, db='copy.db')
        with patch('novel_factory.style.legacy_sqlite.SQLiteLegacyStore') as adapter, \
             patch.object(full, 'source', side_effect=AssertionError('raw source fallback')):
            adapter.return_value.get_legacy_window.return_value = {
                'window_id': 'poland-b01-w01', 'portion': 'primary', 'text': 'DB BODY'}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                full.show(args)
            adapter.return_value.get_legacy_window.assert_called_once_with(
                'reverse-20260925-i1', 'poland', 1, 1,
                alternative=False, inspect=False)
        self.assertEqual(json.loads(output.getvalue())['text'], 'DB BODY')

    def test_inspect_is_metadata_only_even_for_later_window(self):
        args = SimpleNamespace(work='poland', band=6, slot=8, alternative=False,
                               inspect=True, db='copy.db')
        with patch('novel_factory.style.legacy_sqlite.SQLiteLegacyStore') as adapter:
            adapter.return_value.get_legacy_window.return_value = {
                'window_id': 'poland-b06-w08', 'review_decision': None}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                full.show(args)
            adapter.return_value.get_legacy_window.assert_called_once_with(
                'reverse-20260925-i1', 'poland', 6, 8,
                alternative=False, inspect=True)
        shown = json.loads(output.getvalue())
        self.assertNotIn('text', shown)
        self.assertIsNone(shown['review_decision'])

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

    def test_legacy_writers_are_unconditionally_archived(self):
        args = SimpleNamespace(work='goryeo', band=1, slot=1, input='unused.json')
        # Even a missing import schema cannot reopen the old file writer.
        with patch('novel_factory.style.legacy_sqlite.SQLiteLegacyStore.has_import_schema',
                   return_value=False), patch.object(full, 'collect',
                   side_effect=AssertionError('legacy source read')):
            for operation in (full.freeze, full.init_review, full.save, full.checkpoint):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaisesRegex(ValueError, 'archived'):
                        operation(args)


if __name__ == '__main__':
    unittest.main()
