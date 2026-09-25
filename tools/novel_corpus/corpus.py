#!/usr/bin/env python3
"""Lossless UTF-8 novel corpus storage. Only ingest writes to SQLite."""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / 'data/analysis/novel-corpus.sqlite3'
DEFAULT_MANIFEST = ROOT / 'docs/references/manifest.json'
BOUNDARY_DIR = ROOT / 'docs/research/chapter-ingestion'
SCHEMA = Path(__file__).with_name('schema.sql')
WORK_IDS = {
    '폭군 고종대왕': 'gogjong', '성군 순종대왕': 'sunjong',
    '초대 콧수염': 'mustache', '1588 샤인머스캣': '1588',
    '대영제국 선비': 'fair-trade', '고려 신대륙': 'goryeo',
    '폴란드 여왕': 'poland',
}
KINDS = {'numbered', 'title_section', 'prologue', 'epilogue', 'note', 'frontmatter', 'tail', 'unresolved'}
STATUSES = {'confirmed', 'candidate', 'hold'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def work_id(item):
    name = item['original_filename']
    matches = [v for k, v in WORK_IDS.items() if name.startswith(k)]
    if len(matches) != 1:
        raise ValueError(f'unknown work filename: {name}')
    return matches[0]


def relative_path(item):
    rel = Path(item['relative_path'])
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('source path must be inside docs/references')
    return rel


def segment_specs(text, config):
    length = len(text)
    if config is None:
        specs = [dict(start_cp=0, end_cp=length, kind='unresolved', boundary_status='hold', label=None, number_claimed=None, note='boundary file unavailable')]
    elif 'segments' in config:
        specs = [dict(x) for x in config['segments']]
    elif 'markers' in config:
        markers = sorted(config['markers'], key=lambda x: x['start_cp'])
        starts = [x['start_cp'] for x in markers]
        if len(starts) != len(set(starts)):
            raise ValueError('duplicate marker start_cp')
        specs = []
        if not markers or starts[0] > 0:
            specs.append(dict(start_cp=0, end_cp=starts[0] if markers else length,
                              kind='frontmatter' if markers else 'unresolved', boundary_status='hold',
                              label=None, number_claimed=None, note='unmarked prefix or whole source'))
        for i, marker in enumerate(markers):
            spec = dict(marker)
            spec['end_cp'] = starts[i + 1] if i + 1 < len(starts) else length
            specs.append(spec)
    else:
        raise ValueError('boundary JSON needs markers or segments')
    gap_adjusted = False
    for current, following in zip(specs, specs[1:]):
        before, after = current.get('number_claimed'), following.get('number_claimed')
        if (current.get('kind') == 'numbered' and following.get('kind') == 'numbered'
                and isinstance(before, int) and isinstance(after, int) and after > before + 1
                and current.get('boundary_status', current.get('confidence', 'hold')) != 'hold'):
            current['boundary_status'] = 'hold'
            current['note'] = ((current.get('note') or '') +
                               f' Automatic hold: next numbered header jumps from {before} to {after}; intervening episode boundary is unknown.').strip()
            gap_adjusted = True
    normalized = []
    cursor = 0
    occurrences = {}
    for spec in specs:
        start, end = spec['start_cp'], spec['end_cp']
        if not isinstance(start, int) or not isinstance(end, int) or start != cursor or end < start or end > length:
            raise ValueError(f'non-contiguous or invalid codepoint range at {cursor}: {start},{end}')
        if end == start and length != 0:
            raise ValueError('empty segment in nonempty source')
        kind = spec.get('kind', 'unresolved')
        status = spec.get('boundary_status', spec.get('confidence', 'hold'))
        if kind not in KINDS or status not in STATUSES:
            raise ValueError(f'invalid kind/status: {kind}/{status}')
        label = spec.get('label')
        if label is not None and not text.startswith(label, start):
            raise ValueError(f'label mismatch at codepoint {start}')
        number = spec.get('number_claimed')
        if number is not None and (not isinstance(number, int) or number < 1):
            raise ValueError('number_claimed must be a positive integer or null')
        if number is not None:
            occurrences[number] = occurrences.get(number, 0) + 1
        body = text[start:end]
        normalized.append((len(normalized) + 1, kind, status, label, number,
                           occurrences.get(number) if number is not None else None,
                           start, end, digest(body.encode('utf-8')), body, spec.get('note')))
        cursor = end
    if cursor != length or not normalized:
        raise ValueError('segments do not cover full source')
    if ''.join(x[9] for x in normalized) != text:
        raise ValueError('segments fail text reconstruction')
    return normalized, gap_adjusted


def validate_source(item, refs_dir):
    rel = relative_path(item)
    raw = (refs_dir / rel).read_bytes()
    sha = digest(raw)
    if item.get('local_sha256') and sha != item['local_sha256']:
        raise ValueError(f'manifest SHA-256 mismatch: {rel}')
    if item.get('local_size_bytes') is not None and len(raw) != item['local_size_bytes']:
        raise ValueError(f'manifest size mismatch: {rel}')
    text = raw.decode('utf-8')  # Keep U+FEFF, CRLF, final newline, and every codepoint.
    if text.encode('utf-8') != raw:
        raise ValueError('UTF-8 roundtrip mismatch')
    return rel, raw, text, sha


def check_db(conn):
    if conn.execute('PRAGMA user_version').fetchone()[0] != 1:
        raise ValueError('unsupported corpus schema version')
    if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('SQLite integrity_check failed')
    if conn.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('SQLite foreign_key_check failed')


def ingest(args):
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    files = manifest['files']
    refs_dir = args.manifest.parent
    prepared = []
    for item in files:
        wid = work_id(item)
        rel, raw, text, sha = validate_source(item, refs_dir)
        boundary_path = args.boundaries / f'{wid}-boundaries.json'
        config = json.loads(boundary_path.read_text(encoding='utf-8')) if boundary_path.exists() else None
        if config is not None:
            if config.get('work_id') != wid or config.get('source_sha256') != sha:
                raise ValueError(f'boundary work/source mismatch: {boundary_path}')
        segments, gap_adjusted = segment_specs(text, config)
        rule_source = json.dumps(config if config is not None else {'unresolved': True},
                                 ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        if gap_adjusted:
            rule_source += '\nsequence-gap-guard-v1'
        rule_sha = digest(rule_source.encode('utf-8'))
        prepared.append((item, wid, str(rel), raw, text, sha, rule_sha, segments))
    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        if conn.execute('PRAGMA user_version').fetchone()[0] not in (0, 1):
            raise ValueError('unsupported corpus schema version')
        conn.executescript(SCHEMA.read_text(encoding='utf-8'))
        conn.execute('BEGIN IMMEDIATE')
        for item, wid, rel, raw, text, sha, rule_sha, segments in prepared:
            conn.execute('INSERT INTO works(work_id,author,title,drive_file_id,manifest_relative_path) VALUES(?,?,?,?,?) ON CONFLICT(work_id) DO NOTHING',
                         (wid, item['author'], item['original_filename'], item['drive_file_id'], rel))
            conn.execute('INSERT INTO source_revisions(work_id,sha256_raw,byte_size,codepoint_length,relative_path,drive_file_id,utf8_bom,crlf_count,bare_lf_count,bare_cr_count) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(work_id,sha256_raw) DO NOTHING',
                         (wid, sha, len(raw), len(text), rel, item['drive_file_id'], int(raw.startswith(b'\xef\xbb\xbf')),
                          text.count('\r\n'), text.count('\n') - text.count('\r\n'), text.count('\r') - text.count('\r\n')))
            rev_id = conn.execute('SELECT id FROM source_revisions WHERE work_id=? AND sha256_raw=?', (wid, sha)).fetchone()[0]
            conn.execute('INSERT INTO segmentations(source_revision_id,rules_sha256) VALUES(?,?) ON CONFLICT(source_revision_id,rules_sha256) DO NOTHING', (rev_id, rule_sha))
            seg_id = conn.execute('SELECT id FROM segmentations WHERE source_revision_id=? AND rules_sha256=?', (rev_id, rule_sha)).fetchone()[0]
            if not conn.execute('SELECT 1 FROM segments WHERE segmentation_id=?', (seg_id,)).fetchone():
                conn.executemany('INSERT INTO segments(segmentation_id,ordinal,kind,boundary_status,label,number_claimed,number_occurrence,start_cp,end_cp,text_sha256,body,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                                 [(seg_id, *row) for row in segments])
            conn.execute('UPDATE works SET current_segmentation_id=? WHERE work_id=?', (seg_id, wid))
            verify_one(conn, wid, seg_id)
        check_db(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(json.dumps({'db': str(args.db), 'works': len(prepared), 'status': 'ingested'}, ensure_ascii=False))


def verify_one(conn, wid, seg_id):
    rev = conn.execute('SELECT sr.sha256_raw,sr.byte_size,sr.codepoint_length FROM source_revisions sr JOIN segmentations sg ON sg.source_revision_id=sr.id WHERE sg.id=? AND sr.work_id=?', (seg_id, wid)).fetchone()
    if rev is None:
        raise ValueError('segmentation/source/work mismatch')
    rows = conn.execute('SELECT ordinal,start_cp,end_cp,text_sha256,body FROM segments WHERE segmentation_id=? ORDER BY ordinal', (seg_id,)).fetchall()
    cursor = 0
    parts = []
    for expected, (ordinal, start, end, sha, body) in enumerate(rows, 1):
        if ordinal != expected or start != cursor or len(body) != end - start or digest(body.encode('utf-8')) != sha:
            raise ValueError(f'segment coverage/hash mismatch: {wid}/{ordinal}')
        parts.append(body)
        cursor = end
    raw = ''.join(parts).encode('utf-8')
    if not rows or cursor != rev[2] or len(raw) != rev[1] or digest(raw) != rev[0]:
        raise ValueError(f'source reconstruction/hash mismatch: {wid}')
    return len(raw), len(rows)


def read_conn(db):
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def verify(args):
    with read_conn(args.db) as conn:
        check_db(conn)
        result = []
        for wid, seg_id, current in conn.execute('SELECT sr.work_id,sg.id,(w.current_segmentation_id=sg.id) FROM segmentations sg JOIN source_revisions sr ON sr.id=sg.source_revision_id JOIN works w ON w.work_id=sr.work_id ORDER BY sr.work_id,sg.id'):
            size, count = verify_one(conn, wid, seg_id)
            result.append({'work_id': wid, 'segmentation_id': seg_id, 'current': bool(current), 'bytes': size, 'segments': count})
        for item in json.loads(args.manifest.read_text(encoding='utf-8'))['files']:
            wid = work_id(item)
            rel, raw, _, sha = validate_source(item, args.manifest.parent)
            current = conn.execute('SELECT sr.sha256_raw,sr.byte_size,sr.relative_path,sr.drive_file_id FROM works w JOIN segmentations sg ON sg.id=w.current_segmentation_id JOIN source_revisions sr ON sr.id=sg.source_revision_id WHERE w.work_id=?', (wid,)).fetchone()
            if current != (sha, len(raw), str(rel), item['drive_file_id']):
                raise ValueError(f'current DB revision differs from manifest/source: {wid}')
    print(json.dumps({'verified': result}, ensure_ascii=False))


def status(args):
    with read_conn(args.db) as conn:
        result = []
        for wid, title, size, segid in conn.execute('SELECT w.work_id,w.title,sr.byte_size,w.current_segmentation_id FROM works w JOIN segmentations sg ON sg.id=w.current_segmentation_id JOIN source_revisions sr ON sr.id=sg.source_revision_id ORDER BY w.work_id'):
            kinds = dict(conn.execute('SELECT kind,COUNT(*) FROM segments WHERE segmentation_id=? GROUP BY kind', (segid,)))
            boundaries = dict(conn.execute('SELECT boundary_status,COUNT(*) FROM segments WHERE segmentation_id=? GROUP BY boundary_status', (segid,)))
            confirmed_numbered = conn.execute("SELECT COUNT(*) FROM segments WHERE segmentation_id=? AND kind='numbered' AND boundary_status='confirmed'", (segid,)).fetchone()[0]
            mapped = conn.execute("SELECT COUNT(*) FROM first_50_status WHERE work_id=? AND mapping_status='mapped'", (wid,)).fetchone()[0]
            hold = conn.execute("SELECT COUNT(*) FROM first_50_status WHERE work_id=? AND mapping_status IN ('hold','conflict')", (wid,)).fetchone()[0]
            result.append({'work_id': wid, 'title': title, 'bytes': size, 'segments_by_kind': kinds,
                           'segments_by_boundary_status': boundaries, 'numbered_confirmed': confirmed_numbered,
                           'first_50_mapped': mapped, 'first_50_hold_or_conflict': hold,
                           'first_50_unmapped': 50-mapped-hold})
    print(json.dumps(result, ensure_ascii=False, indent=2))


def chapters(args):
    with read_conn(args.db) as conn:
        rows = conn.execute('SELECT f.target_number,f.mapping_status,s.label,s.start_cp,s.end_cp,s.number_occurrence FROM first_50_status f LEFT JOIN segments s ON s.id=f.segment_id WHERE f.work_id=? AND f.target_number BETWEEN ? AND ? ORDER BY f.target_number',
                            (args.work, args.start, args.end)).fetchall()
    print(json.dumps([dict(zip(('target_number','status','label','start_cp','end_cp','number_occurrence'), r)) for r in rows], ensure_ascii=False, indent=2))


def ranges(args):
    with read_conn(args.db) as conn:
        rows = conn.execute('SELECT ordinal,kind,boundary_status,label,number_claimed,number_occurrence,start_cp,end_cp,text_sha256 FROM current_segments WHERE work_id=? AND ordinal BETWEEN ? AND ? ORDER BY ordinal',
                            (args.work, args.start, args.end)).fetchall()
    print(json.dumps([dict(zip(('ordinal','kind','boundary_status','label','number_claimed','number_occurrence','start_cp','end_cp','text_sha256'), r)) for r in rows], ensure_ascii=False, indent=2))


def titles(args):
    with read_conn(args.db) as conn:
        rows = conn.execute("SELECT ROW_NUMBER() OVER (ORDER BY ordinal) AS title_sequence,ordinal,label,start_cp,end_cp,boundary_status FROM current_segments WHERE work_id=? AND kind='title_section' ORDER BY ordinal", (args.work,)).fetchall()
    print(json.dumps([dict(zip(('title_sequence','segment_ordinal','label','start_cp','end_cp','boundary_status'), r)) for r in rows], ensure_ascii=False, indent=2))


def export(args):
    if args.output.resolve().is_relative_to(DEFAULT_MANIFEST.parent.resolve()):
        raise ValueError('export output may not overwrite source copies')
    with read_conn(args.db) as conn:
        if args.ordinal is not None:
            row = conn.execute('SELECT body FROM current_segments WHERE work_id=? AND ordinal=?', (args.work, args.ordinal)).fetchone()
            if row is None:
                raise ValueError('unknown segment ordinal')
            data = row[0].encode('utf-8')
        elif args.chapter is None:
            row = conn.execute('SELECT current_segmentation_id FROM works WHERE work_id=?', (args.work,)).fetchone()
            if row is None:
                raise ValueError('unknown work')
            verify_one(conn, args.work, row[0])
            parts = (r[0] for r in conn.execute('SELECT body FROM segments WHERE segmentation_id=? ORDER BY ordinal', row))
            data = ''.join(parts).encode('utf-8')
        else:
            row = conn.execute('SELECT s.body FROM first_50_status f JOIN segments s ON s.id=f.segment_id WHERE f.work_id=? AND f.target_number=? AND f.mapping_status="mapped"', (args.work, args.chapter)).fetchone()
            if row is None:
                raise ValueError('chapter is not uniquely confirmed')
            data = row[0].encode('utf-8')
    if args.output.exists() and not args.force:
        raise ValueError('output exists; pass --force to replace')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(json.dumps({'output': str(args.output), 'bytes': len(data), 'sha256': digest(data)}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, default=DEFAULT_DB)
    sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('ingest', help='atomically import all manifest works')
    i.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    i.add_argument('--boundaries', type=Path, default=BOUNDARY_DIR)
    v = sub.add_parser('verify')
    v.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    sub.add_parser('status')
    c = sub.add_parser('chapters', help='show first-50 mapping without body text')
    c.add_argument('work', choices=sorted(WORK_IDS.values()))
    c.add_argument('--start', type=int, default=1)
    c.add_argument('--end', type=int, default=50)
    r = sub.add_parser('ranges', help='show current segment ranges without body text')
    r.add_argument('work', choices=sorted(WORK_IDS.values()))
    r.add_argument('--start', type=int, default=1)
    r.add_argument('--end', type=int, default=999999)
    t = sub.add_parser('titles', help='list unnumbered title sections in source order')
    t.add_argument('work', choices=sorted(WORK_IDS.values()))
    e = sub.add_parser('export', help='write exact UTF-8 source or confirmed chapter')
    e.add_argument('work', choices=sorted(WORK_IDS.values()))
    e.add_argument('output', type=Path)
    e.add_argument('--chapter', type=int)
    e.add_argument('--ordinal', type=int, help='export a current segment, including unresolved ranges')
    e.add_argument('--force', action='store_true')
    args = p.parse_args()
    if args.command == 'export' and args.chapter is not None and args.ordinal is not None:
        p.error('--chapter and --ordinal are mutually exclusive')
    try:
        {'ingest': ingest, 'verify': verify, 'status': status, 'chapters': chapters, 'ranges': ranges, 'titles': titles, 'export': export}[args.command](args)
    except (ValueError, OSError, sqlite3.Error, UnicodeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
