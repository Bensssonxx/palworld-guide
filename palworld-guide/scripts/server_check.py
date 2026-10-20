#!/usr/bin/env python3
"""Read-only checks of supplied Palworld configs, Info.json and logs. No server connection."""
import argparse
import json
import math
from pathlib import Path
import re

OFFICIAL_CONFIG='https://docs.palworldgame.com/settings-and-operation/configuration/'
OFFICIAL_MODS='https://docs.palworldgame.com/settings-and-operation/mod/'
MOD_TECH='https://github.com/pocketpairjp/PalworldModUploader/blob/main/PalworldModUploader/docs/en/04-Tech.md'
MOD_HELP='https://pwmodding.wiki/docs/users/workshop/troubleshooting'
SAFE_KEYS={'ServerPlayerMaxNum','BaseCampWorkerMaxNum','PalStomachDecreaceRate','EnemyDropItemRate',
           'bEnableNonLoginPenalty','bIsUseBackupSaveData','bAllowClientMod','bGlobalEnableMod','ActiveModList'}
MOD_TYPES={'UE4SS':'Mods/NativeMods/UE4SS','Lua':'Mods/NativeMods/UE4SS/Mods/{PackageName}',
           'PalSchema':'Mods/NativeMods/UE4SS/Mods/PalSchema/mods/{PackageName}',
           'LogicMods':'Pal/Content/Paks/LogicMods','Paks':'Pal/Content/Paks/~WorkshopMods/{PackageName}'}


def tokens(text):
    """Split top-level INI/OptionSettings values, respecting quotes and nested tuples."""
    out=[];start=0;depth=0;quoted=False;escaped=False
    for i,c in enumerate(text):
        if escaped: escaped=False;continue
        if c=='\\' and quoted: escaped=True;continue
        if c=='"': quoted=not quoted
        elif not quoted:
            if c=='(': depth+=1
            elif c==')': depth-=1
            elif c==',' and depth==0: out.append(text[start:i]);start=i+1
    if quoted or depth!=0: raise ValueError('Unbalanced quotes or parentheses in OptionSettings')
    out.append(text[start:]);return out


def parse_settings(text):
    if len(text)>4_000_000: raise ValueError('Configuration exceeds 4 MB limit')
    settings={};repeated={};section=''
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith((';','#')): continue
        if line.startswith('[') and line.endswith(']'): section=line[1:-1];continue
        if '=' not in line: continue
        key,value=line.split('=',1);key=key.strip();value=value.strip()
        if key=='OptionSettings':
            if not value.startswith('(') or not value.endswith(')'): raise ValueError('OptionSettings must be parenthesized')
            for item in tokens(value[1:-1]):
                if '=' in item:
                    k,v=item.split('=',1)
                    if k.strip() in SAFE_KEYS: settings[k.strip()]=v.strip().strip('"')
        elif key in SAFE_KEYS:
            if key=='ActiveModList': repeated.setdefault(key,[]).append(value.strip('"'))
            else: settings[key]=value.strip('"')
    result=settings | repeated
    for key,value in list(result.items()):
        if key=='ActiveModList':continue
        if key.startswith('b'):
            result[key]=value if value.casefold() in ('true','false') else '<invalid value>'
        else:
            try:
                number=float(value)
                if not math.isfinite(number):raise ValueError()
                result[key]=number
            except (ValueError,TypeError):result[key]='<invalid value>'
    return result


def safe_package(value):
    # Package names are identifiers, never filesystem paths or command text.
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',value) or value in ('.','..'):
        raise ValueError('PackageName or dependency is not a supported identifier')
    return value


