"""Bounded bilingual task drafting. The host handles open-ended language and reviews the task."""
import re
from name_aliases import aliases

TOOLS = {'breed', 'pair', 'pal', 'craft', 'compare', 'entry', 'locations', 'map',
         'odds', 'chain', 'revisit', 'server', 'sources', 'fetch', 'research'}
PROFILE_FIELDS = {'version', 'platform', 'mode', 'level', 'owned_pals', 'inventory',
                  'unlocked_fast_travel', 'position'}
RESOURCES = {'金属矿石': 'Ore', '金属矿': 'Ore', '铁矿': 'Ore', 'ore': 'Ore',
             '煤炭': 'Coal', '煤矿': 'Coal', '挖煤': 'Coal', 'coal': 'Coal', '纯水晶': 'Pure Quartz',
             '石英': 'Pure Quartz', 'quartz': 'Pure Quartz', '硫磺': 'Sulfur', 'sulfur': 'Sulfur'}


def profile_checked(value):
    if not isinstance(value, dict) or set(value)-PROFILE_FIELDS:
        raise ValueError('Profile must contain only supported gameplay fields; keep credentials and raw logs separate')
    if value.get('level') is not None and (isinstance(value['level'], bool) or not isinstance(value['level'], int) or not 1 <= value['level'] <= 1000):
        raise ValueError('Player level must be a positive integer')
    for field in ('owned_pals', 'unlocked_fast_travel'):
        if value.get(field) is not None and (not isinstance(value[field], list) or len(value[field]) > 300 or any(not isinstance(n, str) or not n.strip() or len(n) > 150 for n in value[field])):
            raise ValueError('Profile species/travel fields must be lists of names')
    if value.get('inventory') is not None and (not isinstance(value['inventory'], dict) or any(not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int) or v < 0 for k, v in value['inventory'].items())):
        raise ValueError('Inventory must map names to nonnegative integers')
    if value.get('position') is not None:
        import math
        pos = value['position']
        if not isinstance(pos, list) or len(pos) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in pos):
            raise ValueError('Position needs two finite coordinates')
    for field in ('version', 'platform', 'mode'):
        if value.get(field) is not None and (not isinstance(value[field], str) or len(value[field]) > 100):
            raise ValueError('Context text must be a short string')
    return value


def named(text, kind):
    hits = []
    for name, identities in aliases(kind).items():
        pattern = re.escape(name) if re.search('[\u3400-\u9fff]', name) else r'(?<![a-z0-9])'+re.escape(name)+r'(?![a-z0-9])'
        for match in re.finditer(pattern, text, re.I):
            if len(identities) == 1:
                hits.append((match.start(), match.end(), next(iter(identities))))
    selected = []
    for hit in sorted(hits, key=lambda h: (-(h[1]-h[0]), h[0])):
        if not any(hit[0] < old[1] and old[0] < hit[1] for old in selected):
            selected.append(hit)
    return list(dict.fromkeys(h[2] for h in sorted(selected)))


