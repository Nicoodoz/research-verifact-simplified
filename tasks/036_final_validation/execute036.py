"""Resumable GT-blind execution. Stage prerequisites, raw receipts and150CNY cap."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,threading,time,traceback
import common036 as c
import api036 as a
import retrieval036 as r
def pace():
    original=a.native.HttpClient.send;lock=threading.Lock();clock=[0.];spacing=[2.]
    def send(self,account,job):
        with lock:
            delay=max(0.,clock[0]-time.monotonic())
            if delay:time.sleep(delay)
            clock[0]=time.monotonic()+spacing[0]
        result=original(self,account,job)
        if result.get('http_status')==429:
            with lock:spacing[0]=min(8.,spacing[0]*2);clock[0]=max(clock[0],time.monotonic()+30)
        return result
    a.native.HttpClient.send=send
def auxiliary_jobs():
    out=c.OUT/'candidate_freeze_001'
    if out.exists():return c.lines(out/'jobs.jsonl')
    mats={x['proposition_id']:x for x in c.lines(c.OUT/'judge_inputs_001/materials.jsonl')};_,terminal,_=a.state();ledger=[];jobs=[]
    for job in c.lines(c.OUT/'judge_inputs_001/jobs.jsonl'):
        if job['role']!='score':continue
        pid=job['proposition_id'];round_name=job['round'];p=terminal.get(job['request_id'],{}).get('parsed',dict(status='missing'));candidate=False;u0=u2=None
        if p['status'] in a.api.VALID:
            z=c.base.old.logs(p['scores']);u0=int(c.base.old.decode(z,0));u2=int(c.base.old.decode(z,2));candidate=u0!=0 and u2==0
        ledger.append(dict(round=round_name,proposition_id=pid,subject_id=mats[pid]['subject_id'],score_status=p['status'],u0=u0,u2=u2,candidate=candidate))
        if candidate:
            mat=mats[pid];jobs.append(dict(request_id='036_'+round_name+'_peer_'+pid,round=round_name,proposition_id=pid,kind='chat',role='peer',body=a.body(mat['text'],mat['reference'],'peer')))
    jobs.sort(key=lambda j:c.digest(['036_peer_order',j['request_id']]));r.seal(out,jobs);c.jsonl(out/'candidates.jsonl',ledger);c.put(out/'summary.json',dict(created_utc=c.now(),candidates=len(jobs),score_invalid=sum(x['u0'] is None for x in ledger),GT_read=False));return jobs
def verify_freeze():
    f=c.OUT/'final_freeze_001';m=c.read(f/'manifest.json')
    for name,h in m['files'].items():assert c.sha(f/name)==h,'Frozen final parameters changed'
    assert c.sha(c.TASK/'protocol.md')==m['protocol_sha256']
    for name,h in c.read(c.OUT/'execution_freeze_001.json')['sha256'].items():assert c.sha(c.ROOT/name)==h,'Execution binding changed: '+name
def run(stage):
    verify_freeze()
    if stage=='embedding':jobs=c.lines(c.OUT/'materials_001/embedding_jobs.jsonl');workers=4
    elif stage=='rerank':jobs=r.candidates();workers=4
    elif stage=='judge':jobs=r.score_jobs();workers=12
    else:jobs=auxiliary_jobs();workers=12
    at,terminal,_=a.state();used=sum(x['charge_cny'] for x in at);todo=[j for j in jobs if j['request_id'] not in terminal]
    means=c.read(c.OUT/'final_freeze_001/budget.json')['historical_mean_role_cny'];forecast=used+sum(a.bound(j) if j['kind']!='chat' else means[j['role']] for j in todo)
    if stage=='judge':forecast+=sum(j['role']=='score' for j in todo)*.25*means['peer']
    assert forecast+3<=c.CAP,'Stage forecast over150'
    print(stage,'pending',len(todo),'used',used,'stage forecast+reserve',forecast+3,flush=True)
    a.run(jobs,stage,workers)
    at,terminal,_=a.state();counts={}
    for x in at:counts[x['request_id']]=counts.get(x['request_id'],0)+1
    assert all(j['request_id'] in terminal or counts.get(j['request_id'],0)>=3 for j in jobs),'Stage unfinished'
    if stage in ('embedding','rerank'):assert all(terminal.get(j['request_id'],{}).get('parsed',{}).get('status')=='success' for j in jobs),'Core retrieval incomplete'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['embedding','rerank','judge','peer','all']);args=p.parse_args();pace()
    try:
        for stage in (['embedding','rerank','judge','peer'] if args.stage=='all' else [args.stage]):run(stage)
        c.put(c.OUT/'CALLS_STATUS.json',dict(status='completed_selected_stages',stage=args.stage,updated_utc=c.now(),evaluation_started=False))
    except BaseException as exc:
        c.put(c.OUT/('error_'+str(time.time_ns())+'.json'),dict(created_utc=c.now(),type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()));raise
