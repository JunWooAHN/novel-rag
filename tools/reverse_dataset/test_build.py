import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import build


class SequentialInputTest(unittest.TestCase):
    def test_show_unit_exposes_current_only_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = build.OUT
            build.OUT = Path(tmp)
            try:
                path = build.OUT / 'private/sections/gogjong-001.json'
                path.parent.mkdir(parents=True)
                packet = {'work_id': 'gogjong', 'batch_id': 'gogjong-001-005',
                          'source_sha256': 'a' * 64, 'segmentation_id': 1,
                          'excerpt_start_cp': 0, 'excerpt_end_cp': 10,
                          'excerpt': 'priorCURNT',
                          'excerpt_sha256': build.sha(b'priorCURNT'),
                          'current_unit': {'section_order': 1, 'start_cp': 5, 'end_cp': 10}}
                path.write_text(json.dumps(packet), encoding='utf-8')
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    build.show_unit(SimpleNamespace(work='gogjong', order=1, prior_start_cp=None))
                shown = json.loads(output.getvalue())
                self.assertEqual(shown['section_text'], 'CURNT')
                self.assertNotIn('prior_text', shown)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    build.show_unit(SimpleNamespace(work='gogjong', order=1, prior_start_cp=2))
                self.assertEqual(json.loads(output.getvalue())['prior_text'], 'ior')
            finally:
                build.OUT = old


if __name__ == '__main__':
    unittest.main()
