#!/usr/bin/env python3
"""Prepare and validate bounded whole-work development selection windows."""
import argparse
import base64
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from build import DB, ROOT, ROLES, serialized, write_frozen
from export import validate_model_payload, validate_role_payload, ensure_unique_target, require

OUT = ROOT / 'data/training/reverse-full-20260925'
BANDS = 6
SLOTS = 8
UNITS_PER_WINDOW = 4  # Two primary units and two held-only alternatives.
SPLIT_NAMES = ('train', 'train', 'train', 'train', 'development_validation',
               'development_holdout')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def source(work):
    raw = (ROOT / work['source_path']).read_bytes()
    require(sha(raw) == work['source_sha256'], 'source hash changed')
    text = raw.decode('utf-8')
    require(len(text) == work['source_codepoints'], 'source length changed')
    return text


def collect():
    manifest = {'schema_version': 1, 'source_pool': 'previously_observed_development_only',
                'coordinate_unit': 'Python Unicode codepoint after raw UTF-8 decode, BOM and CRLF preserved',
                'initial_release': 'reverse-20260925', 'works': {}}
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        for wid, role in ROLES.items():
            header = conn.execute('''SELECT w.current_segmentation_id, sr.id source_revision_id,
                    sr.sha256_raw, sr.byte_size, sr.codepoint_length, sr.relative_path
                    FROM works w JOIN segmentations sg ON sg.id=w.current_segmentation_id
                    JOIN source_revisions sr ON sr.id=sg.source_revision_id
                    WHERE w.work_id=?''', (wid,)).fetchone()
            require(header is not None, f'work unavailable: {wid}')
            units = [dict(r) for r in conn.execute('''SELECT section_order,segment_ordinal,segment_id,
                    segmentation_id,kind,boundary_status,source_number,start_cp,end_cp,text_sha256
                    FROM current_chapter_units WHERE work_id=? ORDER BY section_order''', (wid,))]
            require(len(units) > 50 and [u['section_order'] for u in units] ==
                    list(range(1, len(units) + 1)), f'unit order changed: {wid}')
            path = ROOT / 'docs/references' / header['relative_path']
            raw = path.read_bytes()
            require(sha(raw) == header['sha256_raw'] and len(raw) == header['byte_size'] and
                    len(raw.decode('utf-8')) == header['codepoint_length'], f'source differs: {wid}')
            require(units[49]['end_cp'] == units[50]['start_cp'], f'first-50 boundary changed: {wid}')
            manifest['works'][wid] = {
                'role': role, 'source_path': str(path.relative_to(ROOT)),
                'source_sha256': header['sha256_raw'], 'source_bytes': header['byte_size'],
                'source_codepoints': header['codepoint_length'],
                'source_revision_id': header['source_revision_id'],
                'segmentation_id': header['current_segmentation_id'],
                'first_50_end_cp': units[49]['end_cp'], 'units': units,
                'unsegmented_tail_start_cp': units[-1]['end_cp']}
    return manifest


def bands_for(work):
    units = work['units']
    start = work['first_50_end_cp']
    remaining = work['source_codepoints'] - start
    cut_orders = [51]
    for band in range(1, BANDS):
        desired = start + remaining * band / BANDS
        order = min(range(cut_orders[-1] + UNITS_PER_WINDOW * SLOTS, len(units) + 1),
                    key=lambda n: abs(units[n - 1]['start_cp'] - desired))
        cut_orders.append(order)
    cut_orders.append(len(units) + 1)
    result = []
    for i in range(BANDS):
        lo, hi = cut_orders[i], cut_orders[i + 1]
        require(hi - lo >= UNITS_PER_WINDOW * SLOTS, 'too few units in progress band')
        result.append({'band': i + 1, 'split': SPLIT_NAMES[i],
                       'section_order_start': lo, 'section_order_end_exclusive': hi,
                       'start_cp': units[lo - 1]['start_cp'],
                       'end_cp': units[hi - 1]['start_cp'] if hi <= len(units) else work['source_codepoints']})
    return result


