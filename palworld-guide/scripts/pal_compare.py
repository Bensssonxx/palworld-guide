#!/usr/bin/env python3
"""Read current English PalDB tables; compare matching fields without inventing acquisition difficulty."""
import argparse,json,math,re
from html.parser import HTMLParser
from urllib.parse import urljoin,quote
from public_sources import get_public,PageText
BASE='https://paldb.cc/en/'

class ArticleText(PageText):
    """Exclude site navigation from article evidence; keep genuine body references."""
    excluded={'nav','header','footer'}
    def __init__(self):
        super().__init__();self.links=[];self.anchor=None;self.heading=None;self.section='';self.sections=[]
    def handle_starttag(self,tag,attrs):
        if tag in self.excluded:self.skip+=1
        else:
            super().handle_starttag(tag,attrs)
            if not self.skip:
                if re.fullmatch(r'h[1-6]',tag):self.heading=[]
                if tag=='a':self.anchor={'href':dict(attrs).get('href',''),'parts':[],'section':self.section}
    def handle_data(self,data):
        super().handle_data(data)
        if not self.skip:
            if self.heading is not None:self.heading.append(data)
            if self.anchor is not None:self.anchor['parts'].append(data)
    def handle_endtag(self,tag):
        if tag in self.excluded:self.skip=max(0,self.skip-1)
        else:
            if not self.skip:
                if tag=='a' and self.anchor is not None:
                    url=urljoin(BASE,self.anchor['href']);text=' '.join(''.join(self.anchor['parts']).split())
                    if text and url.startswith(BASE):self.links.append({'label':text,'url':url,'section':self.anchor['section']})
                    self.anchor=None
                if re.fullmatch(r'h[1-6]',tag) and self.heading is not None:
                    self.section=' '.join(''.join(self.heading).split());self.heading=None
                    if self.section and self.section not in self.sections:self.sections.append(self.section)
            super().handle_endtag(tag)


class Tables(HTMLParser):
    """Handle both explicitly closed HTML tables and PalDB's optional closing tags."""
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.link=None
    def finish_cell(self):
        if self.cell is not None:
            self.row.append({'text':' '.join(''.join(self.cell).split()),'href':self.link});self.cell=None;self.link=None
    def finish_row(self):
        self.finish_cell()
        if self.row is not None:self.table.append(self.row);self.row=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='table':self.table=[]
        if tag=='tr' and self.table is not None:self.finish_row();self.row=[]
        if tag in ('td','th') and self.row is not None:self.finish_cell();self.cell=[]
        if tag=='a' and self.cell is not None and self.link is None:self.link=attrs.get('href')
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.finish_cell()
        if tag=='tr' and self.row is not None:self.finish_row()
        if tag=='table' and self.table is not None:self.finish_row();self.tables.append(self.table);self.table=None


def number(value):
    if not value.strip():return None
    result=float(value.replace(',',''))
    if not math.isfinite(result) or result<0:raise ValueError('Unexpected negative or non-finite table value')
    return int(result) if result.is_integer() else result


def parse_table(html,kind):
    if kind=='ground':
        heading=re.search(r'<h5\b[^>]*>\s*Ground Mounts\b[^<]*</h5>',html,re.I)
        if not heading:raise ValueError('Ground Mounts section was not found; inspect the source')
        section=html[heading.end():]
        end=section.find('</table>')
        if end<0:raise ValueError('Ground Mounts table is incomplete')
        html=section[:end+8]
    p=Tables();p.feed(html)
    header=['name','Run Speed','Ride Sprint Speed','Tech Level','Stamina','GravityScale','JumpZVelocity'] if kind=='ground' else ['Pal','Level','4 Level']
    candidates=[table for table in p.tables if table and [c['text'] for c in table[0]]==header]
    if not candidates:raise ValueError('Source table headings changed; inspect the page before adapting the parser')
    table=candidates[0];records=[]
    for row in table[1:]:
        if len(row)!=len(header):raise ValueError('Unexpected table row shape')
        name=row[0]['text'];href=row[0]['href']
        if not name or not href:raise ValueError('Source row is missing its name or article link')
        url=urljoin(BASE,href)
        if not url.startswith(BASE):raise ValueError('Unexpected article host or language')
        if kind=='ground':
            fields=dict(zip(('run_speed','ride_sprint_speed','tech_level','stamina','gravity_scale','jump_velocity'),map(lambda c:number(c['text']),row[1:])))
            if any(fields[k] is None for k in ('run_speed','ride_sprint_speed','stamina')):raise ValueError('Required mount stat is missing')
        else:fields={'listed_work_level':number(row[1]['text']),'four_star_work_level':number(row[2]['text'])}
        records.append({'name':name,'source_url':url,**fields})
    if not records:raise ValueError('No source records parsed')
    return records


