#!/usr/bin/env python3
"""Offline request planning and fixed-probability loot arithmetic; no game data API."""
import argparse
import json
import math
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_reference(name):
    return json.loads((SKILL_ROOT / 'references' / name).read_text(encoding='utf-8'))


def loot_odds(percent, runs, target=0.95):
    if not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError('percent must be a finite number from 0 to 100')
    if isinstance(runs, bool) or not isinstance(runs, int) or not 0 <= runs <= 10**12:
        raise ValueError('runs must be an integer from 0 to 1000000000000')
    if not math.isfinite(target) or not 0 < target < 1:
        raise ValueError('target must be a finite probability between 0 and 1, exclusive')
    p = percent / 100
    if p == 0:
        chance, expected, required = 0.0, None, None
    elif p == 1:
        chance, expected, required = float(runs > 0), 1.0, 1
    else:
        log_failure = math.log1p(-p)
        chance = -math.expm1(runs * log_failure)
        expected = 1 / p
        required = math.ceil(math.log1p(-target) / log_failure)
    return {
        'input_percent': percent, 'runs': runs, 'target_probability': target,
        'at_least_one_probability': chance, 'expected_first_success_runs': expected,
        'runs_for_target_probability': required,
        'assumptions': 'Independent attempts with one fixed probability; no pity or guarantee.',
        'rate_source': 'User-supplied; this tool does not verify a game drop rate.'
    }


def make_plan(topic, goal, level=None, version='', mode='unknown', platform='', host='codex'):
    topics = load_reference('topics.json')
    if topic not in topics:
        raise ValueError('unknown topic')
    if level is not None and (isinstance(level, bool) or not isinstance(level, int) or level < 1):
        raise ValueError('level must be a positive integer, or omitted')
    if mode not in ('unknown', 'single', 'coop', 'dedicated'):
        raise ValueError('unknown play mode')
    if host not in ('codex', 'claude', 'chatgpt'):
        raise ValueError('unknown host')
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError('goal is required')
    selected = topics[topic]
    sources = [s for s in load_reference('sources.json')['sources'] if topic in s['topics']]
    modes = {'unknown':'Unknown', 'single':'Single-player', 'coop':'Co-op', 'dedicated':'Dedicated server'}
    prefix = {'codex':'$palworld-guide', 'claude':'/palworld-guide', 'chatgpt':'@palworld-guide'}[host]
    context = {'version':version.strip() or None, 'level':level,
               'mode':mode, 'platform':platform.strip() or None}
    prompt = '\n'.join([
        prefix,
        f'Goal: {goal.strip()}',
        f'Version: {context["version"] or "Unknown; do not assume the latest release"}',
        f'Level: {level if level is not None else "Unknown"}',
        f'Mode: {modes[mode]}; platform / server OS: {context["platform"] or "Unknown"}',
        'Give the most useful next step, followed by a route or comparison. Ask only for missing context that changes the answer.',
        'Verify the version, entity and metric definitions. Use the comparison, map, reward-chain or server tools as appropriate. Cite evidence and label unknown coordinates, rates and timers.',
        'Provide guidance and read-only checks; do not modify the server or save files.'
    ])
    return {
        'status':'research-plan-not-verified-answer', 'topic':topic,
        'context':context, 'goal':goal.strip(), 'prompt':prompt,
        'search_query':selected['query'].format(version=version.strip(), goal=goal.strip()),
        'verification_checks':selected['checks'], 'source_entries':sources,
        'source_registry_reviewed_on':load_reference('sources.json')['reviewed_on']
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    odds = commands.add_parser('odds', help='calculate from a supplied percentage, not game data')
    odds.add_argument('--percent', required=True, type=float, help='3 means 3 percent, not 0.03 percent')
    odds.add_argument('--runs', required=True, type=int)
    odds.add_argument('--target', default=0.95, type=float)
    plan = commands.add_parser('plan', help='prepare a research request and relevant source entries')
    plan.add_argument('--topic', required=True, choices=tuple(load_reference('topics.json')))
    plan.add_argument('--goal', required=True)
    plan.add_argument('--level', type=int)
    plan.add_argument('--version', default='')
    plan.add_argument('--mode', default='unknown', choices=('unknown','single','coop','dedicated'))
    plan.add_argument('--platform', default='')
    plan.add_argument('--host', default='codex', choices=('codex','claude','chatgpt'))
    args = vars(parser.parse_args())
    command = args.pop('command')
    try:
        result = loot_odds(**args) if command == 'odds' else make_plan(**args)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
