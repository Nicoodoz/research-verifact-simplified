"""Use existing native margins for review; preserve every original verdict.

CLI: python review159.py input.jsonl output.jsonl --fraction .10
Records: id, verdict, native_margin; optional patient_id and reason_status.
No model, GT, fitting, or probability calibration is used by the policy.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
LABELS=('Supported','Not Supported','Not Addressed')

def mark_for_review(records,*,fraction=.10,mode='global_margin'):
    if not 0<=fraction<=1:raise ValueError('fraction must be in [0,1]')
    if mode not in ('global_margin','patient_rank'):raise ValueError('Unknown review mode')
    records=list(records);ids=[r['id'] for r in records]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate input ID')
    if any(not isinstance(i,str) or not i for i in ids):raise ValueError('Nonempty string IDs required')
    if any(r['verdict'] not in LABELS for r in records):raise ValueError('Unknown verdict; do not silently map')
    pool=[r for r in records if r['verdict']=='Supported'];known=[];missing=set()
    for r in pool:
        v=r.get('native_margin')
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):missing.add(r['id'])
        else:known.append(r)
    scores={r['id']:float(r['native_margin']) for r in known}
    if mode=='patient_rank':
        if any(not isinstance(r.get('patient_id'),str) or not r['patient_id'] for r in known):raise ValueError('patient_rank requires nonempty patient_id for every scored S')
        groups=defaultdict(list)
        for r in known:groups[r['patient_id']].append(r)
        for group in groups.values():
            margins=[r['native_margin'] for r in group]
            for r in group:
                v=r['native_margin'];scores[r['id']]=(sum(m<v for m in margins)+.5*sum(m==v for m in margins))/len(margins)
    target=math.floor(len(records)*fraction+1e-12)
    selected=missing|set(sorted(scores,key=lambda i:(scores[i],i))[:max(0,target-len(missing))])
    output=[]
    for r in records:
        result=dict(r);i=r['id'];result.update(review_required=i in selected,review_reason='missing_native_margin' if i in missing else 'low_native_margin' if i in selected else None,review_score=scores.get(i),review_score_kind=mode)
        assert result['verdict']==r['verdict']
        output.append(result)
    n=len(records);summary=dict(N=n,predicted_S_N=len(pool),mode=mode,requested_fraction=fraction,requested_review_N=target,actual_review_N=len(selected),missing_S_margin_N=len(missing),automatic_N=n-len(selected),automatic_coverage=(n-len(selected))/n if n else None,requested_count_exceeded=len(selected)>target,label_changes=0,corrected_cases=0,guarantee=None)
    return output,summary

def selfcheck():
    records=[dict(id='b',verdict='Supported',native_margin=1.,patient_id='p'),dict(id='a',verdict='Supported',native_margin=1.,patient_id='p'),dict(id='c',verdict='Supported',native_margin=None,patient_id='q'),dict(id='d',verdict='Not Addressed',reason_status='unable')]
    out,s=mark_for_review(records,fraction=.5);assert s['actual_review_N']==2 and {r['id'] for r in out if r['review_required']}=={'a','c'}
    assert records[0].keys()=={'id','verdict','native_margin','patient_id'}
    out,s=mark_for_review(records,fraction=0);assert s['actual_review_N']==1 and s['requested_count_exceeded']
    for mode in ('global_margin','patient_rank'):
        out,s=mark_for_review(records,fraction=1,mode=mode);assert s['actual_review_N']==3 and [r['verdict'] for r in out]==[r['verdict'] for r in records]
    try:mark_for_review(records+[records[0]])
    except ValueError:pass
    else:raise AssertionError('Duplicate IDs must fail')
    print('Synthetic interface checks passed; no classification-efficacy claim.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',nargs='?');ap.add_argument('output',nargs='?');ap.add_argument('--fraction',type=float,default=.10);ap.add_argument('--mode',choices=['global_margin','patient_rank'],default='global_margin');ap.add_argument('--selfcheck',action='store_true');a=ap.parse_args()
    if a.selfcheck:selfcheck();return
    if not a.input or not a.output:ap.error('input and output JSONL required')
    if Path(a.input).resolve()==Path(a.output).resolve():raise ValueError('Use a separate output to preserve original predictions')
    records=[json.loads(s) for s in Path(a.input).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    output,summary=mark_for_review(records,fraction=a.fraction,mode=a.mode)
    target=Path(a.output)
    if target.exists():raise FileExistsError('Preserve prior output; choose a new path')
    summary_path=target.with_name(target.name+'.summary.json')
    if summary_path.exists():raise FileExistsError('Preserve existing summary')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in output),encoding='utf-8')
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))

if __name__=='__main__':main()
