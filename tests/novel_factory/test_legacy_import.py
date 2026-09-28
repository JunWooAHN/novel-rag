"""Fixed legacy release stays separate from new analysis tasks and file outputs."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from novel_factory.composition import read_accepted_release, read_legacy_status
from novel_factory.style.legacy_sqlite import SQLiteLegacyStore


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class LegacyReleaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'corpus.sqlite3'
        self.body = 'abcdefgh'
        self.source_sha = sha(self.body.encode())
        conn = sqlite3.connect(self.db)
        conn.executescript('''PRAGMA user_version=1;
            CREATE TABLE works(work_id TEXT PRIMARY KEY);
            CREATE TABLE source_revisions(id INTEGER PRIMARY KEY,work_id TEXT,sha256_raw TEXT);
            CREATE TABLE segmentations(id INTEGER PRIMARY KEY,source_revision_id INTEGER);
            CREATE TABLE segments(segmentation_id INTEGER,start_cp INTEGER,end_cp INTEGER,
                                  text_sha256 TEXT,body TEXT);''')
        conn.execute('INSERT INTO works VALUES(?)', ('gogjong',))
        conn.execute('INSERT INTO source_revisions VALUES(?,?,?)', (1, 'gogjong', self.source_sha))
        conn.execute('INSERT INTO segmentations VALUES(?,?)', (1, 1))
        conn.execute('INSERT INTO segments VALUES(?,?,?,?,?)', (1, 0, 8, self.source_sha, self.body))
        conn.commit(); conn.close()

    def bundle(self):
        record = {'sample_id': 'early-1', 'messages': [], 'metadata': {
            'work_id': 'gogjong', 'role': 'gemma_style', 'split': 'train',
            'source_sha256': self.source_sha, 'segmentation_id': 1,
            'answer_start_cp': 2, 'answer_end_cp': 4,
            'answer_sha256': sha(b'cd')}}
        raw_line = json.dumps(record, ensure_ascii=False, sort_keys=True).encode()
        frozen = {'primary': {'start_cp': 4, 'end_cp': 8, 'section_orders': [2]},
                  'alternative': {'start_cp': 0, 'end_cp': 4, 'section_orders': [1]}}
        window_raw = json.dumps(frozen).encode()
        return {'import_id': 'fixture', 'fingerprint': 'fixed', 'accepted_count': 1,
                'source_hashes': {'gogjong': self.source_sha},
                'selection_policy_hashes': {'initial': 'p1', 'full': 'p2'},
                'artifacts': [('full', 'private/windows/gogjong-b01-w01.json',
                               sha(window_raw), window_raw)],
                'selections': [
                    ('initial', 'early-batch', 'gogjong', 'gemma_style', 'train', 1,
                     self.source_sha, 1, 0, 4, 'r1', 'd1'),
                    ('full', 'gogjong-b01-w01', 'gogjong', 'gemma_style', 'train', 1,
                     self.source_sha, 1, 4, 8, 'r2', 'd2')],
                'attempts': [
                    ('initial', 'early-batch', '1', 'proposed', '', None, 0, 4,
                     sha(b'abcd'), '["early-1"]'),
                    ('full', 'gogjong-b01-w01', 'gogjong-b01-w01', 'hold', 'no complete action',
                     'primary', 4, 8, sha(b'efgh'), '[]')],
                'candidates': [('initial', 'early-batch', 'early-1', 'accepted', 2, 4, 0, 2, '{}')],
                'review_revisions': [('full', 'gogjong-b01-w01',
                    'private/review-revisions/gogjong-b01-w01/old-new.json',
                    'old', 'new', 'corrected evidence')],
                'rows': [('initial', 'gogjong', 'train', 1, 'early-1', raw_line, sha(raw_line))]}

    def test_import_idempotence_and_bounded_read(self):
        store = SQLiteLegacyStore(self.db)
        b = self.bundle()
        self.assertTrue(store.import_bundle(b)['created'])
        self.assertFalse(store.import_bundle(b)['created'])
        release = read_accepted_release(self.db, 'fixture')
        self.assertEqual(release['accepted_count'], 1)
        self.assertEqual(release['rows'][0]['source_answer'], 'cd')
        self.assertEqual(release['rows'][0]['raw_line'].encode(), b['rows'][0][5])
        status = read_legacy_status(self.db, 'fixture', selection_id='gogjong-b01-w01')
        self.assertEqual((status[0]['held'], status[0]['unmade_attempts']), (0, 1))
        self.assertEqual(status[0]['review_revisions'][0]['previous_review_sha256'], 'old')
        self.assertEqual(store.get_legacy_section('fixture', 'gogjong', 1)['section_text'], 'abcd')
        self.assertEqual(store.get_legacy_window('fixture', 'gogjong', 1, 1)['text'], 'efgh')
        self.assertIsNone(store.get_legacy_window('fixture', 'gogjong', 1, 1,
                                                  alternative=True, inspect=True)['review_decision'])
        with self.assertRaisesRegex(ValueError, 'not the imported reviewed selection'):
            store.get_legacy_window('fixture', 'gogjong', 1, 1, alternative=True)

    def test_conflict_and_failed_import_do_not_replace_release(self):
        store = SQLiteLegacyStore(self.db)
        original = self.bundle()
        store.import_bundle(original)
        conflict = self.bundle(); conflict['fingerprint'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'same import ID'):
            store.import_bundle(conflict)
        bad = self.bundle(); bad['import_id'] = 'bad'; bad['rows'][0] = (
            'initial', 'gogjong', 'train', 1, 'ghost', bad['rows'][0][5], bad['rows'][0][6])
        with self.assertRaises(sqlite3.IntegrityError):
            store.import_bundle(bad)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM legacy_imports").fetchone()[0], 1)
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])
        conn.close()

    def test_source_sha_mismatch_is_not_exported(self):
        store = SQLiteLegacyStore(self.db)
        store.import_bundle(self.bundle())
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE segments SET body='xxxxxxxy'")
        conn.commit(); conn.close()
        with self.assertRaisesRegex(ValueError, 'body hash mismatch'):
            read_accepted_release(self.db, 'fixture')

    def test_missing_import_never_falls_back_to_file(self):
        store = SQLiteLegacyStore(self.db)
        with self.assertRaisesRegex(ValueError, 'file fallback is disabled'):
            read_accepted_release(self.db, 'fixture')
        with self.assertRaisesRegex(ValueError, 'file fallback is disabled'):
            store.get_legacy_section('fixture', 'gogjong', 1)
        with self.assertRaisesRegex(ValueError, 'file fallback is disabled'):
            store.get_legacy_window('fixture', 'gogjong', 1, 1)


if __name__ == '__main__':
    unittest.main()
