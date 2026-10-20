#!/usr/bin/env python3
"""Fresh-home/empty-cache interpreter trial. This is not an independent human/model beta."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from zipfile import ZipFile
from build_release import build,ROOT


def trial():
    skill_zip,source_zip=build()
    with tempfile.TemporaryDirectory(prefix='palworld-isolated-beta-') as tmp:
        base=Path(tmp);unpacked=base/'source';unpacked.mkdir()
        with ZipFile(source_zip) as z:z.extractall(unpacked)
        repo=next(unpacked.iterdir());project=base/'project';project.mkdir();home=base/'home';home.mkdir()
        env=os.environ.copy();env.update(HOME=str(home),PYTHONUTF8='1',PYTHONNOUSERSITE='1')
        env.pop('PYTHONPATH',None)
        def run(*args):
            r=subprocess.run([sys.executable,'-E','-s',*map(str,args)],cwd=repo,env=env,capture_output=True,text=True,encoding='utf-8',timeout=45)
            if r.returncode:raise ValueError(r.stderr or r.stdout)
            return r
        run(repo/'tools/install.py','--project',project)
        installed=project/'.agents/skills/palworld-guide';script=installed/'scripts/workflow.py'
        task=base/'task.json';folder=base/'run'
        run(script,'draft','--question','I have Bushi, Penking and Vanwyrm; breed Pyrin','--output',task)
        run(script,'run','--task',task,'--output-dir',folder,'--offline','--cache-dir',base/'empty-cache')
        result=json.loads((folder/'run.json').read_text(encoding='utf-8'))
        if result['execution_status']!='completed' or result['results']['s1']['data']['target']['name']!='Pyrin':raise ValueError('Installed species route failed')
        unknown=base/'unknown.json';run(script,'draft','--question','How does a new Palworld weapon mechanic work?','--output',unknown)
        run(script,'run','--task',unknown,'--output-dir',base/'research')
        researched=json.loads((base/'research/run.json').read_text(encoding='utf-8'))
        if researched['execution_status']!='awaiting-research' or not researched['research_queue']:raise ValueError('Installed research handoff failed')
        pending=researched['research_queue'][0];now=datetime.now(timezone.utc).isoformat()
        url='https://docs.palworldgame.com/settings-and-operation/mod/';excerpt='Synthetic smoke fixture, not a claim of an actual web read.'
        receipt={pending['id']:{'schema':1,'request_id':pending['id'],
            'searches':[{'query':'Palworld synthetic smoke question','provider':'synthetic-smoke-fixture','searched_at':now,'result_urls':[url]}],
            'sources':[{'id':'fixture','title':'Synthetic smoke fixture','url':url,'discovered_from':url,'role':'official','read_status':'read','retrieved_at':now,'excerpt':excerpt,'excerpt_sha256':hashlib.sha256(excerpt.encode()).hexdigest()}],
            'findings':[{'claim':'Synthetic structural resume check only.','source_ids':['fixture']}],
            'resolution':{'action':'answer','limitations':['Synthetic fixture, not live research.']}}}
        receipts=base/'receipts.json';receipts.write_text(json.dumps(receipt),encoding='utf-8')
        run(script,'resume','--task',unknown,'--previous-run',base/'research/run.json','--research',receipts,'--output-dir',base/'resumed')
        resumed=json.loads((base/'resumed/run.json').read_text(encoding='utf-8'))
        if resumed['execution_status']!='completed':raise ValueError('Installed receipt resume failed')
        # Refuse overwriting the first installation.
        denied=subprocess.run([sys.executable,str(repo/'tools/install.py'),'--project',str(project)],capture_output=True,text=True,encoding='utf-8',env=env)
        if denied.returncode==0:raise ValueError('Installer overwrote existing installation')
    report={'status':'passed','scope':'Fresh temporary project/home/cache and isolated interpreter, executed by building assistant; not independent human/model beta',
            'python':sys.version.split()[0],'platform':sys.platform,'checks':['source ZIP extraction','project installation','offline species route','unsupported-question search queue','synthetic receipt resume (not a live search)','existing-install refusal'],
            'skill_sha256':hashlib.sha256(skill_zip.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(source_zip.read_bytes()).hexdigest()}
    (ROOT/'dist/beta-smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':print(json.dumps(trial()))
