"""Select a small, reproducible analysis-only case set; never training data."""
from pathlib import Path
from collections import Counter
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as common


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions',type=Path,default=ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')
    p.add_argument('--out',type=Path,default=ROOT/'.local_models/120_full_pool_sft/resume369/case_review')
    a=p.parse_args()
    keys={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    inputs={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')}
    old={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    new={r['id']:r for r in common.rows(a.predictions)}
    groups={};selected=[];seen=set();patients=set()
    valid=sorted(i for i in new if new[i].get('valid') and old[i].get('valid'))
    for kind,limit in [('falseS_new',2),('falseS_avoided',1),('NS_rescued',1),('NS_harmed',1),
                       ('NA_rescued',1),('NA_harmed',2),('S_rescued',2),('S_harmed',1)]:
        eligible=[]
        for i in valid:
            gt,b,n=keys[i]['GT'],old[i]['verdict'],new[i]['verdict']
            if kind=='falseS_new':match=gt!='Supported' and b!='Supported' and n=='Supported'
            elif kind=='falseS_avoided':match=gt!='Supported' and b=='Supported' and n!='Supported'
            else:
                cl,change=kind.split('_');label={'S':'Supported','NS':'Not Supported','NA':'Not Addressed'}[cl]
                match=gt==label and ((b!=gt and n==gt) if change=='rescued' else (b==gt and n!=gt))
            if match:eligible.append(i)
        groups[kind]=len(eligible)
        for _ in range(limit):
            candidates=sorted((i for i in eligible if i not in seen),key=lambda i:(str(keys[i]['sid']) in patients,i))
            if not candidates:break
            i=candidates[0]
            seen.add(i);patients.add(str(keys[i]['sid']))
            selected.append(dict(id=i,selection_bucket=kind,GT=keys[i]['GT'],sid=str(keys[i]['sid']),
                author=keys[i]['author'],old_panel=keys[i].get('old_panel'),
                baseline107=old[i]['verdict'],candidate=new[i]['verdict'],
                claim=inputs[i]['claim'],reference=inputs[i]['reference'],
                analysis_only=True,never_add_to_training=True))
    a.out.mkdir(parents=True,exist_ok=True);common.putl(a.out/'cases_private.jsonl',selected)
    common.put(a.out/'selection.json',dict(N=len(selected),eligible_by_bucket=groups,
        algorithm='fixed bucket quotas, prefer a new patient, then lexicographic ID',
        representative_rate_not_estimated=True,training_use=False))
    print(common.canonical(dict(N=len(selected),buckets=groups)))


if __name__=='__main__':main()
