"""Thin wrapper around frozen016 retrieval transport with020 task-wide budget checks."""
from pathlib import Path
import sys
import common020 as c
sys.path.insert(0,str(c.ROOT/'tasks/016_disagreement_triggered_review_validation'))
import run016 as r, budget016
r.c.OUT=c.OUT
r.c.patient_ids=lambda phase:c.patient_ids()
def check_before_send(jobfile):
    auth=c.read(c.OUT/'authority_001.json')
    ledger=c.read(c.OUT/'live/ledger.json') if (c.OUT/'live/ledger.json').exists() else {}
    c.require(auth['approved'] and auth['task_cap_cny']==20 and auth['whole_task_cap_cny']==80,'020 authority invalid')
    c.require(ledger.get('used_or_reserved_cny',0)<=auth['projected_total_cny'],'Unexpected retrieval spend')
budget016.check_before_send=check_before_send
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('jobs',type=Path);p.add_argument('--workers',type=int,default=4);p.add_argument('--limit',type=int)
    a=p.parse_args();r.execute(a.jobs,a.workers,a.limit)
