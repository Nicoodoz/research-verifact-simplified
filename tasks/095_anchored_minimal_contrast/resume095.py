"""Explicit shared-budget recovery; completed B is a no-op, never start another task."""
import argparse,subprocess,sys
import common095 as c
import state095
from run095_v3 import remaining_baseline

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','verify-public','resume-B']);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.action=='verify-public':
        from reproduce_public095 import main
        main()
    elif a.action=='status':
        from run095 import summary
        print('Ledger',summary());print('Run lock',(c.PRIVATE/'run.lock').exists());print('Construction decision',c.read(c.OUT/'construction_stop.json')['decision'])
        jobs=remaining_baseline(c.lines(c.PRIVATE/'baseline_jobs.jsonl'),state095.successful_jobs());print('B remaining successful responses',len(jobs))
    else:
        jobs=remaining_baseline(c.lines(c.PRIVATE/'baseline_jobs.jsonl'),state095.successful_jobs())
        if not jobs:print('B_COMPLETE_NO_CALLS: all originally missing B IDs have successful matching responses; invalid answers are retained, not retried.')
        elif not a.execute:print('DRY_RUN_ONLY: missing B',len(jobs),'; use --execute only to resume this already authorized095 within its SAME ledger/cap.')
        else:
            assert not (c.PRIVATE/'run.lock').exists(),'095 executor active or stale lock requires process check'
            subprocess.run([sys.executable,str(c.TASK/'run_remaining_A095.py')],cwd=c.ROOT,check=True)