def inspect_server(world_text='',mod_text='',manifest=None,log_text='',os_name='unknown',revision=None,
                   food='unknown',stuck='unknown',manual_loader=False,workshop_loader=False,world_filename=''):
    if os_name not in ('windows','linux','unknown'): raise ValueError('Unknown server operating system')
    if revision is not None and (isinstance(revision,bool) or not isinstance(revision,int) or revision<0): raise ValueError('Revision must be a nonnegative integer')
    if food not in ('empty','available','unknown') or stuck not in ('yes','no','unknown'): raise ValueError('Unknown observation value')
    if len(log_text)>4_000_000: raise ValueError('Log exceeds 4 MB limit; supply a recent excerpt')
    world=parse_settings(world_text);mods=parse_settings(mod_text);findings=[]
    def add(code,level,message,next_step,source):
        findings.append({'code':code,'level':level,'message':message,'next_step':next_step,'source_url':source})
    if world_filename.lower()=='defaultpalworldsettings.ini':
        add('default-file','warning','This is the default template; editing it does not change an existing world configuration.','Locate the active PalWorldSettings.ini or the corresponding hosting-panel setting.',OFFICIAL_CONFIG)
    if food=='empty':
        add('empty-feedbox','check','Food ran out. Inspect reserves, production and transport first.','Check whether replenishment continues while players are offline before considering a hunger-rate change.',OFFICIAL_CONFIG)
    elif food=='available':
        add('food-present','check','Food remains available, so insufficient total food alone does not explain the symptom.','Check whether Pals can reach the feed box and observe stuck or post-load positions.',OFFICIAL_CONFIG)
    if stuck=='yes':
        add('pathing-observation','check','A stuck Pal is an observed pathfinding clue that needs an in-game check.','Check access to feed boxes and beds. Configuration text cannot establish a pathfinding cause.',OFFICIAL_CONFIG)
    if 'PalStomachDecreaceRate' in world:
        try:
            rate=float(world['PalStomachDecreaceRate'])
            if not 0<=rate<=1e6: raise ValueError()
            add('hunger-rate','info','A Pal hunger-depletion multiplier is present; it does not treat existing illness.','Use food and pathfinding observations; this value alone cannot prove the cause.',OFFICIAL_CONFIG)
        except ValueError: add('invalid-hunger-rate','warning','The hunger multiplier is not a valid nonnegative finite value.','Check the format and the range supported by the current version.',OFFICIAL_CONFIG)
    if 'EnemyDropItemRate' in world:
        add('drop-quantity','info','The official parameter list describes EnemyDropItemRate as a drop-quantity multiplier.','Do not treat it as a legendary schematic probability multiplier.',OFFICIAL_CONFIG)
    if 'bEnableNonLoginPenalty' in world:
        add('legacy-offline-key','check','A legacy offline parameter is present, but the checked official page does not establish it as an offline-problem fix.','Check the current version and hosting documentation; changing it is not a proven hunger fix.',OFFICIAL_CONFIG)
    if str(mods.get('bGlobalEnableMod','')).lower()=='false':
        add('mods-disabled','warning','The global mod switch is False.','Check the switch in the correct client or server instance. This tool does not change it.',OFFICIAL_MODS)
    if 'bGlobalEnableMod' in mods and str(mods['bGlobalEnableMod']).lower() not in ('true','false'):
        add('invalid-mod-switch','warning','The global mod switch must be True or False.','Correct the supplied boolean value before checking activation; no file was changed.',OFFICIAL_MODS)
    info=None
    if manifest is not None:
        if not isinstance(manifest,dict): raise ValueError('Info.json must contain an object')
        package=safe_package(manifest.get('PackageName'))
        dependency_values=manifest.get('Dependencies',[])
        if not isinstance(dependency_values,list): raise ValueError('Dependencies must be an array')
        dependencies=[safe_package(x) for x in dependency_values]
        rules=manifest.get('InstallRule',[])
        if not isinstance(rules,list) or any(not isinstance(r,dict) for r in rules): raise ValueError('InstallRule must be an array of objects')
        if any('IsServer' in r and not isinstance(r['IsServer'],bool) for r in rules): raise ValueError('InstallRule IsServer must be a JSON boolean, not a string or number')
        server_rules=[r for r in rules if r.get('IsServer') is True]
        active=mods.get('ActiveModList',[])
        if isinstance(active,str): active=[active]
        active=[safe_package(x) for x in active]
        required_revision=manifest.get('MinRevision')
        if required_revision is not None and (isinstance(required_revision,bool) or not isinstance(required_revision,int) or required_revision<0): raise ValueError('MinRevision must be a nonnegative integer')
        info={'package_name':package,'dependencies':dependencies,'server_rule_count':len(server_rules),
              'declared_server_types':[str(r.get('Type',''))[:40] for r in server_rules],
              'active_mods':active,'minimum_revision':required_revision,
              'expected_deployment_paths':[MOD_TYPES[r['Type']].replace('{PackageName}',package) for r in server_rules if r.get('Type') in MOD_TYPES],
              'path_anchor':'Relative to the actual PalServer.exe directory; do not substitute the legacy manual UE4SS Win64 layout.'}
        if not server_rules:
            add('no-server-rule','warning','Info.json has no IsServer: true rule, so it does not establish official dedicated-server deployment support.','Check the author compatibility statement and whether this is the client package.',MOD_TECH)
        if os_name=='linux' and server_rules:
            add('documented-os','warning','The checked official server-mod documentation covers Windows; the supplied OS is Linux.','Recheck official support and author guidance before applying Windows paths.',OFFICIAL_MODS)
        if mod_text and package not in active:
            add('package-not-active','warning','This PackageName is absent from the supplied ActiveModList.','Match PackageName rather than a numeric Workshop ID or folder name.',MOD_TECH)
        missing=[d for d in dependencies if d not in active]
        if mod_text and missing:
            add('dependencies-not-listed','check','Not all declared dependencies appear in the supplied ActiveModList.','Check deployment and activation of the dependencies. No live server files were inspected.',MOD_TECH)
        if revision is not None and required_revision is not None and revision<required_revision:
            add('revision-too-old','warning','The supplied game revision is below the declared minimum.','Check the actual revision in the game title and the mod version.',MOD_TECH)
        elif required_revision is not None and revision is None:
            add('revision-unknown','check','The mod declares a minimum revision, but the game revision was not supplied.','Read the revision from the title or log. A version string such as 1.0.5 is not a revision.',MOD_TECH)
    if manual_loader and workshop_loader:
        add('two-loader-paths','check','Both manual and Workshop loaders were reported; investigate possible duplicate loading.','Separate client and server instances and inspect their loading methods before proposing a reversible isolation step.',MOD_HELP)
    log_summary={'ue4ss_mentions':len(re.findall(r'UE4SS',log_text,re.I)),
                 'palschema_mentions':len(re.findall(r'PalSchema',log_text,re.I)),
                 'loader_git_hashes':list(dict.fromkeys(re.findall(r'Git SHA\s*[:=]\s*([a-f0-9]{7,40})',log_text,re.I))),
                 'failure_signal_count':len(re.findall(r'access violation|failed to load|missing dependency|unhandled exception',log_text,re.I))}
    if log_summary['failure_signal_count']:
        add('log-failure-signals','check','Failure or crash keywords were found; keywords alone do not establish the cause.','Check the current launch timestamp, failure stage and latest mod change.',MOD_HELP)
    if not findings: add('need-observations','check','The supplied evidence is insufficient to diagnose the issue.','Add the symptom, affected instance and recent configuration or log excerpts.',OFFICIAL_CONFIG)
    return {'mode':'read-only-local-analysis','inputs_echoed':'Only recognized gameplay settings and mod identifiers; no raw config, path, password, IP or log text.',
            'recognized_gameplay_settings':world,'recognized_mod_settings':{k:v for k,v in mods.items() if k!='ActiveModList'},
            'manifest':info,'log_signals':log_summary,'findings':findings,
            'limits':'Text checks do not prove live deployment, runtime loading, gameplay correctness, or a crash root cause.',
            'documentation_scope':'Official server pages observed on 2026-10-19, labeled 1.0.4; recheck compatibility for other versions.'}


