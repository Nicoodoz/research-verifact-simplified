"""Posthoc objective audit only: no new fits, thresholds, or API requests."""
import math
from collections import Counter
import common079 as c

def stats(rows,arm,g,ref=None,counts=None):
    losses=[];correct=0;grad=0.;by={k:[] for k in c.c53.LABELS}
    for r in rows:
        v=c.c53.calibrated(r[arm], [g], 'G')
        if ref is not None:v=c.c53.prior_adjust(v,ref,counts)
        top=max(v.values());den=sum(math.exp(q-top) for q in v.values())
        loss=math.log(den)+top-v[r['GT']]
        losses.append(loss);by[r['GT']].append(loss)
        correct+=c.c53.decode_logits(v)==r['GT']
        grad+=math.exp(v['Supported']-top)/den-(r['GT']=='Supported')
    avg=sum(losses)/len(losses)
    return dict(n=len(rows),NLL=avg,objective_with_G_penalty=avg+.01*g*g,correct=correct,
                mean_G_gradient_without_penalty=grad/len(rows),
                per_class_NLL={k:sum(v)/len(v) for k,v in by.items() if v})

def main():
    model=c.read(c.OUT/'fitted_models.json');old=c.read(c.OUT/'old_postprocessing.json');ids=set(model['common_ids'])
    train=[dict(id=x['id'],GT=x['GT'],B=x['B']['parsed']['scores'],F4=x['F4']['parsed']['scores']) for x in c.lines(c.OUT/'calibration_predictions.jsonl') if x['id'] in ids]
    ev=[dict(id=x['id'],GT=x['GT'],B=x['arms']['TS']['scores'],F4=x['arms']['F4']['scores']) for x in c.lines(c.OUT/'predictions.jsonl') if x['arms']['TS']['valid'] and x['arms']['F4']['valid']]
    oldg=old['calibration_theta']['T-S']['G'][0];ref=model['reference_prior_counts'];result={}
    for scope,rows in [('train112',train),('eval340',ev)]:
        result[scope]={}
        for arm in ['B','F4']:
            newg=model['models'][arm]['fit']['theta'][0]
            result[scope][arm]={
                'raw_g0':stats(rows,arm,0),
                'old_G':stats(rows,arm,oldg),
                'new_G':stats(rows,arm,newg),
                'old_PriorG':stats(rows,arm,oldg,ref,old['calibration_counts']['T-S']),
                'new_PriorG':stats(rows,arm,newg,ref,model['calibration_counts'])}
    out=c.OUT/'objective_diagnosis_001';out.mkdir(exist_ok=False)
    c.put(out/'results.json',dict(type='posthoc descriptive objective audit',new_fits=0,new_API_calls=0,metrics=result,source_sha256={p:c.sha(c.OUT/p) for p in ['fitted_models.json','old_postprocessing.json','calibration_predictions.jsonl','predictions.jsonl']}))
    print(c.canon(result))

if __name__=='__main__':main()
