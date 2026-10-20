#!/usr/bin/env python3
"""Bounded source/package hygiene checks, not a complete secret scanner or legal opinion."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES={'README.md','LICENSE','THIRD_PARTY_NOTICES.md','VERSION','.gitignore','.gitattributes'}
SOURCE_DIRS={'palworld-guide','tests','tools','docs','examples','.github'}


def files():
    found=[]
    for name in sorted(ROOT_FILES):
        p=ROOT/name
        if not p.is_file():raise ValueError('Missing required root file: '+name)
        found.append(p)
    for folder in sorted(SOURCE_DIRS):
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':found.append(p)
    return found


def check():
    required=['palworld-guide/SKILL.md','palworld-guide/references/research.md','palworld-guide/assets/LICENSE-PalCalc.txt',
              '.github/workflows/check.yml','docs/RELEASE_STATUS.md','examples/breeding-task.json']
    for name in required:
        if not (ROOT/name).is_file():raise ValueError('Missing release component: '+name)
    manifest=[]
    for p in files():
        relative=p.relative_to(ROOT).as_posix()
        if p.is_symlink() or p.suffix.lower() in ('.sav','.webp','.png','.jpg','.log','.bin'):
            raise ValueError('Disallowed public source file: '+relative)
        if set(p.relative_to(ROOT).parts)&{'qa','player-guides','profiles','runs','cache','历史版本'}:
            raise ValueError('Private/generated directory in public source')
        body=p.read_bytes();text=body.decode('utf-8')
        fixture_prefix='/'+'Users'+'/'+'private'+'/'
        inspected=text.replace(fixture_prefix,'/SYNTHETIC/') if relative.startswith('tests/') else text
        if re.search(r'/(?:Users|home)/[A-Za-z0-9_.-]+/|/(?:var|private/var)/folders/|sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',inspected):
            raise ValueError('User path or credential signature in '+relative)
        manifest.append({'path':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
    refs=ROOT/'palworld-guide/references'
    if any((refs/name).exists() for name in ('demo-maps.json','demo-comparisons.json')):
        raise ValueError('Bulk community demonstration snapshots are excluded')
    if json.loads((refs/'integration-examples.json').read_text(encoding='utf-8'))['recipes']:
        raise ValueError('Saved community recipe checks are excluded from public candidate')
    data=json.loads((refs/'breeding-data.json').read_text(encoding='utf-8'))
    notice=ROOT/'palworld-guide/assets/LICENSE-PalCalc.txt'
    if hashlib.sha256(notice.read_bytes()).hexdigest()!=data['source']['files']['license']['sha256']:
        raise ValueError('Bundled upstream license does not match provenance')
    return {'status':'passed','files':manifest,'scope':'Allowlisted source tree and bounded signature/data checks; manual review remains required'}


if __name__=='__main__':
    try:
        r=check();print(json.dumps({'status':r['status'],'files':len(r['files']),'scope':r['scope']}))
    except (ValueError,OSError) as error:raise SystemExit(str(error))
