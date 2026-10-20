#!/usr/bin/env python3
"""Copy the skill into an explicitly selected project's local discovery directory."""
import argparse
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def install(project):
    project=Path(project).resolve()
    if not project.is_dir():raise ValueError('Choose an existing project directory')
    target=project/'.agents/skills/palworld-guide'
    if target.exists() or target.is_symlink():raise ValueError('Installation exists; preserve it and choose another project')
    shutil.copytree(ROOT/'palworld-guide',target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT/name,target/name)
    shutil.copy2(ROOT/'docs/INSTALL_SKILL.md',target/'INSTALL.md')
    return target


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',required=True);a=p.parse_args()
    try:print(install(a.project))
    except (ValueError,OSError) as error:p.exit(2,str(error)+'\n')
