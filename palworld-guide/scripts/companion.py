#!/usr/bin/env python3
"""Direct Palworld shortcuts: mature public data, exact API lookups and source-checked material totals."""
import argparse,json
from pathlib import Path
from urllib.parse import urlencode
from breed_routes import load_data,plan,pair_result
from provider_api import Client,recipe_bundle,material_deficits
from name_aliases import canonical_name

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('breed');b.add_argument('--target',required=True);b.add_argument('--owned',nargs='+',required=True);b.add_argument('--max-generations',type=int,default=6)
    pair=sub.add_parser('pair');pair.add_argument('--parents',nargs=2,required=True);pair.add_argument('--verify-online',action='store_true')
    look=sub.add_parser('pal');look.add_argument('--name',required=True)
    craft=sub.add_parser('craft');craft.add_argument('--item',required=True);craft.add_argument('--quantity',type=int,default=1);craft.add_argument('--inventory')
    recipe=sub.add_parser('recipe');recipe.add_argument('--item',required=True)
    for cmd in (pair,look,craft,recipe):cmd.add_argument('--offline',action='store_true');cmd.add_argument('--refresh',action='store_true');cmd.add_argument('--cache-dir')
    a=vars(p.parse_args());command=a.pop('command')
    try:
        if a.get('offline') and a.get('refresh'):raise ValueError('Choose offline or refresh, not both')
        if command=='breed':result=plan(load_data(),**a)
        elif command=='pair':
            names=a.pop('parents');verify=a.pop('verify_online');result=pair_result(load_data(),*names)
            if verify:
                data=load_data();from breed_routes import resolve
                ids=[data['species'][resolve(data,n)]['id'] for n in names]
                value,evidence=Client(**a).call('breeding/result/',{'a':ids[0],'b':ids[1]})
                expected={r['child']['id'] for r in result['results']}
                actual=value.get('child',{}).get('id') if isinstance(value,dict) else None
                result['api_cross_check']={'status':'agreed' if actual in expected else 'conflict','response':value,'evidence':evidence}
        elif command=='pal':
            name=a.pop('name');value,evidence=Client(**a).pal(name);result={'pal':value,'evidence':evidence,'limits':'API fields retain their provider definitions. Spawn summaries do not establish every location or guaranteed availability.'}
        else:
            item=canonical_name(a.pop('item'),'items');quantity=a.pop('quantity',1);inventory_path=a.pop('inventory',None);inventory={}
            if inventory_path:
                path=Path(inventory_path)
                if path.stat().st_size>100000:raise ValueError('Inventory file exceeds 100 KB')
                inventory=json.loads(path.read_text(encoding='utf-8'))
            bundle=None
            if a.get('offline'):
                snapshots=json.loads((Path(__file__).resolve().parents[1]/'references/integration-examples.json').read_text(encoding='utf-8'))['recipes']
                matches=[r for r in snapshots if item.strip().casefold() in (r['item']['id'].casefold(),r['item']['name'].casefold())]
                if len(matches)==1:bundle=matches[0]
            mode='bundled-public-snapshot' if bundle is not None else 'public-source-reader'
            if bundle is None:bundle=recipe_bundle(Client(**a),item)
            result=material_deficits(bundle,quantity,inventory) if command=='craft' else bundle
            result['access']={'mode':mode,'note':'Preserve each source retrieval date; this mode does not assert a live refresh.' if mode=='bundled-public-snapshot' else 'Each retrieval record states whether public cache or network was used.'}
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    except (ValueError,OSError,KeyError,TypeError) as error:p.exit(2,f'Companion tool failed: {error}\n')

if __name__=='__main__':main()