def read_optional(path):
    if not path:return ''
    p=Path(path)
    if p.stat().st_size>4_000_000:raise ValueError('Input exceeds 4 MB')
    return p.read_text(encoding='utf-8-sig',errors='replace')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--world-config');p.add_argument('--mod-config');p.add_argument('--info');p.add_argument('--log')
    p.add_argument('--os',choices=('windows','linux','unknown'),default='unknown',dest='os_name');p.add_argument('--revision',type=int)
    p.add_argument('--food',choices=('empty','available','unknown'),default='unknown');p.add_argument('--stuck',choices=('yes','no','unknown'),default='unknown')
    p.add_argument('--manual-loader',action='store_true');p.add_argument('--workshop-loader',action='store_true');p.add_argument('--output')
    a=vars(p.parse_args());output=a.pop('output');world_path=a.pop('world_config');mod_path=a.pop('mod_config');info_path=a.pop('info');log_path=a.pop('log')
    try:
        if output and Path(output).exists(): raise ValueError('Output exists; choose a new path')
        result=inspect_server(world_text=read_optional(world_path),mod_text=read_optional(mod_path),
                              manifest=json.loads(read_optional(info_path)) if info_path else None,
                              log_text=read_optional(log_path),world_filename=Path(world_path).name if world_path else '',**a)
        text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
        if output:Path(output).write_text(text, encoding='utf-8')
        else:print(text)
    except (ValueError,OSError) as error:p.exit(2,f'Server check failed: {error}\n')


if __name__=='__main__':main()
