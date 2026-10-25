"""Run existing core scheduler with identical transport plus error-type diagnostics."""
import argparse
import run024_core as runner
from transport024 import DiagnosticClient
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);p.add_argument('--retry-unanswered',action='store_true');p.add_argument('--max-new',type=int);a=p.parse_args()
    runner.c.AliyunClient=DiagnosticClient
    if a.max_new:
        original=runner.c.verify_inputs
        def limited():
            jobs=original();attempts,_=runner.c.load_attempts(jobs);seen={x['request_id'] for x in attempts}
            fresh=[j['request_id'] for j in jobs if j['request_id'] not in seen][:a.max_new]
            return [j for j in jobs if j['request_id'] in seen or j['request_id'] in fresh]
        runner.c.verify_inputs=limited
    runner.run(a.workers,a.retry_unanswered)
