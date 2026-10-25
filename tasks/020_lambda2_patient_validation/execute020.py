"""Run the frozen020 phases, stopping on any unresolved service or budget issue."""
import common020 as c
from run020 import run
from build020 import candidates,judge
from io020 import load_phase

def execute():
    for stage in ('new10_embedding','new10_rerank','new10_judge'):
        if stage=='new10_rerank' and not c.job_preparation(stage).exists():candidates('new10')
        if stage=='new10_judge' and not c.job_preparation(stage).exists():judge('new10')
        if stage=='new10_judge':
            summary=c.read(c.job_preparation(stage)/'summary.json');ledger=c.read(c.OUT/'live_ledger.json')
            received=sum(p['status']=='received' for p in ledger['phases'].get(stage,{}).get('jobs',{}).values())
            projected=ledger['used_or_reserved_cny']+summary['estimated_peak_cny']*(1-received/summary['unique_calls'])+8
            c.require(projected<=80,'Full remaining Judge forecast exceeds80')
            print('JUDGE_FORECAST',round(projected,4),'CNY total incl reserve',flush=True)
        result=run(stage,workers=4 if stage!='new10_judge' else 6)
        if not result['complete']:
            print('EXECUTION_PAUSED',c.canonical(result),flush=True);return
        values,_=load_phase(stage)
        if any(v['status']!='received' for v in values.values()):
            print('MEASUREMENT_BLOCKED; HTTP200 preserved, not reissued',flush=True);return
    c.write_json(c.OUT/'inference_complete.json',dict(created_utc=c.now(),all_stages_complete=True,all_paid_calls_stopped=True,performance_inspected=False))
    print('ALL_020_INFERENCE_COMPLETE; no performance inspected yet',flush=True)

if __name__=='__main__':
    import contextlib
    with (c.OUT/'execution_001.log').open('a',encoding='utf-8') as log:
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):execute()
