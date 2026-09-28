"""Synthetic viewer regression tests and an optional browser fixture writer."""

import argparse
import json
from pathlib import Path
import re
import unittest

from test_export import synthetic_release
from viewer import render_html


def embedded_json(html: str, element_id: str):
    match = re.search(r'<script type="application/json" id="' + element_id +
                      r'">(.*?)</script>', html, re.DOTALL)
    if not match:
        raise AssertionError(f'missing embedded JSON: {element_id}')
    return json.loads(match.group(1))


class ViewerTest(unittest.TestCase):
    def setUp(self):
        self.release = synthetic_release()
        self.html = render_html(self.release, Path('/tmp/fixture-corpus.sqlite3'), 'fixture-import')

    def test_accepted_records_and_db_provenance_are_embedded(self):
        data = embedded_json(self.html, 'dataset')
        provenance = embedded_json(self.html, 'build-provenance')
        self.assertEqual(len(data), 272)
        self.assertEqual(data[0]['record']['sample_id'], 'fixture-000')
        self.assertEqual(data[0]['source_answer'], '</script> & 특수검색 __COUNT__ __PROVENANCE__')
        self.assertEqual(provenance['release_id'], 'fixture-reviewed')
        self.assertEqual(provenance['kind'], 'derived_from_analysis_db')
        self.assertNotIn('</script> & 특수검색', self.html)

    def test_search_filters_detail_and_jsonl_download_controls_remain(self):
        for control in ('search', 'work', 'role', 'split', 'release', 'reset', 'list',
                        'detail', 'allDialog', 'allJson'):
            self.assertIn(f'id="{control}"', self.html)
        for behavior in ('function filter()', 'function renderDetail()',
                         'function select(index)', 'navigator.clipboard.writeText',
                         'new Blob([data.map(x=>x.raw_line)'):
            self.assertIn(behavior, self.html)
        self.assertIn('전체 JSONL · 272건', self.html)
        self.assertIn('reviewed-reverse-dataset-272.jsonl', self.html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-fixture', type=Path)
    args, unittest_args = parser.parse_known_args()
    if args.write_fixture:
        output = args.write_fixture.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_html(synthetic_release(),
                                      Path('/tmp/fixture-corpus.sqlite3'), 'fixture-import'),
                          encoding='utf-8')
        print(output)
    else:
        unittest.main(argv=[__file__, *unittest_args])
