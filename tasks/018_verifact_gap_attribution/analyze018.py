"""Complete1251 claim accounting,002 metrics, observable bridge; no semantic claims."""
from collections import Counter
from pathlib import Path
import argparse
import common018 as c

def analyze(out):
    c.require(not out.exists(),'Analysis exists');c.check(c.OUT/'preparation_001')
    rows=c.jsonlines(c.OUT/'preparation_001/ledger.jsonl');cohort={r['proposition_id']:r for r in c.csvrows(c.OUT/'preparation_001/cohort.csv')}
    metrics={};pairs={};core=[];classes=[];strata=[];patterns=[];patients=[];bridge=[];sensitivity=[]
    for q in ('010','016','pooled'):
        rr=[r for r in rows if q=='pooled' or r['cohort']==q];systems=('O','C','V') if q=='010' else ('O','C','Q') if q=='016' else ('O','C')
        metrics[q]={};pairs[q]={}
        for author in ('llm','human'):
            own=[r for r in rr if r['author_type']==author];cc=[cohort[r['proposition_id']] for r in own]
            pp={s:[dict(proposition_id=r['proposition_id'],verdict=r[s]) for r in own] for s in systems}
            mm={s:c.evaluate(cc,p,iterations=1000,missing='error') for s,p in pp.items()};metrics[q][author]=mm
            comparisons=[('O','C')]+([('O','V'),('V','C')] if q=='010' else [('O','Q')] if q=='016' else [])
            pairs[q][author]={a+'_minus_'+b:c.paired_compare(cc,pp[b],pp[a],iterations=1000) for a,b in comparisons}
            for s,m in mm.items():
                core.append(dict(cohort=q,author=author,system=s,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc'],
                    false_S=m['per_class']['Supported']['fp'],GT_S=sum(r['human_gt']=='Supported' for r in own),predicted_S=m['per_class']['Supported']['predicted']))
                for label,v in m['per_class'].items():classes.append(dict(cohort=q,author=author,system=s,label=label,**v))
            if q=='010':
                correct={s:sum(r[s]==r['human_gt'] for r in own) for s in systems}
                bridge.append(dict(author=author,n=len(own),O_minus_C=correct['O']-correct['C'],O_minus_V=correct['O']-correct['V'],V_minus_C=correct['V']-correct['C'],
                    O_only=sum(r['bucket']=='O_only' for r in own),O_only_V_correct=sum(r['bucket']=='O_only' and r['V']==r['human_gt'] for r in own),
                    O_only_V_wrong=sum(r['bucket']=='O_only' and r['V']!=r['human_gt'] for r in own),
                    C_only=sum(r['bucket']=='C_only' for r in own),C_only_V_correct=sum(r['bucket']=='C_only' and r['V']==r['human_gt'] for r in own),
                    C_only_V_wrong=sum(r['bucket']=='C_only' and r['V']!=r['human_gt'] for r in own)))
                for pat,count in sorted(Counter(r['correctness_pattern'] for r in own).items()):patterns.append(dict(author=author,pattern_OVC=pat,n=count))
            if q=='016':
                for label in ['ALL']+list(c.LABELS):
                    sub=[r for r in own if label=='ALL' or r['human_gt']==label]
                    sensitivity.append(dict(author=author,human_gt=label,n=len(sub),**{b:sum(c.bucket(r['O'],r['Q'],r['human_gt'])==b for r in sub) for b in c.BUCKETS}))
        dimensions=[(),('author_type',),('human_gt',),('subject_id',),('author_type','human_gt'),('subject_id','author_type')]
        for keys in dimensions:
            for vals in sorted({tuple(r[k] for k in keys) for r in rr}):
                own=[r for r in rr if tuple(r[k] for k in keys)==vals]
                counts={b:sum(r['bucket']==b for r in own) for b in c.BUCKETS}
                strata.append(dict(cohort=q,dimension='+'.join(keys) or 'ALL',value='|'.join(vals) or 'ALL',n=len(own),**counts,net_O_minus_C=counts['O_only']-counts['C_only']))
        if q!='pooled':
            for sid in sorted({r['subject_id'] for r in rr}):
                for author in ('llm','human'):
                    own=[r for r in rr if r['subject_id']==sid and r['author_type']==author]
                    for s in systems:
                        m=c.evaluate([cohort[r['proposition_id']] for r in own],[dict(proposition_id=r['proposition_id'],verdict=r[s]) for r in own],profile='none')
                        patients.append(dict(cohort=q,subject_id=sid,author=author,system=s,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc'],false_S=m['per_class']['Supported']['fp']))
    out.mkdir(parents=True)
    for name,data in [('metrics',metrics),('paired',pairs)]:c.write_json(out/(name+'.json'),data)
    for name,data in [('core_results',core),('classes',classes),('strata',strata),('bridge010',bridge),('patterns010',patterns),('patients',patients),('Qwen_sensitivity',sensitivity)]:c.write_csv(out/(name+'.csv'),data)
    total=[r for r in strata if r['dimension']=='ALL']
    c.write_json(out/'summary.json',dict(claims=len(rows),cohorts=total,bridge010=bridge,new_API_calls=0,cost_cny=0,semantic_attribution_not_inferred_from_labels=True))
    c.seal(out,[c.OUT/'preparation_001/manifest.json'],[Path(__file__),c.TASK/'common018.py'])
    print(c.canonical(c.read(out/'summary.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'analysis_001');analyze(p.parse_args().output)
