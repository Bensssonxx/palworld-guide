#!/usr/bin/env python3
"""Local task -> typed tool steps -> evidence/artifacts -> delivery review. No MCP or model API."""
import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from task_plan import draft, validate, profile_checked

ROOT = Path(__file__).resolve().parents[1]
MAX_INPUT = 2_000_000


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_INPUT:
        raise ValueError('JSON input exceeds 2 MB')
    def invalid(value):
        raise ValueError('Nonfinite JSON numbers are unsupported')
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=invalid)


def save(path, value):
    path = Path(path)
    if path.exists():
        raise ValueError('Output exists; choose a new path')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def links(value):
    found = []
    def walk(v, parent=None):
        if isinstance(v, dict):
            for child in v.values():
                walk(child, v)
        elif isinstance(v, list):
            for child in v:
                walk(child, parent)
        elif isinstance(v, str) and v.startswith(('https://', 'http://')):
            url = urlparse(v)
            if url.hostname and not url.username and not url.password:
                record = {'url': v}
                if parent:
                    record.update({k: parent[k] for k in ('fetched_at', 'sha256', 'stale', 'cache', 'game_version', 'revision', 'version', 'data_version') if k in parent})
                if record not in found:
                    found.append(record)
    walk(value)
    return found


def metadata(value, key):
    result = []
    if isinstance(value, dict):
        if key in value and value[key] is not None:
            result.append(value[key])
        for v in value.values():
            result.extend(metadata(v, key))
    elif isinstance(value, list):
        for v in value:
            result.extend(metadata(v, key))
    return list({json.dumps(v, sort_keys=True): v for v in result}.values())


def envelope(tool, data=None, status='completed', gaps=None, artifacts=None):
    data = {} if data is None else data
    conflicts = []
    for field in ('cross_check', 'api_cross_check'):
        for check in metadata(data, field):
            if isinstance(check, dict) and check.get('status') in ('conflict', 'unavailable'):
                conflicts.append(check)
    if data.get('status') == 'recipe-evidence-incomplete':
        conflicts.append({'status': 'unresolved-recipe', 'reason': data.get('reason')})
    gaps = list(gaps or [])
    if conflicts:
        gaps.append('Resolve source disagreement or unavailable cross-check before presenting one settled result')
        if status == 'completed':
            status = 'partial'
    return {'schema': 1, 'tool': tool, 'status': status, 'data': data, 'evidence': links(data),
            'retrieved_at': list(dict.fromkeys(metadata(data, 'fetched_at')+metadata(data, 'retrieved_at'))),
            'version_scope': {'provider_versions': metadata(data, 'game_version'),
                              'data_versions': metadata(data, 'data_version'), 'pinned_revisions': metadata(data, 'revision'),
                              'note': 'Provider versions and pinned data revisions do not establish compatibility with the player version'},
            'conflicts': conflicts, 'gaps': gaps, 'next_steps': gaps.copy(), 'artifacts': artifacts or []}


