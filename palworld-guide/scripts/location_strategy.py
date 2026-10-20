"""Purpose-specific selection over sourced points; density is not terrain suitability."""
import math
from copy import deepcopy
from map_tools import load_dataset, point_from_record


def resource_locations(category, purpose='nodes', count=5, radius=40, sort='source',
                       near=None, unlocked_fast_travel=None, **network):
    if purpose not in ('nodes', 'clusters', 'base-candidates'):
        raise ValueError('Unknown location purpose')
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 30:
        raise ValueError('Location count must be an integer from 1 to 30')
    if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or not 1 <= radius <= 200:
        raise ValueError('Cluster radius must be 1..200 coordinate units')
    if sort not in ('source', 'fast-travel', 'near'):
        raise ValueError('Unknown location ordering')
    if near is not None and (not isinstance(near, list) or len(near) != 2 or
                            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in near)):
        raise ValueError('Reference coordinates must be two finite numbers')
    if sort == 'near' and near is None:
        raise ValueError('Near ordering needs actual player coordinates')
    if unlocked_fast_travel is not None and (not isinstance(unlocked_fast_travel, list) or
                                            not unlocked_fast_travel or
                                            any(not isinstance(n, str) or not n.strip() for n in unlocked_fast_travel)):
        raise ValueError('Unlocked travel needs a nonempty list of exact names')
    records, retrieval = load_dataset(**network)
    nodes, travel, seen = [], [], set()
    for row in records:
        p = point_from_record(row, retrieval)
        if not p:
            continue
        if row.get('type') == 'Fast Travel':
            travel.append(p)
        if str(row.get('type', '')).casefold() == category.casefold():
            key = (p['x'], p['y'])
            if key not in seen:
                nodes.append(p); seen.add(key)
    if unlocked_fast_travel is not None:
        import json
        from map_tools import ROOT
        labels = json.loads((ROOT/'references/name-aliases.json').read_text(encoding='utf-8')).get('map_labels', {})
        wanted = {n.strip().casefold() for n in unlocked_fast_travel}
        matched = {name for t in travel for name in (t['label'].casefold(), labels.get(t['label'], '').casefold()) if name in wanted}
        if wanted - matched:
            raise ValueError('Some unlocked travel names do not match source records')
        travel = [t for t in travel if {t['label'].casefold(), labels.get(t['label'], '').casefold()} & wanted]
    def distance(a, b):
        return math.hypot(a['x']-b['x'], a['y']-b['y'])
    for p in nodes:
        if travel:
            t = min(travel, key=lambda t: distance(p, t))
            p['nearest_fast_travel'] = {k: t[k] for k in ('label', 'x', 'y', 'source_url')}
            p['nearest_fast_travel'].update(distance_coordinate_units=distance(p, t), distance_kind='Straight-line, not traversable distance')
        if near is not None:
            p['straight_line_coordinate_distance'] = math.hypot(p['x']-near[0], p['y']-near[1])
    if sort == 'fast-travel' and nodes and not travel:
        raise ValueError('No eligible fast-travel records')
    def order(p):
        return p['nearest_fast_travel']['distance_coordinate_units'] if sort == 'fast-travel' else p.get('straight_line_coordinate_distance', 0) if sort == 'near' else 0
    candidates = []
    if purpose == 'nodes':
        candidates = sorted(nodes, key=order)[:count]
    else:
        # Each candidate is a node-centred neighbourhood, not a connected-component
        # chain that can stretch across the map. Greedy disjoint selection is explicit.
        ranked = []
        for i, p in enumerate(nodes):
            members = [j for j, q in enumerate(nodes) if distance(p, q) <= radius]
            if len(members) >= 2:
                ranked.append((p, members, i))
        ranked.sort(key=lambda row: (-len(row[1]), order(row[0]), row[2]))
        used = set()
        for p, members, _ in ranked:
            if used.intersection(members):
                continue
            point = deepcopy(p)
            point['cluster'] = {'radius_coordinate_units': radius, 'record_count': len(members),
                                'members': [{k: nodes[j][k] for k in ('x', 'y', 'source_url')} for j in members]}
            candidates.append(point); used.update(members)
            if len(candidates) == count:
                break
    limits = ['Source-record geometry only; altitude, access, danger, yield and respawn are unverified.',
              'All distances are straight-line coordinate units; this is not route navigation.']
    if purpose != 'nodes':
        limits.append('Density counts distinct mapped nodes in a supplied radius. Greedy disjoint neighbourhoods are not a global optimum or a verified mine yield.')
    checks = ['terrain_flatness', 'build_permission', 'base_radius_fit', 'enemy_risk', 'resource_access'] if purpose == 'base-candidates' else []
    if checks:
        limits.append('These are scouting candidates, not verified buildable base sites.')
    return {'map_id': 'palpagos-main', 'category': category, 'purpose': purpose,
            'retrieval': retrieval, 'total_matches': len(nodes), 'points': candidates,
            'selection': {'sort': sort, 'count': count, 'radius': radius if purpose != 'nodes' else None,
                          'travel_scope': 'player-unlocked' if unlocked_fast_travel is not None else 'all-source-records'},
            'unverified_checks': checks, 'limits': limits}
