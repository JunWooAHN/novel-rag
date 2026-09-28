import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import build


class SequentialInputTest(unittest.TestCase):
    def test_archived_cli_writer_is_blocked_without_touching_legacy_files(self):
        result = subprocess.run([sys.executable, str(Path(build.__file__)), 'freeze'],
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('legacy file input writer is archived', result.stderr)

    def test_legacy_writers_are_unconditionally_archived(self):
        args = SimpleNamespace(work='gogjong', start=1, end=1)
        with patch('novel_factory.style.legacy_sqlite.SQLiteLegacyStore.has_import_schema',
                   return_value=False), patch.object(build, 'collect',
                   side_effect=AssertionError('legacy source read')):
            for operation in (build.freeze, build.batch):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaisesRegex(ValueError, 'archived'):
                        operation(args)

    def test_show_unit_uses_only_imported_db_section(self):
        args = SimpleNamespace(work='gogjong', order=1, prior_start_cp=None, db='copy.db')
        with patch('novel_factory.style.legacy_sqlite.SQLiteLegacyStore') as adapter:
            adapter.return_value.get_legacy_section.return_value = {
                'work_id': 'gogjong', 'section_order': 1, 'section_text': 'CURNT',
                'import_id': 'reverse-20260925-i1', 'task_id': None}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                build.show_unit(args)
            adapter.assert_called_once_with('copy.db')
            adapter.return_value.get_legacy_section.assert_called_once_with(
                'reverse-20260925-i1', 'gogjong', 1)
        shown = json.loads(output.getvalue())
        self.assertEqual(shown['section_text'], 'CURNT')
        self.assertIsNone(shown['task_id'])

    def test_prior_context_needs_separate_approval(self):
        args = SimpleNamespace(work='gogjong', order=1, prior_start_cp=0, db='copy.db')
        with self.assertRaisesRegex(ValueError, 'explicitly approved'):
            build.show_unit(args)

    def test_missing_imported_section_fails_closed(self):
        args = SimpleNamespace(work='gogjong', order=1, prior_start_cp=None, db='copy.db')
        with patch('novel_factory.style.legacy_sqlite.SQLiteLegacyStore') as adapter:
            adapter.return_value.get_legacy_section.side_effect = ValueError('not imported')
            with self.assertRaisesRegex(ValueError, 'not imported'):
                build.show_unit(args)



if __name__ == '__main__':
    unittest.main()
