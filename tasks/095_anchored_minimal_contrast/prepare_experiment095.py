import re,copy,statistics
from collections import Counter
import common095 as c
import method095 as m
from prepare_baseline095 import make_job
PATTERN=r'\b(before|after|during|following|transferred|removed|resolved|remained|stable|stabiliz\w*|discharged|started|stopped|continued|underwent|because|due to|found|improved|worsened|planned|scheduled|increased|decreased|left|right)\b|\d'

def select(pool,meta,excluded,tag,natural,enriched):
    used=set(excluded);out=[]
    for pid in sorted(set(pool)-used,key=lambda x:c.h('095/'+tag+'/natural/'+x))[:natural]:out.append(dict(id=pid,panel='natural'));used.add(pid)
    counts=Counter();labels=['Supported','Not Supported','Not Addressed']
    for i in range(enriched):
        label=labels[i%3];available=[pid for pid,r in pool.items() if pid not in used and meta[pid]['GT']==label and re.search(PATTERN,r['text'],re.I)]
        pid=min(available,key=lambda x:(counts[meta[x]['sid']],c.h('095/'+tag+'/patient/'+str(meta[x]['sid'])),c.h('095/'+tag+'/mechanism/'+x)))
        out.append(dict(id=pid,panel='mechanism'));used.add(pid);counts[meta[pid]['sid']]+=1
    return out

def main():
    pool={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')};meta={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};excluded={r['id'] for r in c.lines(c.OUT/'diagnosis_sample.jsonl')}
    chosen=select(pool,meta,excluded,'screen',200,100);sample=[];inputs=[];jobs=[]
    for r in chosen:
        pid=r['id'];sample.append(dict(**r,**{k:meta[pid][k] for k in ['sid','author','GT','historical_role']},source=pool[pid]['source']))
        inputs.append(dict(id=pid,text=pool[pid]['text'],reference=pool[pid]['reference']))
        jobs.append(make_job(pid,'method','construct',m.builder(pool[pid])))
    pilot_ids=[r['id'] for r in chosen if r['panel']=='natural'][:10]+[r['id'] for r in chosen if r['panel']=='mechanism'][:6]
    c.putl(c.OUT/'screen_sample.jsonl',sample);c.putl(c.PRIVATE/'screen_inputs.jsonl',inputs);c.putl(c.PRIVATE/'construct_jobs.jsonl',jobs);c.putl(c.PRIVATE/'construct_pilot_jobs.jsonl',[j for j in jobs if j['id'] in pilot_ids])
    extension=select(pool,meta,excluded|{r['id'] for r in chosen},'extension',400,200)
    c.putl(c.OUT/'extension_registered_order.jsonl',[dict(**r,**{k:meta[r['id']][k] for k in ['sid','author','GT','historical_role']}) for r in extension])
    paths=[c.TASK/p for p in ['experiment_protocol.md','method095.py','prepare_experiment095.py']]+[c.OUT/'screen_sample.jsonl',c.OUT/'extension_registered_order.jsonl',c.PRIVATE/'screen_inputs.jsonl',c.PRIVATE/'construct_jobs.jsonl',c.PRIVATE/'construct_pilot_jobs.jsonl']
    c.put(c.OUT/'experiment_freeze.json',dict(utc=c.now(),N=300,pilot_ids=pilot_ids,panels={p:dict(N=sum(r['panel']==p for r in sample),patients=len({r['sid'] for r in sample if r['panel']==p}),GT=dict(Counter(r['GT'] for r in sample if r['panel']==p))) for p in ['natural','mechanism']},estimated_final_judge_busy_cny=900*.0263,estimated_auxiliary_busy_cny=8,method_cap_cny=45,normal_task_cap_cny=130,hard_cap_cny=150,prior_outcome_inspection=False,sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},pattern=PATTERN))
    print(c.read(c.OUT/'experiment_freeze.json')['panels'])
if __name__=='__main__':main()