def draft(question, profile=None, language=None):
    if not isinstance(question, str) or not question.strip() or len(question) > 12000:
        raise ValueError('Question must be 1..12000 characters')
    context = profile_checked(profile or {}).copy()
    spoken_level = re.search(r'(?:level\s*|等级\s*)(\d+)|(\d+)\s*级', question, re.I)
    if spoken_level:
        context['level'] = int(spoken_level[1] or spoken_level[2])
        profile_checked(context)
    task = {'schema': 1, 'question': question, 'language': language or ('zh' if re.search('[\u3400-\u9fff]', question) else 'en'),
            'context': context, 'assumptions': [], 'missing_information': [], 'steps': [],
            'parser': 'bounded-bilingual-rules; host review required for open-ended or ambiguous requests'}
    def add(tool, args, dependencies=None, bindings=None):
        step = {'id': f's{len(task["steps"])+1}', 'tool': tool, 'arguments': args, 'depends_on': dependencies or []}
        if bindings:
            step['bindings'] = bindings
        task['steps'].append(step)
        return step['id']
    def missing(field, reason, blocks):
        task['missing_information'].append({'field': field, 'reason': reason, 'blocks': blocks})
    q = question.lower()
    resource_names = [v for k, v in RESOURCES.items() if (k in q if re.search('[\u3400-\u9fff]', k) else re.search(r'\b'+re.escape(k)+r'\b', q))]
    resource_names = list(dict.fromkeys(resource_names))
    wants_location = bool(resource_names and re.search(r'哪里|地点|位置|矿点|矿群|矿区|建家|基地|where|location|deposit|cluster|base site', q))
    if wants_location:
        clauses = re.split(r'[。？！?;；,，\n]|另外|\balso\b', q)
        location_clauses = [c for c in clauses if any(k in c for k in RESOURCES) and re.search(r'哪里|地点|位置|矿点|矿群|矿区|建家|基地|where|location|deposit|cluster|base site', c)]
        scope = ' '.join(location_clauses) if location_clauses else q
        count_match = re.search(r'(\d+)\s*(?:(?:ore|coal|quartz|sulfur)\s+)?(?:locations?|spots?|deposits?|clusters?|base\s+sites?)', scope) or re.search(r'(\d+)\s*(?:个|处|片)', scope) or re.search(r'\b(?:find|show|get)\s+(\d+)\s+(?:ore|coal|quartz|sulfur)\b', scope)
        chinese_count = re.search(r'([一二两三四五六七八九十])\s*(?:个|处|片)', scope)
        count = int(count_match[1]) if count_match else {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}[chinese_count[1]] if chinese_count else 5
        if not count_match and not chinese_count:
            task['assumptions'].append({'field': 'locations.count', 'value': 5, 'reason': 'No count supplied; adjustable display limit'})
        # A disclaimer or a question about our recommendation is not a request
        # to select a base. Keep positive requests elsewhere in the sentence.
        purpose_scope = re.sub(r'(?:有没有|是否|是不是).{0,12}(?:当成|作为).{0,6}(?:建家|建基地|建据点)(?:推荐)?', '', q)
        purpose_scope = re.sub(r'(?:不需要|不用|不要|无需|不是|不作|别).{0,8}(?:建家|建基地|建据点)(?:推荐)?', '', purpose_scope)
        purpose_scope = re.sub(r'\b(?:not(?:\s+looking)?\s+for|no|without)\s+(?:a\s+)?(?:base\s+sites?|building\s+(?:a\s+)?base)\b', '', purpose_scope)
        purpose = 'base-candidates' if re.search(r'建家|建基地|建据点|base site|build.*base', purpose_scope) else 'clusters' if re.search(r'矿群|矿区|密集|一片矿|成片|cluster|dense', purpose_scope) else 'nodes'
        sort = 'fast-travel' if re.search(r'传送|fast.?travel', q) else 'near' if re.search(r'我附近|离我|near me|closest to me', q) else 'source'
        args = {'category': resource_names[0], 'purpose': purpose, 'count': count, 'sort': sort}
        if context.get('position') is not None:
            args['near'] = context['position']
        if context.get('unlocked_fast_travel') is not None:
            args['unlocked_fast_travel'] = context['unlocked_fast_travel']
        if purpose != 'nodes':
            args['radius'] = 40
            task['assumptions'].append({'field': 'locations.radius', 'value': 40, 'reason': 'Adjustable geometric neighbourhood, not measured mining reach'})
        if sort == 'source':
            task['assumptions'].append({'field': 'locations.sort', 'value': 'source', 'reason': 'No best/nearest criterion supplied; source order is not a recommendation ranking'})
        loc = add('locations', args)
        if not 1 <= count <= 30:
            missing('location_count', 'Choose 1..30 locations per map or split into separate maps', [loc])
        if len(resource_names) != 1:
            missing('resource', 'Multiple resources found; split into explicit location steps', [loc])
        if sort == 'near' and context.get('position') is None:
            missing('position', 'Closest to you requires your actual game coordinates', [loc])
        if re.search(r'已解锁|unlocked', q) and not context.get('unlocked_fast_travel'):
            missing('unlocked_fast_travel', 'Supply the actual unlocked travel names', [loc])
        if re.search(r'最安全|最适合|最好|最佳|best|safest', q) and purpose == 'nodes':
            missing('ranking_criterion', 'Specify safety, density, access or another criterion; source order cannot establish best', [loc])
        add('map', {}, [loc], {'points': {'step': loc, 'path': []}})
    if re.search(r'配种|配出|breed|parents?|offspring', q):
        pals = named(question, 'pals')
        if re.search(r'生什么|生出什么|结果|offspring|child|pair', q) and len(pals) == 2:
            add('pair', {'parents': pals})
        else:
            marker = re.search(r'配出|培育|目标|想要|想得到|breed(?:\s+(?:an?|to))?|target|obtain', question, re.I)
            targets = named(question[marker.end():], 'pals') if marker else []
            target = targets[0] if len(targets) == 1 else pals[0] if len(pals) == 1 else None
            owned = context.get('owned_pals')
            if not owned and marker:
                owned = named(question[:marker.start()], 'pals')
            step = add('breed', {'target': target, 'owned': owned or []})
            if not target:
                missing('target', 'Resolve one exact target species', [step])
            if not owned:
                missing('owned_pals', 'Supply available species; do not use a historical roster', [step])
            if re.search(r'被动|个体值|passive|\bivs?\b', q):
                missing('individual_breeding_model', 'Species planning does not optimize passives, IVs or individual gender availability', [step])
    if re.search(r'缺.*材料|材料.*缺|做.*(?:个|球)|craft|materials|recipe|配方', q):
        items = named(question, 'items')
        count_match = re.search(r'(\d+)\s*(?:个|枚|颗|份)?\s*(?:'+('|'.join(re.escape(x) for x in items) if items else r'球')+r')', question, re.I)
        if not count_match:
            count_match = re.search(r'(?:做|制作|craft|make)\s*(\d+)', q)
        step = add('craft', {'item': items[0] if len(items) == 1 else None,
                             'quantity': int(count_match[1]) if count_match else 1,
                             'inventory': context.get('inventory', {})})
        if not count_match:
            task['assumptions'].append({'field': f'{step}.quantity', 'value': 1, 'reason': 'No quantity supplied'})
        if len(items) != 1:
            missing('item', 'Resolve one exact craftable item', [step])
        if context.get('inventory') is None:
            task['assumptions'].append({'field': f'{step}.inventory', 'value': {}, 'reason': 'No inventory supplied: show full requirements, not a claim about actual stock'})
    if re.search(r'服务器|server|饱食|\bsan\b', q) or (re.search(r'模组|\bmod\b', q) and re.search(r'安装|加载|没生效|崩溃|install|load|missing|crash', q)):
        args = {}
        if re.search(r'食物.*(?:没了|空了)|饲料箱.*空|food.*(?:empty|ran out)', q):
            args['food'] = 'empty'
        elif re.search(r'食物.*(?:还有|剩)|饲料箱.*有|food.*(?:available|remaining)', q):
            args['food'] = 'available'
        crossplay = bool(re.search(r'跨平台|互通|cross.?play|cross.?platform', q) or all(name in q for name in ('steam', 'xbox', 'ps5')))
        if args or not crossplay:
            add('server', args)
        if crossplay:
            add('research', {'question': question, 'topic': 'server'})
        elif re.search(r'自动暂停|没人.*暂停|auto.?pause|linux.*mod|mod.*linux|模组.*linux|linux.*模组', q):
            add('research', {'question': question, 'topic': 'mods' if re.search(r'mod|模组', q) else 'base'})
    if re.search(r'坐骑|mount|挖矿帕鲁|手工帕鲁', q):
        kind = 'mining' if '挖矿帕鲁' in q else 'handiwork' if '手工帕鲁' in q else 'ground'
        args = {'kind': kind}
        if kind == 'ground' and context.get('level') is not None:
            args['level'] = context['level']
        add('compare', args)
        task['assumptions'].append({'field': 'comparison', 'value': 'table-only', 'reason': 'Acquisition feasibility still needs exact articles and player conditions'})
    if re.search(r'概率|掉率|chance|probability|drop rate', q):
        rates = re.findall(r'(\d+(?:\.\d+)?)\s*%', q)
        runs = re.search(r'(\d+)\s*(?:次|attempts?|runs?|tries)', q)
        if len(rates) == 1 and runs:
            add('odds', {'percent': float(rates[0]), 'runs': int(runs[1])})
            task['assumptions'].append({'field': 'odds.rate_semantics', 'value': 'user-supplied fixed independent probability', 'reason': 'The question supplies a number; no game drop-rate verification is implied'})
        else:
            sid = add('sources', {'topic': 'loot', 'question': question})
            missing('probability_model', 'Provide conditional stages and their sources, or one fixed percentage and attempt count', [sid])
    if not task['steps']:
        add('research', {'question': question})
    return task


