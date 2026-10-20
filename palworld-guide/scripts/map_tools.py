#!/usr/bin/env python3
"""Find sourced PalDB locations and project markers onto the provider's real map tiles."""
import argparse
from datetime import datetime,timezone
import hashlib
from html import escape,unescape
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode

from public_sources import get_public, PageText

ROOT=Path(__file__).resolve().parents[1]
MAP_DATA_URL='https://paldb.cc/js/map_data_en.js'
MAP_PAGE_URL='https://paldb.cc/en/Palpagos_Islands'
ALIASES={'coal':'Coal','quartz':'Pure Quartz','sulfur':'Sulfur','fast travel':'Fast Travel',
         'sea base':'SeaBase','yakumo effigy':'Yakumo Effigy'}


def json_assignment(text,name):
    match=re.search(r'\b(?:var|const|let)\s+'+re.escape(name)+r'\s*=\s*',text)
    if not match: raise ValueError(f'Public map response no longer contains {name}; adapter needs review')
    # Parse only the JSON literal; do not evaluate any downloaded JavaScript.
    return json.JSONDecoder().raw_decode(text[match.end():])[0]


def clean(text):
    p=PageText();p.feed(str(text));return ' '.join(p.lines())


def profile():
    return json.loads((ROOT/'references/map-profile.json').read_text(encoding='utf-8'))


def world_bounds(p=None):
    p=p or profile();b=p['raw_bounds'];scale=p['units_per_game_coordinate'];ox,oy=p['raw_offsets']
    return [(b['y_min']+oy)/scale-1000,(b['y_max']+oy)/scale-1000,
            (b['x_min']+ox)/scale-1000,(b['x_max']+ox)/scale-1000]


def raw_to_game(raw,p=None):
    p=p or profile();ox,oy=p['raw_offsets'];scale=p['units_per_game_coordinate']
    return (float(raw['Y'])+oy)/scale-1000,(float(raw['X'])+ox)/scale-1000


def game_to_normal(x,y,p=None):
    xmin,xmax,ymin,ymax=world_bounds(p)
    return (x-xmin)/(xmax-xmin),(ymax-y)/(ymax-ymin)


def map_url(x,y,label=''):
    return MAP_PAGE_URL+'?'+urlencode({'pos':f'{x:.6f},{y:.6f}','item':label})


def validate_config(config,p=None):
    p=p or profile();b=p['raw_bounds']
    expected={'landScapeRealPositionMin':{'X':b['x_min'],'Y':b['y_min']},
              'landScapeRealPositionMax':{'X':b['x_max'],'Y':b['y_max']}}
    for group,values in expected.items():
        for axis,value in values.items():
            if config.get(group,{}).get(axis)!=value:
                raise ValueError('Provider map bounds changed; recalibrate before marking locations')


def load_dataset(data_file=None,**network):
    if data_file:
        path=Path(data_file)
        if path.stat().st_size>20_000_000: raise ValueError('Map data file is too large')
        body=path.read_bytes();text=body.decode('utf-8-sig')
        info={'url':MAP_DATA_URL,'fetched_at':None,'sha256':hashlib.sha256(body).hexdigest(),
              'offline_file':True,'stale':'unknown','note':'Local file retrieval date and version are not verified'}
    else:
        body,info=get_public(MAP_DATA_URL,max_bytes=20_000_000,**network);text=body.decode('utf-8-sig')
        page,page_info=get_public(MAP_PAGE_URL,**network)
        html=page.decode('utf-8','replace')
        if not re.search(r'const\s+perPixel\s*=\s*459\s*;',html) or "image/map8/" not in html or '-582888' not in html or '-301000' not in html:
            raise ValueError('Provider projection changed; review the calibration before plotting')
        info['projection_page_sha256']=page_info['sha256']
    if text.lstrip().startswith('{'):
        obj=json.loads(text);config=obj.get('config');points=obj.get('points',obj.get('fixedDungeon',[]));regions=obj.get('regions',obj.get('regionData',[]))
    else:
        config=json_assignment(text,'config');points=json_assignment(text,'fixedDungeon');regions=json_assignment(text,'regionData')
    if not isinstance(config,dict) or not isinstance(points,list) or not isinstance(regions,list): raise ValueError('Unexpected map dataset shape')
    validate_config(config)
    return points+regions,info


