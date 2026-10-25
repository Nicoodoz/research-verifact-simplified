"""Run the pre-frozen 12-case time bridge after complete main A."""
import os,sqlite3
import common097 as c
import run_a

def main():
    plan=c.read(c.OUT/'a_bridge_plan.json');assert c.sha(c.PRIVATE/'a_bridge_jobs.jsonl')==plan['jobs_sha256']
    jobs=c.lines(c.PRIVATE/'a_bridge_jobs.jsonl');assert len(jobs)==12
    main_ids={j['request_id'] for j in c.lines(c.PRIVATE/'a_execution_jobs_corrected.jsonl')}
    run_a.reconcile();con=run_a.db();done={r[0] for r in con.execute('SELECT rid FROM attempts WHERE status=200')};con.close()
    assert main_ids<=done,'main A incomplete; bridge not started'
    lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        for j in jobs:
            outcome=run_a.process(j)
            if outcome=='budget_stop':print('bridge budget stop',run_a.summary(),flush=True);return
            if outcome not in ('success','cached'):raise RuntimeError(f'bridge {j["id"]}: {outcome}')
        print('bridge complete',run_a.summary(),flush=True)
    finally:lock.unlink()
if __name__=='__main__':main()
