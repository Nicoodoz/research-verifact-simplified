"""Additional class-wise paired cluster intervals and full frozen-N coverage; no decision changes."""
from collections import Counter
import json
import numpy as np
import common101 as c
def interval(v):
 v=np.asarray(v);v=v[np.isfinite(v)]
 return dict(ci95=np.quantile(v,[.025,.975]).tolist() if len(v) else None,valid_bootstrap_draws=len(v))
def stats(cm):
 tp=np.diagonal(cm,axis1=-2,axis2=-1);gt=cm.sum(-1);pr=cm.sum(-2)
 div=lambda x,y:np.divide(x,y,out=np.full_like(x,np.nan,dtype=float),where=y!=0)
 return dict(precision=div(tp,pr),recall=div(tp,gt),f1=div(2*tp,gt+pr))
def main():
 allrows=c.lines(c.OUT/'predictions.jsonl');rows=[r for r in allrows if r['baseline_valid']]
 groups={name:[r for r in rows if rule(r)] for name,rule in [('natural',lambda r:r['panel']=='natural'),('pressure',lambda r:r['panel']=='pressure'),('additional200',lambda r:r['origin']=='additional200')]}
 result={}
 for name,rr in groups.items():
  sids=sorted({r['sid'] for r in rr});si={s:i for i,s in enumerate(sids)};arrays={a:np.zeros((len(sids),3,3),dtype=int) for a in ['verifact_ref']+list(c.REVIEW_ARMS)}
  for r in rr:
   for arm,arr in arrays.items():arr[si[r['sid']],c.LABELS.index(r['GT']),c.LABELS.index(r['predictions'][arm])]+=1
  draws=np.array([np.random.RandomState(seed).choice(len(sids),len(sids),replace=True) for seed in range(1000)])
  summaries={a:stats(arr[draws].sum(1)) for a,arr in arrays.items()};points={a:stats(arr.sum(0)) for a,arr in arrays.items()}
  result[name]={}
  for base,arm in [('verifact_ref','nsna_plain'),('verifact_ref','nsna_review'),('nsna_plain','nsna_review')]:
   z={}
   for label in c.LABELS[1:]:
    i=c.LABELS.index(label);z[label]={}
    for measure in ['precision','recall','f1']:
     v=summaries[arm][measure][:,i]-summaries[base][measure][:,i];point=points[arm][measure][i]-points[base][measure][i]
     z[label][measure]=dict(delta=float(point) if np.isfinite(point) else None,**interval(v))
   result[name][arm+'__vs__'+base]=z
 coverage={}
 for panel in ['natural','pressure']:
  rr=[r for r in allrows if r['panel']==panel];good=[r for r in rr if r['baseline_valid']]
  coverage[panel]=dict(frozen_N=len(rr),valid_N=len(good),missing_N=len(rr)-len(good),GT_full=dict(Counter(r['GT'] for r in rr)),known_correct_lower_bounds={a:sum(r['predictions'][a]==r['GT'] for r in rr)/len(rr) for a in ['verifact_ref']+list(c.REVIEW_ARMS)},S_set_SHA={a:c.digest(c.canonical(sorted(r['id'] for r in rr if r['predictions'][a]=='Supported'))) for a in ['verifact_ref']+list(c.REVIEW_ARMS)})
  assert len(set(coverage[panel]['S_set_SHA'].values()))==1
 c.put(c.OUT/'supplemental_statistics.json',dict(class_paired_intervals=result,coverage=coverage,iterations=1000,method='paired patient clusters, same seeds0..999; undefined class ratios omitted from that interval only; decisions untouched'))
 ll=['# 101类别变化与完整分母补充','只补充展示，不修改冻结判据、标签或主结果。']
 for name,pp in result.items():
  ll+=['\n## '+name,'|比较|类别|Δ召回百分点 [95%患者区间]|Δprecision百分点 [区间]|ΔF1 [区间]|','|---|---|---|---|---|']
  for pair,tt in pp.items():
   for label,z in tt.items():
    def display(k,scale):
     q=z[k];iv=q['ci95'];return f"{q['delta']*scale:+.2f} [{iv[0]*scale:+.2f},{iv[1]*scale:+.2f}]" if q['delta'] is not None and iv else '不适用'
    ll.append(f"|{pair}|{label}|{display('recall',100)}|{display('precision',100)}|{display('f1',1)}|")
 (c.OUT/'supplemental_statistics.md').write_bytes(('\n\n'.join(ll)+'\n').encode('utf-8'))
 print('Supplementary class intervals complete')
if __name__=='__main__':main()