def validate(task):
    if not isinstance(task, dict) or task.get('schema') != 1 or not isinstance(task.get('question'), str) or not task['question'].strip():
        raise ValueError('Task needs schema 1 and an original question')
    if task.get('language') not in ('zh', 'en'):
        raise ValueError('Task language must be zh or en')
    profile_checked(task.get('context', {}))
    for field in ('assumptions', 'missing_information'):
        if not isinstance(task.get(field, []), list):
            raise ValueError(f'{field} must be a list')
    for item in task.get('assumptions', []):
        if not isinstance(item, dict) or not isinstance(item.get('field'), str) or not isinstance(item.get('reason'), str) or 'value' not in item:
            raise ValueError('Assumptions need field, value and reason')
    steps = task.get('steps')
    if not isinstance(steps, list) or not 1 <= len(steps) <= 24:
        raise ValueError('Provide 1..24 ordered steps')
    seen = set()
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError('Each step must be an object')
        sid = step.get('id')
        if not isinstance(sid, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', sid) or sid in seen:
            raise ValueError('Step IDs must be unique short identifiers')
        if step.get('tool') not in TOOLS or not isinstance(step.get('arguments', {}), dict):
            raise ValueError('Unknown tool or invalid arguments')
        deps = step.get('depends_on', [])
        if not isinstance(deps, list) or any(d not in seen for d in deps):
            raise ValueError('Dependencies must refer to earlier steps; cycles and forward references are rejected')
        bindings = step.get('bindings', {})
        if not isinstance(bindings, dict):
            raise ValueError('Bindings must be an object')
        for key, binding in bindings.items():
            if not isinstance(binding, dict) or binding.get('step') not in deps or not isinstance(binding.get('path'), list) or any(not isinstance(k, (str, int)) or isinstance(k, bool) for k in binding['path']):
                raise ValueError('Bindings need a declared dependency and an explicit data path')
            if key in step.get('arguments', {}):
                raise ValueError('A bound argument cannot also have a literal value')
        if not isinstance(step.get('requires', []), list) or any(r != 'acquisition' for r in step.get('requires', [])):
            raise ValueError('Unknown delivery requirement')
        if not isinstance(step.get('fallback', {}), dict) or set(step.get('fallback', {}))-{'question', 'enabled'}:
            raise ValueError('Fallback accepts only a public question and enabled flag')
        if 'enabled' in step.get('fallback', {}) and not isinstance(step['fallback']['enabled'], bool):
            raise ValueError('Fallback enabled must be a boolean')
        seen.add(sid)
    for item in task.get('missing_information', []):
        if not isinstance(item, dict) or not isinstance(item.get('field'), str) or not isinstance(item.get('reason'), str) or not isinstance(item.get('blocks'), list) or any(s not in seen for s in item['blocks']):
            raise ValueError('Missing information must identify the affected steps')
    return task
