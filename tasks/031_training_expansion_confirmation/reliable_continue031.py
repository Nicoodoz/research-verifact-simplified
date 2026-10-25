"""Resume with task-local robust progress I/O, preserving all unknown reservations."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import traceback
import common031 as c
import safe_io031
def main():
    safe_io031.register();safe_io031.install()
    for p,h in c.read(c.OUT/'analysis_contract_001.json')['sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Scientific analysis contract changed')
    import api031 as a, resume031
    from fit_predict031 import build,fit_predict
    import analyze031,costs031
    for stage in ('score','auxiliary'):
        attempts,term,_=a.state();used=sum(r['charge_cny'] for r in attempts);cost=c.read(c.OUT/'freeze_001/budget_002.json')['mean_role_cost_cny'];materials=c.lines(c.OUT/'judge_inputs_001/materials.jsonl')
        if stage=='score':
            remaining=sum('031_score_'+r['proposition_id'] not in term for r in materials);forecast=used+remaining*cost['deepseek']+len(materials)*.25*sum(cost[x] for x in ('qwen','repeat','trace'))+3;c.require(forecast<=80,'Whole remaining forecast exceeds80')
        print(c.now(),'continuing',stage,'occupied',used,flush=True);resume031.main(stage)
    if not (c.OUT/'features_001').exists():build()
    if not (c.OUT/'inference_001').exists():fit_predict()
    if not (c.OUT/'analysis_001').exists():analyze031.run('analysis_001')
    if not (c.OUT/'costs_001').exists():costs031.run('costs_001')
    c.put(c.OUT/'execution_complete.json',dict(created_utc=c.now(),all_executable_phases_complete=True,report_and_selfcheck_pending=True));print('031 fixed pipeline completed; report/selfcheck next',flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as e:
        c.put(c.OUT/'reliable_workflow_error.json',dict(created_utc=c.now(),exception=type(e).__name__,message=str(e),traceback=traceback.format_exc()));raise
