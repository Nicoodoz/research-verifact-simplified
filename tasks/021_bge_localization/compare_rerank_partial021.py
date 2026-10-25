"""Compare completed local reranker rows to frozen API reranker outputs; no GT/Judge labels."""
import argparse, json, math
from pathlib import Path
import numpy as np
import common021 as c

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scores',required=True); a=ap.parse_args()
    base={x['proposition_id']:x for x in c.jsonlines(c.BASE20/'inputs.jsonl')}
    rows=c.jsonlines(c.OUT/a.scores)
    spears=[]; ovs=[]; api_all=[]; sig_all=[]; raw_all=[]; exact_full=0; exact_top16=0
    for row in rows:
        pid=row['proposition_id']; api={k:float(v) for k,v in base[pid]['scores'].items()}; loc=row['scores']
        ids=list(api)
        ao=sorted(ids,key=lambda x:(-api[x],x)); lo=sorted(ids,key=lambda x:(-float(loc[x]),x))
        pa={x:i for i,x in enumerate(ao)}; pl={x:i for i,x in enumerate(lo)}
        spears.append(float(np.corrcoef([pa[x] for x in ids],[pl[x] for x in ids])[0,1]))
        ovs.append(len(set(ao[:16])&set(lo[:16]))/min(16,len(ids)))
        exact_full+=ao==lo; exact_top16+=ao[:16]==lo[:16]
        for x in ids:
            api_all.append(api[x]); raw_all.append(float(loc[x])); sig_all.append(1/(1+math.exp(-float(loc[x]))))
    out={
        'claims':len(rows),'pairs':len(api_all),
        'full_order_exact':exact_full,'top16_order_exact':exact_top16,
        'spearman_mean':float(np.mean(spears)),'spearman_min':float(np.min(spears)),
        'top16_set_overlap_mean':float(np.mean(ovs)),
        'api_vs_raw_pearson':float(np.corrcoef(api_all,raw_all)[0,1]),
        'api_vs_sigmoid_pearson':float(np.corrcoef(api_all,sig_all)[0,1]),
        'api_vs_sigmoid_mae':float(np.mean(np.abs(np.asarray(api_all)-np.asarray(sig_all)))),
    }
    print(json.dumps(out,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
