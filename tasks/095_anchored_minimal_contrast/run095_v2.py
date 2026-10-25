"""Versioned time-tariff adapter around the unchanged atomic runner."""
import argparse
import common095 as c
import run095 as runner
import pricing095
import state095

def run(stage,workers):
    assert not (c.PRIVATE/'run.lock').exists(),'another runner is active; do not hot-change accounting'
    for p,hh in c.read(c.OUT/'pricing_v2_freeze.json')['sources'].items():assert c.sha(c.ROOT/p)==hh,p
    snapshot=c.OUT/'peak_ledger_before_time_reconciliation.jsonl'
    if not snapshot.exists():c.putl(snapshot,state095.attempts())
    runner.charge=pricing095.charge
    runner.run(stage,workers)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('--workers',type=int,default=8);a=p.parse_args();run(a.stage,a.workers)
