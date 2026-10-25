"""Audited tariff guard and cross-phase successful-B deduplication."""
import argparse
import common095 as c
import run095 as runner
import pricing095_v3
import state095

def remaining_baseline(jobs,success):
    bodies={(v['job']['id'],v['job']['body_sha256']) for v in success.values() if v['job']['arm']=='B'}
    return [j for j in jobs if (j['id'],j['body_sha256']) not in bodies]

def run(stage,workers):
    assert not (c.PRIVATE/'run.lock').exists(),'another runner is active'
    for p,hh in c.read(c.OUT/'runtime_v3_freeze.json')['sources'].items():assert c.sha(c.ROOT/p)==hh,p
    snapshot=c.OUT/'peak_ledger_before_time_reconciliation.jsonl'
    if not snapshot.exists():c.putl(snapshot,state095.attempts())
    runner.charge=pricing095_v3.charge
    if stage=='baseline':
        jobs=remaining_baseline(c.lines(c.PRIVATE/'baseline_jobs.jsonl'),state095.successful_jobs())
        n=1
        while (c.PRIVATE/f'baseline_resume{n}_jobs.jsonl').exists():n+=1
        stage=f'baseline_resume{n}';path=c.PRIVATE/(stage+'_jobs.jsonl');c.putl(path,jobs)
        c.put(c.OUT/(stage+'_freeze.json'),dict(utc=c.now(),jobs=len(jobs),jobs_path=path.relative_to(c.ROOT).as_posix(),jobs_sha256=c.sha(path),rule='Original frozen baseline order, omit any successful same-ID/same-body B across ALL095 phases, including invalid HTTP200; no correctness preference'))
    runner.run(stage,workers)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('--workers',type=int,default=8);a=p.parse_args();run(a.stage,a.workers)
