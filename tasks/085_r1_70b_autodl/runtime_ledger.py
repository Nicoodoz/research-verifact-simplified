"""GPU rental time is not a token-API budget. User records instance lifetime and price."""
import argparse,time,datetime
from common import *
def timestamp(s):
    d=datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Use ISO8601 with timezone for rental timestamps')
    return d
def event(kind,at,price=None,note=''):
    timestamp(at)
    if price is not None and price<=0:raise ValueError('Hourly price must be actual positive CNY/hour')
    row=dict(kind=kind,at=at,hourly_price_cny=price,note=note,recorded_utc=now())
    put(OUT/'gpu_runtime_events'/f'{time.time_ns()}.json',row);return row
def summarize():
    rows=sorted([read(p) for p in (OUT/'gpu_runtime_events').glob('*.json')],key=lambda r:timestamp(r['at']))
    intervals=[]
    for kind in ('instance','service'):
        start=None;price=None
        for r in rows:
            if r['kind']==kind+'_start':
                if start:raise ValueError('Overlapping rental intervals')
                start=r['at'];price=r['hourly_price_cny']
            elif r['kind']==kind+'_end':
                if not start:raise ValueError('End without recorded start')
                hours=(timestamp(r['at'])-timestamp(start)).total_seconds()/3600
                intervals.append(dict(kind=kind,start=start,end=r['at'],hours=hours,hourly_price_cny=price,estimate_cny=hours*price if price is not None else None));start=None
        if start:
            hours=(timestamp(now())-timestamp(start)).total_seconds()/3600
            intervals.append(dict(kind=kind,start=start,end=None,as_of=now(),hours=hours,hourly_price_cny=price,estimate_cny=hours*price if price is not None else None))
    runs=[read(p) for p in (OUT/'formal_runs').glob('*/runtime.json')]
    return dict(events=rows,intervals=intervals,formal_runs=runs,instance_time_known=any(r['kind']=='instance' for r in intervals),
        gpu_cost_cny=None if not any(r['kind']=='instance' for r in intervals) or any(r['kind']=='instance' and r['estimate_cny'] is None for r in intervals) else sum(r['estimate_cny'] for r in intervals if r['kind']=='instance'),
        warning='Instance rental includes preparation/startup/idle. Service/formal intervals overlap instance time: do not sum them. No assumed20CNY GPU cap. Unknown price/time stays null, not zero.',
        project_paid_API_calls=0,project_paid_API_cny=0)
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('event','summary'));p.add_argument('--kind',choices=('instance_start','instance_end','service_start','service_end'));p.add_argument('--at');p.add_argument('--hourly-price',type=float);p.add_argument('--note',default='')
    a=p.parse_args()
    if a.action=='event':
        if not a.kind or not a.at:raise ValueError('kind and actual at timestamp required')
        print(canonical(event(a.kind,a.at,a.hourly_price,a.note)))
    else:print(canonical(summarize()))
if __name__=='__main__':main()