def compare(kind='ground',level=None,names=None,baseline=None,sort='sprint',limit=10,**network):
    if kind not in ('ground','mining','handiwork'):raise ValueError('Unsupported comparison kind')
    if level is not None and (isinstance(level,bool) or not isinstance(level,int) or level<1):raise ValueError('Level must be a positive integer')
    if not 1<=limit<=100:raise ValueError('Limit must be 1..100')
    if kind!='ground' and (level is not None or baseline):raise ValueError('Work tables do not establish capture levels or mount baselines')
    slug={'ground':'Mounts','mining':'Mining','handiwork':'Handiwork'}[kind]
    body,meta=get_public(BASE+slug,**network);rows=parse_table(body.decode('utf-8-sig'),kind);all_rows=rows
    if names:
        wanted={n.casefold().strip() for n in names};available={r['name'].casefold() for r in rows}
        if not wanted<=available:raise ValueError('Requested names not found in this source table: '+', '.join(sorted(wanted-available)))
        rows=[r for r in rows if r['name'].casefold() in wanted]
    if kind=='ground':
        rows=[dict(r) for r in rows if level is None or r['tech_level'] is not None and r['tech_level']<=level]
        for row in rows:
            row['pareto_frontier']=not any((r['ride_sprint_speed']>=row['ride_sprint_speed'] and r['stamina']>=row['stamina']) and (r['ride_sprint_speed']>row['ride_sprint_speed'] or r['stamina']>row['stamina']) for r in rows)
            row['acquisition_status']='Not established by the mount table; check wild/Alpha/breeding routes separately.'
        if baseline:
            matches=[r for r in all_rows if r['name'].casefold()==baseline.casefold()]
            if not matches:raise ValueError('Baseline name was not found')
            b=matches[0]
            for row in rows:row['delta_from_baseline']={k:row[k]-b[k] for k in ('ride_sprint_speed','stamina')}
        if sort not in ('sprint','stamina'):raise ValueError('Mount sorting must be sprint or stamina')
        rows.sort(key=lambda r:(r['ride_sprint_speed'],r['stamina']) if sort=='sprint' else (r['stamina'],r['ride_sprint_speed']),reverse=True)
    else:rows=sorted(rows,key=lambda r:(r['listed_work_level'],r['four_star_work_level']),reverse=True)
    return {'kind':kind,'retrieval':meta,'records_parsed':len(all_rows),'matching_records':len(rows),'player_level':level,
            'baseline':baseline,'records':rows[:limit],
            'limits':['Tech Level filters the listed technology requirement, not capture or ownership feasibility.','Sprint speed and stamina are separate metrics; stamina is not duration and their product is not range.','Work table columns remain separate; higher listed suitability does not prove higher measured throughput.','No passives, upgrades or acquisition difficulty inferred. Current source version is not assumed to match the player version.']}


def entry(slug,contains='',max_chars=1800,**network):
    if not re.fullmatch(r"[A-Za-z0-9_'()-][A-Za-z0-9_'() .-]{0,99}",slug):raise ValueError('Use an English article slug from a verified PalDB link')
    if not 100<=max_chars<=5000:raise ValueError('max-chars must be 100..5000')
    body,meta=get_public(BASE+quote(slug.replace(' ','_'),safe="_'()-"),**network)
    p=ArticleText();p.feed(body.decode('utf-8-sig','replace'));lines=p.lines();selected=[]
    for i,line in enumerate(lines):
        if contains and contains.casefold() in line.casefold():selected.extend(lines[max(0,i-1):i+3])
    excerpt='\n'.join(dict.fromkeys(selected))[:max_chars]
    links=[a for a in p.links if contains and (contains.casefold() in a['section'].casefold() or a['label'] in excerpt)] if selected else []
    return {'retrieval':meta,'matched':bool(selected),'contains':contains,'excerpt':excerpt,'article_links':list({a['url']:a for a in links}.values())[:20],
            'available_sections':p.sections[:30],
            'overview_excerpt':'\n'.join(lines[:30])[:max_chars] if not selected else '',
            'overview_links':list({a['url']:a for a in p.links}.values())[:20] if not selected else [],
            'limits':'Article text is retrieved evidence. Resolve the entity and inspect the exact item/ammo/skill/acquisition section before answering.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('compare');c.add_argument('--kind',choices=('ground','mining','handiwork'),default='ground');c.add_argument('--level',type=int);c.add_argument('--names',nargs='+');c.add_argument('--baseline');c.add_argument('--sort',choices=('sprint','stamina'),default='sprint');c.add_argument('--limit',type=int,default=10)
    e=sub.add_parser('entry');e.add_argument('--slug',required=True);e.add_argument('--contains',required=True);e.add_argument('--max-chars',type=int,default=1800)
    for cmd in (c,e):
        cmd.add_argument('--cache-dir');cmd.add_argument('--offline',action='store_true');cmd.add_argument('--refresh',action='store_true')
    args=vars(p.parse_args());command=args.pop('command')
    try:result=compare(**args) if command=='compare' else entry(**args);print(json.dumps(result,indent=2,allow_nan=False))
    except (ValueError,OSError) as error:p.exit(2,f'Comparison tool failed: {error}\n')

if __name__=='__main__':main()