def windows_for(wid, work, bands, text):
    result = []
    units = work['units']
    for band in bands:
        lo, hi = band['section_order_start'], band['section_order_end_exclusive']
        count = hi - lo
        last_end = lo
        for slot in range(1, SLOTS + 1):
            ideal = lo + ((2 * slot - 1) * (count - UNITS_PER_WINDOW)) // (2 * SLOTS)
            candidates = [n for n in range(lo, hi - UNITS_PER_WINDOW + 1)
                          if n >= last_end and all(u['boundary_status'] == 'confirmed'
                          for u in units[n - 1:n - 1 + UNITS_PER_WINDOW])]
            require(bool(candidates), f'no confirmed window: {wid}/{band["band"]}/{slot}')
            start_order = min(candidates, key=lambda n: (abs(n - ideal), n))
            last_end = start_order + UNITS_PER_WINDOW
            selected = units[start_order - 1:last_end - 1]
            start_cp, end_cp = selected[0]['start_cp'], selected[-1]['end_cp']
            primary_end_cp = selected[1]['end_cp']
            window_id = f'{wid}-b{band["band"]:02d}-w{slot:02d}'
            result.append({'schema_version': 1, 'window_id': window_id,
                           'work_id': wid, 'role': work['role'], 'band': band['band'],
                           'slot': slot, 'split': band['split'],
                           'source_sha256': work['source_sha256'],
                           'segmentation_id': work['segmentation_id'],
                           'start_cp': start_cp, 'end_cp': end_cp,
                           'window_sha256': sha(text[start_cp:end_cp].encode('utf-8')),
                           'progress_fraction': round((start_cp - work['first_50_end_cp']) /
                                                      (work['source_codepoints'] - work['first_50_end_cp']), 6),
                           'primary': {'start_cp': start_cp, 'end_cp': primary_end_cp,
                                       'section_orders': [u['section_order'] for u in selected[:2]]},
                           'alternative': {'start_cp': primary_end_cp, 'end_cp': end_cp,
                                           'section_orders': [u['section_order'] for u in selected[2:]]},
                           'units': selected})
    require(len(result) == BANDS * SLOTS, f'wrong window count: {wid}')
    return result


def freeze(_args):
    raise ValueError('legacy freeze is archived; use DB workflow commands')
    manifest = collect()
    old = read(ROOT / 'data/training/reverse-20260925/source-manifest.json')
    for wid, work in manifest['works'].items():
        previous = old['works'][wid]
        require(work['source_sha256'] == previous['source_sha256'] and
                work['segmentation_id'] == previous['segmentation_id'] and
                work['first_50_end_cp'] == previous['next_unit_start_cp'],
                f'initial release differs: {wid}')
    policy = {'schema_version': 1, 'source_manifest_sha256': sha(serialized(manifest)),
              'pool': 'development; no unseen final test',
              'sampling_target': 'six progress bands and eight windows per band per work; operational choice',
              'partition_rule': 'bands 1-4 train, 5 development_validation, 6 development_holdout',
              'rules': ['All target, prior, and evidence spans must stay in the chosen window portion and frozen split.',
                        'A window is a reading task, not a claim that scenes are children of source units.',
                        'A scene can cross adjacent source-unit borders inside its window portion.',
                        'Read the alternative portion only after holding the primary portion.',
                        'Hold a window if no complete action has adequate source evidence; do not fill a quota.',
                        'Unresolved source units remain in metadata but cannot be selection targets.',
                        'No initial-release holdout material becomes new training context or target.'],
              'works': {}}
    windows = []
    for wid, work in manifest['works'].items():
        bands = bands_for(work)
        policy['works'][wid] = {'role': work['role'], 'first_50_end_cp': work['first_50_end_cp'],
                                'bands': bands, 'unresolved_units': [u for u in work['units'][50:]
                                if u['boundary_status'] != 'confirmed']}
        windows.extend(windows_for(wid, work, bands, source(work)))
    write_frozen(OUT / 'source-manifest.json', manifest)
    write_frozen(OUT / 'split-policy.json', policy)
    for window in windows:
        write_frozen(OUT / 'private/windows' / (window['window_id'] + '.json'), window)
    print(json.dumps({'source_manifest_sha256': sha(serialized(manifest)),
                      'split_policy_sha256': sha(serialized(policy)),
                      'windows': len(windows), 'by_work': {wid: sum(w['work_id'] == wid for w in windows)
                      for wid in ROLES}}))


