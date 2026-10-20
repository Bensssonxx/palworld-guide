#!/usr/bin/env python3
"""Compare conditional reward chains and calculate user-supplied revisit windows; no game rates built in."""
import argparse,json,math
from datetime import datetime,timedelta
from urllib.parse import urlparse
from guide_tools import loot_odds

def finite(value,label,low=0,high=1e9):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError(f'{label} must be a finite number in {low}..{high}')
    return value

def reward_chain(stages,runs=100,target=.95,retry_wait_minutes=0):
    if not isinstance(stages,list) or not 1<=len(stages)<=12:raise ValueError('Provide 1..12 conditional stages')
    finite(retry_wait_minutes,'Retry wait')
    probability=1.0;cost=0.0
    for stage in stages:
        if not isinstance(stage,dict) or not isinstance(stage.get('label'),str) or not stage['label'].strip() or len(stage['label'])>200:raise ValueError('Each stage requires a label')
        parsed=urlparse(stage.get('source_url',''))
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Every stage needs its rate source URL without credentials')
        percent=finite(stage.get('conditional_percent'),'Conditional rate',high=100)
        minutes=finite(stage.get('minutes'),'Stage minutes')
        cost+=probability*minutes;probability*=percent/100
    if cost<=0:raise ValueError('Expected active time must be positive')
    if probability==0:expected=None
    else:expected=(cost+(1-probability)*retry_wait_minutes)/probability
    result=loot_odds(probability*100,runs,target)
    return {'stages':[{k:s[k] for k in ('label','conditional_percent','minutes','source_url')} for s in stages],
            'rate_verification':'Supplied sources are retained, but their claims are not independently verified by this calculator.',
            'conditional_success_probability':probability,'expected_active_minutes_per_attempt':cost,
            'retry_wait_minutes':retry_wait_minutes,'expected_minutes_to_first_success':expected,**result,
            'assumptions':['Each stage rate is conditional on reaching that stage, not an unrelated marginal probability.','Later stage time is spent only after earlier success; failure ends the attempt.','Complete attempts are independent with fixed rates. Retry wait follows a failed attempt; first attempt starts immediately.','Minutes and intervals are supplied estimates; no respawn timer or drop table is inferred. Expected time is not a guarantee.']}


def revisit_window(last_cleared,minimum_minutes,maximum_minutes):
    minimum_minutes=finite(minimum_minutes,'Minimum wait');maximum_minutes=finite(maximum_minutes,'Maximum wait')
    if maximum_minutes<minimum_minutes:raise ValueError('Maximum wait must be at least minimum wait')
    start=datetime.fromisoformat(last_cleared.replace('Z','+00:00'))
    if start.utcoffset() is None:raise ValueError('Timestamp needs a timezone offset, for example 2026-10-19T14:00:00-04:00')
    return {'last_cleared':start.isoformat(),'check_from':(start+timedelta(minutes=minimum_minutes)).isoformat(),
            'check_until':(start+timedelta(minutes=maximum_minutes)).isoformat(),
            'scope':'A check window from your supplied interval, not a verified respawn time. No reminder or background task was created.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('chain');c.add_argument('--input',required=True);c.add_argument('--runs',type=int,default=100);c.add_argument('--target',type=float,default=.95);c.add_argument('--retry-wait',type=float,default=0)
    w=sub.add_parser('revisit');w.add_argument('--last-cleared',required=True);w.add_argument('--minimum-minutes',required=True,type=float);w.add_argument('--maximum-minutes',required=True,type=float)
    args=vars(p.parse_args());command=args.pop('command')
    try:
        if command=='chain':
            from pathlib import Path
            path=Path(args.pop('input'))
            if path.stat().st_size>100000:raise ValueError('Input exceeds 100 KB')
            args['retry_wait_minutes']=args.pop('retry_wait');result=reward_chain(json.loads(path.read_text(encoding='utf-8'))['stages'],**args)
        else:result=revisit_window(**args)
        print(json.dumps(result,indent=2,allow_nan=False))
    except (ValueError,OSError,KeyError,TypeError,OverflowError) as error:p.exit(2,f'Farm planner failed: {error}\n')

if __name__=='__main__':main()
