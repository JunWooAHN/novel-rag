#!/usr/bin/env python3
"""Validate reviewed reverse-design candidates and export local development JSONL."""
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


def build(_args):
    manifest_raw = (BASE / 'source-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    policy = read_json(BASE / 'split-policy.json')
    require(digest(manifest_raw) == policy['source_manifest_sha256'], 'frozen policy hash mismatch')
    reports = {}
    output_files = {}
    seen_normalized_targets = set()
    for wid in WORKS:
        work = manifest['works'][wid]
        raw = (ROOT / work['source_path']).read_bytes()
        require(digest(raw) == work['source_sha256'], f'raw source changed: {wid}')
        text = raw.decode('utf-8')
        reports[wid] = {}
        seen_ranges = []
        for split in policy['works'][wid]['splits']:
            name = split['name']
            rows = []
            counts = {'attempted_units': 0, 'proposed_candidates': 0, 'accepted': 0,
                      'held': 0, 'rejected': 0, 'unit_holds': 0}
            attempted = []
            for start in range(split['section_order_start'], split['section_order_end'] + 1, 5):
                end = min(start + 4, split['section_order_end'])
                bid = f'{wid}-{start:03d}-{end:03d}'
                bundle = read_json(BASE / 'private/batches' / f'{bid}.json')
                review_raw = (BASE / 'private/reviews' / f'{bid}.json').read_bytes()
                review = json.loads(review_raw)
                decision = read_json(BASE / 'private/decisions' / f'{bid}.json')
                require(bundle['batch_id'] == bid and bundle['work_id'] == wid and bundle['split'] == name,
                        f'batch identity changed: {bid}')
                require('excerpt' not in bundle and len(bundle['section_inputs']) == len(bundle['units']),
                        f'batch index must contain metadata only: {bid}')
                for unit, ref in zip(bundle['units'], bundle['section_inputs']):
                    section_path = ROOT / ref['path']
                    require(section_path.parent == BASE / 'private/sections', f'unsafe section path: {bid}')
                    section = read_json(section_path)
                    require(section['batch_id'] == bid and section['work_id'] == wid and
                            section['source_sha256'] == work['source_sha256'] and
                            section['current_unit'] == unit and
                            section['excerpt_end_cp'] == unit['end_cp'] == ref['excerpt_end_cp'] and
                            section['excerpt_start_cp'] == split['start_cp'],
                            f'section identity/range differs: {bid}')
                    excerpt = text[section['excerpt_start_cp']:section['excerpt_end_cp']]
                    require(excerpt == section['excerpt'] and
                            digest(excerpt.encode('utf-8')) == section['excerpt_sha256'] == ref['excerpt_sha256'],
                            f'section excerpt differs: {bid}')
                got, count = validate_batch(bundle, review, decision, work, split, text, review_raw)
                rows.extend(got)
                attempted.extend(a['section_order'] for a in review['attempts'])
                for key in counts:
                    counts[key] += count[key]
            require(attempted == list(range(split['section_order_start'], split['section_order_end'] + 1)),
                    f'split section coverage incomplete: {wid}/{name}')
            for row in rows:
                a, b = row['metadata']['answer_start_cp'], row['metadata']['answer_end_cp']
                require(all(b <= x or a >= y for x, y in seen_ranges), f'accepted targets overlap: {wid}')
                ensure_unique_target(text[a:b], f'{wid}/{name}', seen_normalized_targets)
                seen_ranges.append((a, b))
            path = BASE / 'private/export' / wid / f'{name}.jsonl'
            data = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows).encode('utf-8')
            output_files[path] = data
            reports[wid][name] = {**counts, 'jsonl_path': str(path.relative_to(ROOT)),
                                  'jsonl_sha256': digest(data),
                                  'input_characters': sum(r['metadata']['input_characters'] for r in rows),
                                  'output_characters': sum(r['metadata']['output_characters'] for r in rows),
                                  'source_answer_characters': sum(r['metadata']['source_answer_characters'] for r in rows),
                                  'truncated': False}
    report = {'schema_version': 1, 'pool': 'previously_observed_development_only',
              'final_unseen_test': False, 'manual_semantic_leakage_review_required': True,
              'token_validation': 'not_run', 'truncated': False,
              'source_manifest_sha256': digest(manifest_raw), 'works': reports}
    for path, data in output_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (BASE / 'quality-report.json').write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'works': {w: {s: v['accepted'] for s, v in ss.items()} for w, ss in reports.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build'])
    parser.add_argument('--release', choices=['initial', 'full'], default='initial',
                        help='select the frozen development release; initial is the existing first-50 set')
    args = parser.parse_args()
    try:
        if args.release == 'full':
            from full import export as export_full
            export_full(args)
        else:
            build(args)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f'error: {exc}\n')
