"""Frozen candidate stages; private text, public source fingerprints, exact B aliases."""
import argparse,statistics,json
from collections import Counter
import common095 as c
import method095 as m
import state095 as s
from prepare_baseline095 import make_job

def verify_freeze():
    for p,h in c.read(c.OUT/'experiment_freeze.json')['sources'].items():assert c.sha(c.ROOT/p)==h,p

def build_checks(pilot=False):
    verify_freeze();inputs={r['id']:r for r in c.lines(c.PRIVATE/'screen_inputs.jsonl')};success=s.success_index();jobs=c.lines(c.PRIVATE/'construct_jobs.jsonl');pilot_ids=c.read(c.OUT/'experiment_freeze.json')['pilot_ids'];records=[];checks=[]
    if pilot:jobs=[j for j in jobs if j['id'] in pilot_ids]
    for j in jobs:
        assert j['request_id'] in success,('unfinished constructor',j['id'])
        tr=s.receipt(success[j['request_id']]);v=m.parse_builder(tr,inputs[j['id']]);records.append(dict(id=j['id'],constructor_request_id=j['request_id'],**v))
        if v['valid']:checks.append(make_job(j['id'],'method','check',m.checker(inputs[j['id']],v)))
    tag='pilot_' if pilot else ''
    c.putl(c.PRIVATE/(tag+'constructed.jsonl'),records);c.putl(c.PRIVATE/('check_pilot_jobs.jsonl' if pilot else 'check_jobs.jsonl'),checks)
    c.put(c.OUT/(tag+'construction_status.json'),dict(N=len(records),program_valid=sum(r['valid'] for r in records),reasons=dict(Counter(r.get('error','valid') for r in records)),private_sha256=c.sha(c.PRIVATE/(tag+'constructed.jsonl'))))
    print('constructor',len(records),'source/program valid',len(checks),'status',dict(Counter(r.get('error','valid') for r in records)))

def collect(pilot=False):
    verify_freeze();tag='pilot_' if pilot else '';records=c.lines(c.PRIVATE/(tag+'constructed.jsonl'));success=s.success_index();jobs={j['id']:j for j in c.lines(c.PRIVATE/('check_pilot_jobs.jsonl' if pilot else 'check_jobs.jsonl'))};out=[];public=[]
    for v in records:
        check=dict(valid=False,issue='no_program_valid_candidate',checks={})
        if v['valid']:
            j=jobs[v['id']];assert j['request_id'] in success;check=m.parse_checker(s.receipt(success[j['request_id']]))
        operated=v['valid'] and check['valid'];out.append(dict(**v,checker=check,operated=operated))
        public_check=dict(valid=check['valid'],checks=check['checks'],issue_sha256=c.h(check.get('issue','')))
        p=dict(id=v['id'],constructor_request_id=v['constructor_request_id'],program_valid=v['valid'],operated=operated,program_error=v.get('error'),checker=public_check,check_request_id=jobs[v['id']]['request_id'] if v['id'] in jobs else None)
        if v['valid']:
            p.update(attribute=v['attribute'],edit_start=v['edit_start'],edit_end=v['edit_end'],old_span_sha256=c.h(v['old_span']),new_span_sha256=c.h(v['new_span']),alternative_sha256=c.h(v['alternative']),anchors=[dict(reference_id=a['reference_id'],reference_start=a['reference_start'],reference_end=a['reference_end'],quote_sha256=c.h(a['quote'])) for a in v['anchors']])
        public.append(p)
    c.putl(c.PRIVATE/(tag+'checked.jsonl'),out);c.putl(c.OUT/(tag+'construction_audit.jsonl'),public)
    print('checked',len(out),'operated',sum(v['operated'] for v in out))

