"""Source/replay checks plus independent arithmetic of confusion-derived metrics."""
import math,subprocess
from collections import Counter
from common090 import *
from analyze090 import parse_arm
from normalize090 import *
import api090 as api
def independent_metric(rows,arm,method):
    cm=[[0]*3 for _ in range(3)]
    for x in rows:cm[LABELS.index(x['GT'])][LABELS.index(x['labels'][arm][method])]+=1
    n=len(rows);truth=[sum(v) for v in cm];pred=[sum(cm[i][j] for i in range(3)) for j in range(3)];correct=sum(cm[i][i] for i in range(3));pa=correct/n
    den=(n*n-sum(x*x for x in truth))*(n*n-sum(x*x for x in pred))
    mcc=(correct*n-sum(a*b for a,b in zip(truth,pred)))/math.sqrt(den) if den>0 else 0.
    f1=sum(2*cm[i][i]/(truth[i]+pred[i]) if truth[i]+pred[i] else 0 for i in range(3))/3
    pooled=[(truth[i]+pred[i])/(2*n) for i in range(3)];pe=sum(p*(1-p) for p in pooled)/2;ac1=(pa-pe)/(1-pe)
    return dict(MCC=mcc,PA=pa,Macro_F1=f1,AC1=ac1,correct=correct,confusion_matrix=cm,false_S=cm[1][0]+cm[2][0])
def main():
    checks=0
    def check(v,msg):
        nonlocal checks
        assert v,msg;checks+=1
    jobs=api.validate_main();attempts,success,counts=api.state();check(all(j['request_id'] in success for j in jobs),'complete')
    check(max(counts.values())<=3,'finite retry');check(sum(x['cost_or_unknown_cny'] for x in attempts)<=40,'cap')
    check(sum(x['cost_or_unknown_cny'] for x in attempts if x['phase']!='main')<=4,'construction cap')
    for name in ('constructor_freeze.json','checker_tests_freeze.json'):
        f=read(OUT/name)
        for rel,d in f.get('source_sha256',{}).items():check(sha(ROOT/rel)==d,rel)
    for rel,d in read(OUT/'final/source_repair_freeze.json')['sources'].items():check(sha(ROOT/rel)==d,rel)
    for folder in (OUT,OUT/'final'):
        f=read(folder/'demonstration_freeze.json')
        for rel,d in f['files'].items():check(sha(folder/rel)==d,rel)
    examples=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');demos=read(OUT/'final/demonstrations.json');records=read(OUT/'final/construction_summary.json');srcs=read(OUT/'source_units.json')
    for arm in ('F4','P90','Q90'):
        for i,(old,new) in enumerate(zip(examples,demos[arm])):
            check({k:v for k,v in old.items() if k!='reference'}=={k:v for k,v in new.items() if k!='reference'},'demo unchanged')
            src=srcs[old['proposition_id']];sel=all_ids(src) if arm=='F4' else records[i][arm]['selected_ids']
            check(source_check(old['reference'],src,sel,new['reference']),'source exact')
    systems=read(OUT/'final/templates.json')['systems'];oldsystems=read(ROOT/'outputs/087_f4_evidence_intervention/templates.json')['systems']
    for a in ('B','F4'):check(systems[a]==oldsystems[a],'original system')
    rows=lines(OUT/'predictions.jsonl');sample=lines(OUT/'sample_blind.jsonl');pm={x['id']:x for x in rows};sm={x['id']:x for x in sample};check(set(pm)==set(sm),'cohort')
    check(len(sm)==len(sample),'disjoint panels')
    audit=read(PUB/'sampling_audit.json');check(Counter(x['sid'] for x in sample if x['panel']=='natural')==Counter({s:audit['natural_per_patient'] for s in audit['eval_patients']}),'natural patient quota')
    pressure=[x for x in rows if x['panel']=='pressure'];check(Counter(x['GT'] for x in pressure)==Counter(audit['pressure_label_counts']),'pressure GT quota')
    check(max(Counter((x['sid'],x['GT']) for x in pressure).values())<=3,'pressure concentration')
    jf={j['request_id']:j for j in jobs}
    for j in jobs:
        x=sm[j['id']];check(j['body']['messages'][0]['content']==systems[j['arm']],'system freeze')
        check(json.loads(j['body']['messages'][1]['content'])==dict(proposition=x['claim'],reference=x['reference']),'no target edits or GT')
        check(j['body']['model']==MODEL and j['body']['max_tokens']==8192,'model budget');check(h(canonical(j['body']))==j['body_sha256'],'SHA')
    for al in lines(OUT/'logical_aliases.jsonl'):
        j=jf[al['request_id']];check(al['body_sha256']==j['body_sha256'],'alias SHA');check(systems[al['arm']]==j['body']['messages'][0]['content'],'same body sharing')
        receipt=ROOT/success[al['request_id']]['receipt_source'];info,labels=parse_arm(read(receipt)['transport'],sm[al['id']]['fallback_U2'])
        check(labels==pm[al['id']]['labels'][al['arm']],'reparse labels')
        check(info['raw_verdict']==pm[al['id']]['arms'][al['arm']]['raw_verdict'],'native raw kept')
    a=read(OUT/'analysis.json');ind=[]
    for panel in ('natural','pressure'):
        z=[x for x in rows if x['panel']==panel]
        for method,arms in a['panels'][panel]['full_metrics'].items():
            for arm,old in arms.items():
                value=independent_metric(z,arm,method)
                for k,v in value.items():check(abs(v-old[k])<1e-12 if isinstance(v,float) else v==old[k],f'independent {panel}/{method}/{arm}/{k}')
                ind.append(dict(panel=panel,method=method,arm=arm,**value))
    for jpath in (OUT/'registered_jobs').glob('*.json'):
        j=read(jpath)
        if j['phase'] in ('review','review_v2','checker_test'):
            payload=json.loads(j['body']['messages'][1]['content']);check('physician_label' not in payload and 'arm' not in payload,'label/arm blind review')
            check(set(payload['retained_ids']).isdisjoint(payload['deleted_ids']),'source sets')
    check(subprocess.check_output(['git','check-ignore',str(OUT/'probe.json')],cwd=ROOT,text=True).strip()!='','private data ignored')
    check(subprocess.check_output(['git','diff','HEAD','--','.gitignore'],cwd=ROOT)==b'','gitignore unchanged')
    check(not (OUT/'run.lock').exists(),'no live runner')
    result=dict(status='PASS',checks=checks,synthetic_tests=11,independent_arithmetic_rows=len(ind),independent_audit=False,created_utc=now(),analysis_sha256=sha(OUT/'analysis.json'))
    if (PUB/'selfcheck.json').exists():
        check(read(PUB/'selfcheck.json')['analysis_sha256']==result['analysis_sha256'],'replay analysis');print(canonical(dict(status='PASS',checks=checks,replay=True)))
    else:put(PUB/'independent_arithmetic.json',ind);put(PUB/'selfcheck.json',result);print(canonical(result))
if __name__=='__main__':main()