def frozen():
    manifest_raw = (OUT / 'source-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    policy = read(OUT / 'split-policy.json')
    require(sha(manifest_raw) == policy['source_manifest_sha256'], 'frozen policy hash mismatch')
    return manifest, policy


def window_at(wid, band, slot):
    require(wid in ROLES and 1 <= band <= BANDS and 1 <= slot <= SLOTS, 'invalid window id')
    return read(OUT / 'private/windows' / f'{wid}-b{band:02d}-w{slot:02d}.json')


def require_prior_reviews(wid, band, slot):
    position = (band - 1) * SLOTS + slot
    for earlier in range(1, position):
        ep = OUT / 'private/reviews' / f'{wid}-b{(earlier - 1)//SLOTS + 1:02d}-w{(earlier - 1)%SLOTS + 1:02d}.json'
        require(ep.exists(), f'previous window not saved: {ep.name}')


def validate_review(window, review, raw, manifest, policy):
    wid = window['work_id']
    work = manifest['works'][wid]
    band = policy['works'][wid]['bands'][window['band'] - 1]
    require(window['source_sha256'] == work['source_sha256'] and
            window['segmentation_id'] == work['segmentation_id'] and
            window['split'] == band['split'] and
            band['start_cp'] <= window['start_cp'] < window['end_cp'] <= band['end_cp'],
            'window escapes frozen source/partition')
    text = source(work)
    require(sha(text[window['start_cp']:window['end_cp']].encode('utf-8')) ==
            window['window_sha256'], 'window source changed')
    require((review.get('schema_version'), review.get('window_id'), review.get('work_id'),
             review.get('source_sha256'), review.get('segmentation_id')) ==
            (1, window['window_id'], wid, work['source_sha256'], work['segmentation_id']),
            'review identity differs')
    attempts = review.get('attempts')
    require(isinstance(attempts, list) and len(attempts) == 1, 'one window attempt required')
    attempt = attempts[0]
    require(attempt.get('window_id') == window['window_id'] and
            attempt.get('status') in ('proposed', 'hold') and
            attempt.get('portion') in ('primary', 'alternative'), 'invalid attempt')
    if attempt['portion'] == 'alternative':
        require(bool(attempt.get('primary_hold_reason')), 'alternative requires primary hold reason')
    candidates = review.get('candidates')
    require(isinstance(candidates, list), 'candidates array required')
    ids = [c.get('candidate_id') for c in candidates]
    require(len(ids) == len(set(ids)) and all(isinstance(cid, str) and
            cid.startswith(window['window_id'] + '-') for cid in ids), 'candidate ids invalid')
    require(attempt.get('candidate_ids') == ids and bool(ids) == (attempt['status'] == 'proposed'),
            'attempt/candidate references mismatch')
    require(attempt['status'] == 'proposed' or bool(attempt.get('reason')), 'hold reason missing')
    portion = window[attempt['portion']]
    for c in candidates:
        a,b,pa,pb = (c.get(k) for k in ('answer_start_cp','answer_end_cp','prior_start_cp','prior_end_cp'))
        require(all(isinstance(v,int) for v in (a,b,pa,pb)) and
                portion['start_cp'] <= pa <= pb <= a < b <= portion['end_cp'],
                f'candidate escapes chosen portion: {c.get("candidate_id")}')
        require(text[a:b].strip(), 'empty target')
        rec = c.get('review_record')
        require(isinstance(rec,dict) and rec.get('leakage_check') == 'pass' and
                bool(rec.get('boundary_reason')) and bool(rec.get('scene_function')) and
                bool(rec.get('selection_reason')) and isinstance(rec.get('observed'),list) and
                bool(rec['observed']) and isinstance(rec.get('reconstructed_assumptions'),list),
                'review record incomplete')
        for ev in rec['observed']:
            require(isinstance(ev.get('claim'),str) and bool(ev['claim']) and
                    isinstance(ev.get('start_cp'),int) and isinstance(ev.get('end_cp'),int) and
                    a <= ev['start_cp'] < ev['end_cp'] <= b,
                    'observed evidence outside target')
        if work['role'] == 'gemma_style':
            require('planner_input' not in c and 'plan_target' not in c and
                    isinstance(c.get('writer_input'),dict), 'writer role mismatch')
            validate_role_payload(c, work['role'], c['candidate_id'])
            model_input = c['writer_input']
        else:
            require('writer_input' not in c and isinstance(c.get('planner_input'),dict) and
                    isinstance(c.get('plan_target'),dict),
                    'planner role mismatch')
            validate_role_payload(c, work['role'], c['candidate_id'])
            model_input = c['planner_input']
            validate_model_payload(c['plan_target'], work, 'plan_target')
        validate_model_payload(model_input, work, 'model_input')
        require(text[a:b] not in json.dumps(model_input,ensure_ascii=False), 'target leaked into input')
    return text


def show(args):
    from novel_factory.style.legacy_import import IMPORT_ID
    from novel_factory.style.legacy_sqlite import SQLiteLegacyStore
    result = SQLiteLegacyStore(getattr(args, 'db', DB)).get_legacy_window(
        IMPORT_ID, args.work, args.band, args.slot,
        alternative=args.alternative, inspect=args.inspect)
    print(json.dumps(result, ensure_ascii=False))


def init_review(args):
    raise ValueError('legacy review packet is archived; use DB submit/review')
    manifest, policy = frozen()
    w = window_at(args.work,args.band,args.slot)
    require_prior_reviews(args.work,args.band,args.slot)
    portion = 'alternative' if args.alternative else 'primary'
    if args.alternative:
        path = OUT / 'private/reviews' / (w['window_id'] + '.json')
        require(path.exists() and read(path)['attempts'][0]['status'] == 'hold',
                'alternative requires saved primary hold')
    attempt = {'window_id':w['window_id'],'status':'hold','portion':portion,
               'candidate_ids':[],'reason':''}
    if args.alternative:
        attempt['primary_hold_reason'] = read(path)['attempts'][0]['reason']
    print(json.dumps({'schema_version':1,'window_id':w['window_id'],'work_id':args.work,
                      'source_sha256':w['source_sha256'],
                      'segmentation_id':w['segmentation_id'],
                      'attempts':[attempt],'candidates':[]},ensure_ascii=False,indent=2))


def save(args):
    raise ValueError('legacy review file writing is archived; use DB submit/review')
    manifest, policy = frozen()
    w = window_at(args.work,args.band,args.slot)
    require_prior_reviews(args.work,args.band,args.slot)
    raw=Path(args.input).read_bytes()
    review=json.loads(raw)
    validate_review(w,review,raw,manifest,policy)
    path=OUT/'private/reviews'/(w['window_id']+'.json')
    expected_sha=getattr(args,'replace_review_sha',None)
    correction_reason=getattr(args,'correction_reason',None)
    if path.exists():
        old_raw=path.read_bytes()
        old=json.loads(old_raw)
        old_sha=sha(old_raw)
        require(expected_sha == old_sha and bool(correction_reason and correction_reason.strip()),
                'replacement requires current review SHA and correction reason')
        require(sha(raw) != old_sha, 'replacement review is unchanged')
        if review['attempts'][0]['portion']=='alternative':
            require(old['attempts'][0]['status']=='hold' and
                    old['attempts'][0]['portion']=='primary' and
                    review['attempts'][0]['primary_hold_reason']==old['attempts'][0]['reason'],
                    'alternative requires the saved primary hold reason')
        audit={'schema_version':1,'window_id':w['window_id'],
               'previous_review_sha256':old_sha,'new_review_sha256':sha(raw),
               'correction_reason':correction_reason.strip(),
               'previous_review_base64':base64.b64encode(old_raw).decode('ascii')}
        audit_path=OUT/'private/review-revisions'/w['window_id']/(old_sha+'-'+sha(raw)+'.json')
        write_frozen(audit_path,audit)
        require(sha(path.read_bytes())==old_sha,'saved review changed during replacement')
    else:
        require(expected_sha is None and correction_reason is None,
                'replacement flags require an existing saved review')
        require(review['attempts'][0]['portion']=='primary',
                'alternative requires a saved primary hold')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.'+w['window_id']+'-',
                                         suffix='.tmp', delete=False) as file:
            temporary=Path(file.name)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps({'review_path':str(path),'review_sha256':sha(raw),
                      'status':review['attempts'][0]['status'],
                      'superseded_review_sha256':expected_sha,
                      'checkpoint_due':((args.band-1)*SLOTS+args.slot)%4==0}))


