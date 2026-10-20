#!/usr/bin/env python3
"""Species-level breeding shortcuts backed by pinned, MIT-licensed PalCalc breeding records."""
from pathlib import Path
import json,difflib
from name_aliases import canonical_name
ROOT=Path(__file__).resolve().parents[1]
GENDERS={0:'compatible opposite sexes',1:'male',2:'female'}

def load_data():
    data=json.loads((ROOT/'references/breeding-data.json').read_text(encoding='utf-8'))
    if data.get('schema')!=1 or not isinstance(data.get('species'),list) or not isinstance(data.get('pairs'),list):raise ValueError('Breeding snapshot schema is unsupported')
    return data

def resolve(data,name):
    if not isinstance(name,str) or not name.strip():raise ValueError('An English Pal name or internal ID is required')
    key=canonical_name(name,'pals').casefold();matches=[i for i,p in enumerate(data['species']) if key in (p['name'].casefold(),p['id'].casefold())]
    if len(matches)!=1:
        suggestions=difflib.get_close_matches(name,[p['name'] for p in data['species']],n=4,cutoff=.4)
        raise ValueError('Pal not uniquely resolved: '+name+'. Suggestions: '+', '.join(suggestions))
    return matches[0]

def pair_result(data,a,b):
    ia,ib=resolve(data,a),resolve(data,b);rows=[]
    for row_index,(p1,p2,child,g1,g2) in enumerate(data['pairs']):
        if (ia,ib)==(p1,p2) or (ia,ib)==(p2,p1):rows.append({'parent_a':data['species'][p1],'parent_b':data['species'][p2],'child':data['species'][child],'gender_a':GENDERS[g1],'gender_b':GENDERS[g2],'upstream_record_index':row_index})
    return {'status':'source-records' if rows else 'no-recorded-pair','results':rows,'source':data['source'],
            'limits':'Gender-specific records are alternatives, not guaranteed simultaneous outcomes. Passive skills, IVs and mutations are not inferred.'}

def plan(data,target,owned,max_generations=6):
    if not isinstance(owned,list) or not 1<=len(owned)<=100:raise ValueError('Supply 1..100 owned species names')
    if isinstance(max_generations,bool) or not isinstance(max_generations,int) or not 1<=max_generations<=10:raise ValueError('Generation limit must be 1..10')
    goal=resolve(data,target);initial={resolve(data,n) for n in owned};depth={i:0 for i in initial};parents={}
    for wave in range(1,max_generations+1):
        if goal in depth:break
        candidates={}
        for row_index,row in enumerate(data['pairs']):
            a,b,c,g1,g2=row
            if c in depth or a not in depth or b not in depth:continue
            if max(depth[a],depth[b])+1!=wave:continue
            # Stable tie-break among the minimum-generation candidates; no time-optimality claim.
            score=(depth[a]+depth[b],a,b,g1,g2,row_index)
            if c not in candidates or score<candidates[c][0]:candidates[c]=(score,row_index,row)
        for c,(_,row_index,row) in candidates.items():depth[c]=wave;parents[c]=(row_index,row)
        if not candidates:break
    steps=[];visited=set()
    def visit(c):
        if c in initial or c in visited:return
        row_index,(a,b,child,g1,g2)=parents[c];visit(a);visit(b);visited.add(c)
        steps.append({'step':len(steps)+1,'parent_a':data['species'][a],'parent_b':data['species'][b],'child':data['species'][child],
                      'parent_a_gender_rule':GENDERS[g1],'parent_b_gender_rule':GENDERS[g2],
                      'generation':depth[c],'upstream_record_index':row_index})
    if goal in depth:visit(goal)
    state='already-owned' if goal in initial else 'species-route-found' if goal in depth else 'no-route-within-limit'
    return {'status':state,'target':data['species'][goal],'owned_species':[data['species'][i] for i in sorted(initial)],
            'dependency_generations':depth.get(goal),'breeding_operations_in_this_plan':len(steps),'steps':steps,
            'next_action':'Target species is already listed as owned.' if state=='already-owned' else 'Confirm the parent gender requirements, breeding setup and cake supply for step 1.' if steps else 'No route was found using only the supplied species within the generation limit; add available species or inspect a capture route.',
            'source':data['source'],'limits':['Minimum dependency generations in this species-only snapshot, not minimum eggs or real time.','Owned species do not establish compatible individuals or sexes. Each step retains the upstream gender rule.','No passive/IV inheritance, mutation probability, cake cost, hatch time or guaranteed real-world feasibility is modeled.','Snapshot data version is not an assertion that it matches your game version.']}
