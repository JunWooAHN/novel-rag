#!/usr/bin/env python3
"""Export the accepted, fixed DB release as derived development JSONL.

Legacy candidate validators remain for the existing review fixtures and
``full.py``. The operational export path only uses the public release reader.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/training/reverse-20260925'
WORKS = ('gogjong', 'goryeo', 'poland')
SPLITS = ('train', 'development_validation', 'development_holdout')
PROVENANCE_TOKENS = {'source', 'evidence', 'excerpt', 'segment', 'section', 'chapter',
                     'startcp', 'endcp', 'cpstart', 'cpend', 'sha256'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_model_payload(value, work, label):
    """Keep corpus locations and identifiers out of model-visible content."""
    if isinstance(value, dict):
        for key, child in value.items():
            snake_key = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', key)
            key_parts = set(re.findall(r'[a-z0-9]+', snake_key.lower()))
            normalized_key = ''.join(re.findall(r'[a-z0-9]+', key.lower()))
            has_coordinate = (('cp' in key_parts and bool({'start', 'end'} & key_parts)) or
                              any(token in normalized_key for token in
                                  ('startcp', 'endcp', 'cpstart', 'cpend')))
            has_provenance = (bool(key_parts & PROVENANCE_TOKENS) or
                              normalized_key.startswith(('source', 'evidence', 'excerpt',
                                                         'segment', 'section', 'chapter')))
            require(not (has_coordinate or has_provenance),
                    f'provenance key in model payload: {label}/{key}')
            validate_model_payload(child, work, f'{label}/{key}')
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_model_payload(child, work, f'{label}/{index}')
    elif isinstance(value, str):
        require(work['source_path'] not in value and work['source_sha256'] not in value,
                f'source identity in model payload: {label}')


def ensure_unique_target(answer, split_name, seen_targets):
    normalized = ' '.join(answer.split())
    require(normalized not in seen_targets,
            f'duplicate normalized target across samples/splits: {split_name}')
    seen_targets.add(normalized)


def validate_role_payload(candidate, role, label):
    """Check the small shared writer/planner shape before serializing model content."""
    if role == 'gemma_style':
        payload = candidate.get('writer_input')
        require(isinstance(payload, dict), f'writer input missing: {label}')
        require(isinstance(payload.get('prior_context'), str) and
                isinstance(payload.get('virtual_history'), list) and
                all(isinstance(x, dict) for x in payload['virtual_history']) and
                isinstance(payload.get('character_knowledge'), list) and
                all(isinstance(x, dict) for x in payload['character_knowledge']) and
                isinstance(payload.get('scene_spec'), dict), f'writer payload shape invalid: {label}')
    else:
        payload = candidate.get('planner_input')
        target = candidate.get('plan_target')
        require(isinstance(payload, dict) and isinstance(target, dict),
                f'planner input/target missing: {label}')
        require(isinstance(payload.get('prior_state'), str) and bool(payload['prior_state']) and
                isinstance(payload.get('goal'), str) and bool(payload['goal']) and
                isinstance(payload.get('constraints'), list) and bool(payload['constraints']) and
                all(isinstance(x, str) for x in payload['constraints']) and
                isinstance(target.get('virtual_history'), list) and
                all(isinstance(x, dict) for x in target['virtual_history']) and
                isinstance(target.get('character_knowledge'), list) and
                all(isinstance(x, dict) for x in target['character_knowledge']) and
                isinstance(target.get('scene_spec'), dict), f'planner payload shape invalid: {label}')


def validate_batch(bundle, review, decision, work, split, text, review_raw=None):
    bid = bundle['batch_id']
    require((review.get('schema_version'), review.get('batch_id'), review.get('work_id'),
             review.get('source_sha256'), review.get('segmentation_id')) ==
            (1, bid, bundle['work_id'], bundle['source_sha256'], bundle['segmentation_id']),
            f'batch identity mismatch: {bid}')
    require((decision.get('schema_version'), decision.get('batch_id')) == (2, bid),
            f'decision identity mismatch: {bid}')
    if review_raw is None:
        review_raw = json.dumps(review, ensure_ascii=False, sort_keys=True).encode('utf-8')
    require(decision.get('review_sha256') == digest(review_raw),
            f'decision review hash mismatch: {bid}')
    require(bool(decision.get('reviewer')), f'missing independent reviewer: {bid}')
    unit_ids = [u['section_order'] for u in bundle['units']]
    attempts = review.get('attempts', [])
    require(sorted(a.get('section_order') for a in attempts) == unit_ids,
            f'every section needs exactly one attempt: {bid}')
    candidates = review.get('candidates', [])
    by_id = {c.get('candidate_id'): c for c in candidates}
    require(len(by_id) == len(candidates) and all(by_id), f'duplicate candidate ID: {bid}')
    used = set()
    for attempt in attempts:
        require(attempt.get('status') in ('proposed', 'hold', 'reject'), f'invalid attempt: {bid}')
        ids = attempt.get('candidate_ids', [])
        require(isinstance(ids, list) and all(cid in by_id for cid in ids), f'unknown candidate: {bid}')
        require(bool(ids) == (attempt['status'] == 'proposed'), f'attempt/candidate mismatch: {bid}')
        require(attempt['status'] == 'proposed' or bool(attempt.get('reason')), f'hold reason missing: {bid}')
        for cid in ids:
            require(attempt['section_order'] in by_id[cid]['covered_section_orders'],
                    f'candidate coverage mismatch: {bid}')
            used.add(cid)
    require(used == set(by_id), f'unreferenced candidate: {bid}')
    accepted = decision.get('accepted_candidate_ids', [])
    held = decision.get('hold_candidate_ids', [])
    rejected = decision.get('rejected_candidate_ids', [])
    require(all(isinstance(x, list) for x in (accepted, held, rejected)) and
            len(accepted + held + rejected) == len(set(accepted + held + rejected)) and
            set(accepted + held + rejected) == set(by_id), f'incomplete decision: {bid}')
    units = {u['section_order']: u for u in bundle['units']}
    attempts_by_order = {a['section_order']: a for a in attempts}
    for order, unit in units.items():
        if unit.get('boundary_status') == 'hold' and unit.get('kind') == 'unresolved':
            require(attempts_by_order[order]['status'] == 'hold',
                    f'unresolved unit must remain hold: {bid}/{order}')
    output = []
    for cid in accepted:
        c = by_id[cid]
        covered = c['covered_section_orders']
        require(covered and sorted(set(covered)) == list(range(min(covered), max(covered) + 1)) and
                set(covered) <= set(units), f'noncontiguous covered sections: {bid}/{cid}')
        a, b = c['answer_start_cp'], c['answer_end_cp']
        pa, pb = c['prior_start_cp'], c['prior_end_cp']
        require(split['start_cp'] <= bundle['excerpt_start_cp'] <= pa <= pb <= a < b <=
                bundle['excerpt_end_cp'] <= split['end_cp'], f'answer/prior escapes split: {bid}/{cid}')
        require(units[min(covered)]['start_cp'] <= a < b <= units[max(covered)]['end_cp'],
                f'answer escapes cited units: {bid}/{cid}')
        require(all(attempts_by_order[n]['status'] == 'proposed' and
                    cid in attempts_by_order[n]['candidate_ids'] for n in covered),
                f'accepted candidate includes held/unreferenced unit: {bid}/{cid}')
        require(all(b <= u['start_cp'] or a >= u['end_cp'] for u in units.values()
                    if u.get('boundary_status') == 'hold' and u.get('kind') == 'unresolved'),
                f'accepted target overlaps unresolved unit: {bid}/{cid}')
        for n in covered:
            require(a < units[n]['end_cp'] and b > units[n]['start_cp'],
                    f'answer does not intersect covered unit: {bid}/{cid}')
        rec = c['review_record']
        require(rec.get('leakage_check') == 'pass', f'leakage review not passed: {bid}/{cid}')
        for ev in rec.get('observed', []):
            require(split['start_cp'] <= ev['start_cp'] < ev['end_cp'] <= b,
                    f'observation uses future or other split: {bid}/{cid}')
        answer = text[a:b]
        require(answer.strip(), f'empty target: {bid}/{cid}')
        role = work['role']
        if role == 'gemma_style':
            require('planner_input' not in c and 'plan_target' not in c, f'mixed role fields: {bid}/{cid}')
            validate_role_payload(c, role, f'{bid}/{cid}')
            validate_model_payload(c['writer_input'], work, f'{bid}/{cid}/writer_input')
            user_content = json.dumps(c['writer_input'], ensure_ascii=False, sort_keys=True)
            assistant_content = answer
            target_basis = 'observed_exact_source_slice'
        else:
            require('writer_input' not in c, f'mixed role fields: {bid}/{cid}')
            validate_role_payload(c, role, f'{bid}/{cid}')
            planner = c['planner_input']
            validate_model_payload(planner, work, f'{bid}/{cid}/planner_input')
            user_content = json.dumps(planner, ensure_ascii=False, sort_keys=True)
            plan_target = c['plan_target']
            validate_model_payload(plan_target, work, f'{bid}/{cid}/plan_target')
            assistant_content = json.dumps(plan_target, ensure_ascii=False, sort_keys=True)
            target_basis = 'reviewed_reconstruction_not_author_intent'
        require(answer not in user_content and work['source_path'] not in user_content and
                work['source_sha256'] not in user_content and assistant_content not in user_content,
                f'model input contains target/source identity: {bid}/{cid}')
        output.append({'sample_id': cid, 'messages': [
            {'role': 'user', 'content': user_content}, {'role': 'assistant', 'content': assistant_content}],
            'metadata': {'work_id': bundle['work_id'], 'role': role, 'split': bundle['split'],
                         'source_sha256': work['source_sha256'], 'segmentation_id': work['segmentation_id'],
                         'answer_start_cp': a, 'answer_end_cp': b, 'answer_sha256': digest(answer.encode('utf-8')),
                         'covered_section_orders': covered, 'target_basis': target_basis,
                         'reviewed_by': decision['reviewer'], 'input_characters': len(user_content),
                         'output_characters': len(assistant_content),
                         'source_answer_characters': len(answer), 'truncated': False,
                         'token_validation': 'not_run'}})
    return output, {'attempted_units': len(attempts), 'proposed_candidates': len(candidates),
                    'accepted': len(accepted), 'held': len(held), 'rejected': len(rejected),
                    'unit_holds': sum(a['status'] == 'hold' for a in attempts)}


def checked_release(release):
    """Check the public release shape without querying its private DB tables."""
    require(isinstance(release, dict) and isinstance(release.get('release_id'), str)
            and isinstance(release.get('rows'), list), 'invalid DB release result')
    require(release.get('accepted_count') == len(release['rows']), 'accepted release count differs from rows')
    require(isinstance(release.get('source_hashes'), dict) and
            isinstance(release.get('selection_policy_hashes'), dict), 'release provenance missing')
    seen = set()
    for item in release['rows']:
        require(isinstance(item, dict) and set(item) >=
                {'release', 'record', 'raw_line', 'source_answer'}, 'invalid release row')
        record, raw_line, answer = item['record'], item['raw_line'], item['source_answer']
        require(item['release'] in ('initial', 'full') and isinstance(record, dict)
                and isinstance(raw_line, str) and isinstance(answer, str)
                and '\n' not in raw_line and '\r' not in raw_line, 'invalid row content')
        require(json.loads(raw_line) == record, 'stored JSONL line differs from release record')
        meta = record['metadata']
        require(meta['work_id'] in WORKS and meta['split'] in SPLITS and
                meta['role'] in ('gemma_style', 'sota_planning'), 'invalid role/split/work')
        require(record['sample_id'] not in seen, 'duplicate accepted sample ID')
        seen.add(record['sample_id'])
        require(digest(answer.encode('utf-8')) == meta['answer_sha256'] and
                len(answer) == meta['answer_end_cp'] - meta['answer_start_cp'],
                'DB source span or hash differs from accepted record')
        require([message['role'] for message in record['messages']] == ['user', 'assistant'],
                'invalid model message roles')
    return release


def read_release(db_path, import_id):
    from novel_factory.composition import read_accepted_release
    return checked_release(read_accepted_release(db_path, import_id))


def render_jsonl_files(release):
    """Return the nine legacy-shaped files, preserving accepted row bytes/order."""
    release = checked_release(release)
    groups = {(work, split): [] for work in WORKS for split in SPLITS}
    for item in release['rows']:
        meta = item['record']['metadata']
        groups[(meta['work_id'], meta['split'])].append(item['raw_line'])
    return {(work, split): ('\n'.join(lines) + ('\n' if lines else '')).encode('utf-8')
            for (work, split), lines in groups.items()}


def export_release(db_path: Path | str, import_id: str, output_dir: Path | str) -> dict:
    """Write a new derived directory; never rewrite the frozen legacy bundle."""
    from tempfile import TemporaryDirectory

    db_path, output_dir = Path(db_path), Path(output_dir)
    release = read_release(db_path, import_id)
    require(len(release['rows']) == 272, 'fixed reviewed release must contain 272 accepted rows')
    out = output_dir.resolve()
    require(not out.exists(), 'output directory already exists')
    for original in (BASE.resolve(), (ROOT / 'data/training/reverse-full-20260925').resolve()):
        require(not out.is_relative_to(original), 'do not overwrite legacy source artifacts')
    files = render_jsonl_files(release)
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.db-export-', dir=out.parent) as temporary:
        stage = Path(temporary) / 'release'
        stage.mkdir(mode=0o700)
        report = {'schema_version': 1, 'kind': 'derived_from_analysis_db',
                  'db_path': str(db_path.resolve()), 'import_id': import_id,
                  'release_id': release['release_id'],
                  'source_hashes': release['source_hashes'],
                  'selection_policy_hashes': release['selection_policy_hashes'],
                  'count': len(release['rows']), 'files': {}}
        for (work, split), data in files.items():
            path = stage / work / f'{split}.jsonl'
            path.parent.mkdir(exist_ok=True, mode=0o700)
            path.write_bytes(data)
            report['files'][f'{work}/{split}.jsonl'] = {'rows': len(data.splitlines()),
                                                       'bytes': len(data), 'sha256': digest(data)}
        (stage / 'release-manifest.json').write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        stage.rename(out)
    return {'path': str(out), 'release_id': release['release_id'],
            'records': len(release['rows']), 'files': 9}


def build(args):
    print(json.dumps(export_release(args.db, args.import_id, args.output_dir), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build'])
    parser.add_argument('--db', type=Path, default=ROOT / 'data/analysis/novel-corpus.sqlite3')
    parser.add_argument('--import-id', required=True, help='fixed, imported reviewed release ID')
    parser.add_argument('--output-dir', type=Path, required=True, help='new directory for DB-derived JSONL')
    args = parser.parse_args()
    try:
        build(args)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f'error: {exc}\n')