def checkpoint(args):
    raise ValueError('legacy checkpoint file writing is archived; use DB resume')
    manifest,policy=frozen()
    require(args.work in manifest['works'], 'unknown work')
    saved=[]
    for band in range(1,BANDS+1):
        for slot in range(1,SLOTS+1):
            w=window_at(args.work,band,slot)
            path=OUT/'private/reviews'/(w['window_id']+'.json')
            if not path.exists():
                continue
            raw=path.read_bytes()
            review=json.loads(raw)
            validate_review(w,review,raw,manifest,policy)
            saved.append({'window_id':w['window_id'],'review_sha256':sha(raw),
                          'status':review['attempts'][0]['status']})
    require([x['window_id'] for x in saved] ==
            [f'{args.work}-b{(i//SLOTS)+1:02d}-w{(i%SLOTS)+1:02d}' for i in range(len(saved))],
            'review sequence has gap')
    result={'schema_version':1,'work_id':args.work,'source_sha256':manifest['works'][args.work]['source_sha256'],
            'source_manifest_sha256':sha((OUT/'source-manifest.json').read_bytes()),
            'split_policy_sha256':sha((OUT/'split-policy.json').read_bytes()),
            'saved_count':len(saved),'windows':saved,
            'next_window_id':f'{args.work}-b{len(saved)//SLOTS+1:02d}-w{len(saved)%SLOTS+1:02d}'
            if len(saved)<BANDS*SLOTS else None}
    path=OUT/'private/checkpoints'/f'{args.work}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(serialized(result))
    print(json.dumps({'checkpoint_path':str(path),'saved_count':len(saved),
                      'next_window_id':result['next_window_id']}))


