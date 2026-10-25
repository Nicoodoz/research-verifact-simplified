"""Bounded-batch driver; every batch uses frozen scope and re-estimates whole016."""
import argparse
import complete016 as run
from completion_io016 import OUT
import common016 as c

def main(phase):
    for _ in range(20):
        run.send(phase,48)
        ledger=c.read(OUT/'live/ledger.json');states=list(ledger['phases'][phase]['jobs'].values())
        if all(p['status']=='received' for p in states):return
        c.require(not ledger.get('bound_violation') and not any(p['status'] in ('retry','failed','in_flight') for p in states), 'Batch halted for service or budget review')
    raise ValueError('Bounded driver exhausted; inspect checkpoint')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('base','review'));main(p.parse_args().phase)
