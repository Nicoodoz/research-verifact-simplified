"""Targeted CPU checks of the new schedule and package, no 9B load."""
from pathlib import Path
from collections import Counter
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
def main():
 p=R/'.local_models/114_matched_refresh';rows=c.rows(p/'train.jsonl');plan=c.read(p/'plan.json');manifest=c.rows(R/'outputs/114_matched_refresh/second_pass_manifest.jsonl');old=c.rows(R/'.local_models/107_support_aux/gpu_bundle_5090_run/data/train/label_only.jsonl')
 assert rows[:196]==old and len(rows)==392 and len({r['id'] for r in rows})==351
 assert Counter(i for step in plan for i in step['indices'])==Counter(range(392))
 assert [s['divisor'] for s in plan]==[8]*24+[4]+[8]*24+[4]
 for a,b in zip(plan[:25],plan[25:]):
  assert [(rows[i]['sid'],rows[i]['GT'],rows[i]['author']) for i in a['indices']]==[(rows[i]['sid'],rows[i]['GT'],rows[i]['author']) for i in b['indices']]
  # An all-one micro-loss still contributes one at either short tail.
  assert sum(1/a['divisor'] for i in a['indices'])==1 and sum(1/b['divisor'] for i in b['indices'])==1
 assert sum(r['replaced'] for r in manifest)==155 and all(r['GT']==rows[r['slot']+196]['GT'] for r in manifest)
 ev=c.rows(p/'bundle/data/eval_inputs.jsonl');batches=c.read(p/'bundle/data/eval_batches.json')['batches']
 assert len(ev)==500 and Counter(r['id'] for r in ev)==Counter(i for b in batches for i in b['ids'])
 assert all(set(r)=={'id','claim','reference'} for r in ev)
 c.put(R/'outputs/114_matched_refresh/schedule_selfcheck.json',dict(PASS=True,exact_first196=True,second_unique155=True,per_position_patient_GT_author_match=True,all392_presentations_exactly_once_in_schedule=True,tail4_normalization=True,eval500_full_no_GT=True,no_model_loaded=True))
 print('PASS: 392 presentations, 50 steps, exact first pass, matched second pass, complete GT-free500')
if __name__=='__main__':main()
