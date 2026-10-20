#!/usr/bin/env python3
"""Small read-only adapter for the documented PalDB.gg JSON API and PalDB.cc recipe evidence."""
import json,math,re
from html.parser import HTMLParser
from urllib.parse import quote,urlencode,urljoin
from public_sources import get_public,PageText
from name_aliases import canonical_name,canonical_inventory

API='https://paldb.gg/api/v1/'
CREDIT={'text':'Data from PalDB.gg','url':'https://paldb.gg','documentation':'https://paldb.gg/developers/'}

class Client:
    def __init__(self,**network):self.network=network;self.calls=0;self.game_version=None;self.evidence=[]
    def call(self,path,params=None):
        if not re.fullmatch(r'(?:pals|items|breeding/result|updates/latest)(?:/[A-Za-z0-9_-]+)?/',path):raise ValueError('Unsupported public API operation')
        if self.calls>=12:raise ValueError('Public API request budget exceeded; narrow this request')
        self.calls+=1;url=API+path+('?' + urlencode(params) if params else '')
        body,meta=get_public(url,max_age_seconds=3600,**self.network)
        obj=json.loads(body)
        if not isinstance(obj,dict) or obj.get('apiVersion')!='v1' or not obj.get('gameVersion') or 'data' not in obj:raise ValueError('Public API envelope changed; adapter review required')
        version=str(obj['gameVersion'])
        if self.game_version is not None and version!=self.game_version:raise ValueError('API build changed within this request; do not mix recipes across builds')
        self.game_version=version
        evidence={'retrieval':meta,'game_version':version,'provider_verified_at':obj.get('verifiedAt'),'attribution':CREDIT}
        self.evidence.append(evidence)
        return obj['data'],evidence
    def item(self,identifier):
        if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',identifier):raise ValueError('Use an item ID returned by this API')
        data,meta=self.call('items/'+quote(identifier,safe='')+'/')
        if not isinstance(data,dict) or not isinstance(data.get('id'),str) or not data.get('name'):raise ValueError('Item schema changed')
        return data,meta
    def resolve(self,kind,name):
        if kind not in ('pals','items') or not isinstance(name,str) or not 1<=len(name.strip())<=100:raise ValueError('Use an exact English Pal or item name')
        name=canonical_name(name,kind)
        rows,meta=self.call(kind+'/',{'q':name.strip(),'limit':100})
        if not isinstance(rows,list):raise ValueError('Search schema changed')
        key=name.strip().casefold();matches=[r for r in rows if isinstance(r,dict) and key in (str(r.get(k,'')).casefold() for k in ('name','id','slug'))]
        if len(matches)!=1:raise ValueError('Name not uniquely resolved. Candidates: '+', '.join(str(r.get('name')) for r in rows[:8]))
        return matches[0]
    def pal(self,name):
        row=self.resolve('pals',name);data,meta=self.call('pals/'+quote(row['id'],safe='')+'/')
        if not isinstance(data,dict) or data.get('id')!=row['id']:raise ValueError('Resolved Pal identity does not match the detail response')
        return data,meta


class RecipeTables(HTMLParser):
    """Retain each linked ingredient and the numeric text immediately following it."""
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.anchor=None
    def cell_end(self):
        if self.cell is not None:self.row.append(self.cell);self.cell=None;self.anchor=None
    def row_end(self):
        self.cell_end()
        if self.row is not None:self.table.append(self.row);self.row=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='table':self.table=[]
        if tag=='tr' and self.table is not None:self.row_end();self.row=[]
        if tag in ('td','th') and self.row is not None:self.cell_end();self.cell={'text':'','links':[]}
        if tag=='a' and self.cell is not None:
            self.anchor={'href':attrs.get('href',''),'label':'','following':''};self.cell['links'].append(self.anchor)
    def handle_endtag(self,tag):
        if tag=='a':self.anchor=None
        if tag in ('td','th'):self.cell_end()
        if tag=='tr' and self.row is not None:self.row_end()
        if tag=='table' and self.table is not None:self.row_end();self.tables.append(self.table);self.table=None
    def handle_data(self,data):
        if self.cell is None:return
        self.cell['text']+=data
        if self.anchor is not None:self.anchor['label']+=data
        elif self.cell['links']:self.cell['links'][-1]['following']+=data


