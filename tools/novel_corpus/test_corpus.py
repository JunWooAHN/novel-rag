import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import corpus


class CorpusTest(unittest.TestCase):
    def test_number_gap_preceding_span_is_hold(self):
        text = '1화\nA\n3화\nB'
        rows, adjusted = corpus.segment_specs(text, {'markers': [
            {'start_cp': 0, 'label': '1화', 'kind': 'numbered', 'number_claimed': 1, 'confidence': 'confirmed'},
            {'start_cp': 5, 'label': '3화', 'kind': 'numbered', 'number_claimed': 3, 'confidence': 'confirmed'},
        ]})
        self.assertTrue(adjusted)
        self.assertEqual(rows[0][2], 'hold')
        self.assertEqual(rows[1][2], 'confirmed')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.refs = self.base / 'refs'
        self.refs.mkdir()
        self.boundaries = self.base / 'boundaries'
        self.boundaries.mkdir()
        self.db = self.base / 'corpus.sqlite3'
        self.manifest = self.refs / 'manifest.json'
        self.name = '폭군 고종대왕 fixture.txt'
        self.source = self.refs / self.name
        self.raw = '\ufeffhead\r\n1화\r\nA\r\n1화\r\nB\nTAIL'.encode('utf-8')
        self.write_source(self.raw)
        self.write_boundaries()
        self.args = SimpleNamespace(db=self.db, manifest=self.manifest, boundaries=self.boundaries)

    def write_source(self, raw):
        self.source.write_bytes(raw)
        self.manifest.write_text(json.dumps({'files': [{
            'author': 'fixture', 'original_filename': self.name,
            'drive_file_id': 'fixture-drive', 'relative_path': self.name,
            'local_sha256': corpus.digest(raw), 'local_size_bytes': len(raw),
        }]}), encoding='utf-8')

    def write_boundaries(self):
        text = self.raw.decode('utf-8')
        first = text.index('1화')
        second = text.index('1화', first + 1)
        tail = text.index('TAIL')
        config = {'work_id': 'gogjong', 'source_sha256': corpus.digest(self.raw), 'segments': [
            {'start_cp': 0, 'end_cp': first, 'kind': 'frontmatter', 'boundary_status': 'confirmed'},
            {'start_cp': first, 'end_cp': second, 'kind': 'numbered', 'boundary_status': 'confirmed', 'label': '1화', 'number_claimed': 1},
            {'start_cp': second, 'end_cp': tail, 'kind': 'numbered', 'boundary_status': 'confirmed', 'label': '1화', 'number_claimed': 1},
            {'start_cp': tail, 'end_cp': len(text), 'kind': 'tail', 'boundary_status': 'hold', 'label': 'TAIL'},
        ]}
        (self.boundaries / 'gogjong-boundaries.json').write_text(json.dumps(config), encoding='utf-8')

    def ingest(self):
        with contextlib.redirect_stdout(io.StringIO()):
            corpus.ingest(self.args)

    def counts(self):
        with sqlite3.connect(self.db) as conn:
            return tuple(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                         for table in ('works', 'source_revisions', 'segmentations', 'segments'))

    def test_lossless_duplicate_number_and_idempotence(self):
        self.ingest()
        before = self.counts()
        self.ingest()
        self.assertEqual(before, self.counts())
        with sqlite3.connect(self.db) as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            segid = conn.execute('SELECT current_segmentation_id FROM works').fetchone()[0]
            self.assertEqual(corpus.verify_one(conn, 'gogjong', segid), (len(self.raw), 4))
            self.assertEqual(conn.execute("SELECT mapping_status,candidate_count FROM first_50_status WHERE target_number=1").fetchone(), ('conflict', 2))
            self.assertEqual(conn.execute('SELECT number_occurrence FROM segments WHERE number_claimed=1 ORDER BY ordinal').fetchall(), [(1,), (2,)])
        out = self.base / 'export.txt'
        with contextlib.redirect_stdout(io.StringIO()):
            corpus.export(SimpleNamespace(db=self.db, work='gogjong', chapter=None, ordinal=None, output=out, force=False))
        self.assertEqual(out.read_bytes(), self.raw)
        part = self.base / 'segment.txt'
        with contextlib.redirect_stdout(io.StringIO()):
            corpus.export(SimpleNamespace(db=self.db, work='gogjong', chapter=None, ordinal=2, output=part, force=False))
        self.assertEqual(part.read_bytes(), '1화\r\nA\r\n'.encode('utf-8'))
        self.assertNotEqual(part.read_bytes(), self.raw)

    def test_revision_history_and_failed_batch_rollback(self):
        self.ingest()
        original_counts = self.counts()
        new_raw = self.raw + b'\r\nnew'
        self.raw = new_raw
        self.write_source(new_raw)
        # Stale boundary hash makes the entire batch fail before any DB mutation.
        with self.assertRaises(ValueError):
            self.ingest()
        self.assertEqual(original_counts, self.counts())
        self.write_boundaries()
        self.ingest()
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM source_revisions').fetchone()[0], 2)
            for segid, wid in conn.execute('SELECT sg.id,sr.work_id FROM segmentations sg JOIN source_revisions sr ON sr.id=sg.source_revision_id'):
                corpus.verify_one(conn, wid, segid)

    def test_invalid_coverage_rejected(self):
        self.ingest()
        before = self.counts()
        path = self.boundaries / 'gogjong-boundaries.json'
        config = json.loads(path.read_text())
        config['segments'][1]['start_cp'] += 1
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            self.ingest()
        self.assertEqual(before, self.counts())

    def test_same_source_new_boundary_revision_retained(self):
        self.ingest()
        path = self.boundaries / 'gogjong-boundaries.json'
        config = json.loads(path.read_text())
        config['segments'][2]['boundary_status'] = 'hold'
        path.write_text(json.dumps(config))
        self.ingest()
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM source_revisions').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM segmentations').fetchone()[0], 2)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM segments').fetchone()[0], 8)
            self.assertEqual(conn.execute("SELECT mapping_status FROM first_50_status WHERE target_number=1").fetchone()[0], 'conflict')
            self.assertEqual(conn.execute('SELECT boundary_status FROM current_segments WHERE ordinal=3').fetchone()[0], 'hold')
        current = self.counts()
        self.ingest()
        self.assertEqual(current, self.counts())

    def test_section_order_does_not_invent_source_number(self):
        self.raw = '첫 장\nA\n2화\nB'.encode('utf-8')
        self.write_source(self.raw)
        config = {'work_id': 'gogjong', 'source_sha256': corpus.digest(self.raw), 'markers': [
            {'start_cp': 0, 'label': '첫 장', 'kind': 'title_section', 'confidence': 'confirmed'},
            {'start_cp': 6, 'label': '2화', 'kind': 'numbered', 'number_claimed': 2, 'confidence': 'confirmed'},
        ]}
        (self.boundaries / 'gogjong-boundaries.json').write_text(json.dumps(config), encoding='utf-8')
        self.ingest()
        with sqlite3.connect(self.db) as conn:
            rows = conn.execute('SELECT section_order,kind,source_number FROM current_chapter_units ORDER BY section_order').fetchall()
            self.assertEqual(rows, [(1, 'title_section', None), (2, 'numbered', 2)])
            identity = conn.execute('SELECT sha256_raw,segmentation_id,segment_id FROM current_chapter_units WHERE section_order=1').fetchone()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            corpus.sections(SimpleNamespace(db=self.db, work='gogjong', start=1, end=1))
        shown = json.loads(out.getvalue())[0]
        self.assertEqual((shown['source_sha256'], shown['segmentation_id'], shown['segment_id']), identity)
        self.ingest()
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM current_chapter_units').fetchone()[0], 2)

    def test_selected_ingest_ignores_unselected_source(self):
        obj = json.loads(self.manifest.read_text(encoding='utf-8'))
        obj['files'].append({'author': 'unused', 'original_filename': '폴란드 여왕 missing.txt',
                             'drive_file_id': 'missing', 'relative_path': 'missing.txt'})
        self.manifest.write_text(json.dumps(obj), encoding='utf-8')
        self.args.work = ['gogjong']
        self.ingest()
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT work_id FROM works').fetchall(), [('gogjong',)])

    def test_labeled_hold_range_remains_visible_in_section_order(self):
        self.raw = '장 제목\n본문'.encode('utf-8')
        self.write_source(self.raw)
        config = {'work_id': 'gogjong', 'source_sha256': corpus.digest(self.raw), 'markers': [
            {'start_cp': 0, 'label': '장 제목', 'kind': 'unresolved', 'confidence': 'hold'},
        ]}
        (self.boundaries / 'gogjong-boundaries.json').write_text(json.dumps(config), encoding='utf-8')
        self.ingest()
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT section_order,kind,boundary_status,source_number FROM current_chapter_units').fetchall(),
                             [(1, 'unresolved', 'hold', None)])


if __name__ == '__main__':
    unittest.main()
