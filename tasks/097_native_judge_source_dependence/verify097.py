"""Independent-formula replay by the executor; not an independent audit."""
import csv,json,sqlite3
from decimal import Decimal
from pathlib import Path
from sklearn.metrics import matthews_corrcoef,f1_score,confusion_matrix
import common097 as c

def main():
    a=c.read(c.OUT/'a_analysis.json')
    with (c.OUT/'a_same_id.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==160
    models=['Original','C48_B_raw','published_B','C48_native','published_native','C48_B_PriorG']
    common=[r for r in rows if all(r[m] in c.LABELS for m in models)]
    assert len(common)==a['raw_common_N']==158
    y=[r['GT'] for r in common];tests={}
    for m in models:
        pred=[r[m] for r in common];expected=a['raw_common_metrics'][m]
        cm=confusion_matrix(y,pred,labels=c.LABELS).tolist()
        ncorrect=sum(g==p for g,p in zip(y,pred));falseS=sum(g!='Supported' and p=='Supported' for g,p in zip(y,pred))
        assert ncorrect==expected['correct'] and cm==expected['confusion_matrix'] and falseS==expected['false_S']
        assert abs(ncorrect/len(common)-expected['PA'])<1e-12
        assert abs(matthews_corrcoef(y,pred)-expected['MCC'])<1e-12
        assert abs(f1_score(y,pred,labels=c.LABELS,average='macro',zero_division=0)-expected['Macro_F1'])<1e-12
        tests[m]=dict(correct=ncorrect,MCC=expected['MCC'],false_S=falseS,confusion_recomputed=True)
    money=Decimal('0');attempts=0
    for p in (c.PRIVATE/'attempts').glob('*/request.json'):
        req=c.read(p);tr=c.read(p.parent/'receipt.json')['transport'];assert tr['http_status']==200
        raw=json.loads(tr['body_text']);u=raw['usage'];cache=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        charge=(Decimal(u['prompt_tokens']-cache)*3+Decimal(cache)*Decimal('0.3')+Decimal(u['completion_tokens'])*9)/1000000
        money+=charge;attempts+=1
    assert attempts==492 and abs(float(money)-a['new_busy_price_or_reserved_cny'])<1e-9
    c.write_json(c.OUT/'verification.json',dict(status='PASS',scope='executor independent-formula recomputation; not external independent audit',N=len(rows),common_N=len(common),models=tests,attempts=attempts,busy_price_cny=str(money),official_evaluator_replay_in_a_analysis=True,patient_cluster_bootstrap_repeats=1000,independent_audit=False))
    print('VERIFY_PASS',len(common),'rows',attempts,'attempts',money)
if __name__=='__main__':main()