def parse_cc_recipe(html,name):
    match=re.search(r'<h5\b[^>]*>\s*Production\s*</h5>',html,re.I)
    if not match:raise ValueError('No Production section found in the cross-check source')
    section=html[match.end():];end=section.find('</table>')
    if end<0:raise ValueError('Production table is incomplete')
    parser=RecipeTables();parser.feed(section[:end+8]);recipes=[]
    for table in parser.tables:
        if not table or [' '.join(c['text'].split()) for c in table[0]]!=['Materials','Product','Schematic']:continue
        for row in table[1:]:
            if len(row)!=3 or not row[1]['links']:continue
            product=row[1]['links'][0]
            if ' '.join(product['label'].split()).casefold()!=name.casefold():continue
            def ingredient(link):
                count=re.match(r'\s*(\d+)',link['following'])
                label=' '.join(link['label'].split())
                if not count or not label:raise ValueError('Ingredient quantity is not explicit in the source row')
                return {'name':label,'count':int(count[1]),'source_url':urljoin('https://paldb.cc/en/',link['href'])}
            materials=[ingredient(x) for x in row[0]['links']];yield_count=ingredient(product)['count']
            if not materials or yield_count<1:raise ValueError('Incomplete recipe row')
            level=re.search(r'Technology\s+Lv\.?\s*(\d+)',row[2]['text'],re.I)
            if row[2]['links']:continue # A schematic-specific recipe is a different acquisition requirement.
            recipes.append({'materials':materials,'yields':yield_count,'technology_level':int(level[1]) if level else None})
    unique={json.dumps(r,sort_keys=True):r for r in recipes}
    if len(unique)!=1:raise ValueError('Cross-check needs exactly one unambiguous ordinary production recipe')
    return next(iter(unique.values()))


def recipe_bundle(client,name):
    row=client.resolve('items',name);item,meta=client.item(row['id']);recipe=item.get('recipe')
    if not isinstance(recipe,dict) or not isinstance(recipe.get('materials'),list) or not recipe['materials']:raise ValueError('API has no explicit material recipe for this item')
    yields=recipe.get('yields')
    if isinstance(yields,bool) or not isinstance(yields,int) or yields<1:raise ValueError('Recipe batch yield must be a positive integer')
    materials=[]
    for entry in recipe['materials']:
        if not isinstance(entry,dict) or not isinstance(entry.get('count'),int) or isinstance(entry['count'],bool) or entry['count']<1:raise ValueError('Recipe has an invalid material count')
        material,_=client.item(entry['itemId']);materials.append({'id':material['id'],'name':material['name'],'count':entry['count'],'source_url':material['url']})
    if len({m['id'] for m in materials})!=len(materials):raise ValueError('Duplicate material IDs need explicit recipe aggregation')
    cc_url='https://paldb.cc/en/'+quote(item['name'].replace(' ','_'),safe="_'-()")
    try:
        body,cc_meta=get_public(cc_url,**client.network);cc_recipe=parse_cc_recipe(body.decode('utf-8-sig'),item['name'])
        api_counts={m['name'].casefold():m['count'] for m in materials};cc_counts={m['name'].casefold():m['count'] for m in cc_recipe['materials']}
        status='agreed' if api_counts==cc_counts and yields==cc_recipe['yields'] else 'conflict'
        check={'status':status,'recipe':cc_recipe,'retrieval':cc_meta}
    except (ValueError,OSError) as error:check={'status':'unavailable','source_url':cc_url,'reason':str(error)}
    return {'item':{'id':item['id'],'name':item['name'],'url':item['url']},'materials':materials,'yields':yields,
            'api_evidence':client.evidence.copy(),'cross_check':check,'attribution':CREDIT,
            'limits':'Agreement is between public providers, not in-game verification. No recipe is silently selected when providers disagree.'}


def material_deficits(bundle,quantity,inventory=None):
    if isinstance(quantity,bool) or not isinstance(quantity,int) or not 1<=quantity<=1_000_000:raise ValueError('Quantity must be an integer from 1 to 1,000,000')
    inventory={} if inventory is None else inventory
    if not isinstance(inventory,dict) or any(not isinstance(k,str) or isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=1_000_000_000 for k,v in inventory.items()):raise ValueError('Inventory must map exact item names or IDs to nonnegative integers')
    inventory=canonical_inventory(inventory)
    if bundle['cross_check']['status']!='agreed':return {'status':'recipe-evidence-incomplete','reason':'Resolve the provider conflict or missing cross-check before presenting one material total.','recipe':bundle}
    names={v.casefold():m['id'] for m in bundle['materials'] for v in (m['id'],m['name'])};known={};unknown=[]
    for key,value in inventory.items():
        mid=names.get(key.casefold())
        if mid is None:unknown.append(key);continue
        if mid in known:raise ValueError('The same material was supplied twice under a name and ID')
        known[mid]=value
    batches=math.ceil(quantity/bundle['yields']);rows=[]
    for m in bundle['materials']:
        need=m['count']*batches;have=known.get(m['id'],0);rows.append({**m,'required':need,'in_inventory':have,'missing':max(0,need-have)})
    return {'status':'materials-ready','item':bundle['item'],'requested_quantity':quantity,'batches':batches,
            'produced_quantity':batches*bundle['yields'],'materials':rows,'ignored_inventory_entries':unknown,
            'technology_level':bundle['cross_check']['recipe']['technology_level'],
            'scope':'Direct recipe ingredients only; sub-recipes, station ownership and crafting duration are not inferred.',
            'evidence':{'api':bundle['api_evidence'],'cross_check':bundle['cross_check']['retrieval']},'attribution':CREDIT}
