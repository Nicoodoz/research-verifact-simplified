"""Locked raw/final paired evaluation; no inference or parameter fitting."""
import json,sys
from collections import Counter
import common093 as c
import api093
sys.path.insert(0,str(c.ROOT/'tasks/090_demo_constructor_repair_validation'))
from analyze090 import parse_arm
sys.path.insert(0,str(c.ROOT/'tasks/092_task_adapted_verifier'))
from analyze092 import paired,table
ARMS=['B','F','A'];METHODS=['raw','U0','U2','PriorG']
def view(rows,method):
    return [dict(id=r['id'],sid=r['sid'],GT=r['GT'],predictions={'Original':r['Original'],**{a:r['labels'][a][method] for a in ARMS}},probabilities={}) for r in rows]
def score(rows,method):return table(view(rows,method),['Original']+ARMS) if rows else None
def compare(rows,b,a,method):return paired(view(rows,method),b,a) if rows else None
def main():
    jobs=api093.load_jobs();attempts,success,_=api093.state()
    assert all(j['request_id'] in success for j in jobs),'complete frozen requests first'
    old={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
    sample=c.lines(c.OUT/'sample.jsonl');rows={r['id']:dict(r,Original=old[r['id']]['original'],arms={},labels={}) for r in sample}
    info={}
    for job in jobs:
        rec=success[job['request_id']];tr=c.read(c.ROOT/rec['receipt_path'])['transport'];parsed,labels=parse_arm(tr,None)
        parsed['core_invalid_no_imputation']=parsed.pop('fallback_used')
        parsed['raw_invalid_no_imputation']=parsed.pop('raw_fallback_used')
        info[job['request_id']]=(parsed,labels,rec)
    for alias in c.lines(c.OUT/'logical_aliases.jsonl'):
        parsed,labels,rec=info[alias['request_id']];row=rows[alias['id']]
        row['arms'][alias['arm']]={**parsed,'request_id':alias['request_id'],'body_sha256':alias['body_sha256'],'receipt_sha256':c.sha(c.ROOT/rec['receipt_path'])}
        row['labels'][alias['arm']]=labels
        assert row['GT']==old[row['id']]['GT'],'original physician GT drift'
    rows=list(rows.values());c.putl(c.OUT/'predictions_public.jsonl',rows)
    panels={};transitions=[];pairs=[('B','A'),('B','F'),('F','A')]
    for panel in ['natural','pressure']:
        full=[r for r in rows if r['panel']==panel]
        core=[r for r in full if all(r['arms'][a]['valid'] for a in ARMS)]
        raw=[r for r in full if all(r['arms'][a]['raw_valid'] for a in ARMS)]
        changed=[r for r in core if r['A_added']>0]
        d=dict(N=len(full),patients=len({r['sid'] for r in full}),GT=dict(Counter(r['GT'] for r in full)),common_core_N=len(core),common_raw_N=len(raw),
          full_status={a:dict(core_invalid=sum(not r['arms'][a]['valid'] for r in full),raw_invalid=sum(not r['arms'][a]['raw_valid'] for r in full),known_final_correct=sum(r['labels'][a]['PriorG']==r['GT'] for r in full),conservative_full_N_PA=sum(r['labels'][a]['PriorG']==r['GT'] for r in full)/len(full)) for a in ARMS},
          common_core_metrics={m:score(core,m) for m in METHODS},native_raw_metrics=score(raw,'raw'),
          comparisons={m:{a+'-'+b:compare(raw if m=='raw' else core,b,a,m) for b,a in pairs} for m in ['raw','PriorG']},
          operated_core_N=len(changed),operated_GT=dict(Counter(r['GT'] for r in changed)),operated_metrics=score(changed,'PriorG'),
          core_excluded_ids=[r['id'] for r in full if r not in core],raw_excluded_ids=[r['id'] for r in full if r not in raw])
        panels[panel]=d
        for b,a in pairs:
            for r in full:
                vb,va=r['arms'][b]['valid'],r['arms'][a]['valid']
                br,ar=r['arms'][b]['raw_verdict'],r['arms'][a]['raw_verdict'];bf,af=r['labels'][b]['PriorG'],r['labels'][a]['PriorG'];gt=r['GT']
                transitions.append(dict(id=r['id'],sid=r['sid'],panel=panel,GT=gt,comparison=a+'-'+b,both_valid=vb and va,base_raw=br,new_raw=ar,base_final=bf,new_final=af,raw_rescue=(br!=gt and ar==gt) if br and ar else None,raw_harm=(br==gt and ar!=gt) if br and ar else None,final_rescue=(bf!=gt and af==gt) if vb and va else None,final_harm=(bf==gt and af!=gt) if vb and va else None,A_added=r['A_added']))
    costs=dict(task_cap_cny=20,attempts=len(attempts),HTTP200=len(success),physical_main=len(jobs)-1,retries=len(attempts)-len(success),original_or_reserved_cny=sum(r['cost_or_reserved_cny'] for r in attempts),preflight_cny=sum(r['cost_or_reserved_cny'] for r in attempts if r['phase']=='preflight'),new_embedding_reranker_auxiliary_calls=0,cloud_GPU_rented=False,logical_panels={})
    for panel in ['natural','pressure']:
        rr=[r for r in rows if r['panel']==panel];costs['logical_panels'][panel]={}
        for arm in ARMS:
            us=[r['arms'][arm]['usage'] for r in rr];elapsed=[r['arms'][arm]['elapsed_seconds'] for r in rr]
            costs['logical_panels'][panel][arm]=dict(N=len(rr),prompt_tokens=sum(u['prompt_tokens'] for u in us),completion_tokens=sum(u['completion_tokens'] for u in us),undiscounted_cny=sum((u['prompt_tokens']*3+u['completion_tokens']*9)/1e6 for u in us),mean_elapsed_seconds=sum(elapsed)/len(elapsed))
    assert costs['original_or_reserved_cny']<=20
    costs['logical_cost_note']='Same-body aliases describe deployment cost; sum physical receipts only for actual task spend. Existing shared retrieval cost not newly incurred, not claimed free at deployment.'
    c.put(c.OUT/'analysis.json',dict(panels=panels,primary='natural A-B PriorG, three-arm common core; full-N invalid coverage separately',no_imputed_labels=True,bootstrap='1000 patient clusters, fixed predictions; exploratory, zero crossing not equivalence'))
    c.put(c.OUT/'cost_ledger.json',costs);c.putl(c.OUT/'attempt_ledger.jsonl',attempts);c.putl(c.OUT/'transitions.jsonl',transitions)
    representatives=[]
    for panel in ['natural','pressure']:
        for kind in ['final_rescue','final_harm','raw_rescue','raw_harm']:
            rr=[r for r in transitions if r['panel']==panel and r['comparison']=='A-B' and r[kind]]
            if rr:representatives.append(dict(selected_for=kind,**min(rr,key=lambda r:c.h('093/case/'+r['id']))))
    c.putl(c.OUT/'representative_cases.jsonl',representatives)
    for p,d in panels.items():print(p,'core',d['common_core_N'],{a:(v['correct'],v['MCC'],v['false_S']) for a,v in d['common_core_metrics']['PriorG'].items()},flush=True)
    print('API cost',costs['original_or_reserved_cny'],flush=True)
if __name__=='__main__':main()