def export(args):
    from novel_factory.style.legacy_import import IMPORT_ID
    from export import export_release
    output_dir = getattr(args, 'output_dir', None) or (
        ROOT / 'data/training/db-derived' / IMPORT_ID / 'private/export')
    print(json.dumps(export_release(getattr(args, 'db', DB), IMPORT_ID, output_dir),
                     ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    subs.add_parser('freeze')
    p=subs.add_parser('show-window');p.add_argument('work',choices=sorted(ROLES));p.add_argument('band',type=int);p.add_argument('slot',type=int);p.add_argument('--alternative',action='store_true');p.add_argument('--inspect',action='store_true');p.add_argument('--db',type=Path,default=DB)
    p=subs.add_parser('init-review');p.add_argument('work',choices=sorted(ROLES));p.add_argument('band',type=int);p.add_argument('slot',type=int);p.add_argument('--alternative',action='store_true')
    p=subs.add_parser('save-review');p.add_argument('work',choices=sorted(ROLES));p.add_argument('band',type=int);p.add_argument('slot',type=int);p.add_argument('input');p.add_argument('--replace-review-sha');p.add_argument('--correction-reason')
    p=subs.add_parser('checkpoint');p.add_argument('work',choices=sorted(ROLES))
    e=subs.add_parser('export');e.add_argument('--db',type=Path,default=DB);e.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    try:
        if args.command in ('freeze', 'init-review', 'save-review', 'checkpoint'):
            raise ValueError('legacy file review writer is archived; use novel-factory DB workflow')
        {'show-window': show, 'export': export}[args.command](args)
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as exc:
        parser.exit(1,f'error: {exc}\n')


if __name__=='__main__': main()