def point_from_record(record,retrieval):
    if 'pos' in record: x,y=raw_to_game(record['pos'])
    elif isinstance(record.get('ipos'),dict): x,y=float(record['ipos']['X']),float(record['ipos']['Y'])
    else: return None
    if not all(math.isfinite(v) for v in (x,y)): return None
    xmin,xmax,ymin,ymax=world_bounds()
    if not xmin<=x<=xmax or not ymin<=y<=ymax: return None
    name=clean(record.get('item') or record.get('id') or record.get('type','Location'))
    return {'label':name[:140],'x':x,'y':y,'map_id':'palpagos-main',
            'category':record.get('type'),'record_id':record.get('id'),
            'reward_group':record.get('RewardName'),'source_url':map_url(x,y,name),
            'dataset_url':retrieval['url'],'source_hash':retrieval['sha256'],
            'status':'source-record','scope':'Map-record anchor; not verified in game and not an exact interior chest location.'}


def locate(query='',category=None,limit=8,near=None,data_file=None,sort='source',min_separation=0,**network):
    if not 1<=limit<=100: raise ValueError('limit must be between 1 and 100')
    records,retrieval=load_dataset(data_file,**network)
    needle=ALIASES.get(query.strip().casefold(),query.strip()).casefold()
    matches=[]
    for record in records:
        if category and record.get('type','').casefold()!=category.casefold(): continue
        searchable=clean(' '.join(str(record.get(k,'')) for k in ('item','id','type','RewardName','comment'))).casefold()
        if needle and needle not in searchable: continue
        point=point_from_record(record,retrieval)
        if point: matches.append(point)
    if near:
        nx,ny=near
        if not all(math.isfinite(v) for v in (nx,ny)): raise ValueError('near coordinates must be finite')
        for point in matches: point['straight_line_coordinate_distance']=math.hypot(point['x']-nx,point['y']-ny)
        matches.sort(key=lambda point:point['straight_line_coordinate_distance'])
    travel=[]
    for record in records:
        if record.get('type')=='Fast Travel':
            point=point_from_record(record,retrieval)
            if point: travel.append(point)
    if not math.isfinite(min_separation) or min_separation<0: raise ValueError('min-separation must be nonnegative and finite')
    if sort not in ('source','fast-travel'): raise ValueError('Unknown sort mode')
    for point in matches:
        if travel:
            closest=min(travel,key=lambda t:(t['x']-point['x'])**2+(t['y']-point['y'])**2)
            point['nearest_fast_travel']={'label':closest['label'],'x':closest['x'],'y':closest['y'],
                'source_url':closest['source_url'],'distance_coordinate_units':math.hypot(closest['x']-point['x'],closest['y']-point['y']),
                'distance_kind':'Straight-line coordinate distance, not a traversable route length'}
    if sort=='fast-travel':
        if not travel: raise ValueError('No fast-travel records available for distance sorting')
        matches.sort(key=lambda point:point['nearest_fast_travel']['distance_coordinate_units'])
    total=len(matches)
    selected=[]
    for point in matches:
        if all(math.hypot(point['x']-other['x'],point['y']-other['y'])>=min_separation for other in selected): selected.append(point)
        if len(selected)>=limit:break
    return {'map_id':'palpagos-main','query':query,'category':category,'retrieval':retrieval,
            'total_matches':total,'points':selected,'selection':{'sort':sort,'minimum_separation_coordinate_units':min_separation},
            'source_status':'Community map records; map version is not inferred from the player version.',
            'coordinate_system':'game X east, Y north; raw UE axes are swapped by the provider transform'}


def checked_points(payload):
    if not isinstance(payload,dict) or payload.get('map_id')!='palpagos-main': raise ValueError('Only the calibrated palpagos-main map is supported; World Tree needs a separate profile')
    points=payload.get('points')
    if not isinstance(points,list) or not 1<=len(points)<=30: raise ValueError('Provide between 1 and 30 map points')
    xmin,xmax,ymin,ymax=world_bounds()
    for p in points:
        if not isinstance(p,dict): raise ValueError('Invalid point')
        for axis in ('x','y'):
            if isinstance(p.get(axis),bool) or not isinstance(p.get(axis),(int,float)) or not math.isfinite(p[axis]): raise ValueError('Point coordinates must be finite numbers')
        if not xmin<=p['x']<=xmax or not ymin<=p['y']<=ymax: raise ValueError('Point is outside the calibrated map')
        if not p.get('source_url'): raise ValueError('Every map point needs its coordinate source URL')
        if not isinstance(p.get('label'),str) or len(p['label'])>200: raise ValueError('Point label must be a short string')
        if not p['source_url'].startswith(('https://','http://')): raise ValueError('Map evidence links must be HTTP(S) URLs')
    return points


