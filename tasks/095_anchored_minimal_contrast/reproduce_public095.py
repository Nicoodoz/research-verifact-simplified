"""Recompute public point metrics and Frozen PriorG without clinical text or API."""
import math
import common095 as c
from metrics095 import score,LABELS

def frozen_prior(scores):
    ref=[1108/1378,100/1378,170/1378];cal=[48/143,47/143,48/143];bias=[math.log(r/q) for r,q in zip(ref,cal)];bias=[x-bias[2] for x in bias]
    v=[math.log(max(float(scores[k])/100,1e-6))+bias[i]+(.1342909508820116 if i==0 else 0) for i,k in enumerate(LABELS)]
    return LABELS[max(range(3),key=lambda i:v[i])]

def main():
    rows=c.lines(c.OUT/'unified_9065_predictions.jsonl');reported=c.read(c.OUT/'baseline_metrics.json');core=[r for r in rows if r['B_core_valid']];raw=[r for r in rows if r['B_raw_valid']]
    scopes={'full_9065_existing':rows,'common_core':core,'common_raw':raw}
    for scope,rr in scopes.items():
        tt=score(rr,list(reported[scope]))
        for model,z in tt.items():
            expected=reported[scope][model]
            for field in ['PA','MCC','AC1','Macro_F1']:assert abs(z[field]-expected[field])<1e-12,(scope,model,field)
            for field in ['correct','false_S','true_non_S','confusion_matrix']:assert z[field]==expected[field],(scope,model,field)
    for r in core:assert frozen_prior(r['B']['parsed']['scores'])==r['predictions']['B_PriorG'],r['id']
    assert len(rows)==len({r['id'] for r in rows})==9065
    print('PUBLIC_REPRO_PASS',dict(universe=len(rows),core=len(core),raw=len(raw),no_API=True,no_clinical_text=True))
if __name__=='__main__':main()
