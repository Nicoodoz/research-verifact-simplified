"""Process a distant, disjoint tail of frozen jobs while prefix runner progresses.

Only engineering scheduling; shared transactional ledger and first-success reuse.
Refuses a tail near any already dispatched prefix. No inputs/scale changes.
"""
import argparse
import common103 as c
import runtime103 as rt
from run_api103 import guarded
def main():
 p=argparse.ArgumentParser();p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True);p.add_argument('--workers',type=int,default=16);a=p.parse_args()
 frozen=c.read(c.OUT/'api_execution_freeze.json')
 for rel,h in frozen['files'].items():assert c.sha(c.ROOT/rel)==h
 jobs=c.lines(c.PRIVATE/'jobs_selected.jsonl');con=rt.db();seen={r[0] for r in con.execute('SELECT rid FROM attempts')};con.close()
 probes=set(c.read(c.OUT/'data_freeze.json')['usage_probe_ids'])
 indexes=[i for i,j in enumerate(jobs[:a.start]) if j['request_id'] in seen and j['request_id'] not in probes]
 assert not indexes or max(indexes)<a.start-256,'Prefix too close: do not overlap in-flight work'
 assert not any(j['request_id'] in seen and j['request_id'] not in probes for j in jobs[a.start:a.end]),'Tail already dispatched'
 c.put(c.OUT/f'scheduling_{a.start}_{a.end}.json',dict(utc=c.utc(),start=a.start,end=a.end,workers=a.workers,largest_dispatched_prefix=max(indexes,default=-1),shared_budget=True,request_bodies_unchanged=True))
 # Primary already owns recovery; do not reconcile its in-flight receipt/commit window.
 rt.reconcile=lambda:None
 rt.process=guarded;rt.run(jobs[a.start:a.end],a.workers)
if __name__=='__main__':main()