def prepare_judge():
    verify_freeze();sample=c.lines(c.OUT/'screen_sample.jsonl');inputs={r['id']:r for r in c.lines(c.PRIVATE/'screen_inputs.jsonl')};vv={r['id']:r for r in c.lines(c.PRIVATE/'checked.jsonl')};success=s.successful_jobs();b_byid={}
    for rid,v in sorted(success.items(),key=lambda kv:(kv[1]['utc'],kv[0])):
        if v['job']['arm']=='B':b_byid.setdefault(v['job']['id'],(rid,v))
    operated=[r for r in sample if vv[r['id']]['operated']];counts=Counter(r['panel'] for r in operated)
    gate=len(operated)>=60 and len({r['sid'] for r in operated})>=10 and counts['natural']>=20 and counts['mechanism']>=20
    c.put(c.OUT/'operation_gate.json',dict(pass_gate=gate,N=len(sample),operated=len(operated),patients=len({r['sid'] for r in operated}),panels=dict(counts),rule='at least60,10patients,20 each panel; fixed before calls'))
    if not gate:print('STOP candidate Judge: insufficient deployable operation coverage; continue A/F');return
    template=c.read(c.PRIVATE/'judge_template.json');jobs=[];aliases=[]
    for r in sample:
        pid=r['id'];row=inputs[pid];v=vv[pid];body=m.judge(template,row)
        if pid in b_byid:
            rid,info=b_byid[pid];j=info['job'];assert j['body_sha256']==c.h(c.canonical(body));bj=j
        else:
            bj=make_job(pid,'method','B',body);jobs.append(bj)
        for arm in ['B','E','C']:
            if arm=='B' or not v['operated']:j=bj
            else:j=make_job(pid,'method',arm,m.judge(template,row,arm,v));jobs.append(j)
            aliases.append(dict(id=pid,arm=arm,operated=v['operated'],request_id=j['request_id'],body_sha256=j['body_sha256'],exact_B_alias=arm!='B' and not v['operated']))
    c.putl(c.PRIVATE/'screen_judge_jobs.jsonl',jobs);c.putl(c.OUT/'screen_aliases.jsonl',aliases)
    at=s.attempts();used=sum(x['charge_or_reserved_cny'] for x in at);method=sum(x['charge_or_reserved_cny'] for x in at if x['phase']=='method')
    amounts=[]
    for x in at:
        if x['phase']=='baseline' and x['http_status']==200 and x['usage']:amounts.append((x['usage']['prompt_tokens']*3+x['usage']['completion_tokens']*9)/1e6)
    mean=statistics.mean(amounts);estimate=len(jobs)*(mean+.006)
    assert method+estimate+3<=45 and used+estimate+3<=130,('complete paired queue estimate exceeds reserved plan',used,method,estimate)
    c.put(c.OUT/'screen_judge_freeze.json',dict(utc=c.now(),new_jobs=len(jobs),arms=dict(Counter(j['arm'] for j in jobs)),reuse_B=len(sample)-sum(j['arm']=='B' for j in jobs),current_task_conservative_cny=used,current_method_conservative_cny=method,estimated_remaining_busy_no_cache_cny=estimate,expected_recovery_margin_cny=3,mean_baseline_busy_no_cache=mean,sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.PRIVATE/'checked.jsonl',c.PRIVATE/'screen_judge_jobs.jsonl',c.OUT/'screen_aliases.jsonl',c.TASK/'workflow095.py']}))
    print('Judge jobs',len(jobs),'estimate',estimate,'already',used)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['checks','collect','judge','run']);p.add_argument('--pilot',action='store_true');p.add_argument('--stage');p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    if a.action=='checks':build_checks(a.pilot)
    elif a.action=='collect':collect(a.pilot)
    elif a.action=='judge':prepare_judge()
    else:
        verify_freeze()
        if a.stage=='screen_judge':
            for path,hh in c.read(c.OUT/'screen_judge_freeze.json')['sources'].items():assert c.sha(c.ROOT/path)==hh,path
        from run095_v3 import run
        run(a.stage,a.workers)
