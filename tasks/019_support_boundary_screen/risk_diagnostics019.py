"""Supplementary paired risk intervals. Does not participate in parameter selection."""
from collections import defaultdict
import argparse, csv
import numpy as np
import common019 as c

RATE_KEYS=('S_recall','false_S_rate','S_precision','NS_recall','NA_recall')

def rates(counts):
    # rows are GT, columns are predictions; nominal labels S, NS, NA.
    x=np.asarray(counts,dtype=float)
    total=x.sum(axis=-1);pred=x.sum(axis=-2)
    divide=lambda a,b:np.divide(a,b,out=np.full(np.shape(a),np.nan),where=b>0)
    return np.stack([divide(x[...,0,0],total[...,0]),divide(x[...,1:,0].sum(axis=-1),total[...,1:].sum(axis=-1)),
        divide(x[...,0,0],pred[...,0]),divide(x[...,1,1],total[...,1]),divide(x[...,2,2],total[...,2])],axis=-1)

def matrices(rows,labels):
    ids=sorted({r['subject_id'] for r in rows});lookup={s:i for i,s in enumerate(ids)}
    labels_lookup={s:i for i,s in enumerate(c.LABELS)};counts=np.zeros((len(ids),3,3),dtype=int)
    for r,p in zip(rows,labels):counts[lookup[r['subject_id']],labels_lookup[r['human_gt']],labels_lookup[p]]+=1
    return counts

def intervals(draws):
    result={}
    for i,key in enumerate(RATE_KEYS):
        v=draws[:,i];valid=v[np.isfinite(v)]
        result[key]=dict(valid_draws=len(valid),total_draws=len(v),ci95=np.percentile(valid,[2.5,97.5]).tolist() if len(valid)>=950 else None,
            note='Undefined denominators reported explicitly; no CI when fewer than950/1000 draws defined')
    return result

def analyze(stage):
    folder=c.OUT/stage/'analysis_001';out=c.OUT/stage/'risk_diagnostics_001';out.mkdir(exist_ok=False)
    c.check_manifest(folder/'manifest.json')
    result={}
    for file in sorted(folder.glob('predictions_r*.csv')):
        with file.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        rep=file.stem.split('_')[-1]
        arms=[k for k in rows[0] if k not in ('proposition_id','subject_id','author_type','human_gt')]
        for author in ('llm','human','all'):
            rr=[r for r in rows if author=='all' or r['author_type']==author]
            mats={arm:matrices(rr,[r[arm] for r in rr]) for arm in arms}
            n=len(next(iter(mats.values())))
            draws=np.array([np.random.RandomState(i).choice(n,n,replace=True) for i in range(1000)])
            rate_draws={arm:rates(m[draws].sum(axis=1)) for arm,m in mats.items()}
            for arm,m in mats.items():
                value=rates(m.sum(axis=0))
                result[f'{rep}/{author}/{arm}']=dict(point={k:float(x) if np.isfinite(x) else None for k,x in zip(RATE_KEYS,value)},
                    bootstrap=intervals(rate_draws[arm]),difference_vs_B=intervals(rate_draws[arm]-rate_draws['B']),
                    difference_vs_U0=intervals(rate_draws[arm]-rate_draws['U0']))
    c.write_json(out/'rates_and_paired_intervals.json',result)
    c.write_json(out/'manifest.json',dict(created_utc=c.now(),scope='supplementary diagnostics only; no gate or parameter changes',
        sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [out/'rates_and_paired_intervals.json',c.TASK/'risk_diagnostics019.py']}))
    print('RISK_INTERVALS',len(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['selection','validation']);a=p.parse_args();analyze(a.stage)
