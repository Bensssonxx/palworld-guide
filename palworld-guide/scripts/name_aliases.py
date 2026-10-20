"""Exact, provenance-backed display aliases; never fuzzy-match a different species."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=2)
def aliases(kind):
    data = json.loads((Path(__file__).resolve().parents[1] / 'references/name-aliases.json').read_text(encoding='utf-8'))
    result = {}
    for english, translated in data[kind].items():
        for name in (english, translated):
            key = name.strip().casefold()
            result.setdefault(key, set()).add(english)
    return result


def canonical_name(value, kind):
    if not isinstance(value, str):
        raise ValueError('Use an exact Pal or item name')
    value = value.strip()
    matches = aliases(kind).get(value.casefold())
    if matches and len(matches) != 1:
        raise ValueError('Translated name is ambiguous; use an exact English name or ID')
    return next(iter(matches)) if matches else value


def canonical_inventory(inventory):
    result = {}
    seen = set()
    for name, count in inventory.items():
        key = canonical_name(name, 'items')
        if key.casefold() in seen:
            raise ValueError('The same material was supplied twice under translated aliases')
        seen.add(key.casefold())
        result[key] = count
    return result
