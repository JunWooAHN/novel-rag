#!/usr/bin/env python3
"""Freeze source/split metadata and make bounded, local reviewer excerpts."""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))  # direct legacy CLI can reach the local product package
DB = ROOT / 'data/analysis/novel-corpus.sqlite3'
OUT = ROOT / 'data/training/reverse-20260925'
ROLES = {'gogjong': 'gemma_style', 'goryeo': 'sota_planning', 'poland': 'sota_planning'}
SPLITS = ((1, 30, 'train'), (31, 40, 'development_validation'),
          (41, 50, 'development_holdout'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def serialized(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def write_frozen(path, value):
    data = serialized(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'frozen metadata differs: {path}')
        return
    path.write_bytes(data)


def corpus():
    conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def collect():
    result = {'schema_version': 1, 'source_pool': 'previously_observed_development_only',
              'coordinate_unit': 'Python Unicode codepoint after raw UTF-8 decode, BOM and CRLF preserved',
              'works': {}}
    with corpus() as conn:
        for wid, role in ROLES.items():
            header = conn.execute('''SELECT w.current_segmentation_id, sr.id AS source_revision_id,
                                            sr.sha256_raw, sr.byte_size, sr.codepoint_length,
                                            sr.relative_path
                                     FROM works w JOIN segmentations sg ON sg.id=w.current_segmentation_id
                                     JOIN source_revisions sr ON sr.id=sg.source_revision_id
                                     WHERE w.work_id=?''', (wid,)).fetchone()
            if header is None:
                raise ValueError(f'work unavailable: {wid}')
            source_path = ROOT / 'docs/references' / header['relative_path']
            raw = source_path.read_bytes()
            if sha(raw) != header['sha256_raw'] or len(raw) != header['byte_size']:
                raise ValueError(f'raw source differs: {wid}')
            units = [dict(row) for row in conn.execute('''SELECT section_order,segment_ordinal,segment_id,
                    segmentation_id,kind,boundary_status,source_number,start_cp,end_cp,text_sha256
                    FROM current_chapter_units WHERE work_id=? AND section_order BETWEEN 1 AND 51
                    ORDER BY section_order''', (wid,))]
            if len(units) != 51 or [u['section_order'] for u in units] != list(range(1, 52)):
                raise ValueError(f'need 51 consecutive section boundaries: {wid}')
            result['works'][wid] = {'role': role,
                'source_path': str(source_path.relative_to(ROOT)),
                'source_sha256': header['sha256_raw'], 'source_bytes': header['byte_size'],
                'source_codepoints': header['codepoint_length'],
                'source_revision_id': header['source_revision_id'],
                'segmentation_id': header['current_segmentation_id'],
                'units': units[:50], 'next_unit_start_cp': units[50]['start_cp']}
    return result


def policy_for(manifest):
    result = {'schema_version': 1, 'source_manifest_sha256': sha(serialized(manifest)),
              'pool': 'development; no unseen final test',
              'references': 'train only',
              'unit_meaning': 'source-order heading; not an inferred official episode number',
              'rules': [
                  'Target, prior context, evidence, and all derived variants stay inside one split codepoint range.',
                  'Overlapping targets, windows, contexts, and derivative questions form one split group.',
                  'A scene may cross section headings but may not cross a split boundary; count one scene once.',
                  'At each eligible section attempt one complete action; hold missing evidence instead of filling a quota.',
                  'Writer input contains no source path, coordinate, target wording, later prose, or unauthorized future knowledge.',
                  'Reviewer observation and reconstruction remain distinct; target is exact raw-source text slice.'
              ], 'works': {}}
    for wid, work in manifest['works'].items():
        units = work['units']
        bounds = [0, units[30]['start_cp'], units[40]['start_cp'], work['next_unit_start_cp']]
        result['works'][wid] = {'role': work['role'], 'splits': [
            {'name': name, 'section_order_start': start, 'section_order_end': end,
             'start_cp': bounds[i], 'end_cp': bounds[i + 1]}
            for i, (start, end, name) in enumerate(SPLITS)]}
    return result


def freeze(_args):
    raise ValueError('legacy freeze is archived; use DB workflow commands')
    manifest = collect()
    write_frozen(OUT / 'source-manifest.json', manifest)
    write_frozen(OUT / 'split-policy.json', policy_for(manifest))
    print(json.dumps({'works': list(manifest['works']), 'units_per_work': 50,
                      'source_manifest_sha256': sha(serialized(manifest))}))


def batch(args):
    raise ValueError('legacy batch file writing is archived; use DB workflow commands')
    if not (1 <= args.start <= args.end <= 50):
        raise ValueError('batch section order must be within 1–50')
    manifest_bytes = (OUT / 'source-manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    policy = json.loads((OUT / 'split-policy.json').read_bytes())
    if sha(manifest_bytes) != policy['source_manifest_sha256']:
        raise ValueError('split policy and source manifest differ')
    work = manifest['works'][args.work]
    units = work['units'][args.start - 1:args.end]
    if not units or len(units) != args.end - args.start + 1 or len(units) > 5:
        raise ValueError('batch must cover 1–5 frozen units')
    split = next((s for s in policy['works'][args.work]['splits']
                  if s['section_order_start'] <= args.start <= args.end <= s['section_order_end']), None)
    if split is None:
        raise ValueError('batch crosses split boundary')
    source = (ROOT / work['source_path']).read_bytes()
    if sha(source) != work['source_sha256']:
        raise ValueError('source hash changed')
    text = source.decode('utf-8')
    packet = {'schema_version': 1, 'batch_id': f'{args.work}-{args.start:03d}-{args.end:03d}',
              'work_id': args.work, 'role': work['role'], 'split': split['name'],
              'source_sha256': work['source_sha256'], 'segmentation_id': work['segmentation_id'],
              'coordinate_unit': manifest['coordinate_unit'],
              'excerpt_start_cp': split['start_cp'], 'excerpt_end_cp': units[-1]['end_cp'],
              'units': units, 'section_inputs': []}
    for unit in units:
        order = unit['section_order']
        start_cp, end_cp = split['start_cp'], unit['end_cp']
        if not start_cp < end_cp <= split['end_cp']:
            raise ValueError('section input exceeds frozen split')
        excerpt = text[start_cp:end_cp]
        section = {'schema_version': 1, 'batch_id': packet['batch_id'],
                   'work_id': args.work, 'role': work['role'], 'split': split['name'],
                   'source_sha256': work['source_sha256'], 'segmentation_id': work['segmentation_id'],
                   'current_unit': unit, 'excerpt_start_cp': start_cp, 'excerpt_end_cp': end_cp,
                   'excerpt_sha256': sha(excerpt.encode('utf-8')), 'excerpt': excerpt}
        section_path = OUT / 'private/sections' / f'{args.work}-{order:03d}.json'
        write_frozen(section_path, section)
        packet['section_inputs'].append({'section_order': order,
                                         'path': str(section_path.relative_to(ROOT)),
                                         'excerpt_end_cp': end_cp,
                                         'excerpt_sha256': section['excerpt_sha256']})
    path = OUT / 'private/batches' / f'{packet["batch_id"]}.json'
    write_frozen(path, packet)
    print(json.dumps({'batch_index': str(path), 'units': len(units),
                      'first_section_path': str(ROOT / packet['section_inputs'][0]['path']),
                      'split': split['name']}))


def show_unit(args):
    if args.prior_start_cp is not None:
        raise ValueError('prior context requires its own explicitly approved DB window')
    from novel_factory.style.legacy_import import IMPORT_ID
    from novel_factory.style.legacy_sqlite import SQLiteLegacyStore
    result = SQLiteLegacyStore(getattr(args, 'db', DB)).get_legacy_section(
        IMPORT_ID, args.work, args.order)
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('freeze')
    b = subs.add_parser('batch')
    b.add_argument('work', choices=sorted(ROLES))
    b.add_argument('start', type=int)
    b.add_argument('end', type=int)
    u = subs.add_parser('show-unit', help='show only the current section unless prior context is requested')
    u.add_argument('work', choices=sorted(ROLES))
    u.add_argument('order', type=int)
    u.add_argument('--prior-start-cp', type=int)
    u.add_argument('--db', type=Path, default=DB)
    args = parser.parse_args()
    try:
        if args.command != 'show-unit':
            raise ValueError('legacy file input writer is archived; use novel-factory DB workflow')
        show_unit(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'error: {exc}\n')


if __name__ == '__main__':
    main()