def call_tool(tool, args, network, directory, language):
    """Explicit dispatch only. No user-selected command, module, URL or executable."""
    args = deepcopy(args)
    artifacts, gaps = [], []
    status = 'completed'
    if tool in ('breed', 'pair'):
        from breed_routes import load_data, plan, pair_result, resolve
        data = load_data()
        if tool == 'breed':
            out = plan(data, **args)
            if out['status'] == 'no-route-within-limit':
                status = 'partial'; gaps.append('Add available species or inspect a capture route; bounded search found no species route')
        else:
            parents = args.pop('parents'); verify = args.pop('verify_online', False)
            if args or not isinstance(parents, list) or len(parents) != 2:
                raise ValueError('Pair needs exactly two parent names')
            out = pair_result(data, *parents)
            if verify:
                from provider_api import Client
                ids = [data['species'][resolve(data, n)]['id'] for n in parents]
                value, evidence = Client(**network).call('breeding/result/', {'a': ids[0], 'b': ids[1]})
                actual = value.get('child', {}).get('id') if isinstance(value, dict) else None
                out['api_cross_check'] = {'status': 'agreed' if actual in {r['child']['id'] for r in out['results']} else 'conflict',
                                          'response': value, 'evidence': evidence}
            if not out['results']:
                status = 'partial'; gaps.append('No pair record found; do not invent an offspring')
    elif tool in ('craft', 'pal'):
        from provider_api import Client, recipe_bundle, material_deficits
        from name_aliases import canonical_name
        if tool == 'pal':
            value, evidence = Client(**network).pal(**args)
            out = {'pal': value, 'evidence': evidence}
        else:
            item = canonical_name(args.pop('item'), 'items')
            quantity = args.pop('quantity', 1); inventory = args.pop('inventory', {})
            if args:
                raise ValueError('Unsupported crafting arguments')
            bundle = None
            if network.get('offline'):
                recipes = read_json(ROOT/'references/integration-examples.json')['recipes']
                bundle = next((r for r in recipes if item.casefold() in (r['item']['id'].casefold(), r['item']['name'].casefold())), None)
            mode = 'bundled-public-snapshot' if bundle else 'public-source-reader'
            bundle = bundle or recipe_bundle(Client(**network), item)
            out = material_deficits(bundle, quantity, inventory)
            out['access'] = {'mode': mode}
            if out['status'] != 'materials-ready':
                status = 'partial'
    elif tool in ('compare', 'entry'):
        from pal_compare import compare, entry
        out = (compare if tool == 'compare' else entry)(**args, **network)
        if tool == 'entry' and not out.get('matched'):
            status = 'partial'; gaps.append('Requested article section was not matched; inspect actual linked sections')
        if tool == 'compare' and not out.get('records'):
            status = 'partial'; gaps.append('No eligible source rows returned')
    elif tool == 'locations':
        from location_strategy import resource_locations
        out = resource_locations(**args, **network)
        if len(out['points']) < args.get('count', 5):
            gaps.append('Fewer matching distinct locations than requested')
            status = 'partial'
        if out['unverified_checks']:
            gaps.extend(out['unverified_checks']); status = 'partial'
    elif tool == 'map':
        from map_tools import render_svg
        payload = args.pop('points')
        if not payload.get('points'):
            return envelope(tool, {}, 'blocked', ['No sourced points available for a map'])
        svg, evidence = render_svg(payload, language=language, embed_tiles=True, show_fast_travel=True, **args, **network)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory/'map.svg'; proof = directory/'map.evidence.json'
        path.write_text(svg, encoding='utf-8'); save(proof, evidence)
        artifacts = [{'kind': 'map', 'path': str(path.resolve()), 'sha256': hashlib.sha256(svg.encode()).hexdigest()},
                     {'kind': 'map-evidence', 'path': str(proof.resolve()), 'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}]
        out = {'point_count': len(evidence['markers']), 'points': payload['points'], 'retrieval': payload.get('retrieval', {})}
    elif tool in ('odds', 'chain', 'revisit'):
        from guide_tools import loot_odds
        from farm_plan import reward_chain, revisit_window
        out = {'odds': loot_odds, 'chain': reward_chain, 'revisit': revisit_window}[tool](**args)
    elif tool == 'server':
        from server_check import inspect_server, read_optional
        files = args.pop('files', {})
        allowed = {'world_text', 'mod_text', 'log_text', 'manifest'}
        if not isinstance(files, dict) or set(files)-allowed:
            raise ValueError('Unsupported local server file type')
        for key, value in files.items():
            if key in args:
                raise ValueError('Duplicate server input')
            args[key] = read_json(value) if key == 'manifest' else read_optional(value)
        out = inspect_server(**args)
        if any(f['code'] == 'need-observations' for f in out['findings']):
            status = 'partial'; gaps.append('Supply the current symptom, instance and relevant observations')
    elif tool in ('sources', 'fetch'):
        from public_sources import select_sources, fetch_source
        out = select_sources(**args) if tool == 'sources' else fetch_source(**args, **network)
        if tool == 'sources':
            status = 'partial'; gaps.append('Source directory is an entry point; retrieve the exact supporting page')
        elif not out.get('matched'):
            status = 'partial'; gaps.append('No matching source excerpt')
    else:
        raise ValueError('Unsupported tool')
    return envelope(tool, out, status, gaps, artifacts)


def task_text(task):
    # Raw server excerpts remain in the user's original local task/file, not reports.
    clean = deepcopy(task)
    for step in clean['steps']:
        if step['tool'] == 'server':
            step['arguments'] = {k: '[local input omitted]' if k in ('world_text', 'mod_text', 'log_text', 'manifest', 'files') else v
                                 for k, v in step.get('arguments', {}).items()}
    return '# Reviewed task\n\n```json\n'+json.dumps(clean, ensure_ascii=False, indent=2)+'\n```\n'


def execute(task, output, offline=False, refresh=False, cache_dir=None, research=None, previous=None, host_trace=None):
    validate(task)
    if offline and refresh:
        raise ValueError('Choose offline or refresh')
    output = Path(output)
    if output.exists():
        raise ValueError('Run directory already exists; preserve prior results and choose a new directory')
    output.mkdir(parents=True)
    (output/'task.md').write_text(task_text(task), encoding='utf-8')
    network = {'offline': offline, 'refresh': refresh}
    if cache_dir:
        network['cache_dir'] = cache_dir
    from research_bridge import request as make_request, validate_packet, result as research_result, fingerprint
    if previous is not None and previous.get('task_fingerprint') != fingerprint(task):
        raise ValueError('Resume requires the same task; author a new reviewed task for replanning')
    packets = research or {}
    if not isinstance(packets, dict):raise ValueError('Research receipts must map request IDs to packets')
    results = {}; queue = []
    for step in task['steps']:
        sid, tool = step['id'], step['tool']
        old = previous.get('results', {}).get(sid) if previous else None
        if old and old['status'] not in ('awaiting-research', 'blocked'):
            # Preserve completed work, prior source failures and exhausted research attempts.
            results[sid] = deepcopy(old)
            continue
        gaps = [m.get('reason', 'Missing context') for m in task.get('missing_information', []) if sid in m['blocks']]
        gaps += [f'Dependency {dep} did not return usable data' for dep in step.get('depends_on', [])
                 if results[dep]['status'] in ('failed', 'blocked', 'awaiting-research') or not results[dep]['data']]
        if gaps:
            results[sid] = envelope(tool, status='blocked', gaps=gaps)
            continue
        args = deepcopy(step.get('arguments', {}))
        try:
            for key, binding in step.get('bindings', {}).items():
                value = results[binding['step']]['data']
                for component in binding['path']:
                    if isinstance(component, int) and component < 0:
                        raise ValueError('Negative binding indexes are unsupported')
                    value = value[component]
                args[key] = deepcopy(value)
            if tool == 'research':
                results[sid] = envelope(tool, status='awaiting-research', gaps=['Host public search/read receipts are required'])
            elif old and old.get('research_request'):
                results[sid] = deepcopy(old.get('original_result') or old)
            else:
                results[sid] = call_tool(tool, args, network, output/sid, task['language'])
        except (ValueError, OSError, KeyError, TypeError, IndexError, OverflowError) as error:
            # Preserve a useful error without echoing paths, file contents or credentials.
            code = getattr(error, 'code', None)
            label = type(error).__name__+(f' (HTTP {code})' if isinstance(code, int) else '')
            if str(error) == 'No cached public source is available; run online first':
                label += ': public cache missing; retry this task online or supply a dated public cache'
            results[sid] = envelope(tool, status='failed', gaps=[f'{label}: operation failed; inspect inputs and source availability'])
        current = results[sid]
        eligible = tool == 'research' or (tool in ('entry', 'pal', 'craft', 'compare', 'locations', 'map', 'fetch') and
                    current['status'] in ('failed', 'partial') and
                    not current['data'].get('unverified_checks') and not current.get('research_attempted'))
        if not eligible or step.get('fallback', {}).get('enabled') is False:
            continue
        original = deepcopy(current)
        pending = None
        try:
            pending = old.get('research_request') if old else None
            pending = pending or make_request(task, step, original)
            packet = packets.get(pending['id'])
            if packet is None:
                if offline:
                    current = deepcopy(original)
                    if tool == 'research':current['status'] = 'blocked'
                    current['gaps'].append('Online research is disabled in offline mode')
                else:
                    current = envelope(tool, current['data'], 'awaiting-research', ['Awaiting the host search/read handoff'], current['artifacts'])
                current['research_request'] = pending; current['original_result'] = original
                if not offline:queue.append(pending)
            else:
                if offline:raise ValueError('Research receipts cannot resume in explicit offline mode')
                packet = validate_packet(packet, pending); findings = research_result(packet)
                if host_trace:
                    from research_trace import audit
                    findings['trace_audit'] = audit(packet, pending, host_trace)
                action = packet['resolution']['action']
                if action == 'retry' and tool != 'research':
                    current = call_tool(tool, packet['resolution']['arguments'], network, output/sid, task['language'])
                    current['original_result'] = original
                    current['research_findings'] = findings
                    current['evidence'] += links(findings)
                    if packet['resolution'].get('remaining_gaps'):
                        current['gaps'] += packet['resolution']['remaining_gaps']
                        current['status'] = 'partial'
                elif tool == 'research':
                    current = envelope(tool, findings, 'completed' if action == 'answer' else 'partial',
                                       packet['resolution'].get('limitations', []) if action == 'unresolved' else [])
                else:
                    current = envelope(tool, {**original['data'], 'research_findings': findings}, 'partial',
                                       original['gaps']+['Supplementary evidence returned; original tool constraints remain unresolved'], original['artifacts'])
                current['research_attempted'] = True; current['research_request'] = pending
                current['research_packet'] = packet
            current['next_steps'] = current['gaps'].copy()
            results[sid] = current
        except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
            from research_trace import TraceAuditError
            from research_bridge import PacketValidationError
            detail = str(error) if isinstance(error, (TraceAuditError, PacketValidationError)) else 'inspect the focused public question and receipt structure'
            results[sid] = envelope(tool, original['data'], 'partial' if original['data'] else 'blocked',
                                   ['Research handoff rejected or unavailable; '+detail], original['artifacts'])
            results[sid]['research_attempted'] = True
            if 'pending' in locals() and pending:
                results[sid]['research_request'] = pending
                results[sid]['original_result'] = original
    statuses = [r['status'] for r in results.values()]
    state = 'awaiting-research' if queue else 'completed' if all(s == 'completed' for s in statuses) else 'blocked' if all(s in ('failed', 'blocked') for s in statuses) else 'partial'
    run = {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
           'question': task['question'], 'language': task['language'], 'context': task.get('context', {}),
           'assumptions': task.get('assumptions', []), 'missing_information': task.get('missing_information', []),
           'steps': [{'id': s['id'], 'tool': s['tool'], 'depends_on': s.get('depends_on', []), 'requires': s.get('requires', [])} for s in task['steps']],
           'execution_status': state, 'results': results, 'research_queue': queue, 'task_fingerprint': fingerprint(task),
           'limits': ['Host interpretation and source truth are not certified by this runner.',
                      'Task/profile/run artifacts are local player data; do not place them in a shared skill archive.']}
    run['delivery_review'] = review(run)
    save(output/'run.json', run)
    save(output/'review.json', run['delivery_review'])
    save(output/'research-queue.json', {'schema': 1, 'requests': queue})
    return run


def review(run, answer=None):
    """Structural delivery gate. No semantic truth or natural-language accuracy claim."""
    issues, checks = [], []
    for missing in run.get('missing_information', []):
        issues.append({'step': 'context', 'code': 'missing-context', 'detail': missing['reason']})
    results = run['results']
    for sid, result in results.items():
        for gap in result['gaps']:
            issues.append({'step': sid, 'code': 'unresolved', 'detail': gap})
        data = result['data']
        if result['tool'] == 'locations' and data.get('points'):
            maps = [r for step in run['steps'] if sid in step['depends_on'] and step['tool'] == 'map' for r in [results[step['id']]]]
            valid = False
            for mapped in maps:
                files = mapped['artifacts']
                try:
                    image = next(a for a in files if a['kind'] == 'map')
                    proof = next(a for a in files if a['kind'] == 'map-evidence')
                    for a in (image, proof):
                        path = Path(a['path'])
                        if hashlib.sha256(path.read_bytes()).hexdigest() != a['sha256']:
                            raise ValueError('Artifact changed')
                    svg = ET.fromstring(Path(image['path']).read_text(encoding='utf-8'))
                    evidence = read_json(proof['path'])
                    expected = [(p['x'], p['y'], p['source_url']) for p in data['points']]
                    actual = [(p['x'], p['y'], p['source_url']) for p in evidence['markers']]
                    valid = expected == actual and svg.tag.endswith('svg') and evidence['embedded_tiles'] and evidence['language'] == run['language']
                    if answer is not None:
                        valid = valid and (image['path'] in answer or Path(image['path']).name in answer)
                except (OSError, KeyError, ValueError, StopIteration, ET.ParseError):
                    valid = False
                if valid:
                    break
            checks.append({'step': sid, 'check': 'matching-real-map', 'passed': valid})
            if not valid:
                issues.append({'step': sid, 'code': 'map-missing-or-mismatched', 'detail': 'Deliver an intact map of the actual selected coordinates in the requested language'})
            if answer is not None:
                table = all(re.search(r'\(\s*'+re.escape(f'{p["x"]:.2f}')+r'\s*[,，]\s*'+re.escape(f'{p["y"]:.2f}')+r'\s*\)', answer) for p in data['points'])
                if not table:
                    issues.append({'step': sid, 'code': 'point-table-missing', 'detail': 'Include each coordinate pair to two decimals; source geometry remains unrounded'})
        if result['tool'] == 'locations' and data.get('purpose') == 'base-candidates':
            issues.append({'step': sid, 'code': 'base-feasibility-unverified', 'detail': 'Density does not establish buildable terrain or base suitability'})
        if result['tool'] == 'compare' or 'acquisition' in next(s for s in run['steps'] if s['id'] == sid)['requires']:
            # An exact matched article is evidence to review, not automated proof of ease.
            candidates = [r['name'] for r in data.get('records', [])] if result['tool'] == 'compare' else [data.get('target', {}).get('name')]
            followups = [results[s['id']] for s in run['steps'] if sid in s['depends_on'] and s['tool'] == 'entry']
            covered = []
            for name in candidates:
                if not name:
                    continue
                slug = name.replace(' ', '_')
                if any(r['status'] == 'completed' and r['data'].get('matched') and
                       any(urlparse(e['url']).path.rstrip('/').endswith('/'+slug) for e in r['evidence']) and
                       re.search(r'habitat|acquisition|obtain|breeding|egg|捕捉|获取', r['data'].get('contains', ''), re.I)
                       for r in followups):
                    covered.append(name)
            checks.append({'step': sid, 'check': 'candidate-acquisition-pages', 'covered': covered, 'candidates': candidates})
            if not candidates or len(covered) != len(candidates):
                issues.append({'step': sid, 'code': 'acquisition-evidence-missing', 'detail': 'Open candidate-specific acquisition sections for all presented candidates; host must still check player feasibility'})
        if answer is not None and result['evidence'] and result['tool'] not in ('sources',):
            if not any(e['url'] in answer for e in result['evidence']):
                issues.append({'step': sid, 'code': 'citation-missing', 'detail': 'Attach at least one exact supporting source URL for this step'})
    if answer is not None and run.get('assumptions') and not re.search(r'\bassumptions?\b|\bdefaults?\b|假设|默认|选择方法', answer, re.I):
        issues.append({'step': 'task', 'code': 'assumptions-not-disclosed', 'detail': 'Disclose task defaults and inferred preferences'})
    if answer is None:
        issues.append({'step': 'answer', 'code': 'answer-not-reviewed', 'detail': 'Write the player-facing answer, then review with --answer'})
    return {'status': 'ready-for-human-review' if not issues else 'needs-attention', 'checks': checks, 'issues': issues,
            'scope': 'Structural evidence/artifact checks only. Host must inspect source semantics, recommendation feasibility, language and final readability.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('draft'); p.add_argument('--question', required=True); p.add_argument('--profile'); p.add_argument('--language', choices=('zh', 'en')); p.add_argument('--output', required=True)
    for command in ('run', 'resume'):
        p = sub.add_parser(command); p.add_argument('--task', required=True); p.add_argument('--output-dir', required=True)
        p.add_argument('--offline', action='store_true'); p.add_argument('--refresh', action='store_true'); p.add_argument('--cache-dir'); p.add_argument('--research'); p.add_argument('--host-trace')
        if command == 'resume':p.add_argument('--previous-run', required=True)
    p = sub.add_parser('review'); p.add_argument('--run', required=True); p.add_argument('--answer', required=True); p.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'draft':
            task = draft(args.question, read_json(args.profile) if args.profile else None, args.language)
            validate(task); save(args.output, task)
            print(json.dumps({'task': args.output, 'steps': len(task['steps']), 'missing_information': task['missing_information']}, ensure_ascii=False))
        elif args.command in ('run', 'resume'):
            run = execute(read_json(args.task), args.output_dir, args.offline, args.refresh, args.cache_dir,
                          read_json(args.research) if args.research else None,
                          read_json(args.previous_run) if args.command == 'resume' else None, args.host_trace)
            print(json.dumps({'run': str(Path(args.output_dir)/'run.json'), 'execution_status': run['execution_status'], 'delivery_status': run['delivery_review']['status']}, ensure_ascii=False))
        else:
            answer = Path(args.answer)
            if answer.stat().st_size > MAX_INPUT:
                raise ValueError('Answer exceeds 2 MB')
            result = review(read_json(args.run), answer.read_text(encoding='utf-8')); save(args.output, result)
            print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f'Workflow failed: {error}\n')


if __name__ == '__main__':
    main()