def crop_bounds(points):
    p=profile();xmin,xmax,ymin,ymax=world_bounds(p)
    side=min(xmax-xmin,max(480,max(x['x'] for x in points)-min(x['x'] for x in points),max(x['y'] for x in points)-min(x['y'] for x in points))*1.3)
    cx=(max(x['x'] for x in points)+min(x['x'] for x in points))/2
    cy=(max(x['y'] for x in points)+min(x['y'] for x in points))/2
    left=min(max(cx-side/2,xmin),xmax-side);bottom=min(max(cy-side/2,ymin),ymax-side)
    return [left,left+side,bottom,bottom+side]


def render_svg(payload,title='Palworld location map',embed_tiles=False,language='en',show_fast_travel=False,**network):
    if language not in ('en','zh'):raise ValueError('Map language must be en or zh')
    if language=='zh' and title=='Palworld location map':title='帕鲁位置标注图'
    labels=json.loads((ROOT/'references/name-aliases.json').read_text(encoding='utf-8')).get('map_labels',{}) if language=='zh' else {}
    def label(text, fallback='点位'):
        value=labels.get(text,text)
        # Do not invent official place translations or leak English UI labels.
        # Canonical source names remain in the evidence JSON, with coordinates.
        return fallback if language=='zh' and not re.search('[\u3400-\u9fff]',value) else value
    def tr(en,zh):return zh if language=='zh' else en
    points=checked_points(payload);travel=[];travel_ids={}
    if show_fast_travel:
        for point in points:
            nearest=point.get('nearest_fast_travel')
            if not isinstance(nearest,dict):continue
            key=(nearest.get('x'),nearest.get('y'))
            if key not in travel_ids:
                entry={k:nearest.get(k) for k in ('label','x','y','source_url')}
                checked_points({'map_id':'palpagos-main','points':[entry]})
                travel.append(entry);travel_ids[key]=len(travel)
    p=profile();xmin,xmax,ymin,ymax=crop_bounds(points+travel)
    x0,y0,size=35,110,760;W,H=1260,max(960,190+len(points)*96)
    def xy(x,y): return x0+(x-xmin)/(xmax-xmin)*size,y0+(ymax-y)/(ymax-ymin)*size
    bounds=world_bounds(p);origin=xy(bounds[0],bounds[3]);span=(bounds[1]-bounds[0])/8
    tile_size=span/(xmax-xmin)*size
    n0=game_to_normal(xmin,ymax);n1=game_to_normal(xmax,ymin)
    xs=range(max(0,math.floor(n0[0]*8)),min(7,math.floor(n1[0]*8))+1)
    ys=range(max(0,math.floor(n0[1]*8)),min(7,math.floor(n1[1]*8))+1)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<defs><clipPath id="mapclip"><rect x="35" y="110" width="760" height="760" rx="8"/></clipPath></defs>',
           '<rect width="100%" height="100%" fill="#172323"/>','<g font-family="system-ui,Arial,sans-serif" fill="#eff4e9">',
           f'<text x="35" y="48" font-size="27">{escape(title[:100])}</text>',
           f'<text x="35" y="79" font-size="13" fill="#c4cfc4">{tr("Real PalDB terrain · Game-coordinate projection · Sources at right · Not verified in game","真实地形 · 游戏坐标投影 · 右侧附来源 · 未在游戏内实测")}</text>',
           '<g clip-path="url(#mapclip)">']
    import base64
    for tx in xs:
        for ty in ys:
            url=p['tile_template'].format(x=tx,y=ty)
            if embed_tiles:
                image,meta=get_public(url,max_bytes=2_000_000,**network)
                if not image.startswith(b'RIFF') or image[8:12]!=b'WEBP': raise ValueError('Map tile response is not WebP')
                url='data:image/webp;base64,'+base64.b64encode(image).decode()
            parts.append(f'<image href="{escape(url,quote=True)}" x="{origin[0]+tx*tile_size:.6f}" y="{origin[1]+ty*tile_size:.6f}" width="{tile_size+.01:.6f}" height="{tile_size+.01:.6f}" preserveAspectRatio="none"/>')
    resource_parts=[];badges=[];shifted=False
    for i,point in enumerate(points,1):
        px,py=xy(point['x'],point['y']);verified=point.get('status')=='source-record';color='#aff1b0' if verified else '#ffd27f'
        bx,by=px,py
        if any(math.hypot(bx-x,by-y)<34 for x,y in badges):
            available=[]
            for radius in (36,60,84,108,140,180):
                for angle in range(0,360,30):
                    x=px+radius*math.cos(math.radians(angle));y=py+radius*math.sin(math.radians(angle))
                    if x0+16<=x<=x0+size-16 and y0+16<=y<=y0+size-16 and all(math.hypot(x-a,y-b)>=34 for a,b in badges):available.append((x,y))
                if available:break
            if available:bx,by=available[0]
        badges.append((bx,by))
        leader=''
        if (bx,by)!=(px,py):
            shifted=True
            leader=f'<path d="M {px:.6f},{py:.6f} L {bx:.6f},{by:.6f}" stroke="{color}" stroke-width="1.5"/><circle cx="{px:.6f}" cy="{py:.6f}" r="3" fill="{color}"/>'
        resource_parts.append(f'<g><title>{escape(label(point["label"]))} ({point["x"]:.2f}, {point["y"]:.2f})</title>{leader}<circle cx="{bx:.6f}" cy="{by:.6f}" r="14" fill="{color}" stroke="#152323" stroke-width="3"/><text x="{bx:.6f}" y="{by+5:.6f}" text-anchor="middle" fill="#152323" font-size="13" font-weight="700">{i}</text></g>')
    travel_badges=[]
    for i,point in enumerate(travel,1):
        px,py=xy(point['x'],point['y'])
        # A small separate badge keeps a nearby resource pin visible at overview scale.
        tx,ty=px+29,py-30
        for dx,dy in ((29,-30),(-29,-30),(29,30),(-29,30),(0,-55),(55,0),(-55,0),(0,55)):
            x,y=px+dx,py+dy
            if x0+16<=x<=x0+size-16 and y0+16<=y<=y0+size-16 and all(math.hypot(x-a,y-b)>=34 for a,b in badges+travel_badges):tx,ty=x,y;break
        travel_badges.append((tx,ty))
        parts.append(f'<g><title>{escape(label(point["label"]))} ({point["x"]:.2f}, {point["y"]:.2f})</title><path d="M {px:.6f},{py-8:.6f} l 8,8 -8,8 -8,-8 Z" fill="#83b1ff" stroke="#152323" stroke-width="2"/><path d="M {px:.6f},{py:.6f} L {tx:.6f},{ty:.6f}" stroke="#83b1ff" fill="none"/><rect x="{tx-13:.6f}" y="{ty-10:.6f}" width="26" height="19" rx="3" fill="#83b1ff"/><text x="{tx:.6f}" y="{ty+4:.6f}" text-anchor="middle" fill="#101827" font-size="12" font-weight="700">T{i}</text></g>')
    parts.extend(resource_parts)
    parts.append('</g>')
    for i,point in enumerate(points,1):
        yy=143+(i-1)*96;status=tr('Public source record','公开来源点位') if point.get('status')=='source-record' else tr('User supplied / unverified','用户提供／未核实')
        point_label=label(point['label'])[:43]
        if point.get('cluster'):
            cluster=point['cluster'];count=cluster['record_count'];radius=cluster['radius_coordinate_units']
            point_label+=tr(f' · {count} nodes / radius {radius:g}',f' · 半径{radius:g}内{count}个矿点')
        parts.extend([f'<text x="830" y="{yy}" font-size="15">{i}. {escape(point_label)}</text>',
                      f'<text x="830" y="{yy+27}" font-size="16" fill="#aff1b0">({point["x"]:.2f}, {point["y"]:.2f})</text>',
                      f'<a href="{escape(point["source_url"],quote=True)}"><text x="830" y="{yy+51}" font-size="12" fill="#c4cfc4">{status} · {tr("Source","来源")} ↗</text></a>'])
        nearest=point.get('nearest_fast_travel',{})
        key=(nearest.get('x'),nearest.get('y'))
        if key in travel_ids:
            name=label(nearest['label'],'传送点')[:28]
            parts.append(f'<text x="830" y="{yy+75}" font-size="12" fill="#83b1ff">T{travel_ids[key]} · {escape(name)} · {math.hypot(point["x"]-nearest["x"],point["y"]-nearest["y"]):.1f} {tr("coord. units","坐标单位")}</text>')
    if travel:
        parts.append(f'<text x="35" y="{H-78}" font-size="12" fill="#83b1ff">{tr("Blue T markers: nearest fast travel · distances are straight-line, not travel routes","蓝色 T 标记：最近传送点 · 距离为直线坐标差，不是实际行进路线")}</text>')
    if shifted:
        parts.append(f'<text x="35" y="95" font-size="11" fill="#aff1b0">{tr("Leader lines connect displaced number labels to the exact coordinate anchors.","密集编号已错开；引线连接真实坐标锚点，矿点坐标未改变。")}</text>')
    parts.extend([f'<text x="35" y="{H-54}" font-size="12" fill="#c4cfc4">{tr("Terrain © Pocketpair · Map/data PalDB · Markers Palworld Guide · Checked","地形 © Pocketpair · 地图数据 PalDB · 标注 Palworld Guide · 核对日期")} {datetime.now(timezone.utc).date()}</text>',
                  f'<text x="35" y="{H-29}" font-size="12" fill="#c4cfc4">{tr("Data retrieved:","数据读取：")} {escape(str(payload.get("retrieval",{}).get("fetched_at") or tr("Unknown (local file)","未知（本地文件）")))}; {tr("markers do not verify respawn or rewards.","点位不证明刷新时间或掉落奖励。")}</text>',
                  '</g></svg>'])
    return '\n'.join(parts),{'crop_game_bounds':[xmin,xmax,ymin,ymax],'markers':[{**point,'svg_position':list(xy(point['x'],point['y'])),'number_label_position':list(badges[i])} for i,point in enumerate(points)],
                            'embedded_tiles':embed_tiles,'map_profile':p['id'],'tiles':len(list(xs))*len(list(ys)),
                            'language':language,'fast_travel_markers':[{**point,'marker_id':f'T{i}','svg_position':list(xy(point['x'],point['y']))} for i,point in enumerate(travel,1)]}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    locate_p=sub.add_parser('locate');locate_p.add_argument('--query',default='');locate_p.add_argument('--category');locate_p.add_argument('--limit',type=int,default=8);locate_p.add_argument('--near',type=float,nargs=2);locate_p.add_argument('--data-file');locate_p.add_argument('--output');locate_p.add_argument('--sort',choices=('source','fast-travel'),default='source');locate_p.add_argument('--min-separation',type=float,default=0)
    mark=sub.add_parser('mark');mark.add_argument('--points',required=True);mark.add_argument('--output',required=True);mark.add_argument('--title',default='Palworld location map');mark.add_argument('--embed-tiles',action='store_true')
    mark.add_argument('--language',choices=('en','zh'),default='en');mark.add_argument('--show-fast-travel',action='store_true')
    for cmd in (locate_p,mark): cmd.add_argument('--cache-dir');cmd.add_argument('--offline',action='store_true');cmd.add_argument('--refresh',action='store_true')
    args=vars(parser.parse_args());command=args.pop('command');output=args.pop('output',None)
    try:
        if output and Path(output).exists(): raise ValueError('Output exists; choose a new path to preserve it')
        if command=='locate':
            result=locate(**args);text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
            if output: Path(output).write_text(text, encoding='utf-8')
            print(text if not output else json.dumps({'output':output,'points':len(result['points']),'total_matches':result['total_matches']},ensure_ascii=False))
        else:
            points=Path(args.pop('points'));payload=json.loads(points.read_text(encoding='utf-8'))
            report=Path(output).with_suffix('.evidence.json')
            if report.exists(): raise ValueError('Evidence output exists; use a new output name')
            svg,result=render_svg(payload,**args)
            Path(output).write_text(svg, encoding='utf-8')
            report.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False), encoding='utf-8')
            print(json.dumps({'output':output,'evidence':str(report),'points':len(result['markers']),'embedded_tiles':result['embedded_tiles']},ensure_ascii=False))
    except (ValueError,OSError,KeyError) as error: parser.exit(2,f'Map tool failed: {error}\n')


if __name__=='__main__': main()
