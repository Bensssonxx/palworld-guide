#!/usr/bin/env python3
"""Deterministic source and Agent Skill ZIPs, positive file lists, hashes and manifests."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from check_release import ROOT,check


def archive(path,entries):
    with ZipFile(path,'w',ZIP_DEFLATED,compresslevel=9) as bundle:
        for name,body in sorted(entries):
            info=ZipInfo(name,date_time=(2020,1,1,0,0,0));info.compress_type=ZIP_DEFLATED
            info.external_attr=0o100644<<16;info.create_system=3
            bundle.writestr(info,body)


def build():
    manifest=check();version=(ROOT/'VERSION').read_text(encoding='utf-8').strip();dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    skill=[];source=[]
    for record in manifest['files']:
        p=ROOT/record['path'];body=p.read_bytes();source.append((f'palworld-guide-{version}/'+record['path'],body))
        if record['path'].startswith('palworld-guide/'):
            skill.append((record['path'],body))
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
        skill.append(('palworld-guide/'+name,(ROOT/name).read_bytes()))
    skill.append(('palworld-guide/INSTALL.md',(ROOT/'docs/INSTALL_SKILL.md').read_bytes()))
    paths=[dist/f'palworld-guide-{version}.zip',dist/f'palworld-guide-source-{version}.zip']
    archive(paths[0],skill);archive(paths[1],source)
    (dist/'release-manifest.json').write_text(json.dumps({'version':version,'source_files':manifest['files'],
        'skill_entries':len(skill),'distribution':'Local candidate, not a public release','no_mcp':True},indent=2)+'\n',encoding='utf-8')
    (dist/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths),encoding='utf-8')
    return paths


if __name__=='__main__':
    for p in build():print(p.name)
